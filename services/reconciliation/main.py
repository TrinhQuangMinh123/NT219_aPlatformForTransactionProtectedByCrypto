from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import pika
from sqlalchemy.exc import IntegrityError

from database import SessionLocal, init_db
from models import ReceiptRecord

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("RECONCILIATION_QUEUE", "reconciliation_queue")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


def store_receipt(payload: dict) -> None:
    receipt = payload.get("receipt")
    signature = payload.get("signature")
    if not isinstance(receipt, dict) or not signature:
        raise ValueError("payload missing receipt or signature")

    raw_order_id = receipt.get("order_id")
    order_id = str(raw_order_id) if raw_order_id not in (None, "") else None

    record = ReceiptRecord(
        order_id=order_id,
        psp_reference=receipt.get("psp_reference"),
        signature=signature,
        receipt=receipt,
        status=receipt.get("status"),
        processed_at=datetime.now(timezone.utc),
    )

    with SessionLocal() as session:
        session.add(record)
        try:
            session.commit()
            logger.info(f"[RECONCILIATION] Stored receipt for order {order_id}")
        except IntegrityError:
            session.rollback()
            logger.warning(f"[RECONCILIATION] Duplicate receipt (already stored): order {order_id}")
        except Exception as exc:
            session.rollback()
            logger.error(f"[RECONCILIATION] Failed to persist receipt: {exc}")
            raise


def main() -> None:
    logger.info("[RECONCILIATION] Starting reconciliation worker...")
    init_db()
    logger.info("[RECONCILIATION] Database initialized")
    
    params = pika.URLParameters(RABBITMQ_URL)
    while True:
        try:
            logger.info("[RECONCILIATION] Connecting to RabbitMQ...")
            with pika.BlockingConnection(params) as connection:
                channel = connection.channel()
                channel.queue_declare(queue=QUEUE_NAME, durable=False)
                logger.info(f"[RECONCILIATION] Connected to queue: {QUEUE_NAME}")

                def _on_message(_ch, _method, _properties, body: bytes) -> None:
                    try:
                        payload = json.loads(body.decode("utf-8"))
                    except json.JSONDecodeError:
                        logger.error("[RECONCILIATION] Received malformed message", exc_info=True)
                        return

                    try:
                        store_receipt(payload)
                    except Exception as exc:
                        logger.error(f"[RECONCILIATION] Failed to persist receipt: {exc}", exc_info=True)

                channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message, auto_ack=True)
                logger.info("[RECONCILIATION] Waiting for messages...")
                channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            logger.error(f"[RECONCILIATION] Connection failed: {exc}. Retrying in 5s...", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
