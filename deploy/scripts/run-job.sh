#!/usr/bin/env bash
# Run a one-off task from the jobs task definition and wait for it: migrate or seed.
# Usage: deploy/scripts/run-job.sh migrate|seed
source "$(dirname "$0")/lib.sh"
check_account
case "${1:-}" in
  migrate) command='["alembic","upgrade","head"]' ;;
  seed) command='["python","-m","seed.seed"]' ;;
  *) echo "Usage: run-job.sh migrate|seed" >&2; exit 1 ;;
esac
AWS_ARGS="${AWS_ARGS[*]}" CLUSTER="$CLUSTER" APP_SUBNETS="$APP_SUBNETS" \
  APP_SECURITY_GROUP="$APP_SECURITY_GROUP" TASK_DEFINITION=tracehome-jobs \
  "$REPO_DIR/pipeline/scripts/run-ecs-job.sh" "$command"
