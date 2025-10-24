from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    currency: str = "usd"


class PaymentResponse(BaseModel):
    order_id: str
    status: str


app = FastAPI()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/payments", response_model=PaymentResponse)
async def orchestrate_payment(payment: PaymentRequest) -> PaymentResponse:
    return PaymentResponse(order_id=payment.order_id, status="accepted")
