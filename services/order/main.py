import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import schemas
from database import get_session, init_db
from models import Order, OrderStatus

app = FastAPI(title="Order Service")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


async def require_user(
    x_user_id: Annotated[str | None, Header(alias="x-user-id", convert_underscores=False)] = None,
) -> str:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="x-user-id header required")
    return x_user_id


def _dump_items(items: list[schemas.OrderItem]) -> list[dict]:
    return [item.model_dump() for item in items]


def _load_items(payload: dict | list | None) -> list[schemas.OrderItem] | None:
    if payload is None:
        return None
    if isinstance(payload, list):
        return [schemas.OrderItem(**item) for item in payload]
    return None


@app.post("/orders", response_model=schemas.OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: schemas.OrderCreate,
    user_id: Annotated[str, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> schemas.OrderRead:
    db_order = Order(
        user_id=user_id,
        amount=order.amount,
        currency=order.currency.upper(),
        status=OrderStatus.CREATED,
        items=_dump_items(order.items),
        payment_token=order.payment_token,
        notes=order.notes,
    )
    session.add(db_order)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.refresh(db_order)
    return schemas.OrderRead(
        id=db_order.id,
        user_id=db_order.user_id,
        amount=db_order.amount,
        currency=db_order.currency,
        status=db_order.status,
        items=_load_items(db_order.items),
        payment_token=db_order.payment_token,
        notes=db_order.notes,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )


@app.get("/orders/{order_id}", response_model=schemas.OrderRead)
async def get_order(
    order_id: uuid.UUID,
    user_id: Annotated[str, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> schemas.OrderRead:
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    )
    db_order = result.scalar_one_or_none()
    if db_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    return schemas.OrderRead(
        id=db_order.id,
        user_id=db_order.user_id,
        amount=db_order.amount,
        currency=db_order.currency,
        status=db_order.status,
        items=_load_items(db_order.items),
        payment_token=db_order.payment_token,
        notes=db_order.notes,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )


@app.put("/orders/{order_id}/status", response_model=schemas.OrderRead)
async def update_order_status(
    order_id: uuid.UUID,
    payload: schemas.OrderUpdateStatus,
    user_id: Annotated[str, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> schemas.OrderRead:
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .values(status=payload.status)
        .returning(Order)
    )
    result = await session.execute(stmt)
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    await session.commit()
    db_order: Order = row[0]
    return schemas.OrderRead(
        id=db_order.id,
        user_id=db_order.user_id,
        amount=db_order.amount,
        currency=db_order.currency,
        status=db_order.status,
        items=_load_items(db_order.items),
        payment_token=db_order.payment_token,
        notes=db_order.notes,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "order"}
