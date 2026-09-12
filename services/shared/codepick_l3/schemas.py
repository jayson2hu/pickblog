from datetime import datetime
from pydantic import BaseModel, Field


class Page(BaseModel):
    items: list["ContentSummary"]
    next_cursor: str | None = None
    total: int


class Translation(BaseModel):
    title: str
    summary: str
    base_analysis: dict


class ContentSummary(BaseModel):
    id: str
    title: str
    source: str
    url: str
    vertical: str
    status: str = "COMPLETED"
    published_at: datetime
    thumbnail: str | None = None
    summary: str
    scores: dict[str, int] = Field(default_factory=dict)


class ContentDetail(ContentSummary):
    base_analysis: dict
    translations: dict[str, Translation] = Field(default_factory=dict)


class User(BaseModel):
    id: int
    email: str
    locale: str = "en"
    plan: str = "free"


class Brief(BaseModel):
    id: str
    user_id: int | None = None
    vertical_code: str | None = None
    brief_date: str
    items: list[ContentSummary]
    channels: dict = Field(default_factory=dict)
    status: str = "generated"

