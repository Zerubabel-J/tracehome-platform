#!/usr/bin/env bash
# Build the production image and push it to ECR, tagged with the current commit.
# Used for the first, manual deployment (phase 4). After that, CodeBuild does this.
source "$(dirname "$0")/lib.sh"
check_account

tag=$(git -C "$REPO_DIR" rev-parse --short=12 HEAD)
if [[ -n "$(git -C "$REPO_DIR" status --porcelain -- backend)" ]]; then
  echo "backend/ has uncommitted changes; commit first so the tag matches the code." >&2
  exit 1
fi
uri="$(ecr_uri):$tag"

aws ecr get-login-password "${AWS_ARGS[@]}" |
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
# --target runtime: never the test image. linux/amd64: what the task definitions ask Fargate for.
docker build --platform linux/amd64 --target runtime -t "$uri" "$REPO_DIR/backend"
docker push "$uri"
echo "$uri"
