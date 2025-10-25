from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, PositiveInt

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str = "ok"


class FraudScoreRequest(BaseModel):
    amount: PositiveInt
    user_ip: str | None = None
    device_id: str | None = None


class FraudScoreResponse(BaseModel):
    score: int
    action: str


app = FastAPI(title="Fraud Engine")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("[STARTUP] Fraud Engine initialized")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    logger.info("[HEALTH] Health check requested")
    return HealthResponse()


@app.post("/score", response_model=FraudScoreResponse)
async def score(payload: FraudScoreRequest) -> FraudScoreResponse:
    logger.info(f"[FRAUD_SCORE] Evaluating transaction: amount={payload.amount}, device_id={payload.device_id}")
    
    if payload.amount > 10_000_000:
        logger.warning(f"[FRAUD_SCORE] BLOCK: Amount {payload.amount} exceeds threshold")
        return FraudScoreResponse(score=95, action="BLOCK")
    
    logger.info(f"[FRAUD_SCORE] ALLOW: Amount {payload.amount} within acceptable range")
    return FraudScoreResponse(score=10, action="ALLOW")
