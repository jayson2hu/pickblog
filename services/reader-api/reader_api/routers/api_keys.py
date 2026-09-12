from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from codepick_l3.auth import current_user
from codepick_l3.schemas import User
from codepick_l3.usage import api_key_usage_days, create_api_key, list_api_keys, revoke_api_key


router = APIRouter(tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    scopes: list[str] = Field(default_factory=lambda: ["read"], min_length=1, max_length=5)

    @field_validator("scopes")
    @classmethod
    def read_only_public_scopes(cls, scopes: list[str]) -> list[str]:
        if scopes != ["read"]:
            raise ValueError("public api keys only support read scope")
        return scopes


@router.get("/api-keys")
def list_keys(user: User = Depends(current_user)) -> dict:
    return {"items": list_api_keys(user.id)}


@router.get("/api-keys/usage")
def key_usage(user: User = Depends(current_user)) -> dict:
    return api_key_usage_days(user.id, window=7)


@router.post("/api-keys")
def create_key(payload: ApiKeyCreateRequest, user: User = Depends(current_user)) -> dict:
    return create_api_key(user.id, scopes=payload.scopes)


@router.delete("/api-keys/{key_ref}")
def revoke_key(key_ref: str, user: User = Depends(current_user)) -> dict:
    if not revoke_api_key(user.id, key_ref):
        raise HTTPException(status_code=404, detail="api key not found")
    return {"ok": True, "status": "revoked"}
