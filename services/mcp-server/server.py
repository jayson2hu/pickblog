"""Minimal MCP-facing wrapper around CodePick /v1 contracts.

The production package can expose these functions through the Python MCP SDK.
Keeping this file dependency-light lets contract tests run without a live MCP client.
"""

from codepick_l3.public_contract import completed_public_items, public_content_item
from codepick_l3.provider import get_content_provider


def _public_limit(limit: int) -> int:
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")
    return limit


def today(limit: int = 10) -> dict:
    limit = _public_limit(limit)
    page = get_content_provider().list(limit=limit, filters={"sort": "score"})
    return {"items": [public_content_item(item) for item in completed_public_items(page.items)]}


def search(q: str, limit: int = 10) -> dict:
    limit = _public_limit(limit)
    page = get_content_provider().list(limit=limit, filters={"q": q})
    return {
        "items": [
            public_content_item(item) for item in completed_public_items(page.items)
        ]
    }


def item(content_id: str) -> dict:
    detail = get_content_provider().get(content_id)
    if detail.status != "COMPLETED":
        raise KeyError(content_id)
    return public_content_item(detail)


def tool_manifest() -> dict:
    return {
        "name": "codepick",
        "tools": [
            {"name": "today", "description": "Return high-signal public CodePick items"},
            {"name": "search", "description": "Search public CodePick items"},
            {"name": "item", "description": "Return one public CodePick item by id"},
        ],
    }


def smoke() -> dict:
    manifest = tool_manifest()
    sample = today(limit=1)
    return {"ok": bool(sample["items"]), "manifest": manifest}


if __name__ == "__main__":
    import json

    print(json.dumps(smoke(), indent=2, sort_keys=True))
