#!/usr/bin/env bash
# Wait for ECR's scan of the new image, and fail the build on any CRITICAL finding.
# Usage: check-image-scan.sh <repository-name> <image-tag>
set -euo pipefail
read -r -a aws_args <<<"${AWS_ARGS:-}"
repo="${1:?}"
tag="${2:?}"

aws ecr wait image-scan-complete "${aws_args[@]}" --repository-name "$repo" --image-id "imageTag=$tag"
counts=$(aws ecr describe-image-scan-findings "${aws_args[@]}" --repository-name "$repo" \
  --image-id "imageTag=$tag" --query 'imageScanFindings.findingSeverityCounts' --output json)
echo "Scan findings by severity: $counts"
critical=$(jq -r '.CRITICAL // 0' <<<"${counts:-null}")
if [[ "$critical" != "0" ]]; then
  echo "Image has $critical CRITICAL vulnerabilities. Stopping before deployment." >&2
  exit 1
fi
