from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from typing import Literal

from codepick_l3.auth import current_user
from codepick_l3.billing import get_billing_client, parse_billing_webhook, verify_webhook
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["billing"])
class CheckoutRequest(BaseModel):
    cadence: Literal["month", "year", "earlybird"] = "month"


@router.post("/billing/checkout")
def checkout(payload: CheckoutRequest, user: User = Depends(current_user)) -> dict:
    return {"checkout_url": get_billing_client().checkout_url(user.id, payload.cadence), "currency": "USD"}


@router.post("/billing/webhook")
async def webhook(request: Request, x_paddle_signature: str | None = Header(default=None, alias="X-Paddle-Signature")) -> dict:
    body = await request.body()
    verify_webhook(body, x_paddle_signature)
    payload = await request.json()
    event = parse_billing_webhook(payload)
    get_repository().set_subscription_plan(event["user_id"], event["plan"])
    return {"ok": True, "user_id": event["user_id"], "plan": event["plan"], "event": event["event"]}
