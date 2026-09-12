from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from codepick_l3.auth import current_user
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["admin"])


class CategoryPayload(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label_en: str | None = None
    label_zh: str | None = None
    color_from: str | None = None
    color_to: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class AudiencePayload(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label_en: str | None = None
    label_zh: str | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class AudienceCategoriesPayload(BaseModel):
    categories: list[str] = Field(default_factory=list)


def require_admin_user(user: User = Depends(current_user)) -> User:
    if not get_repository().require_admin(user.id):
        raise HTTPException(status_code=403, detail="admin required")
    return user


@router.get("/admin/taxonomy")
def admin_taxonomy(_: User = Depends(require_admin_user)) -> dict:
    repo = get_repository()
    return {"categories": repo.list_taxonomy_categories(include_inactive=True), "audiences": repo.list_audiences()}


@router.post("/admin/categories")
def create_category(payload: CategoryPayload, _: User = Depends(require_admin_user)) -> dict:
    return {"category": get_repository().upsert_taxonomy_category(payload.model_dump(exclude_none=True))}


@router.patch("/admin/categories/{code}")
def update_category(code: str, payload: CategoryPayload, _: User = Depends(require_admin_user)) -> dict:
    data = payload.model_dump(exclude_none=True)
    data["code"] = code
    return {"category": get_repository().upsert_taxonomy_category(data)}


@router.delete("/admin/categories/{code}")
def delete_category(code: str, _: User = Depends(require_admin_user)) -> dict:
    if not get_repository().delete_taxonomy_category(code):
        raise HTTPException(status_code=404, detail="category not found")
    return {"ok": True}


@router.post("/admin/audiences")
def create_audience(payload: AudiencePayload, _: User = Depends(require_admin_user)) -> dict:
    return {"audience": get_repository().upsert_audience(payload.model_dump(exclude_none=True))}


@router.patch("/admin/audiences/{code}")
def update_audience(code: str, payload: AudiencePayload, _: User = Depends(require_admin_user)) -> dict:
    data = payload.model_dump(exclude_none=True)
    data["code"] = code
    return {"audience": get_repository().upsert_audience(data)}


@router.delete("/admin/audiences/{code}")
def delete_audience(code: str, _: User = Depends(require_admin_user)) -> dict:
    if not get_repository().delete_audience(code):
        raise HTTPException(status_code=400, detail="audience cannot be deleted")
    return {"ok": True}


@router.put("/admin/audiences/{code}/categories")
def set_audience_categories(code: str, payload: AudienceCategoriesPayload, _: User = Depends(require_admin_user)) -> dict:
    try:
        return get_repository().set_audience_categories(code, payload.categories)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="audience or category not found") from exc
