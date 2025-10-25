from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import messaging, schemas
from .database import get_session, init_db
from .hsm_service import decrypt_token, encrypt_token, get_public_key_der, initialize_keys_if_not_exist, sign_message
from .models import PaymentIntent, PaymentStatus, UsedToken
from .psp_client import PSPMock, build_psp

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8000")
FRAUD_ENGINE_URL = os.getenv("FRAUD_ENGINE_URL", "http://fraud_engine:8003")
PSP_PROVIDER = os.getenv("PSP_PROVIDER", "mock")

app = FastAPI(title="Payment Orchestrator")

_http_client: httpx.AsyncClient | None = None
_psp_client: PSPMock | None = None


def mask_pan(pan: str) -> str:
    return "".join("*" if i < len(pan) - 4 else pan[i] for i in range(len(pan)))


def card_brand(pan: str) -> str:
    if pan.startswith("4"):
        return "visa"
    if pan[:2] in {"51", "52", "53", "54", "55"}:
        return "mastercard"
    return "card"


async def require_user(
    x_user_id: Annotated[str | None, Header(alias="x-user-id", convert_underscores=False)] = None,
) -> str:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="x-user-id header required")
    return x_user_id


@app.on_event("startup")
async def on_startup() -> None:
    global _http_client, _psp_client
    initialize_keys_if_not_exist()
    await init_db()
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    _psp_client = build_psp()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _http_client
    if _http_client is not None:
        client, _http_client = _http_client, None
        await client.aclose()


def _http() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialised")
    return _http_client


def _psp() -> PSPMock:
    if _psp_client is None:
        raise RuntimeError("PSP client not initialised")
    return _psp_client


async def _psp_charge(**kwargs: object) -> dict:
    return await asyncio.to_thread(_psp().charge, **kwargs)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "provider": PSP_PROVIDER}


@app.post("/sign", response_model=schemas.SignResponse)
async def sign_endpoint(payload: schemas.SignRequest) -> schemas.SignResponse:
    signature = sign_message(payload.message)
    return schemas.SignResponse.from_bytes(signature)


@app.get("/public-key", response_model=schemas.PublicKeyResponse)
async def public_key() -> schemas.PublicKeyResponse:
    public_key_der = get_public_key_der()
    return schemas.PublicKeyResponse(public_key=base64.b64encode(public_key_der).decode("ascii"))


@app.get("/payment/health", tags=["health"])
async def payment_health_alias() -> dict[str, str]:
    return await health()


@app.get("/payment/public-key", response_model=schemas.PublicKeyResponse)
async def payment_public_key_alias() -> schemas.PublicKeyResponse:
    return await public_key()


@app.post("/payment/sign", response_model=schemas.SignResponse)
async def payment_sign_alias(payload: schemas.SignRequest) -> schemas.SignResponse:
    return await sign_endpoint(payload)


@app.post("/payment/tokenize", response_model=schemas.TokenizeResponse)
async def tokenize(
    payload: schemas.TokenizeRequest,
    user_id: Annotated[str, Depends(require_user)],
) -> schemas.TokenizeResponse:
    token = encrypt_token(payload.pan.encode("utf-8"))
    return schemas.TokenizeResponse(
        token=token,
        brand=card_brand(payload.pan),
        last4=payload.pan[-4:],
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        mask=mask_pan(payload.pan),
        owner=user_id,
    )


@app.post("/payment/charge", response_model=schemas.ChargeResponse)
async def charge(
    payload: schemas.ChargeRequest,
    user_id: Annotated[str, Depends(require_user)],
) -> schemas.ChargeResponse:
    try:
        pan = decrypt_token(payload.token).decode("utf-8")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = await _psp_charge(
        pan=pan,
        amount=payload.amount,
        currency=payload.currency,
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        cvc=payload.cvc,
    )
    return schemas.ChargeResponse(
        id=result["id"],
        status=result["status"],
        amount=result["amount"],
        currency=result["currency"],
        last4=result["last4"],
        receipt=result.get("receipt"),
        provider=PSP_PROVIDER,
        owner=user_id,
    )


async def _fetch_order(order_id: str, user_id: str) -> dict:
    response = await _http().get(
        f"{ORDER_SERVICE_URL}/orders/{order_id}",
        headers={"x-user-id": user_id},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    response.raise_for_status()
    return response.json()


async def _update_order_status(order_id: str, status_value: str, user_id: str) -> None:
    response = await _http().put(
        f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
        headers={"x-user-id": user_id},
        json={"status": status_value},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    response.raise_for_status()


async def _fraud_check(amount: int, user_id: str) -> schemas.FraudDecision:
    response = await _http().post(
        f"{FRAUD_ENGINE_URL}/score",
        json={"amount": amount, "user_ip": None, "device_id": user_id},
    )
    response.raise_for_status()
    payload = response.json()
    return schemas.FraudDecision(**payload)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/payments", response_model=schemas.PaymentResponse)
async def orchestrate_payment(
    payload: schemas.PaymentRequest,
    user_id: Annotated[str, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> schemas.PaymentResponse:
    order = await _fetch_order(str(payload.order_id), user_id)
    amount = order.get("amount")
    currency = order.get("currency", "VND")
    if not isinstance(amount, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order missing amount")

    fraud_decision = await _fraud_check(amount, user_id)
    if fraud_decision.action.upper() == "BLOCK":
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="transaction blocked by fraud engine")

    token_hash = _hash_token(payload.payment_token)
    existing = await session.execute(select(UsedToken).where(UsedToken.token_hash == token_hash))
    if existing.scalar_one_or_none():
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment token already used")

    try:
        pan = decrypt_token(payload.payment_token).decode("utf-8")
    except ValueError as exc:
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid payment token") from exc

    result = await _psp_charge(pan=pan, amount=amount, currency=currency)
    if result.get("status") != "succeeded":
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="psp charge failed")

    receipt = schemas.ReceiptEnvelope(
        order_id=payload.order_id,
        amount=amount,
        currency=currency,
        timestamp=datetime.now(timezone.utc),
        status=PaymentStatus.SUCCESS,
    )
    receipt_dict = receipt.to_serialisable() | {"psp_reference": result["id"], "last4": result["last4"]}
    signature_bytes = sign_message(json.dumps(receipt_dict, sort_keys=True))
    signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

    payment_intent = PaymentIntent(
        order_id=payload.order_id,
        amount=amount,
        currency=currency,
        status=PaymentStatus.SUCCESS,
        signed_receipt=signature_b64,
        receipt_payload=receipt_dict,
    )
    used_token = UsedToken(token_hash=token_hash, order_id=payload.order_id)
    session.add_all([payment_intent, used_token])
    await session.commit()

    await _update_order_status(str(payload.order_id), PaymentStatus.SUCCESS.value, user_id)

    await asyncio.to_thread(messaging.publish_receipt, {"receipt": receipt_dict, "signature": signature_b64})

    return schemas.PaymentResponse(status=PaymentStatus.SUCCESS, signed_receipt=signature_b64, receipt=receipt_dict)
