"""Local stand-in for GuardDuty + the upload-checks Lambda function.

On AWS: GuardDuty scans the upload, EventBridge queues the scan result, and the Lambda function
decides, moves the file, and sends one message to the upload results queue. LocalStack has no
GuardDuty, so this script plays that role. Like the real function, it never touches the database:
it only moves files and sends the message. The worker does the rest.

Examples (run inside the worker container):
  python scripts/simulate_check_result.py                      # approve the newest upload
  python scripts/simulate_check_result.py --outcome flagged --reason "Phone number in photo"
  python scripts/simulate_check_result.py --outcome rejected --reason "Malware found"
  python scripts/simulate_check_result.py --duplicate          # send the result twice
  python scripts/simulate_check_result.py --malformed          # a broken message -> DLQ
  python scripts/simulate_check_result.py --show-queues
"""

import argparse
import json
import os
import sys

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
INCOMING = os.environ.get("INCOMING_BUCKET", "tracehome-incoming-local")
PHOTOS = os.environ.get("PHOTOS_BUCKET", "tracehome-photos-local")
QUEUE = os.environ.get("UPLOAD_RESULTS_QUEUE_NAME", "upload-results")

s3 = boto3.client("s3", region_name=REGION)
sqs = boto3.client("sqs", region_name=REGION)


def newest_upload() -> str:
    objects = s3.list_objects_v2(Bucket=INCOMING, Prefix="uploads/").get("Contents", [])
    if not objects:
        sys.exit("No uploads waiting. Upload a photo in the advertiser page first.")
    return max(objects, key=lambda o: o["LastModified"])["Key"]


def move(key: str, bucket: str, new_key: str) -> None:
    """S3 has no move: copy, then delete the original."""
    s3.copy_object(Bucket=bucket, Key=new_key, CopySource={"Bucket": INCOMING, "Key": key})
    if bucket == INCOMING:
        s3.delete_object(Bucket=INCOMING, Key=key)


def show_queues() -> None:
    for name in (QUEUE, f"{QUEUE}-dlq"):
        url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
        attrs = sqs.get_queue_attributes(
            QueueUrl=url,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )["Attributes"]
        print(
            f"{name}: {attrs['ApproximateNumberOfMessages']} waiting, "
            f"{attrs['ApproximateNumberOfMessagesNotVisible']} being processed"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--key", help="uploads/... key (default: the newest upload)")
    parser.add_argument("--outcome", choices=["approved", "flagged", "rejected"], default="approved")
    parser.add_argument("--reason", help="why it was flagged or rejected")
    parser.add_argument("--duplicate", action="store_true", help="send the same result twice")
    parser.add_argument("--malformed", action="store_true", help="send a message the worker rejects")
    parser.add_argument("--show-queues", action="store_true", help="count messages in both queues")
    args = parser.parse_args()

    queue_url = sqs.get_queue_url(QueueName=QUEUE)["QueueUrl"]
    if args.show_queues:
        show_queues()
        return
    if args.malformed:
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"type": "upload.checked"}))
        print("Sent a malformed message. The worker fails it 3 times, then SQS moves it to the DLQ.")
        return

    key = args.key or newest_upload()
    # Decision 80: the decision belongs to one exact version of the file.
    version = s3.head_object(Bucket=INCOMING, Key=key).get("VersionId")
    rest = key.removeprefix("uploads/")  # "<listing_id>/<file>"
    message = {
        "type": "upload.checked",
        "version": 1,
        "object_key": key,
        "object_version": version,
        "outcome": args.outcome,
        "reason": args.reason,
        "public_key": None,
    }
    if args.outcome == "approved":
        # The real function also re-encodes the photo, which strips GPS data.
        message["public_key"] = f"photos/{rest}"
        move(key, PHOTOS, message["public_key"])
    elif args.outcome == "flagged":
        move(key, INCOMING, f"held/{rest}")  # kept 30 days for a moderator (decision 75)
    else:
        move(key, INCOMING, f"quarantine/{rest}")  # never published (decision 77)

    for _ in range(2 if args.duplicate else 1):
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
    print(f"{args.outcome}: {key} -> sent {'2 copies' if args.duplicate else '1 message'}")


if __name__ == "__main__":
    main()
