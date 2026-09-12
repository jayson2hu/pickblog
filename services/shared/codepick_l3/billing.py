import hmac
import hashlib
from fastapi import HTTPException
from urllib.parse import urlencode

from .config import get_settings


ACTIVE_BILLING_EVENTS = {"subscription.activated", "subscription.created", "transaction.completed"}
CANCELED_BILLING_EVENTS = {"subscription.canceled", "subscription.paused", "subscription.past_due"}
SUPPORTED_CADENCES = {"month", "year", "earlybird"}


def sign_webhook(payload: bytes, secret: str | None = None) -> str:
    key = (secret or get_settings().paddle_webhook_secret).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_webhook(payload: bytes, signature: str | None) -> None:
    if not signature:
        raise HTTPException(status_code=401, detail="missing webhook signature")
    expected = sign_webhook(payload)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="invalid webhook signature")


def parse_billing_webhook(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    custom_data = data.get("custom_data") if isinstance(data.get("custom_data"), dict) else {}
    user_id = payload.get("user_id") or custom_data.get("user_id")
    event = payload.get("event") or payload.get("event_type") or data.get("event_type") or "subscription.activated"
    if user_id is None:
        raise HTTPException(status_code=422, detail="billing webhook missing user_id")
    if event in ACTIVE_BILLING_EVENTS:
        plan = "pro"
    elif event in CANCELED_BILLING_EVENTS:
        plan = "free"
    else:
        raise HTTPException(status_code=422, detail=f"unsupported billing event: {event}")
    return {"user_id": int(user_id), "event": event, "plan": plan}


class SandboxBilling:
    def checkout_url(self, user_id: int, cadence: str) -> str:
        if cadence not in SUPPORTED_CADENCES:
            raise ValueError("unsupported cadence")
        return f"https://sandbox-payments.codepick.local/checkout?{urlencode({'user_id': user_id, 'cadence': cadence, 'currency': 'USD'})}"


class PaddleBilling:
    def __init__(self, checkout_base_url: str, environment: str = "sandbox") -> None:
        self.checkout_base_url = checkout_base_url.rstrip("/")
        self.environment = environment

    def checkout_url(self, user_id: int, cadence: str) -> str:
        if cadence not in SUPPORTED_CADENCES:
            raise ValueError("unsupported cadence")
        query = urlencode({"user_id": user_id, "cadence": cadence, "currency": "USD", "provider": "paddle", "env": self.environment})
        return f"{self.checkout_base_url}/checkout?{query}"


def get_billing_client():
    settings = get_settings()
    if settings.billing_environment == "sandbox":
        return SandboxBilling()
    if settings.billing_environment == "production":
        return PaddleBilling(settings.paddle_checkout_base_url, environment="production")
    raise RuntimeError(f"unsupported BILLING_ENVIRONMENT: {settings.billing_environment}")
