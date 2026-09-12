from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from pydantic import BaseModel

from codepick_l3.auth import current_user
from codepick_l3.provider import get_content_provider
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["events"])
class EventRequest(BaseModel):
    content_id: str
    type: Literal["click", "deep_read", "bookmark", "not_interested"]


@router.post("/events")
def track_event(payload: EventRequest, user: User = Depends(current_user)) -> dict:
    try:
        detail = get_content_provider().get(payload.content_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="content not found") from exc
    if detail.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="content not found")

    get_repository().save_reading_event(user.id, payload.content_id, payload.type)
    return {"ok": True, "north_star": get_repository().north_star()}
