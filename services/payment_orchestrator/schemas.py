import base64
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, PositiveInt, constr

from models import PaymentStatus


class TokenizeRequest(BaseModel):
    pan: constr(min_length=12, max_length=19)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2024, le=2100)
    cvc: constr(min_length=3, max_length=4)


class TokenizeResponse(BaseModel):
    token: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    mask: str
    owner: str


class ChargeRequest(BaseModel):
    token: str
    amount: PositiveInt
    currency: constr(min_length=3, max_length=16) = "VND"
    exp_month: Optional[int] = Field(default=None, ge=1, le=12)
    exp_year: Optional[int] = Field(default=None, ge=2024, le=2100)
    cvc: Optional[str] = Field(default=None, min_length=3, max_length=4)


class ChargeResponse(BaseModel):
    id: str
    status: str
    amount: int
    currency: str
    last4: str
    receipt: Optional[str]
    provider: str
    owner: str


class SignRequest(BaseModel):
    message: str


class SignResponse(BaseModel):
    signature: str

    @staticmethod
    def from_bytes(raw: bytes) -> "SignResponse":
        return SignResponse(signature=base64.b64encode(raw).decode("ascii"))


class PublicKeyResponse(BaseModel):
    public_key: str


class PaymentRequest(BaseModel):
    order_id: uuid.UUID
    payment_token: str


class PaymentResponse(BaseModel):
    status: PaymentStatus
    signed_receipt: str
    receipt: dict


class FraudRequest(BaseModel):
    amount: int
    user_ip: Optional[str] = None
    device_id: Optional[str] = None


class FraudDecision(BaseModel):
    score: int
    action: constr(to_upper=True)


class ReceiptEnvelope(BaseModel):
    order_id: uuid.UUID
    amount: int
    currency: str
    timestamp: datetime
    status: PaymentStatus
    provider: str = "mock"

    def to_serialisable(self) -> dict:
        return {
            "order_id": str(self.order_id),
            "amount": self.amount,
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "provider": self.provider,
        }
