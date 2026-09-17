from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from codepick_l3.auth import current_user, has_plan
from codepick_l3.config import get_settings
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["me"])


class AudienceRequest(BaseModel):
    audience_code: str


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return get_repository().get_user_profile(user.id, user.email, user.locale)


@router.patch("/me/audience")
def update_audience(payload: AudienceRequest, user: User = Depends(current_user)) -> dict:
    if payload.audience_code != "general":
        try:
            profile = get_repository().set_user_audience(user.id, payload.audience_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="audience not found") from exc
        return {"audience_code": profile["audience_code"]}
    profile = get_repository().set_user_audience(user.id, payload.audience_code)
    return {"audience_code": profile["audience_code"]}


@router.get("/companion/quota")
def companion_quota(user: User = Depends(current_user)) -> dict:
    plan = get_repository().get_subscription_plan(user.id)
    unlimited = has_plan(user, "pro")
    used = get_repository().get_companion_usage(user.id, date.today())
    return {"used": used, "limit": get_settings().companion_free_daily, "plan": plan, "unlimited": unlimited}
