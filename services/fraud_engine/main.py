from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class FraudCheckRequest(BaseModel):
    order_id: str
    amount: float


class FraudCheckResponse(BaseModel):
    order_id: str
    risk_score: float
    flagged: bool


app = FastAPI()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/fraud-check", response_model=FraudCheckResponse)
async def fraud_check(request: FraudCheckRequest) -> FraudCheckResponse:
    score = min(request.amount / 1000.0, 1.0)
    return FraudCheckResponse(order_id=request.order_id, risk_score=score, flagged=score > 0.7)
