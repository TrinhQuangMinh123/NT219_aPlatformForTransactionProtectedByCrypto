from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import pika
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal, init_db
from .models import ReceiptRecord

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
        except IntegrityError:
            session.rollback()
            # Already stored (duplicate signature) -> ignore
        except Exception:
            session.rollback()
            raise


def main() -> None:
    init_db()
    params = pika.URLParameters(RABBITMQ_URL)
    while True:
        try:
            with pika.BlockingConnection(params) as connection:
                channel = connection.channel()
                channel.queue_declare(queue=QUEUE_NAME, durable=False)

                def _on_message(_ch, _method, _properties, body: bytes) -> None:
                    try:
                        payload = json.loads(body.decode("utf-8"))
                    except json.JSONDecodeError:
                        print("[RECONCILIATION] Received malformed message", file=sys.stderr, flush=True)
                        return

                    try:
                        store_receipt(payload)
                        print(
                            f"[RECONCILIATION] Stored receipt for order {payload.get('receipt', {}).get('order_id')}",
                            flush=True,
                        )
                    except Exception as exc:  # noqa: BLE001
                        print(f"[RECONCILIATION] Failed to persist receipt: {exc}", file=sys.stderr, flush=True)

                channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message, auto_ack=True)
                print("[RECONCILIATION] Waiting for messages...", flush=True)
                channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            print(f"[RECONCILIATION] Connection failed: {exc}. Retrying in 5s...", file=sys.stderr, flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
