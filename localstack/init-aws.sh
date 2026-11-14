#!/bin/bash
# Creates the local stand-ins for the AWS resources the app talks to. LocalStack runs this when
# it is ready. On AWS the same resources are created in the console or with the AWS CLI
# (decision 81), and every real command there names the profile: --profile tracehome.
set -euo pipefail

INCOMING=tracehome-incoming-local
PHOTOS=tracehome-photos-local

# Incoming bucket: versioning on, so a scan result belongs to one exact file version (decision 80).
awslocal s3api create-bucket --bucket "$INCOMING"
awslocal s3api put-bucket-versioning --bucket "$INCOMING" \
  --versioning-configuration Status=Enabled
# The browser uploads straight to this bucket with a presigned POST, so it needs CORS.
awslocal s3api put-bucket-cors --bucket "$INCOMING" --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["http://localhost:8080", "http://localhost:5173"],
    "AllowedMethods": ["POST"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }]
}'

# Photos bucket. On AWS only CloudFront can read it (Origin Access Control). Locally, the "edge"
# container reads it on CloudFront's behalf.
awslocal s3api create-bucket --bucket "$PHOTOS"

# Upload results queue with its dead-letter queue: after 3 failed receives a message moves to
# the DLQ, kept 14 days (decision 53). The visibility timeout is short locally (10 s) so the DLQ
# demo is quick; on AWS it follows the worker's real processing time.
DLQ_URL=$(awslocal sqs create-queue --queue-name upload-results-dlq \
  --attributes MessageRetentionPeriod=1209600 --query QueueUrl --output text)
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)
cat > /tmp/upload-results-attributes.json <<EOF
{
  "VisibilityTimeout": "10",
  "RedrivePolicy": "{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"
}
EOF
awslocal sqs create-queue --queue-name upload-results \
  --attributes file:///tmp/upload-results-attributes.json

echo "TraceHome local AWS resources are ready."
