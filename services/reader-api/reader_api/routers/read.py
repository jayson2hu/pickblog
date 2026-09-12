from fastapi import APIRouter, HTTPException

from codepick_l3.provider import get_content_provider


router = APIRouter(tags=["read"])


@router.get("/read/{content_id}")
def read(content_id: str) -> dict:
    try:
        detail = get_content_provider().get(content_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="content not found") from exc
    if detail.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="content not found")
    return detail.model_dump(mode="json")
