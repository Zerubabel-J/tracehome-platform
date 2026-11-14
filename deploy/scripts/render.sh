#!/usr/bin/env bash
# Render every template in deploy/ (task definitions, IAM policies, bucket and queue settings)
# into deploy/out/ with this account's values. Usage: deploy/scripts/render.sh [image-uri]
source "$(dirname "$0")/lib.sh"
check_account
export IMAGE_URI="${1:-$(ecr_uri):latest-not-set}"

rm -rf "$OUT_DIR" && mkdir -p "$OUT_DIR"
for dir in ecs iam s3 sqs; do
  mkdir -p "$OUT_DIR/$dir"
  for template in "$DEPLOY_DIR/$dir"/*.json; do
    render "$template" >"$OUT_DIR/$dir/$(basename "$template")"
    jq empty "$OUT_DIR/$dir/$(basename "$template")" # stop on invalid JSON
  done
done
echo "Rendered into $OUT_DIR (ignored by git). Image: $IMAGE_URI"
