from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from codepick_l3.auth import issue_token
from codepick_l3.config import get_settings
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    locale: str = "en"


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    if get_settings().auth_login_mode != "development":
        raise HTTPException(status_code=503, detail="development email login is disabled")
    profile = get_repository().get_or_create_user(str(payload.email), payload.locale)
    user = User(id=profile["id"], email=profile["email"], locale=profile["locale"], plan=profile["plan"])
    return {"token": issue_token(user), "user": user.model_dump()}
