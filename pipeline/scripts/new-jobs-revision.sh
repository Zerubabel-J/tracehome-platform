#!/usr/bin/env bash
# Register a new revision of the tracehome-jobs task definition that uses a new image, copying
# everything else (roles, secrets, logging) from the current revision. Prints the new ARN.
# Usage: new-jobs-revision.sh <image-uri>
set -euo pipefail
read -r -a aws_args <<<"${AWS_ARGS:-}"
image="${1:?Usage: new-jobs-revision.sh <image-uri>}"

current=$(aws ecs describe-task-definition "${aws_args[@]}" --task-definition tracehome-jobs \
  --query taskDefinition --output json)
next=$(jq --arg image "$image" '
  .containerDefinitions[0].image = $image
  | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities,
        .registeredAt, .registeredBy, .deregisteredAt)' <<<"$current")
file=$(mktemp)
echo "$next" >"$file"
aws ecs register-task-definition "${aws_args[@]}" --cli-input-json "file://$file" \
  --query taskDefinition.taskDefinitionArn --output text
rm -f "$file"
