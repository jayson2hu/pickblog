from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from codepick_l3.auth import current_user, has_plan
from codepick_l3.config import get_settings
from codepick_l3.provider import get_content_provider
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["companion"])
class CompanionRequest(BaseModel):
    content_id: str
    question: str


@router.post("/companion")
def companion(payload: CompanionRequest, user: User = Depends(current_user)) -> StreamingResponse:
    provider = get_content_provider()
    try:
        detail = provider.get(payload.content_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="content not found") from exc
    if detail.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="content not found")

    count = get_repository().increment_companion_usage(user.id, date.today())
    settings = get_settings()
    unlimited = has_plan(user, "pro")
    if not unlimited and count > settings.companion_free_daily:
        raise HTTPException(status_code=429, detail="companion quota exceeded")

    def stream():
        for chunk in provider.companion(payload.content_id, payload.question):
            yield f"data: {chunk}\n\n"

    headers = {
        "X-Companion-Limit": str(settings.companion_free_daily),
        "X-Companion-Remaining": "-1" if unlimited else str(max(0, settings.companion_free_daily - count)),
    }
    if unlimited:
        headers["X-Companion-Unlimited"] = "true"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
