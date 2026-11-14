#!/usr/bin/env bash
# Run a one-off ECS task (a migration, or the seed) in the private app subnets, wait for it to
# stop, and exit with its result. Used by CodeBuild and by deploy/scripts/run-job.sh.
#
# Environment:
#   CLUSTER, TASK_DEFINITION (family or ARN), APP_SUBNETS (comma-separated), APP_SECURITY_GROUP
#   AWS_ARGS  optional, e.g. "--profile tracehome --region us-east-1" on a laptop. Empty in
#             CodeBuild, which uses the project's own IAM role.
# Argument: the container command as a JSON array, e.g. '["alembic","upgrade","head"]'
set -euo pipefail
read -r -a aws_args <<<"${AWS_ARGS:-}"
command_json="${1:?Usage: run-ecs-job.sh '<command as JSON array>'}"

network="awsvpcConfiguration={subnets=[${APP_SUBNETS:?}],securityGroups=[${APP_SECURITY_GROUP:?}],assignPublicIp=DISABLED}"
overrides=$(jq -cn --argjson cmd "$command_json" '{containerOverrides: [{name: "app", command: $cmd}]}')

task_arn=$(aws ecs run-task "${aws_args[@]}" \
  --cluster "${CLUSTER:?}" --launch-type FARGATE \
  --task-definition "${TASK_DEFINITION:?}" \
  --network-configuration "$network" \
  --overrides "$overrides" \
  --started-by one-off-job \
  --query 'tasks[0].taskArn' --output text)
if [[ "$task_arn" != arn:* ]]; then
  echo "run-task did not start a task: $task_arn" >&2
  exit 1
fi
echo "Started $task_arn with command $command_json; waiting for it to stop..."
aws ecs wait tasks-stopped "${aws_args[@]}" --cluster "$CLUSTER" --tasks "$task_arn"

details=$(aws ecs describe-tasks "${aws_args[@]}" --cluster "$CLUSTER" --tasks "$task_arn" \
  --query 'tasks[0].{exit: containers[0].exitCode, reason: stoppedReason}' --output json)
exit_code=$(jq -r '.exit' <<<"$details")
echo "Task stopped: $details"
if [[ "$exit_code" != "0" ]]; then
  # "null" means the container never started: often a missing secret permission, or no route
  # to ECR (is the NAT instance running?).
  echo "One-off job failed. Logs: CloudWatch log group /ecs/tracehome-dev, stream prefix jobs/" >&2
  exit 1
fi
echo "One-off job succeeded."
