from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from codepick_l3.auth import current_user
from codepick_l3.public_contract import completed_public_items
from codepick_l3.provider import get_content_provider
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["library"])

class InterestsRequest(BaseModel):
    tags: list[str] = Field(min_length=5, max_length=8)


class FollowRequest(BaseModel):
    target_type: str
    target_id: str


class BookmarkRequest(BaseModel):
    content_id: str
    note: str | None = None
    highlights: list[str] = Field(default_factory=list)


@router.post("/interests")
def save_interests(payload: InterestsRequest, user: User = Depends(current_user)) -> dict:
    get_repository().save_interests(user.id, payload.tags)
    return {"ok": True, "count": len(payload.tags), "tags": payload.tags}


@router.get("/interests")
def get_interests(user: User = Depends(current_user)) -> dict:
    return {"tags": get_repository().get_interests(user.id)}


@router.post("/follow")
def follow(payload: FollowRequest, user: User = Depends(current_user)) -> dict:
    follows = get_repository().add_follow(user.id, payload.target_type, payload.target_id)
    return {"ok": True, "follows": follows}


@router.post("/bookmarks")
def bookmark(payload: BookmarkRequest, user: User = Depends(current_user)) -> dict:
    try:
        detail = get_content_provider().get(payload.content_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="content not found") from exc
    if detail.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="content not found")
    repo = get_repository()
    saved = repo.add_bookmark(user.id, payload.content_id, payload.note, payload.highlights)
    repo.save_reading_event(user.id, payload.content_id, "bookmark")
    return {"ok": True, "bookmark": saved, "north_star": repo.north_star(user.id)}


@router.get("/bookmarks")
def bookmarks(user: User = Depends(current_user)) -> dict:
    return {"items": get_repository().list_bookmarks(user.id)}


@router.get("/recommendations")
def recommendations(vertical: str | None = None, user: User = Depends(current_user)) -> dict:
    items = get_content_provider().recommend(user.id, vertical=vertical, limit=10)
    return {"items": [item.model_dump(mode="json") for item in completed_public_items(items)]}
