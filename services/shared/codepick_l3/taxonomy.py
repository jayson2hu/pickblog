from __future__ import annotations

from .provider import get_content_provider
from .repository import get_repository


def taxonomy_from_content(locale: str = "en", audience_code: str | None = None) -> dict:
    taxonomy = get_repository().taxonomy_for_audience(audience_code, locale=locale)
    if taxonomy["categories"]:
        return taxonomy
    page = get_content_provider().list(limit=50)
    verticals = sorted({item.vertical for item in page.items if item.status == "COMPLETED"})
    for index, code in enumerate(verticals):
        label = code.replace("-", " ").title()
        get_repository().upsert_taxonomy_category({"code": code, "label_en": label, "label_zh": label, "sort_order": index})
    get_repository().set_audience_categories("general", verticals)
    return get_repository().taxonomy_for_audience("general", locale=locale)
