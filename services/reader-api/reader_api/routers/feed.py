from fastapi import APIRouter, Query

from codepick_l3.public_contract import completed_public_items
from codepick_l3.provider import get_content_provider
from codepick_l3.schemas import Page


router = APIRouter(tags=["feed"])


@router.get("/feed")
def feed(
    vertical: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    sort: str = "published_at",
) -> dict:
    page = get_content_provider().list(vertical=vertical, cursor=cursor, limit=limit, filters={"sort": sort})
    items = completed_public_items(page.items)
    return Page(items=items, next_cursor=page.next_cursor, total=len(items)).model_dump(mode="json")
