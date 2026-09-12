from datetime import date

from .public_contract import completed_public_items
from .provider import ContentReadProvider
from .schemas import Brief, User


def generate_public_brief(provider: ContentReadProvider, vertical: str | None = None) -> Brief:
    page = provider.list(vertical=vertical, limit=10, filters={"sort": "score"})
    seen: set[str] = set()
    items = []
    for item in completed_public_items(page.items):
        if item.id in seen:
            continue
        seen.add(item.id)
        if item.scores.get("quality", 0) >= 80:
            items.append(item)
    return Brief(id=f"public-{date.today().isoformat()}", vertical_code=vertical, brief_date=date.today().isoformat(), items=items)


def generate_personal_brief(provider: ContentReadProvider, user: User, vertical: str | None = None) -> Brief:
    items = completed_public_items(provider.recommend(user_id=user.id, vertical=vertical, limit=10))
    return Brief(id=f"user-{user.id}-{date.today().isoformat()}", user_id=user.id, vertical_code=vertical, brief_date=date.today().isoformat(), items=items)
