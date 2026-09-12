from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol
import json
import urllib.parse
import urllib.request

from .config import get_settings
from .schemas import ContentDetail, ContentSummary, Page


class ProviderUnavailable(RuntimeError):
    pass


class ContentReadProvider(Protocol):
    def list(
        self,
        vertical: str | None = None,
        status: str = "COMPLETED",
        filters: dict | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> Page: ...

    def get(self, content_id: str) -> ContentDetail: ...

    def recommend(self, user_id: int, vertical: str | None = None, limit: int = 10) -> list[ContentSummary]: ...

    def companion(self, content_id: str, question: str) -> Iterator[str]: ...


class StubContentReadProvider:
    def __init__(self, fixture_path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self.fixture_path = fixture_path or root / "fixtures" / "l2_completed.json"
        raw = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        self._items = [ContentDetail.model_validate(item) for item in raw]

    def list(
        self,
        vertical: str | None = None,
        status: str = "COMPLETED",
        filters: dict | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> Page:
        offset = int(cursor or 0)
        rows = [item for item in self._items if item.status == status and (vertical is None or item.vertical == vertical)]
        sort = (filters or {}).get("sort", "published_at")
        if sort == "score":
            rows.sort(key=lambda item: item.scores.get("quality", 0), reverse=True)
        else:
            rows.sort(key=lambda item: item.published_at, reverse=True)
        page = rows[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(rows) else None
        return Page(items=[ContentSummary.model_validate(item.model_dump()) for item in page], next_cursor=next_cursor, total=len(rows))

    def get(self, content_id: str) -> ContentDetail:
        for item in self._items:
            if item.id == content_id:
                return item
        raise KeyError(content_id)

    def recommend(self, user_id: int, vertical: str | None = None, limit: int = 10) -> list[ContentSummary]:
        page = self.list(vertical=vertical, filters={"sort": "score"}, limit=limit)
        return page.items

    def companion(self, content_id: str, question: str) -> Iterator[str]:
        detail = self.get(content_id)
        chunks = [
            f"Question: {question.strip() or 'Explain the key point.'}\n",
            f"{detail.title}: ",
            detail.base_analysis.get("summary", detail.summary),
            "\nUse the score dimensions to decide whether this is worth a deep read.",
        ]
        yield from chunks


class L2HttpContentReadProvider:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request_json(self, path: str, query: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ProviderUnavailable(f"L2 provider request failed: {path}") from exc

    def list(
        self,
        vertical: str | None = None,
        status: str = "COMPLETED",
        filters: dict | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> Page:
        data = self._request_json(
            "/content",
            {"vertical": vertical, "status": status, "cursor": cursor, "limit": limit, "sort": (filters or {}).get("sort")},
        )
        return Page.model_validate(data)

    def get(self, content_id: str) -> ContentDetail:
        return ContentDetail.model_validate(self._request_json(f"/content/{urllib.parse.quote(content_id)}"))

    def recommend(self, user_id: int, vertical: str | None = None, limit: int = 10) -> list[ContentSummary]:
        data = self._request_json("/recommend", {"user_id": user_id, "vertical": vertical, "limit": limit})
        return [ContentSummary.model_validate(item) for item in data.get("items", data)]

    def companion(self, content_id: str, question: str) -> Iterator[str]:
        data = self._request_json("/companion", {"content_id": content_id, "question": question})
        chunks = data.get("chunks")
        if not isinstance(chunks, list):
            raise ProviderUnavailable("L2 companion response missing chunks")
        yield from (str(chunk) for chunk in chunks)


def get_content_provider() -> ContentReadProvider:
    settings = get_settings()
    if not settings.l3_use_stub_l2:
        if not settings.l2_base_url:
            raise ProviderUnavailable("L2_BASE_URL is required when L3_USE_STUB_L2=false")
        return L2HttpContentReadProvider(settings.l2_base_url, api_key=settings.l2_api_key)
    return StubContentReadProvider()
