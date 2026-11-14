#!/usr/bin/env bash
# Run the backend tests the way CodeBuild does: build the test image and run it against a
# throwaway PostgreSQL 16 container. Needs only Docker, so it also runs on a laptop:
#   pipeline/scripts/ci-test.sh
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
run_id="tracehome-ci-$$"
network="$run_id-net"

cleanup() {
  docker rm -f "$run_id-db" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$network" >/dev/null
docker run -d --name "$run_id-db" --network "$network" --network-alias db \
  -e POSTGRES_USER=tracehome -e POSTGRES_PASSWORD=ci-only -e POSTGRES_DB=tracehome \
  public.ecr.aws/docker/library/postgres:16-alpine >/dev/null
for _ in $(seq 1 60); do
  # TCP check: the image's first-start init server listens on the socket only, then restarts.
  docker exec "$run_id-db" pg_isready -h 127.0.0.1 -U tracehome -d tracehome >/dev/null 2>&1 && break
  sleep 1
done

docker build --target test -t tracehome-backend:ci "$repo/backend"
docker run --rm --network "$network" \
  -e DB_HOST=db -e DB_USER=tracehome -e DB_PASSWORD=ci-only -e DB_NAME=tracehome \
  -e AWS_REGION=us-east-1 \
  tracehome-backend:ci
