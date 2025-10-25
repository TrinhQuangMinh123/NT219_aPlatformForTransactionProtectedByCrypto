from __future__ import annotations

import os
import uuid

import stripe


class PSPMock:
    def charge(self, pan: str, amount: int, currency: str, **_: object) -> dict:
        intent_id = "pi_mock_" + uuid.uuid4().hex[:16]
        receipt = "rcpt_" + uuid.uuid4().hex[:8]
        return {
            "id": intent_id,
            "status": "succeeded",
            "amount": amount,
            "currency": currency,
            "last4": pan[-4:],
            "receipt": receipt,
        }


class PSPStripe:
    def __init__(self, secret_key: str) -> None:
        stripe.api_key = secret_key

    def charge(
        self,
        pan: str,
        amount: int,
        currency: str,
        exp_month: int | None = None,
        exp_year: int | None = None,
        cvc: str | None = None,
        **_: object,
    ) -> dict:
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={"number": pan, "exp_month": exp_month, "exp_year": exp_year, "cvc": cvc},
        )
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency.lower(),
            payment_method=payment_method.id,
            confirm=True,
        )
        charge = intent.charges.data[0] if intent.charges.data else None
        return {
            "id": intent.id,
            "status": intent.status,
            "amount": intent.amount,
            "currency": intent.currency.upper(),
            "last4": (charge.payment_method_details.card.last4 if charge else "****"),
            "receipt": (charge.receipt_number if charge else None),
        }


def build_psp() -> PSPMock | PSPStripe:
    provider = (os.getenv("PSP_PROVIDER", "mock").lower()).strip()
    if provider == "stripe":
        secret = os.getenv("STRIPE_SECRET_KEY", "")
        if not secret:
            raise RuntimeError("STRIPE_SECRET_KEY missing for Stripe provider")
        return PSPStripe(secret)
    return PSPMock()
