# Architecture

This document explains how TraceHome works and why it's designed this way. Every choice
below is a proposal, so challenge it. If evidence changes a decision, update this file.

## What we're designing for

**Problem to validate:** people searching for a home in Addis Ababa rely on scattered listings and
brokers, and it's hard to tell which listings are genuine and current. Interview at least five
renters, buyers, owners, or brokers to test this.

| Quality | Target |
|---|---|
| API availability | 99.9% a month |
| Search speed | 95% of requests under 300 ms in the Region |
| Moderation speed | 95% of photos within 60 seconds |
| AZ failure | No committed data lost |
| Region failure | Under 2 hours to recover, up to 1 hour of data lost |
| Security | Encrypted in transit and at rest, with tenant isolation |
| Deployments | No user-visible downtime, automatic rollback |

**Capacity estimate:** 5,000 daily users making 20 requests each is about 1.2 requests a second on
average, and about 12 at peak. We'll load test to 100. The lesson is to size first: this load
doesn't justify microservices or production Kubernetes.

## System overview

```mermaid
flowchart TB
    subgraph clients["Clients and ecosystem"]
        web["Web app"]
        ai["AI clients through MCP"]
        auto["n8n, Make, Zapier"]
        crm["HubSpot, GoHighLevel"]
    end

    subgraph edge["Global edge, outside the VPC"]
        cf["Route 53, CloudFront, WAF"]
    end

    subgraph access["Access layer"]
        alb["ALB<br/>First-party traffic"]
        apigw["API Gateway<br/>Keys, quotas, throttling"]
        mcp["MCP service on ECS"]
    end

    subgraph core["Core on ECS Fargate"]
        api["API<br/>Modular monolith"]
        worker["Worker<br/>Outbox publisher"]
    end

    subgraph data["Data"]
        rds[("RDS PostgreSQL")]
        ddb[("DynamoDB")]
        s3[("S3")]
    end

    subgraph events["Event backbone"]
        bus["EventBridge"]
        queues["SQS and dead-letter queues"]
        fns["Lambda functions"]
    end

    rek["Rekognition"]
    ops["CloudWatch, CloudTrail, GuardDuty, Config"]

    web --> cf
    cf --> alb --> api
    auto --> apigw
    crm --> apigw
    ai --> mcp --> apigw --> api
    api --> rds
    api --> ddb
    api --> s3
    worker --> rds
    worker --> bus --> queues --> fns
    s3 --> queues
    fns --> rek
    fns --> auto
    ops -. monitors .-> core
```

**Four contracts:** instead of building one integration per product, we build a REST API, webhooks,
an MCP server, and provider connectors. Once the API and webhooks exist, automation tools can reach
hundreds of other apps.

## Accounts and network

```mermaid
flowchart TB
    org["Management account: QedamawiLabs<br/>Billing and Identity Center, no workloads"]
    logs["log-archive<br/>Central audit logs"]
    dev["dev<br/>Daily building"]
    prod["prod<br/>Reviewed changes only"]
    org --> logs
    org --> dev
    org --> prod
    dev -- "audit logs" --> logs
    prod -- "audit logs" --> logs
```

```mermaid
flowchart TB
    internet(["Internet"])
    igw["Internet Gateway"]

    subgraph vpc["VPC 10.20.0.0/16"]
        subgraph aza["Availability Zone A"]
            pubA["Public: ALB, NAT<br/>10.20.0.0/24"]
            appA["Private app: ECS<br/>10.20.10.0/24"]
            dbA["Private data: RDS primary<br/>10.20.20.0/24"]
        end
        subgraph azb["Availability Zone B"]
            pubB["Public: ALB, NAT<br/>10.20.1.0/24"]
            appB["Private app: ECS<br/>10.20.11.0/24"]
            dbB["Private data: RDS standby<br/>10.20.21.0/24"]
        end
    end

    internet <--> igw
    igw <--> pubA
    igw <--> pubB
    pubA --> appA --> dbA
    pubB --> appB --> dbB
    dbA -- "synchronous replication" --> dbB
```

Each tier accepts traffic only from the tier before it: CloudFront to ALB, ALB to app, app to
database. S3 and DynamoDB gateway endpoints keep that traffic inside AWS.

| Setting | `dev` | `prod-ha` |
|---|---|---|
| ECS tasks | 1 small API task | 2 or more API tasks across AZs, plus worker |
| Database | Single-AZ | Multi-AZ |
| NAT Gateway | None | One per AZ |
| WAF | Off | On |
| Deployment | Rolling | Blue/green |

`dev` is deliberately less available so that it stays cheap. `prod-ha` is the design standard.

## Key flows

### Photo upload and moderation

Photos go straight to S3, so large files never pass through the API.

```mermaid
sequenceDiagram
    autonumber
    actor Owner
    participant API
    participant S3 as S3 uploads
    participant Q as SQS queue
    participant Fn as Moderation Lambda
    participant Rek as Rekognition
    participant DB as PostgreSQL

    Owner->>API: Request upload
    API->>DB: Save photo as PENDING
    API-->>Owner: Return short-lived presigned URL
    Owner->>S3: Upload directly
    S3->>Q: Send ObjectCreated event
    Q->>Fn: Deliver message
    Fn->>Rek: Check image
    Rek-->>Fn: Return labels and confidence
    alt Safe
        Fn->>DB: Mark APPROVED and publish resized image
    else Uncertain
        Fn->>DB: Mark NEEDS_REVIEW for an admin
    else Unsafe
        Fn->>DB: Mark REJECTED
    end
    Note over Q,Fn: Repeated failures go to a DLQ and raise an alarm
```

### Inquiry to CRM

The API saves the change and its event in one database transaction, so a crash can't lose the
event. This is the **transactional outbox** pattern.

```mermaid
sequenceDiagram
    autonumber
    actor Buyer
    participant AI as AI client
    participant MCP as MCP service
    participant API as Platform API
    participant DB as PostgreSQL outbox
    participant Bus as EventBridge and SQS
    participant Hook as Webhook Lambda
    participant N8N as n8n
    participant CRM

    Buyer->>AI: Find a 2-bedroom in Bole
    AI->>MCP: Call search_listings
    MCP->>API: Search with a scoped token
    API-->>AI: Return approved listings
    Buyer->>AI: Send an inquiry, then confirm
    AI->>MCP: Call create_inquiry with an idempotency key
    MCP->>API: Create inquiry
    API->>DB: Save inquiry and event together
    DB->>Bus: Worker publishes the event
    Bus->>Hook: Queue delivery
    Hook->>N8N: POST signed webhook
    alt Endpoint is healthy
        N8N->>CRM: Update contact and notify agent
    else Endpoint is down
        Hook->>Bus: Retry with backoff, then DLQ
        Note over Hook,Bus: Replay after recovery
    end
```

Delivery is at least once, so every consumer must be idempotent.

### Code to production

```mermaid
flowchart LR
    pr["Pull request"]
    checks["Tests, Terraform plan,<br/>image scan"]
    review["Peer review"]
    dev["Deploy to dev"]
    approve["Manual approval"]
    green["Start green tasks"]
    verify["Test green"]
    shift["Shift traffic"]
    back["Automatic rollback"]
    pr --> checks --> review --> dev --> approve --> green --> verify --> shift
    shift -. "alarm" .-> back
```

GitHub Actions uses OIDC for short-lived AWS access, so GitHub stores no AWS keys.

## Data

| Data | Store | Why |
|---|---|---|
| Tenants, users, listings, inquiries, outbox | RDS PostgreSQL | Relationships and transactions |
| Photos and web files | S3 | Durable and cheap |
| Delivery logs, idempotency, quotas | DynamoDB | Simple keys and fast conditional writes |
| Secrets | Secrets Manager | Encryption, audit, and rotation |

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ MEMBERSHIPS : has
    USERS ||--o{ MEMBERSHIPS : joins
    ORGANIZATIONS ||--o{ LISTINGS : manages
    LISTINGS ||--o{ PHOTOS : has
    LISTINGS ||--o{ INQUIRIES : receives
    ORGANIZATIONS ||--o{ API_CLIENTS : creates
    ORGANIZATIONS ||--o{ WEBHOOK_ENDPOINTS : registers

    ORGANIZATIONS {
        uuid id PK
        string name
    }
    USERS {
        uuid id PK
        string cognito_sub UK
    }
    MEMBERSHIPS {
        uuid organization_id PK
        uuid user_id PK
        string role
    }
    LISTINGS {
        uuid id PK
        uuid organization_id FK
        string purpose
        bigint price_etb
        string status
    }
    PHOTOS {
        uuid id PK
        uuid listing_id FK
        string status
    }
    INQUIRIES {
        uuid id PK
        uuid listing_id FK
        string status
    }
    API_CLIENTS {
        uuid id PK
        uuid organization_id FK
        string secret_hash
        string scopes
    }
    WEBHOOK_ENDPOINTS {
        uuid id PK
        uuid organization_id FK
        string url
        string event_types
    }
```

Add `organization_id` from the first migration, because retrofitting tenant isolation is risky.

## Decisions and tradeoffs

These are the answers you'll defend in the Q&A and in interviews.

| Decision | Why | Rejected | Tradeoff accepted | Revisit when |
|---|---|---|---|---|
| Separate AWS accounts | Strongest isolation; protects logs | One account | More setup | Team needs account automation |
| `us-east-1`, pending a day-2 latency test | Low cost and broad services | Europe, Cape Town | Slower dynamic requests from Ethiopia | Tests show a better Region |
| ECS Fargate for production | No servers or cluster fee, suits one team | EC2, EKS | Less portable, higher compute price | Many teams need a shared platform |
| Terraform, with CloudFormation bootstrap | Reviewable plans and portable skills | CloudFormation only | Learning curve; state needs protection | It threatens the deadline |
| RDS PostgreSQL | Transactions, relationships, and PostGIS | Aurora, DynamoDB | Writes scale vertically | Targets are missed |
| PostgreSQL search | Enough for this size, no sync work | OpenSearch | Basic relevance | Search targets are missed after tuning |
| Modular monolith | Simple to deploy for three people | Microservices | Modules deploy together | Metrics justify a split |
| Outbox, EventBridge, SQS | Doesn't lose events, separates failures | Direct calls, Kinesis | Eventual consistency, duplicates | Ordered streaming is needed |
| Presigned upload and async moderation | Scales, and protects the API | Upload through API | Photos aren't instantly visible | Pipeline needs more steps |
| Shared tables with Row-Level Security | Lowest cost, with two isolation layers | One database per tenant | Tenants share capacity | A customer needs stronger isolation |
| API Gateway for partners, ALB for our apps | Built-in quotas, and isolates noisy clients | One path for everyone | Two paths to operate | The paths can merge |
| SQS and Lambda for webhooks | Full control, and teaches the patterns | Direct sends, hosted service | We own retries and SSRF defenses | Upkeep exceeds a vendor's price |
| Thin MCP service over the public API | No special privileges | MCP in the core API, AgentCore Gateway | We track protocol changes | A managed gateway becomes better |
| Contracts before native connectors | Quick reach, unaffected by approvals | Native connector for each provider | Early setup isn't one-click | Tenants request a provider |
| Cognito, with app-level authorization | Avoids storing passwords | Custom auth | Migration is harder later | Sign-in needs change |
| Blue/green deployment | Test before traffic moves, and roll back fast | Canary, CodeDeploy | Doubles tasks briefly | Traffic supports canaries |
| Pilot light recovery | Low idle cost | Warm standby | Recovery takes human time | Business needs faster recovery |
| Start and stop environments | Keeps production design affordable | Weaken the design | Not always online | Real users arrive |

**Honest note:** for a real startup on this budget, a fully serverless design could cost much
less while idle. We chose containers, a VPC, and RDS partly because the learning goals require
them. Say that plainly in interviews.

## Security

| Layer | Controls |
|---|---|
| Identity | MFA, Identity Center, OIDC, one least-privilege role per service |
| Edge | CloudFront, Shield Standard, WAF rate limits |
| Network | Private subnets, chained security groups, no SSH |
| Application | Token validation, tenant and ownership checks, input validation |
| Data | KMS, TLS, Secrets Manager, private buckets |
| Detection | CloudTrail, GuardDuty, Config, Security Hub, image scanning |

| Threat | Defense |
|---|---|
| One tenant reads another's data | App checks, Row-Level Security, and automated tests |
| Harmful or fake listings | Moderation, human review, and audit logs |
| Webhook sent to an internal address (SSRF) | HTTPS only; block private and metadata addresses, including after DNS and redirects |
| Forged or replayed webhook | Signature over ID, timestamp, and body; reject stale timestamps |
| Prompt injection in listing text | Treat it as data; tools keep the same limits |
| AI client takes an unwanted action | Narrow scopes, confirmation, idempotency, and audit logs |
| Noisy API client | Per-client quotas |
| Leaked credentials | No long-lived keys, plus secret scanning and GuardDuty |

## Reliability tests

Run these only against your own system, and record the expected result, actual result, and recovery time.

| Test | Expected result |
|---|---|
| Stop an API task under load | ALB avoids it, and ECS replaces it |
| Force RDS failover under load | Brief write errors, then recovery |
| Deploy a bad image | Automatic rollback |
| Delete test data, then restore | Data returns; RTO and RPO are measured |
| Stop the n8n endpoint | Retries, DLQ, then successful replay |
| Make the moderation function fail | Photos wait; nothing is lost |
| Load test to 100 requests a second | ECS scales, and limits are documented |
| Flood the API with one client | That client is throttled, others are fine |
| Region failover, stretch goal | Restore in `us-west-2` and measure recovery |

**Scale in this order:** CloudFront cache, ECS tasks, query tuning, RDS Proxy, read replicas,
ElastiCache, a bigger database, and only then split a service. Each step adds complexity, so
wait for metrics to justify it.

## Lessons from other systems

Use it as a standard for layered presentation, not as a list of services. It's a video platform,
while our hard problems are trust, tenants, and integrations.

**Adopt:** clear layers, async pipelines with DLQs, and automated security response.

**Don't copy:** WAF and CloudFront in a subnet, NAT on an inbound path, the EKS control plane in
your subnet, or Aurora connected to an RDS standby.

**On our final diagram:** use official AWS icons, number the main path, keep edge services outside
the VPC, show two AZs, and mark components as Built, Tested, or Planned.

## Provider limits

Check current terms before building. These rules change often.

| Provider | Plan for |
|---|---|
| WhatsApp | Per-message pricing and limits on general-purpose AI assistants; build a property-specific bot |
| Facebook, Instagram | Business assets only, and possibly App Review |
| LinkedIn | Publishing can require partner approval |
| TikTok | Reported audit requirements |
| X | Paid API access |
| HubSpot, GoHighLevel | OAuth, scopes, and provider rate limits |

## Verify during the build

We haven't tested these in your account yet:

- CloudFront VPC origins, or a public ALB with restricted access
- API Gateway's private connection to the ALB, which may require an NLB
- CloudFront flat-rate plans and bundled WAF features
- Bedrock model access, Region, and pricing
- SES production access, because sandbox mode only sends to verified addresses
- Current MCP authorization requirements, and each AI client you claim to support
