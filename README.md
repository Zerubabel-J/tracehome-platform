# TraceHome

An API-first property platform for selling and renting homes, starting in Addis Ababa and
built on AWS. Web apps, partners, automation tools, CRMs, and AI assistants all connect
through secure, versioned contracts.

**Team:** Getasil Desaleng, Seid Endris, Zerubabel Jember (Evangadi AWS, Group 9)
**Hackathon:** 1-14 November 2026, 8 hours a day
**Presentation:** Saturday, 14 November 2026, on Zoom

This file is the plan. [ARCHITECTURE.md](ARCHITECTURE.md) explains the design and the reasons
behind it. Those are the only two documents you need.

> **Status: planning.** Nothing is deployed yet. On presentation day, say "tested" only for
> things you actually tested, and "planned" for everything else.

## The goal

Close three months of AWS training with a system you can defend in any interview.

**Winning demo:**

1. An AI client finds a home on the platform.
2. The user confirms an inquiry.
3. A signed webhook runs an n8n workflow.
4. The CRM updates and the agent is notified.
5. We stop the n8n endpoint, show retries and the dead-letter queue, then replay the event
   after recovery.

## Scope

### Must ship

- Agencies as isolated tenants, with sign-in and roles
- Listings, search, photo upload, and inquiries
- AI photo moderation with an admin review queue
- Public API with keys, scopes, and rate limits
- Signed webhooks with delivery logs and replay
- Read-first MCP server, with one confirmed write tool
- n8n workflow into a CRM test account
- Multi-AZ production environment, built entirely with Terraform
- Automated deployment with rollback
- Monitoring, alarms, security controls, and backups
- Load test and failure drills, with saved results

### Stretch goals, only if the must-ship list is done

- In-app AI assistant
- EKS lab using the same container image
- Region failover drill
- Telegram or WhatsApp notifications

### Not in this hackathon

- Real payments or property transactions
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

## 14-day schedule

| Day | Date | Goal | Done when |
|---|---|---|---|
| 1 | Sun 1 Nov | Kickoff: agree scope, budget, rotation; secure root account; set budgets; create repo | Budget alert email arrives |
| 2 | Mon 2 Nov | Organization, `dev`, `prod`, `log-archive`, Identity Center, Terraform state, GitHub OIDC | Everyone signs in without long-lived keys |
| 3 | Tue 3 Nov | VPC, security groups, app skeleton, tenants, Row-Level Security, Docker | Tenant isolation test passes locally |
| 4 | Wed 4 Nov | **Buy the domain.** ECR, ECS, ALB, RDS, Route 53, ACM | Health check responds over HTTPS |
| 5 | Thu 5 Nov | Cognito, listings, S3 uploads, CloudFront, web app | A signed-in user posts a listing with photos |
| 6 | Fri 6 Nov | CI/CD with tests, image scanning, and blue/green deployment | A bad image rolls back automatically |
| 7 | Sat 7 Nov | Moderation pipeline, outbox, EventBridge, SQS, dead-letter queues | A failed message reaches the DLQ and replays |
| 8 | Sun 8 Nov | Signed webhooks, delivery logs, SSRF protection, n8n to CRM | An inquiry updates the CRM |
| 9 | Mon 9 Nov | API Gateway, keys, quotas, MCP service; assistant if time allows | An AI client searches real listings |
| 10 | Tue 10 Nov | Dashboards, alarms, WAF, GuardDuty, CloudTrail, Config, AWS Backup | A teammate fixes an alarm using a runbook |
| 11 | Wed 11 Nov | Run `prod-ha`: load test, task failure, RDS failover, database restore | Results and screenshots are saved |
| 12 | Thu 12 Nov | **Feature freeze.** Fix test findings, security review, stretch goals | No critical issues remain |
| 13 | Fri 13 Nov | Final architecture diagram, slides, backup video, two full rehearsals | Anyone can present any section |
| 14 | Sat 14 Nov | Start `prod-ha` 4 hours early, test, present, shut down | Presented, and nothing is left running |

### If you fall behind

Cut in this order: stretch goals, map search, Config and Security Hub depth, blue/green
(use rolling with rollback), MCP write tool.

Never cut budgets, tenant isolation, webhook signing, security basics, backups, or the demo path.

## Start here today

1. Agree the scope, rotation, and budget as a team.
2. Turn on MFA for the root user of QedamawiLabs.
3. Create budget alerts at $10, $20, and $25, and turn on Cost Anomaly Detection.
4. Create an admin user, and stop using root.
5. Set up a CLI profile with `aws configure --profile qedamawilabs`, or `aws configure sso` if you
   use Identity Center.
6. Run `aws sts get-caller-identity --profile qedamawilabs`, and confirm it shows the QedamawiLabs account ID.

**Warning:** Zerubabel's laptop has a default AWS CLI login for a different account. Always use the
correct profile, or you could deploy to the wrong account.

## Budget

AWS Credits showed $0 on 1 November, so every charge is real money. Costs are estimates, so check
them in the AWS Pricing Calculator, and use Cost Explorer to track real spending.

| Item | Estimate |
|---|---|
| `dev`: 120 hours at about $0.07 an hour | $8 |
| `prod-ha`: 30 hours at about $0.25 an hour | $8 |
| Bedrock and Rekognition | $3 |
| Security services, keys, secrets, logs, DNS | $4 |
| API Gateway, MCP service, webhooks | $3 |
| **Must-ship total** | **$26** |
| Stretch: EKS lab and Region failover drill | $5 |
| **Total with stretch goals** | **$31** |

**Decision needed on day 1:** the must-ship plan fits within $30, but with very little margin.
Each member adding $20 would make about $70, which covers the stretch goals and mistakes.

Left running all month, `prod-ha` would cost about $180. So environments run only when you're
using them. The domain is separate, at about $15 a year.

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
| 8 | SQS, EventBridge, Lambda, ECS | Kinesis, Amazon MQ, EKS details |
| 9 | Rekognition | Athena, Redshift, OpenSearch, EMR, SageMaker |
| 10 | CloudWatch, CloudTrail, Config, Backup, DynamoDB | DMS, migration tools |
| 11 | VPC, NAT, endpoints | Peering, Transit Gateway, VPN, Direct Connect |
| 12 | KMS, Secrets Manager, GuardDuty, API Gateway, CloudFormation | Beanstalk, Batch, Trusted Advisor |

Exam domains: Secure 30%, Resilient 26%, High-Performing 24%, Cost-Optimized 20%. Always study
from the current official exam guide.

## After the hackathon

Finish any stretch goals, then Telegram and WhatsApp, a native HubSpot or GoHighLevel connector,
official automation apps, and social publishing. Each provider has its own approval and terms, so
check those first.
