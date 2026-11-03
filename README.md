# TraceHome

A trusted property platform for selling and renting homes, starting in Addis Ababa and built on
AWS. Agencies publish verified listings, seekers find homes they can trust, and leads flow
reliably into the tools agencies already use.

**Team:** Getasil Desaleng, Seid Endris, Zerubabel Jember (Evangadi AWS, Group 9)
**Hackathon:** 1-14 November 2026, 8 hours a day
**Last plan update:** 2 November 2026
**Presentation:** Saturday, 14 November 2026, on Zoom

This file is the plan. [ARCHITECTURE.md](ARCHITECTURE.md) explains the design and the reasons
behind it. Those are the only two documents you need.

> **Status: planning.** Nothing is deployed yet. On presentation day, say "tested" only for
> things you actually tested, and "planned" for everything else.

## The goal

Close three months of AWS training with a system you can defend in any interview.

**Winning demo:**

1. An agent publishes a listing, and an admin verifies it.
2. A seeker browses for free, buys credits through a simulated payment, and spends one credit to
   unlock the advertiser's contact.
3. The unlock creates a lead, and a signed webhook runs an n8n workflow.
4. The CRM updates and the agent is notified.
5. After a reported viewing, the seeker reviews the listing and the advertiser separately.
6. We stop the n8n endpoint, show retries and the dead-letter queue, then replay the event
   after recovery.
7. We stop an API task and force a database failover under load, while showing the results.

## Scope

The rule: build a smaller system, understand it deeply, break it on purpose, and prove what happens.

### Must ship

**Core product**

- Advertiser accounts for owners, brokers, and agencies, with verification levels
- Agency members and roles
- Listings with admin verification, expiry, and reconfirmation
- Free browsing and search by sub-city, neighborhood, price, and type
- Photo upload to S3 with admin review
- Contact credits: simulated purchase, unlocks, and refunds for invalid listings
- Viewing reports and text reviews, with separate listing and advertiser scores
- Tenant isolation and safe credit spending, proven by automated tests

**Production cloud architecture**

- Separate `dev` and `prod`, built with Terraform
- VPC across two AZs, ECS Fargate, ALB, and RDS Multi-AZ
- S3, CloudFront, IAM, and Secrets Manager
- CI/CD with automatic rollback
- CloudWatch monitoring, alarms, and backups

**One deep distributed systems path**

- Transactional outbox, EventBridge, SQS, and a dead-letter queue
- Signed webhooks, with retries, delivery records, and replay
- n8n workflow into a CRM test account

**Proof**

- Load test, failure drills, and a database restore, with saved evidence

### Stretch goals, in order, only when the must-ship list is done

1. MCP server with one read tool, `search_listings`
2. Rekognition photo flagging
3. GuardDuty, Config, and WAF rule tuning
4. Blue/green deployment
5. EKS lab using the same container image
6. Region recovery drill

### Not in this hackathon

- Public partner API with API Gateway, and write tools for MCP
- In-app AI assistant, WhatsApp, and Telegram

- Real payment provider; credit purchases are simulated
- Commission on rentals or sales
- Voice feedback, planned for the first public release
- Map and radius search
- Official apps on the n8n, Make, or Zapier marketplaces
- Publishing to Facebook, Instagram, LinkedIn, X, or TikTok
- Real users' personal data; use made-up seed data

Provider approvals can take longer than two weeks, so nothing in the demo depends on them.

## How we work

**Equal responsibility:** everyone owns every layer at some point, and everyone writes code
and infrastructure. Zerubabel coordinates, but has the same technical duties as everyone else.

### Rotating tracks

| Days | Platform: accounts, network, Terraform | Delivery and data: Docker, CI/CD, database, events | Reliability and security: alarms, security, cost, testing |
|---|---|---|---|
| 2-5 | Getasil | Seid | Zerubabel |
| 6-9 | Seid | Zerubabel | Getasil |
| 10-13 | Zerubabel | Getasil | Seid |

Change this order on day 1 if it suits you better. If someone is newer to coding, pair them
on application work; don't remove them from it.

### Daily rhythm

| Hours | Activity |
|---|---|
| 0:00-0:15 | Stand-up: yesterday, today, blockers, money spent |
| 0:15-1:00 | Learn today's topic together and try it once in the console |
| 1:00-7:15 | Build in pairs, swapping who types |
| 7:15-8:00 | Teach-back, journal entry, and shut down AWS resources |

### Team rules

1. **No magic.** Don't merge anything you can't explain, including AI-generated code.
2. **Console once, then code.** Learn a service by hand in `dev`, delete it, then write Terraform.
3. **Break it on purpose.** Nothing is reliable until you've tested the failure.
4. **Review everything.** Each change needs one teammate's approval on a pull request.
5. **Shut down what you start.** The last person out confirms nothing is left running.
6. **Protect secrets.** No AWS keys, passwords, `.pem` files, or `.env` files in Git or chat.

## Schedule

Revised on 2 November. Day 1 produced the plan and the repository.

| Day | Date | Goal | Done when |
|---|---|---|---|
| 2 | Mon 2 Nov | Architecture review, defense exercise, secure root account, budgets, start interviews | Team agrees scope, and a budget alert arrives |
| 3 | Tue 3 Nov | Business rules for advertisers, credits, and reviews; `dev` and `prod` accounts (half a day at most); Terraform state; OIDC; schema; Docker | Rules, schema, and module boundaries are reviewed |
| 4 | Wed 4 Nov | **Buy the domain.** VPC, ECR, ECS, ALB, RDS in `dev`, tenant model | Health check responds over HTTPS |
| 5 | Thu 5 Nov | Cognito, advertiser accounts, members, listings, Row-Level Security | Cross-tenant tests pass |
| 6 | Fri 6 Nov | S3 upload, CloudFront, area search, web app | A signed-in agent posts a listing with photos |
| 7 | Sat 7 Nov | CI/CD with tests, image scanning, and circuit breaker rollback | A bad image rolls back automatically |
| 8 | Sun 8 Nov | Verification, reconfirmation, credit ledger, contact unlocks, outbox, EventBridge, SQS | Two simultaneous unlocks can't spend one credit twice, and a killed worker loses no events |
| 9 | Mon 9 Nov | Viewing reports, reviews, signed webhooks, SSRF defenses, retries, DLQ, n8n to CRM | An unlock updates the CRM, replay works, and only eligible seekers can review |
| 10 | Tue 10 Nov | Dashboards, alarms, WAF, CloudTrail, AWS Backup, runbooks | A teammate fixes an alarm using a runbook |
| 11 | Wed 11 Nov | Deploy `prod`: load test, task failure, RDS failover, restore | Expected and actual results are saved |
| 12 | Thu 12 Nov | **Feature freeze.** Fix findings, security review, stretch goals if ready | No critical issues remain |
| 13 | Fri 13 Nov | Final diagram, slides, backup video, two full rehearsals | Anyone can present any section |
| 14 | Sat 14 Nov | Start `prod` 4 hours early, test, present, shut down | Presented, and nothing is left running |

### Architecture before implementation

For each major feature: understand the problem, sketch it without AWS, compare two options, map it to
AWS, build it, break it, then update [ARCHITECTURE.md](ARCHITECTURE.md).

### Day 2 architecture review

Each member first answers these alone, without AI, then you compare answers:

1. Why ECS Fargate instead of EC2 or Lambda for TraceHome?
2. Why PostgreSQL, and what would justify adding DynamoDB?
3. How exactly does TraceHome keep operating when its primary AZ fails?

Then decide together: Who is the primary customer? Can a user belong to several agencies? What is
genuinely better than the current alternatives? What happens if a webhook consumer is down for six
hours? Which decisions would be expensive to reverse?

### If you fall behind

Drop stretch goals first. Then let admins handle credit refunds manually, postpone advertiser
replies to reviews, reduce to one `prod` load test, and use a single test CRM action.

Never cut budgets, tenant isolation, webhook signing, security basics, backups, or the demo path.

## Start here today

1. Run the Day 2 architecture review, and agree the scope, rotation, and budget.
2. Turn on MFA for the root user of QedamawiLabs.
3. Create budget alerts at $10, $20, and $25, and turn on Cost Anomaly Detection.
4. Create an admin user, and stop using root.
5. Set up a CLI profile with `aws configure --profile qedamawilabs`, or `aws configure sso` if you
   use Identity Center.
6. Run `aws sts get-caller-identity --profile qedamawilabs`, and confirm it shows the QedamawiLabs account ID.

**Warning:** Zerubabel's laptop has a default AWS CLI login for a different account. Always use the
correct profile, or you could deploy to the wrong account.

## Budget

AWS Credits showed $0 on 1 November, so every charge is real money. These are rough estimates that
leave out data transfer and some logging. **On day 2, rebuild them in the AWS Pricing Calculator**
using your actual Region, resource sizes, and running hours, then track real spending in Cost Explorer.

| Item | Estimate |
|---|---|
| `dev`: 120 hours at about $0.07 an hour | $8 |
| `prod`: 30 hours at about $0.25 an hour | $8 |
| Security services, keys, secrets, logs, DNS | $4 |
| Queues, events, and storage | $1 |
| **Must-ship total** | **$21** |
| Stretch goals | $6 |
| **Total with stretch goals** | **$27** |

**Decision needed today:** this leaves little margin, and one forgotten environment could use it up.
Each member adding $20 would make about $70.

The biggest cost risk is forgetting to shut something down. Left running all month, `prod` would cost
about $180. The domain is separate, at about $15 a year.

## Presentation plan

| Section | Content |
|---|---|
| Problem and users | What you learned from at least five renters, buyers, owners, or brokers |
| Architecture | One clear diagram, service choices, and rejected alternatives |
| Live demo | The winning demo above, with a backup video ready |
| Security, cost, scalability | Controls, actual spending, and load test results |
| Challenges and lessons | Real failures from your daily journals |
| Q&A | Anyone can answer on any layer |

## Course coverage

| Weeks | Built in this project | Study separately for SAA-C03 |
|---|---|---|
| 1-2 | Regions, AZs, Organizations, IAM | Directory Service, Control Tower |
| 3-4 | ALB, scaling, security groups | EC2 pricing, EBS, EFS, AMIs, placement groups |
| 5 | RDS Multi-AZ, Route 53 | Aurora, routing policies, ElastiCache |
| 6-7 | S3, CloudFront | Storage classes, Snow family, FSx, Storage Gateway, Global Accelerator |
| 8 | SQS, EventBridge, ECS | Lambda, Kinesis, Amazon MQ, EKS details |
| 9 | None required; Rekognition is a stretch goal | Athena, Redshift, OpenSearch, EMR, SageMaker |
| 10 | CloudWatch, CloudTrail, AWS Backup | Config, DynamoDB, DMS, migration tools |
| 11 | VPC, NAT, endpoints | Peering, Transit Gateway, VPN, Direct Connect |
| 12 | Encryption, Secrets Manager, CloudFormation | KMS details, GuardDuty, API Gateway, Beanstalk, Batch, Trusted Advisor |

Exam domains: Secure 30%, Resilient 26%, High-Performing 24%, Cost-Optimized 20%. Always study
from the current official exam guide.

## After the hackathon

Finish any stretch goals, then a public partner API, MCP write tools, Telegram and WhatsApp, a native
HubSpot or GoHighLevel connector, official automation apps, and social publishing. Each provider has its own approval and terms, so
check those first.
