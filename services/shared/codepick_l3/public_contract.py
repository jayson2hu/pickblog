from .schemas import ContentDetail, ContentSummary


PUBLIC_CONTENT_FIELDS = {"id", "title", "source", "url", "vertical", "published_at", "thumbnail", "summary", "scores"}


def completed_public_items(items: list[ContentSummary | ContentDetail]) -> list[ContentSummary | ContentDetail]:
    return [item for item in items if item.status == "COMPLETED"]


def public_content_item(item: ContentSummary | ContentDetail) -> dict:
    if item.status != "COMPLETED":
        raise ValueError("public content must be COMPLETED")
    data = item.model_dump(mode="json", include=PUBLIC_CONTENT_FIELDS)
    return {key: value for key, value in data.items() if key in PUBLIC_CONTENT_FIELDS}
