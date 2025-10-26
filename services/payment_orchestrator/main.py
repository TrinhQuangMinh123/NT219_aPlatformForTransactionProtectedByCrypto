from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import messaging
import schemas
from database import get_session, init_db
from hsm_service import decrypt_token, encrypt_token, get_public_key_der, initialize_keys_if_not_exist, sign_message
from models import PaymentIntent, PaymentStatus, UsedToken
from psp_client import PSPMock, build_psp

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8000")
FRAUD_ENGINE_URL = os.getenv("FRAUD_ENGINE_URL", "http://fraud_engine:8000")
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
    logger.info("[STARTUP] Initializing Payment Orchestrator...")
    
    logger.info("[STARTUP] Initializing HSM keys...")
    initialize_keys_if_not_exist()
    logger.info("[STARTUP] HSM keys initialized successfully")
    
    await init_db()
    logger.info("[STARTUP] Database initialized")
    
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    _psp_client = build_psp()
    logger.info(f"[STARTUP] PSP provider: {PSP_PROVIDER}")
    logger.info("[STARTUP] Payment Orchestrator ready")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _http_client
    if _http_client is not None:
        client, _http_client = _http_client, None
        await client.aclose()
    logger.info("[SHUTDOWN] Payment Orchestrator shutting down")


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
    logger.info("[HEALTH] Health check requested")
    return {"status": "ok", "provider": PSP_PROVIDER}


@app.post("/sign", response_model=schemas.SignResponse)
async def sign_endpoint(payload: schemas.SignRequest) -> schemas.SignResponse:
    logger.info(f"[SIGN] Signing message (length: {len(payload.message)})")
    signature = sign_message(payload.message)
    logger.info(f"[SIGN] Signature generated (length: {len(signature)} bytes)")
    return schemas.SignResponse.from_bytes(signature)


@app.get("/public-key", response_model=schemas.PublicKeyResponse)
async def public_key() -> schemas.PublicKeyResponse:
    logger.info("[PUBLIC_KEY] Retrieving public key from HSM")
    public_key_der = get_public_key_der()
    logger.info(f"[PUBLIC_KEY] Public key retrieved (DER length: {len(public_key_der)} bytes)")
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
    logger.info(f"[TOKENIZE] Request from user: {user_id}")
    logger.info(f"[TOKENIZE] Card brand: {card_brand(payload.pan)}, Last4: {payload.pan[-4:]}")
    
    token = encrypt_token(payload.pan.encode("utf-8"))
    logger.info(f"[TOKENIZE] Token generated: {token[:20]}... (length: {len(token)})")
    
    response = schemas.TokenizeResponse(
        token=token,
        brand=card_brand(payload.pan),
        last4=payload.pan[-4:],
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        mask=mask_pan(payload.pan),
        owner=user_id,
    )
    logger.info(f"[TOKENIZE] Tokenization successful for user {user_id}")
    return response


@app.post("/payment/charge", response_model=schemas.ChargeResponse)
async def charge(
    payload: schemas.ChargeRequest,
    user_id: Annotated[str, Depends(require_user)],
) -> schemas.ChargeResponse:
    try:
        pan = decrypt_token(payload.token).decode("utf-8")
    except ValueError as exc:
        logger.error(f"[CHARGE] Token decryption failed: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(f"[CHARGE] Processing charge for user {user_id}, amount: {payload.amount} {payload.currency}")
    result = await _psp_charge(
        pan=pan,
        amount=payload.amount,
        currency=payload.currency,
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        cvc=payload.cvc,
    )
    logger.info(f"[CHARGE] PSP response: {result['status']}, ID: {result['id']}")
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
    logger.info(f"[FRAUD] Checking transaction: amount={amount}, user={user_id}")
    response = await _http().post(
        f"{FRAUD_ENGINE_URL}/score",
        json={"amount": amount, "user_ip": None, "device_id": user_id},
    )
    response.raise_for_status()
    payload = response.json()
    logger.info(f"[FRAUD] Decision: action={payload['action']}, score={payload['score']}")
    return schemas.FraudDecision(**payload)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/payments", response_model=schemas.PaymentResponse)
async def orchestrate_payment(
    payload: schemas.PaymentRequest,
    user_id: Annotated[str, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> schemas.PaymentResponse:
    logger.info(f"[PAYMENT] Orchestrating payment for order {payload.order_id}, user {user_id}")
    
    order = await _fetch_order(str(payload.order_id), user_id)
    amount = order.get("amount")
    currency = order.get("currency", "VND")
    if not isinstance(amount, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order missing amount")

    logger.info(f"[PAYMENT] Order details: amount={amount}, currency={currency}")

    fraud_decision = await _fraud_check(amount, user_id)
    if fraud_decision.action.upper() == "BLOCK":
        logger.warning(f"[PAYMENT] Transaction BLOCKED by fraud engine for order {payload.order_id}")
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="transaction blocked by fraud engine")

    token_hash = _hash_token(payload.payment_token)
    existing = await session.execute(select(UsedToken).where(UsedToken.token_hash == token_hash))
    if existing.scalar_one_or_none():
        logger.warning(f"[PAYMENT] Replay attack detected: token already used for order {payload.order_id}")
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment token already used")

    try:
        pan = decrypt_token(payload.payment_token).decode("utf-8")
    except ValueError as exc:
        logger.error(f"[PAYMENT] Token decryption failed: {exc}")
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid payment token") from exc

    logger.info(f"[PAYMENT] Sending charge to PSP for order {payload.order_id}")
    result = await _psp_charge(pan=pan, amount=amount, currency=currency)
    if result.get("status") != "succeeded":
        logger.error(f"[PAYMENT] PSP charge failed for order {payload.order_id}: {result}")
        await _update_order_status(str(payload.order_id), PaymentStatus.FAILED.value, user_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="psp charge failed")

    logger.info(f"[PAYMENT] PSP charge succeeded: {result['id']}")

    receipt = schemas.ReceiptEnvelope(
        order_id=payload.order_id,
        amount=amount,
        currency=currency,
        timestamp=datetime.now(timezone.utc),
        status=PaymentStatus.SUCCESS,
    )
    receipt_dict = receipt.to_serialisable() | {"psp_reference": result["id"], "last4": result["last4"]}
    
    logger.info(f"[RECEIPT] Signing receipt for order {payload.order_id}")
    signature_bytes = sign_message(json.dumps(receipt_dict, sort_keys=True))
    signature_b64 = base64.b64encode(signature_bytes).decode("ascii")
    logger.info(f"[RECEIPT] Receipt signed (signature length: {len(signature_bytes)} bytes)")

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
    logger.info(f"[PAYMENT] Payment intent saved to database for order {payload.order_id}")

    await _update_order_status(str(payload.order_id), "COMPLETED", user_id)

    logger.info(f"[PAYMENT] Publishing receipt to reconciliation queue for order {payload.order_id}")
    await asyncio.to_thread(messaging.publish_receipt, {"receipt": receipt_dict, "signature": signature_b64})

    logger.info(f"[PAYMENT] Payment orchestration completed successfully for order {payload.order_id}")
    return schemas.PaymentResponse(status=PaymentStatus.SUCCESS, signed_receipt=signature_b64, receipt=receipt_dict)
