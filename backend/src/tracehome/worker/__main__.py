"""The worker loop: pull upload results from SQS and record them in PostgreSQL.

SQS never calls the worker. The worker asks for messages (long polling), handles each one, and
deletes it only after the database commit. If the worker crashes first, the message becomes
visible again after the visibility timeout and is retried.
"""

import json
import logging
import signal
import threading
import time
from pathlib import Path

import boto3

from tracehome.config import get_settings
from tracehome.db import new_session
from tracehome.worker.handlers import record_upload_result

HEARTBEAT = Path("/tmp/worker-heartbeat")
log = logging.getLogger("tracehome.worker")


def _queue_url(sqs, name: str) -> str:
    for attempt in range(1, 31):
        try:
            return sqs.get_queue_url(QueueName=name)["QueueUrl"]
        except Exception as error:  # the queue service may still be starting
            log.warning("Queue %s not reachable yet (%s), attempt %s", name, error, attempt)
            time.sleep(2)
    raise SystemExit(f"Queue {name} not found")


def handle_message(sqs, queue_url: str, message: dict) -> None:
    try:
        body = json.loads(message["Body"])
        with new_session() as session:
            status = record_upload_result(session, body)
            session.commit()
    except Exception:
        # Not deleted, so SQS retries it after the visibility timeout. After 3 receives the
        # queue's redrive policy moves it to the dead-letter queue (decision 53).
        log.exception("Could not record message %s; SQS will retry it", message["MessageId"])
        return
    # Delete only after the commit. A crash between commit and delete means one repeat, which
    # the handler ignores, because it is idempotent.
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    log.info("Recorded message %s: photo is now %s", message["MessageId"], status)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    queue_url = _queue_url(sqs, settings.upload_results_queue_name)

    # Fargate Spot gives a task 2 minutes' warning with SIGTERM. We finish the current batch and
    # stop; unfinished messages simply reappear for another worker.
    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    signal.signal(signal.SIGINT, lambda *_: stopping.set())

    log.info("Worker polling %s", settings.upload_results_queue_name)
    while not stopping.is_set():
        HEARTBEAT.touch()
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,  # long polling: wait up to 20 s for a message, cheaply
        )
        for message in response.get("Messages", []):
            handle_message(sqs, queue_url, message)
    log.info("Worker stopped")


if __name__ == "__main__":
    main()
