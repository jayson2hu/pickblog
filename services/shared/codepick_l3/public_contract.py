from .schemas import ContentDetail, ContentSummary


PUBLIC_CONTENT_FIELDS = {"id", "title", "source", "url", "vertical", "published_at", "thumbnail", "summary", "scores", "language", "reading_minutes", "tags", "provenance"}


def completed_public_items(items: list[ContentSummary | ContentDetail]) -> list[ContentSummary | ContentDetail]:
    return [item for item in items if item.status == "COMPLETED"]


def public_content_item(item: ContentSummary | ContentDetail) -> dict:
    if item.status != "COMPLETED":
        raise ValueError("public content must be COMPLETED")
    data = item.model_dump(mode="json", include=PUBLIC_CONTENT_FIELDS)
    data["provenance"] = {
        key: value for key, value in item.provenance.items()
        if key in {"source_kind", "analysis_method", "scoring_method", "translation_available", "reviewed"}
        and isinstance(value, (str, bool))
    }
    return {key: value for key, value in data.items() if key in PUBLIC_CONTENT_FIELDS}
