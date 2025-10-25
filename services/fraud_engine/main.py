from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, PositiveInt


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


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/score", response_model=FraudScoreResponse)
async def score(payload: FraudScoreRequest) -> FraudScoreResponse:
    if payload.amount > 10_000_000:
        return FraudScoreResponse(score=95, action="BLOCK")
    return FraudScoreResponse(score=10, action="ALLOW")
