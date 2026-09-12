from fastapi import APIRouter, Depends, HTTPException, Query

from codepick_l3.public_contract import completed_public_items, public_content_item
from codepick_l3.provider import get_content_provider
from codepick_l3.taxonomy import taxonomy_from_content
from codepick_l3.usage import ApiKeyRecord, require_api_key


router = APIRouter(tags=["v1"])


def quota_snapshot(key: ApiKeyRecord) -> dict:
    return {"daily": key.daily_quota, "rate_limit_rpm": key.rate_limit_rpm}


@router.get("/today")
def today(cursor: str | None = None, limit: int = Query(default=10, ge=1, le=50), key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    page = get_content_provider().list(cursor=cursor, limit=limit, filters={"sort": "score"})
    return {"items": [public_content_item(item) for item in completed_public_items(page.items)], "next_cursor": page.next_cursor, "quota": quota_snapshot(key)}


@router.get("/search")
def search(q: str = "", cursor: str | None = None, limit: int = Query(default=10, ge=1, le=50), key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    page = get_content_provider().list(cursor=cursor, limit=limit)
    items = [item for item in completed_public_items(page.items) if q.lower() in item.title.lower() or q.lower() in item.summary.lower()]
    return {"items": [public_content_item(item) for item in items], "next_cursor": page.next_cursor, "quota": quota_snapshot(key)}


@router.get("/items/{content_id}")
def item(content_id: str, key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    try:
        detail = get_content_provider().get(content_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="content not found") from exc
    if detail.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="content not found")
    return {"item": public_content_item(detail), "quota": quota_snapshot(key)}


@router.get("/trending")
def trending(key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    page = get_content_provider().list(limit=10, filters={"sort": "score"})
    return {"items": [public_content_item(item) for item in completed_public_items(page.items)], "quota": quota_snapshot(key)}


@router.get("/sources")
def sources(key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    page = get_content_provider().list(limit=50)
    return {"sources": sorted({item.source for item in completed_public_items(page.items)}), "quota": quota_snapshot(key)}


@router.get("/verticals")
def verticals(key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    page = get_content_provider().list(limit=50)
    return {"verticals": sorted({item.vertical for item in completed_public_items(page.items)}), "quota": quota_snapshot(key)}


@router.get("/taxonomy")
def taxonomy(key: ApiKeyRecord = Depends(require_api_key)) -> dict:
    taxonomy_data = taxonomy_from_content()
    return {
        "categories": [{"code": category["code"], "label": category["label"]} for category in taxonomy_data["categories"]],
        "audiences": taxonomy_data["audiences"],
        "quota": quota_snapshot(key),
    }
