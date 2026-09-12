from fastapi import APIRouter, Depends

from codepick_l3.auth import require_plan
from codepick_l3.briefs import generate_personal_brief, generate_public_brief
from codepick_l3.provider import get_content_provider
from codepick_l3.schemas import User


router = APIRouter(tags=["briefs"])


@router.get("/brief/public")
def public_brief(vertical: str | None = None) -> dict:
    return generate_public_brief(get_content_provider(), vertical=vertical).model_dump(mode="json")


@router.get("/brief/me")
def my_brief(vertical: str | None = None, user: User = Depends(require_plan("pro"))) -> dict:
    return generate_personal_brief(get_content_provider(), user=user, vertical=vertical).model_dump(mode="json")

