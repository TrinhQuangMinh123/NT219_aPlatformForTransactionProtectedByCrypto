from __future__ import annotations

import json
import os
from contextlib import contextmanager

import pika

QUEUE_NAME = os.getenv("RECONCILIATION_QUEUE", "reconciliation_queue")


def _build_connection_parameters() -> pika.ConnectionParameters:
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    return pika.URLParameters(url)


@contextmanager
def _channel() -> pika.adapters.blocking_connection.BlockingChannel:
    connection = pika.BlockingConnection(_build_connection_parameters())
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=False)
        yield channel
    finally:
        connection.close()


def publish_receipt(payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    with _channel() as channel:
        channel.basic_publish(exchange="", routing_key=QUEUE_NAME, body=body)
