#!/usr/bin/env bash
# Shared by the laptop deploy scripts. Loads deploy/env/dev.env, pins the AWS profile, and
# refuses to continue unless that profile points to the expected account.
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$DEPLOY_DIR/.." && pwd)"
ENV_FILE="$DEPLOY_DIR/env/dev.env"
OUT_DIR="$DEPLOY_DIR/out" # rendered files hold ARNs: ignored by git

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy dev.env.example to dev.env and fill it in." >&2
  exit 1
fi
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Every AWS command below uses these arguments: the profile is always named explicitly.
AWS_ARGS=(--profile "${AWS_PROFILE_NAME:?}" --region "${AWS_REGION:?}")

check_account() {
  local actual
  actual=$(aws sts get-caller-identity "${AWS_ARGS[@]}" --query Account --output text)
  if [[ -z "${EXPECTED_ACCOUNT_ID:-}" || "$actual" != "$EXPECTED_ACCOUNT_ID" ]]; then
    echo "Profile '$AWS_PROFILE_NAME' points to account $actual, not EXPECTED_ACCOUNT_ID. Stopping." >&2
    exit 1
  fi
  export ACCOUNT_ID="$actual"
}

# Fill ${VAR} placeholders in a template. Only the listed names are replaced, so anything else
# that looks like a variable is left alone.
TEMPLATE_VARS='${ACCOUNT_ID} ${AWS_REGION} ${IMAGE_URI} ${DB_HOST} ${DB_SECRET_ARN} ${TOKEN_SECRET_ARN} ${INCOMING_BUCKET} ${PHOTOS_BUCKET} ${WEB_BUCKET} ${UPLOAD_RESULTS_QUEUE} ${CLOUDFRONT_DOMAIN} ${DISTRIBUTION_ID}'
render() {
  envsubst "$TEMPLATE_VARS" <"$1"
}

ecr_uri() {
  echo "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
}
