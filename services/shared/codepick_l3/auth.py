from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

from .config import get_settings
from .repository import get_repository
from .schemas import User


ALGORITHM = "HS256"
PLAN_ORDER = {"free": 0, "pro": 1}


def issue_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "plan": user.plan,
        "locale": user.locale,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc
    return User(
        id=int(payload["sub"]),
        email=payload["email"],
        plan=payload.get("plan", "free"),
        locale=payload.get("locale", "en"),
    )


def optional_user(authorization: str | None = Header(default=None)) -> User | None:
    if not authorization:
        return None
    return current_user(authorization)


def require_plan(plan: str):
    def dependency(user: User = Depends(current_user)) -> User:
        effective_plan = get_repository().get_subscription_plan(user.id)
        if PLAN_ORDER.get(effective_plan, PLAN_ORDER.get(user.plan, 0)) < PLAN_ORDER[plan]:
            raise HTTPException(status_code=403, detail=f"{plan} plan required")
        user.plan = effective_plan
        return user

    return dependency


def resolve_effective_plan(user: User) -> str:
    return get_repository().get_subscription_plan(user.id)


def has_plan(user: User, plan: str) -> bool:
    claimed_plan = user.plan
    effective_plan = resolve_effective_plan(user)
    user.plan = effective_plan
    return PLAN_ORDER.get(effective_plan, PLAN_ORDER.get(claimed_plan, 0)) >= PLAN_ORDER[plan]
