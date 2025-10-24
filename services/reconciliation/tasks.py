import os

from celery import Celery

BROKER_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//")
BACKEND_URL = os.getenv("CELERY_BACKEND_URL", BROKER_URL)

celery_app = Celery(
    "reconciliation",
    broker=BROKER_URL,
    backend=BACKEND_URL,
)


@celery_app.task(name="reconciliation.process_settlement")
def process_settlement(order_id: str) -> str:
    return f"settlement_processed:{order_id}"
