from fastapi import APIRouter, Depends

from codepick_l3.auth import optional_user
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User
from codepick_l3.taxonomy import taxonomy_from_content


router = APIRouter(tags=["taxonomy"])


@router.get("/taxonomy")
def taxonomy(user: User | None = Depends(optional_user)) -> dict:
    if user is None:
        return taxonomy_from_content("en")
    profile = get_repository().get_user_profile(user.id, user.email, user.locale)
    return taxonomy_from_content(user.locale, profile.get("audience_code"))
