from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from codepick_l3.auth import issue_token
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    locale: str = "en"


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    plan = get_repository().get_subscription_plan(1)
    user = User(id=1, email=str(payload.email), locale=payload.locale, plan=plan)
    return {"token": issue_token(user), "user": user.model_dump()}
