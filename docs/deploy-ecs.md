# Deploying TraceHome to ECS on Fargate (development build)

This runbook takes the app from the laptop to ECS. There is no Terraform (decision 81): we
create resources in the console or with the AWS CLI, and this file records every step.

**Rules for every step**

- Every laptop command names the profile: `--profile tracehome`. The laptop's default profile
  points to a different account. The scripts in `deploy/scripts/` stop if the profile points
  to any account other than `EXPECTED_ACCOUNT_ID`.
- Region: `us-east-1`.
- Account IDs, ARNs, and endpoints go only in `deploy/env/dev.env` and `deploy/out/`, which git
  ignores. Never paste them into committed files.
- Budgets alerts at $10, $25, and $50 exist **before** step 1 (decision 38).
- Tear down the hourly parts after each session (see the last section).

```bash
cp deploy/env/dev.env.example deploy/env/dev.env   # fill it in as you go
aws sts get-caller-identity --profile tracehome     # must show the console account
```

## What runs where

| Part | Service | Notes |
|---|---|---|
| API | ECS service `tracehome-api`, task family `tracehome-api` | Behind the internal ALB, port 8000, health check `/api/health` |
| Worker | ECS service `tracehome-worker`, family `tracehome-worker` | Fargate Spot, no inbound traffic, pulls the upload results queue |
| Migrations and seed | One-off tasks, family `tracehome-jobs` | `alembic upgrade head`, or `python -m seed.seed` |
| Image | ECR repository `tracehome` | One image for all three; container name `app` everywhere |
| Database password | Secrets Manager, created by RDS | Injected as `DB_USER` and `DB_PASSWORD` at task start |
| Token signing key | Secrets Manager `tracehome/dev/token-signing-key` | Injected as `TOKEN_SIGNING_KEY` |
| Logs | CloudWatch Logs `/ecs/tracehome-dev` | Stream prefixes `api/`, `worker/`, `jobs/` |

## Step 1: Network (console)

Follow ARCHITECTURE.md, Network. Name everything `tracehome-dev-...`.

| Item | Setting |
|---|---|
| VPC | `10.20.0.0/16`, DNS hostnames and DNS resolution on |
| Subnets | Public `10.20.0.0/24`, `10.20.1.0/24`; app `10.20.10.0/24`, `10.20.11.0/24`; data `10.20.20.0/24`, `10.20.21.0/24` (zones a and b) |
| Internet gateway | Attached; public route table `0.0.0.0/0 → igw` |
| NAT instance | `t4g.nano` with the fck-nat AMI in public subnet a, **source/destination check off**; app route tables `0.0.0.0/0 → NAT instance` |
| S3 gateway endpoint | Added to both app route tables (free) |
| Data route table | **No** `0.0.0.0/0` route |
| Security groups | `tracehome-dev-alb`: in 80 from CloudFront's VPC origin. `tracehome-dev-app`: in 8000 from `tracehome-dev-alb` only. `tracehome-dev-worker`: no inbound. `tracehome-dev-db`: in 5432 from `-app` and `-worker` only |
| Data NACL | Allow 5432 in from the two app subnets and replies out to them (ports 1024–65535) |

The NAT instance must be running before any task starts: tasks need it to reach ECR's API,
Secrets Manager, CloudWatch Logs, and SQS. With it stopped, tasks fail with
`ResourceInitializationError`.

## Step 2: RDS (console)

PostgreSQL 16, `db.t4g.micro`, 20 GB gp3, **single AZ**, data subnets only (a DB subnet group with
both data subnets), security group `tracehome-dev-db`, no public access, initial database name
`tracehome`, backups 7 days. Credentials: **Managed in AWS Secrets Manager**. RDS creates the
secret (`rds!db-...`) and no person ever sees the password.

Copy into `dev.env`: `DB_HOST` (the endpoint address) and `DB_SECRET_ARN` (the secret's full ARN).

RDS for PostgreSQL 15+ requires TLS, so the task definitions set `DB_SSLMODE=require`.

## Step 3: Secrets, buckets, and queues (CLI)

```bash
# Token signing key: a long random value, never seen by anyone, never in a file.
aws secretsmanager create-secret --profile tracehome --region us-east-1 \
  --name tracehome/dev/token-signing-key \
  --secret-string "$(openssl rand -base64 48)" \
  --query ARN --output text            # put this in dev.env as TOKEN_SECRET_ARN

# Buckets (names must be globally unique; choose yours and put them in dev.env).
for b in "$INCOMING_BUCKET" "$PHOTOS_BUCKET" "$WEB_BUCKET"; do
  aws s3api create-bucket --profile tracehome --region us-east-1 --bucket "$b"
  aws s3api put-public-access-block --profile tracehome --bucket "$b" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
done
# Versioning on the incoming bucket: a scan result belongs to one file version (decision 80).
aws s3api put-bucket-versioning --profile tracehome --bucket "$INCOMING_BUCKET" \
  --versioning-configuration Status=Enabled

# Upload results queue and its dead-letter queue (decision 53)
aws sqs create-queue --profile tracehome --region us-east-1 --queue-name upload-results-dlq \
  --attributes MessageRetentionPeriod=1209600
deploy/scripts/render.sh                  # renders deploy/out/ from the templates
aws sqs create-queue --profile tracehome --region us-east-1 --queue-name upload-results \
  --attributes file://deploy/out/sqs/upload-results.json
aws s3api put-bucket-lifecycle-configuration --profile tracehome --bucket "$INCOMING_BUCKET" \
  --lifecycle-configuration file://deploy/out/s3/incoming-lifecycle.json
```

(Run `set -a; source deploy/env/dev.env; set +a` first so the shell knows the bucket names.)

**Your console-built photo pipeline:** rebuild it against these names in phase 7 rather than
importing it; see the plan.

## Step 4: IAM roles (CLI)

```bash
deploy/scripts/render.sh
for role in ecs-execution api-task worker-task jobs-task; do
  aws iam create-role --profile tracehome --role-name "tracehome-dev-$role" \
    --assume-role-policy-document file://deploy/out/iam/ecs-tasks-trust.json
done
# Execution role: pull the image and write logs (AWS managed), plus read only our two secrets.
aws iam attach-role-policy --profile tracehome --role-name tracehome-dev-ecs-execution \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam put-role-policy --profile tracehome --role-name tracehome-dev-ecs-execution \
  --policy-name read-secrets --policy-document file://deploy/out/iam/execution-secrets.json
# Task roles: what the application itself may do.
aws iam put-role-policy --profile tracehome --role-name tracehome-dev-api-task \
  --policy-name app --policy-document file://deploy/out/iam/api-task.json
aws iam put-role-policy --profile tracehome --role-name tracehome-dev-worker-task \
  --policy-name app --policy-document file://deploy/out/iam/worker-task.json
aws iam put-role-policy --profile tracehome --role-name tracehome-dev-jobs-task \
  --policy-name app --policy-document file://deploy/out/iam/jobs-task.json
```

**Execution role versus task role:** ECS itself uses the *execution* role before the container
starts (pull the image, fetch secrets, create the log stream). The application uses the *task*
role while it runs (sign uploads, read the queue). The API's presigned upload links are signed
with the task role, so it needs `s3:PutObject` on `uploads/*` and nothing else in S3.

## Step 5: ECR, logs, cluster, first image (CLI)

```bash
aws ecr create-repository --profile tracehome --region us-east-1 --repository-name tracehome \
  --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
aws ecr put-lifecycle-policy --profile tracehome --region us-east-1 --repository-name tracehome \
  --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"keep the last 10 images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":10},"action":{"type":"expire"}}]}'
aws logs create-log-group --profile tracehome --region us-east-1 --log-group-name /ecs/tracehome-dev
aws logs put-retention-policy --profile tracehome --region us-east-1 \
  --log-group-name /ecs/tracehome-dev --retention-in-days 14
aws ecs create-cluster --profile tracehome --region us-east-1 --cluster-name tracehome-dev \
  --capacity-providers FARGATE FARGATE_SPOT

IMAGE_URI=$(deploy/scripts/push-image.sh | tail -1)   # builds --target runtime, tags with the commit
deploy/scripts/register-task-defs.sh "$IMAGE_URI"
```

## Step 6: Migrate and seed (one-off tasks)

```bash
deploy/scripts/run-job.sh migrate   # waits; fails loudly with the reason if the task fails
deploy/scripts/run-job.sh seed      # made-up data only (decision 12)
```

## Step 7: Internal ALB (console)

Application Load Balancer, **internal**, both app subnets, security group `tracehome-dev-alb`.
Listener HTTP 80 → target group `tracehome-dev-api` (type **IP**, port 8000, health check path
`/api/health`, healthy threshold 2, interval 15 s, deregistration delay 30 s).

HTTP, not HTTPS, between CloudFront's VPC origin and this internal ALB: an HTTPS listener needs a
certificate for a domain we own, and the domain is bought later (decision 50). The traffic stays
on AWS's private network. Target design: HTTPS.

## Step 8: ECS services (CLI)

```bash
set -a; source deploy/env/dev.env; set +a
NET="awsvpcConfiguration={subnets=[$APP_SUBNETS],securityGroups=[$APP_SECURITY_GROUP],assignPublicIp=DISABLED}"
TG_ARN=$(aws elbv2 describe-target-groups --profile tracehome --region us-east-1 \
  --names tracehome-dev-api --query 'TargetGroups[0].TargetGroupArn' --output text)

# API: 1 task. min 100% / max 200% means a deployment starts the new task first, so there is
# no downtime. The circuit breaker rolls back automatically if new tasks keep failing.
aws ecs create-service --profile tracehome --region us-east-1 --cluster tracehome-dev \
  --service-name tracehome-api --task-definition tracehome-api --desired-count 1 \
  --launch-type FARGATE --network-configuration "$NET" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=app,containerPort=8000" \
  --health-check-grace-period-seconds 30 \
  --deployment-configuration "minimumHealthyPercent=100,maximumPercent=200,deploymentCircuitBreaker={enable=true,rollback=true}" \
  --enable-execute-command

# Worker: 1 task on Fargate Spot (decision 37). Use the worker security group (no inbound).
aws ecs create-service --profile tracehome --region us-east-1 --cluster tracehome-dev \
  --service-name tracehome-worker --task-definition tracehome-worker --desired-count 1 \
  --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
  --network-configuration "awsvpcConfiguration={subnets=[$APP_SUBNETS],securityGroups=[<worker-sg-id>],assignPublicIp=DISABLED}" \
  --deployment-configuration "minimumHealthyPercent=0,maximumPercent=200,deploymentCircuitBreaker={enable=true,rollback=true}" \
  --enable-execute-command
```

**Check it from inside the VPC** (there is no public path yet):

```bash
TASK=$(aws ecs list-tasks --profile tracehome --region us-east-1 --cluster tracehome-dev \
  --service-name tracehome-api --query 'taskArns[0]' --output text)
aws ecs execute-command --profile tracehome --region us-east-1 --cluster tracehome-dev \
  --task "$TASK" --container app --interactive \
  --command "python -c \"import urllib.request;print(urllib.request.urlopen('http://<internal-alb-dns>/api/listings').read()[:200])\""
```

ECS Exec needs the Session Manager plugin on the laptop.

## Step 9: The pipeline (console)

CodeConnections → connect GitHub (the handshake is done once by hand in the console).
CodePipeline V2, trigger: push to `main`, excluding `docs/**` and `*.md`.

| Stage | Action | Details |
|---|---|---|
| Source | GitHub via CodeConnections | Output `SourceArtifact` |
| Build | CodeBuild `tracehome-build` | `pipeline/buildspec-build.yml`, privileged; output `BuildArtifact` |
| Migrate | CodeBuild `tracehome-migrate` | `pipeline/buildspec-migrate.yml`; inputs `SourceArtifact` (primary) and `BuildArtifact` |
| Deploy | Two Amazon ECS actions in parallel | Services `tracehome-api` and `tracehome-worker`, both with `imagedefinitions.json` from `BuildArtifact` |
| Website | CodeBuild `tracehome-frontend` | `pipeline/buildspec-frontend.yml` (after CloudFront exists, phase 6) |

CodeBuild role permissions, beyond logs: build: ECR push to `tracehome` and scan reads. Migrate:
`ecs:DescribeTaskDefinition`, `ecs:RegisterTaskDefinition`, `ecs:RunTask`, `ecs:DescribeTasks`,
and `iam:PassRole` on `tracehome-dev-ecs-execution` and `tracehome-dev-jobs-task`. Website:
`s3:PutObject` on the web bucket and `cloudfront:CreateInvalidation` on the distribution.

**How a failed deployment rolls back:** if new tasks keep failing (3 failed starts with one
desired task), the circuit breaker returns the service to the last good task definition, which
still points at the previous image (images are immutable and the last 10 are kept). The
database is not rolled back, which is why migrations are always backward-compatible.

## Step 10: CloudFront and the website (phase 6)

Distribution with three behaviors (decision 72): `/api/*` → VPC origin to the internal ALB
(policy CachingDisabled; origin request policy AllViewerExceptHostHeader, which forwards the
Authorization header); `/photos/*` → photos bucket via OAC; default → web bucket via OAC, with
`deploy/cloudfront/spa-rewrite.js` as a CloudFront Function on viewer request. Then:

```bash
deploy/scripts/render.sh    # after adding CLOUDFRONT_DOMAIN and DISTRIBUTION_ID to dev.env
aws s3api put-bucket-policy --profile tracehome --bucket "$PHOTOS_BUCKET" --policy file://deploy/out/s3/photos-bucket-policy.json
aws s3api put-bucket-policy --profile tracehome --bucket "$WEB_BUCKET" --policy file://deploy/out/s3/web-bucket-policy.json
aws s3api put-bucket-cors --profile tracehome --bucket "$INCOMING_BUCKET" --cors-configuration file://deploy/out/s3/incoming-cors.json
```

## End of every session: stop what costs money by the hour

```bash
aws ecs update-service --profile tracehome --region us-east-1 --cluster tracehome-dev --service tracehome-api --desired-count 0
aws ecs update-service --profile tracehome --region us-east-1 --cluster tracehome-dev --service tracehome-worker --desired-count 0
aws rds stop-db-instance --profile tracehome --region us-east-1 --db-instance-identifier <db-id>   # restarts by itself after 7 days
aws ec2 stop-instances --profile tracehome --region us-east-1 --instance-ids <nat-instance-id>
```

The ALB costs about $0.54 a day even with no tasks: delete it at the end of a working week, and
recreate it with step 7. Start a session in the reverse order: NAT instance, RDS (wait until
available), then the services back to `--desired-count 1`.
