#!/usr/bin/env bash
# Register new revisions of the api, worker, and jobs task definitions for one image.
# Usage: deploy/scripts/register-task-defs.sh <image-uri>
source "$(dirname "$0")/lib.sh"
check_account
export IMAGE_URI="${1:?Usage: register-task-defs.sh <image-uri>}"

mkdir -p "$OUT_DIR/ecs"
for family in api worker jobs; do
  rendered="$OUT_DIR/ecs/$family.json"
  render "$DEPLOY_DIR/ecs/$family.json" >"$rendered"
  arn=$(aws ecs register-task-definition "${AWS_ARGS[@]}" --cli-input-json "file://$rendered" \
    --query taskDefinition.taskDefinitionArn --output text)
  echo "Registered $arn"
done
