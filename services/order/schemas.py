import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, PositiveInt, conint, constr

from .models import OrderStatus


class OrderItem(BaseModel):
    sku: constr(min_length=1)
    quantity: conint(gt=0) = 1
    price: PositiveInt


class OrderCreate(BaseModel):
    amount: PositiveInt
    currency: constr(min_length=3, max_length=16) = "VND"
    items: List[OrderItem] = Field(default_factory=list)
    payment_token: Optional[str] = None
    notes: Optional[str] = None


class OrderUpdateStatus(BaseModel):
    status: OrderStatus


class OrderRead(BaseModel):
    id: uuid.UUID
    user_id: str
    amount: int
    currency: str
    status: OrderStatus
    items: list[OrderItem] | None = None
    payment_token: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
