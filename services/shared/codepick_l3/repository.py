from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import os
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (
    ApiUsageDailyModel,
    AudienceCategoryModel,
    AudienceModel,
    BookmarkModel,
    BriefModel,
    CompanionUsageModel,
    ReadingEventModel,
    SubscriptionModel,
    TaxonomyCategoryModel,
    UserModel,
    UserFollowModel,
    UserInterestModel,
)
from .schemas import Brief


class L3Repository(Protocol):
    def get_or_create_user(self, email: str, locale: str = "en") -> dict: ...
    def save_interests(self, user_id: int, tags: list[str]) -> None: ...
    def get_interests(self, user_id: int) -> dict[str, int]: ...
    def add_follow(self, user_id: int, target_type: str, target_id: str) -> list[dict[str, str]]: ...
    def add_bookmark(self, user_id: int, content_id: str, note: str | None, highlights: list[str]) -> dict: ...
    def list_bookmarks(self, user_id: int) -> list[dict]: ...
    def save_reading_event(self, user_id: int, content_id: str, event_type: str) -> dict: ...
    def north_star(self, user_id: int | None = None) -> dict[str, int | float]: ...
    def save_brief(self, brief: Brief) -> None: ...
    def list_briefs(self) -> list[Brief]: ...
    def get_companion_usage(self, user_id: int, day: date) -> int: ...
    def increment_companion_usage(self, user_id: int, day: date) -> int: ...
    def set_subscription_plan(self, user_id: int, plan: str) -> None: ...
    def get_subscription_plan(self, user_id: int) -> str: ...
    def get_user_profile(self, user_id: int, email: str | None = None, locale: str = "en") -> dict: ...
    def set_user_audience(self, user_id: int, audience_code: str) -> dict: ...
    def require_admin(self, user_id: int) -> bool: ...
    def list_taxonomy_categories(self, include_inactive: bool = False) -> list[dict]: ...
    def upsert_taxonomy_category(self, data: dict) -> dict: ...
    def delete_taxonomy_category(self, code: str) -> bool: ...
    def list_audiences(self) -> list[dict]: ...
    def upsert_audience(self, data: dict) -> dict: ...
    def delete_audience(self, code: str) -> bool: ...
    def set_audience_categories(self, audience_code: str, categories: list[str]) -> dict: ...
    def taxonomy_for_audience(self, audience_code: str | None = None, locale: str = "en") -> dict: ...


DEFAULT_CATEGORIES = [
    {"code": "ai", "label_en": "AI", "label_zh": "AI", "color_from": "#4f46e5", "color_to": "#14b8a6", "sort_order": 0, "active": True},
    {"code": "data", "label_en": "Data", "label_zh": "数据", "color_from": "#0f766e", "color_to": "#2563eb", "sort_order": 1, "active": True},
    {"code": "infra", "label_en": "Infrastructure", "label_zh": "基础设施", "color_from": "#334155", "color_to": "#4f46e5", "sort_order": 2, "active": True},
    {"code": "product", "label_en": "Product", "label_zh": "产品", "color_from": "#7c3aed", "color_to": "#db2777", "sort_order": 3, "active": True},
]

DEFAULT_AUDIENCES = [
    {"code": "general", "label_en": "General readers", "label_zh": "通用读者", "is_default": True, "sort_order": 0},
    {"code": "engineering-leads", "label_en": "Engineering leads", "label_zh": "工程负责人", "is_default": False, "sort_order": 1},
    {"code": "builders", "label_en": "Builders", "label_zh": "构建者", "is_default": False, "sort_order": 2},
]


@dataclass
class InMemoryL3Repository:
    interests: dict[int, dict[str, int]] = field(default_factory=dict)
    follows: dict[int, list[dict[str, str]]] = field(default_factory=dict)
    bookmarks: dict[tuple[int, str], dict] = field(default_factory=dict)
    reading_events: list[dict] = field(default_factory=list)
    briefs: list[Brief] = field(default_factory=list)
    companion_usage: dict[tuple[int, date], int] = field(default_factory=dict)
    subscription_plans: dict[int, str] = field(default_factory=dict)
    user_profiles: dict[int, dict] = field(default_factory=dict)
    categories: dict[str, dict] = field(default_factory=lambda: {row["code"]: dict(row) for row in DEFAULT_CATEGORIES})
    audiences: dict[str, dict] = field(default_factory=lambda: {row["code"]: dict(row) for row in DEFAULT_AUDIENCES})
    audience_categories: dict[str, list[str]] = field(default_factory=lambda: {row["code"]: [category["code"] for category in DEFAULT_CATEGORIES] for row in DEFAULT_AUDIENCES})

    def get_or_create_user(self, email: str, locale: str = "en") -> dict:
        normalized_email = email.strip().lower()
        for user_id, profile in self.user_profiles.items():
            if profile["email"].lower() == normalized_email:
                return self.get_user_profile(user_id, normalized_email, locale)

        user_id = max(self.user_profiles, default=0) + 1
        return self.get_user_profile(user_id, normalized_email, locale)

    def save_interests(self, user_id: int, tags: list[str]) -> None:
        self.interests[user_id] = {tag: 1 for tag in tags}

    def get_interests(self, user_id: int) -> dict[str, int]:
        return self.interests.get(user_id, {})

    def add_follow(self, user_id: int, target_type: str, target_id: str) -> list[dict[str, str]]:
        self.follows.setdefault(user_id, []).append({"target_type": target_type, "target_id": target_id})
        return self.follows[user_id]

    def add_bookmark(self, user_id: int, content_id: str, note: str | None, highlights: list[str]) -> dict:
        bookmark = {"content_id": content_id, "note": note, "highlights": highlights}
        self.bookmarks[(user_id, content_id)] = bookmark
        return bookmark

    def list_bookmarks(self, user_id: int) -> list[dict]:
        return [value for (owner, _), value in self.bookmarks.items() if owner == user_id]

    def save_reading_event(self, user_id: int, content_id: str, event_type: str) -> dict:
        event = {"user_id": user_id, "content_id": content_id, "type": event_type}
        self.reading_events.append(event)
        return event

    def north_star(self, user_id: int | None = None) -> dict[str, int | float]:
        events = [event for event in self.reading_events if user_id is None or event["user_id"] == user_id]
        closed_loop = [event for event in events if event["type"] in {"deep_read", "bookmark"}]
        total = len(events)
        return {
            "deep_read_closed_loop_events": len(closed_loop),
            "reading_events_total": total,
            "deep_read_closed_loop_rate": len(closed_loop) / total if total else 0.0,
        }

    def save_brief(self, brief: Brief) -> None:
        self.briefs.append(brief)

    def list_briefs(self) -> list[Brief]:
        return list(self.briefs)

    def get_companion_usage(self, user_id: int, day: date) -> int:
        return self.companion_usage.get((user_id, day), 0)

    def increment_companion_usage(self, user_id: int, day: date) -> int:
        key = (user_id, day)
        self.companion_usage[key] = self.companion_usage.get(key, 0) + 1
        return self.companion_usage[key]

    def set_subscription_plan(self, user_id: int, plan: str) -> None:
        self.subscription_plans[user_id] = plan

    def get_subscription_plan(self, user_id: int) -> str:
        return self.subscription_plans.get(user_id, "free")

    def get_user_profile(self, user_id: int, email: str | None = None, locale: str = "en") -> dict:
        profile = self.user_profiles.setdefault(
            user_id,
            {"id": user_id, "email": email or f"user-{user_id}@example.test", "nickname": (email or "user").split("@")[0], "locale": locale, "is_admin": False, "audience_code": "general"},
        )
        if email:
            profile["email"] = email
            profile["nickname"] = email.split("@")[0]
        profile["locale"] = locale or profile.get("locale", "en")
        profile["plan"] = self.get_subscription_plan(user_id)
        return dict(profile)

    def set_user_audience(self, user_id: int, audience_code: str) -> dict:
        if audience_code not in self.audiences:
            raise KeyError(audience_code)
        profile = self.get_user_profile(user_id)
        profile["audience_code"] = audience_code
        self.user_profiles[user_id] = profile
        return dict(profile)

    def require_admin(self, user_id: int) -> bool:
        return bool(self.user_profiles.get(user_id, {}).get("is_admin"))

    def list_taxonomy_categories(self, include_inactive: bool = False) -> list[dict]:
        rows = [dict(row) for row in self.categories.values() if include_inactive or row.get("active", True)]
        return sorted(rows, key=lambda row: (row.get("sort_order", 0), row["code"]))

    def upsert_taxonomy_category(self, data: dict) -> dict:
        current = self.categories.get(data["code"], {})
        row = {
            "code": data["code"],
            "label_en": data.get("label_en", current.get("label_en", data["code"])),
            "label_zh": data.get("label_zh", current.get("label_zh", data.get("label_en", data["code"]))),
            "color_from": data.get("color_from", current.get("color_from", "#4f46e5")),
            "color_to": data.get("color_to", current.get("color_to", "#64748b")),
            "sort_order": data.get("sort_order", current.get("sort_order", len(self.categories))),
            "active": data.get("active", current.get("active", True)),
        }
        self.categories[row["code"]] = row
        return dict(row)

    def delete_taxonomy_category(self, code: str) -> bool:
        if code not in self.categories:
            return False
        del self.categories[code]
        for audience_code, categories in list(self.audience_categories.items()):
            self.audience_categories[audience_code] = [category for category in categories if category != code]
        return True

    def list_audiences(self) -> list[dict]:
        rows = [dict(row) for row in self.audiences.values()]
        return sorted(rows, key=lambda row: (row.get("sort_order", 0), row["code"]))

    def upsert_audience(self, data: dict) -> dict:
        current = self.audiences.get(data["code"], {})
        if data.get("is_default"):
            for row in self.audiences.values():
                row["is_default"] = False
        row = {
            "code": data["code"],
            "label_en": data.get("label_en", current.get("label_en", data["code"])),
            "label_zh": data.get("label_zh", current.get("label_zh", data.get("label_en", data["code"]))),
            "is_default": data.get("is_default", current.get("is_default", False)),
            "sort_order": data.get("sort_order", current.get("sort_order", len(self.audiences))),
        }
        self.audiences[row["code"]] = row
        self.audience_categories.setdefault(row["code"], [])
        return dict(row)

    def delete_audience(self, code: str) -> bool:
        row = self.audiences.get(code)
        if row is None or row.get("is_default") or len(self.audiences) <= 1:
            return False
        del self.audiences[code]
        self.audience_categories.pop(code, None)
        for profile in self.user_profiles.values():
            if profile.get("audience_code") == code:
                profile["audience_code"] = self._default_audience_code()
        return True

    def set_audience_categories(self, audience_code: str, categories: list[str]) -> dict:
        if audience_code not in self.audiences:
            raise KeyError(audience_code)
        missing = [code for code in categories if code not in self.categories]
        if missing:
            raise KeyError(missing[0])
        self.audience_categories[audience_code] = list(dict.fromkeys(categories))
        return self.taxonomy_for_audience(audience_code)

    def taxonomy_for_audience(self, audience_code: str | None = None, locale: str = "en") -> dict:
        selected = audience_code if audience_code in self.audiences else self._default_audience_code()
        category_codes = self.audience_categories.get(selected, [])
        categories = [self.categories[code] for code in category_codes if code in self.categories and self.categories[code].get("active", True)]
        return {
            "categories": [self._localized_category(row, locale) for row in categories],
            "audience": {**self._localized_audience(self.audiences[selected], locale), "categories": [row["code"] for row in categories]},
            "audiences": [self._localized_audience(row, locale) for row in self.list_audiences()],
        }

    def _default_audience_code(self) -> str:
        for row in self.audiences.values():
            if row.get("is_default"):
                return row["code"]
        return next(iter(self.audiences))

    @staticmethod
    def _localized_category(row: dict, locale: str) -> dict:
        return {**row, "label": row["label_zh"] if locale == "zh" else row["label_en"]}

    @staticmethod
    def _localized_audience(row: dict, locale: str) -> dict:
        return {**row, "label": row["label_zh"] if locale == "zh" else row["label_en"]}


class SqlAlchemyL3Repository:
    def __init__(self, session: Session, autocommit: bool = False, close_on_commit: bool = False) -> None:
        self.session = session
        self.autocommit = autocommit
        self.close_on_commit = close_on_commit

    def _commit_if_needed(self) -> None:
        if self.autocommit:
            self.session.commit()

    def _finish(self) -> None:
        if self.close_on_commit:
            self.session.close()

    def get_or_create_user(self, email: str, locale: str = "en") -> dict:
        normalized_email = email.strip().lower()
        try:
            row = self.session.scalars(select(UserModel).where(func.lower(UserModel.email) == normalized_email)).first()
            if row is None:
                row = UserModel(
                    email=normalized_email,
                    nickname=normalized_email.split("@", 1)[0],
                    locale=locale,
                    plan="free",
                    audience_code=self._default_audience_code(),
                )
                self.session.add(row)
                try:
                    self.session.flush()
                except IntegrityError:
                    self.session.rollback()
                    row = self.session.scalars(select(UserModel).where(func.lower(UserModel.email) == normalized_email)).first()
                    if row is None:
                        raise
            row.locale = locale or row.locale
            self.session.flush()
            subscription = self.session.scalars(select(SubscriptionModel).where(SubscriptionModel.user_id == row.id)).first()
            result = {
                "id": row.id,
                "email": row.email,
                "nickname": row.nickname,
                "locale": row.locale,
                "plan": subscription.plan if subscription else "free",
                "is_admin": bool(row.is_admin),
                "audience_code": row.audience_code or self._default_audience_code(),
            }
            self._commit_if_needed()
            return result
        finally:
            self._finish()

    def save_interests(self, user_id: int, tags: list[str]) -> None:
        try:
            self.session.query(UserInterestModel).filter(UserInterestModel.user_id == user_id).delete()
            self.session.add_all([UserInterestModel(user_id=user_id, tag_code=tag, weight=1) for tag in tags])
            self.session.flush()
            self._commit_if_needed()
        finally:
            self._finish()

    def get_interests(self, user_id: int) -> dict[str, int]:
        try:
            rows = self.session.scalars(select(UserInterestModel).where(UserInterestModel.user_id == user_id)).all()
            return {row.tag_code: row.weight for row in rows}
        finally:
            self._finish()

    def add_follow(self, user_id: int, target_type: str, target_id: str) -> list[dict[str, str]]:
        try:
            self.session.add(UserFollowModel(user_id=user_id, target_type=target_type, target_id=target_id))
            self.session.flush()
            rows = self.session.scalars(select(UserFollowModel).where(UserFollowModel.user_id == user_id)).all()
            result = [{"target_type": row.target_type, "target_id": row.target_id} for row in rows]
            self._commit_if_needed()
            return result
        finally:
            self._finish()

    def add_bookmark(self, user_id: int, content_id: str, note: str | None, highlights: list[str]) -> dict:
        try:
            existing = self.session.get(BookmarkModel, {"user_id": user_id, "content_id": content_id})
            if existing is None:
                existing = BookmarkModel(user_id=user_id, content_id=content_id, note=note, highlights=highlights)
                self.session.add(existing)
            else:
                existing.note = note
                existing.highlights = highlights
            self.session.flush()
            self._commit_if_needed()
            return {"content_id": content_id, "note": note, "highlights": highlights}
        finally:
            self._finish()

    def list_bookmarks(self, user_id: int) -> list[dict]:
        try:
            rows = self.session.scalars(select(BookmarkModel).where(BookmarkModel.user_id == user_id)).all()
            return [{"content_id": row.content_id, "note": row.note, "highlights": row.highlights} for row in rows]
        finally:
            self._finish()

    def save_reading_event(self, user_id: int, content_id: str, event_type: str) -> dict:
        try:
            event = ReadingEventModel(user_id=user_id, content_id=content_id, type=event_type)
            self.session.add(event)
            self.session.flush()
            self._commit_if_needed()
            return {"user_id": user_id, "content_id": content_id, "type": event_type}
        finally:
            self._finish()

    def north_star(self, user_id: int | None = None) -> dict[str, int | float]:
        try:
            closed_loop_query = select(func.count()).select_from(ReadingEventModel).where(ReadingEventModel.type.in_(["deep_read", "bookmark"]))
            total_query = select(func.count()).select_from(ReadingEventModel)
            if user_id is not None:
                closed_loop_query = closed_loop_query.where(ReadingEventModel.user_id == user_id)
                total_query = total_query.where(ReadingEventModel.user_id == user_id)
            closed_loop_count = self.session.scalar(closed_loop_query)
            total = self.session.scalar(total_query)
            closed_loop = int(closed_loop_count or 0)
            event_total = int(total or 0)
            return {
                "deep_read_closed_loop_events": closed_loop,
                "reading_events_total": event_total,
                "deep_read_closed_loop_rate": closed_loop / event_total if event_total else 0.0,
            }
        finally:
            self._finish()

    def save_brief(self, brief: Brief) -> None:
        try:
            row = BriefModel(
                user_id=brief.user_id,
                vertical_code=brief.vertical_code,
                brief_date=date.fromisoformat(brief.brief_date),
                items=[item.model_dump(mode="json") for item in brief.items],
                channels=brief.channels,
                status=brief.status,
            )
            self.session.add(row)
            self.session.flush()
            self._commit_if_needed()
        finally:
            self._finish()

    def list_briefs(self) -> list[Brief]:
        try:
            rows = self.session.scalars(select(BriefModel)).all()
            briefs: list[Brief] = []
            for row in rows:
                briefs.append(
                    Brief(
                        id=str(row.id),
                        user_id=row.user_id,
                        vertical_code=row.vertical_code,
                        brief_date=row.brief_date.isoformat(),
                        items=row.items,
                        channels=row.channels,
                        status=row.status,
                    )
                )
            return briefs
        finally:
            self._finish()

    def get_companion_usage(self, user_id: int, day: date) -> int:
        try:
            row = self.session.get(CompanionUsageModel, {"user_id": user_id, "day": day})
            return row.count if row is not None else 0
        finally:
            self._finish()

    def increment_companion_usage(self, user_id: int, day: date) -> int:
        try:
            row = self.session.get(CompanionUsageModel, {"user_id": user_id, "day": day})
            if row is None:
                row = CompanionUsageModel(user_id=user_id, day=day, count=1)
                self.session.add(row)
            else:
                row.count += 1
            self.session.flush()
            count = row.count
            self._commit_if_needed()
            return count
        finally:
            self._finish()

    def set_subscription_plan(self, user_id: int, plan: str) -> None:
        try:
            row = self.session.scalars(select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)).first()
            if row is None:
                row = SubscriptionModel(user_id=user_id, plan=plan, status="active", provider="sandbox", provider_ref=f"sandbox:{user_id}")
                self.session.add(row)
            else:
                row.plan = plan
                row.status = "active" if plan == "pro" else "canceled"
            self.session.flush()
            self._commit_if_needed()
        finally:
            self._finish()

    def get_subscription_plan(self, user_id: int) -> str:
        try:
            row = self.session.scalars(select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)).first()
            return row.plan if row else "free"
        finally:
            self._finish()

    def get_user_profile(self, user_id: int, email: str | None = None, locale: str = "en") -> dict:
        try:
            row = self.session.get(UserModel, user_id)
            if row is None:
                row = UserModel(id=user_id, email=email or f"user-{user_id}@example.test", nickname=(email or "user").split("@")[0], locale=locale, plan="free", audience_code=self._default_audience_code())
                self.session.add(row)
            else:
                if email:
                    row.email = email
                    row.nickname = email.split("@")[0]
                row.locale = locale or row.locale
            self.session.flush()
            self._commit_if_needed()
            return {
                "id": row.id,
                "email": row.email,
                "nickname": row.nickname,
                "locale": row.locale,
                "plan": self.get_subscription_plan(user_id),
                "is_admin": bool(row.is_admin),
                "audience_code": row.audience_code or self._default_audience_code(),
            }
        finally:
            self._finish()

    def set_user_audience(self, user_id: int, audience_code: str) -> dict:
        try:
            if self.session.get(AudienceModel, audience_code) is None:
                raise KeyError(audience_code)
            row = self.session.get(UserModel, user_id)
            if row is None:
                row = UserModel(id=user_id, email=f"user-{user_id}@example.test", nickname=f"user-{user_id}", audience_code=audience_code)
                self.session.add(row)
            else:
                row.audience_code = audience_code
            self.session.flush()
            self._commit_if_needed()
            return self.get_user_profile(user_id, row.email, row.locale)
        finally:
            self._finish()

    def require_admin(self, user_id: int) -> bool:
        try:
            row = self.session.get(UserModel, user_id)
            return bool(row and row.is_admin)
        finally:
            self._finish()

    def list_taxonomy_categories(self, include_inactive: bool = False) -> list[dict]:
        try:
            query = select(TaxonomyCategoryModel)
            if not include_inactive:
                query = query.where(TaxonomyCategoryModel.active.is_(True))
            rows = self.session.scalars(query.order_by(TaxonomyCategoryModel.sort_order, TaxonomyCategoryModel.code)).all()
            return [self._category_dict(row) for row in rows]
        finally:
            self._finish()

    def upsert_taxonomy_category(self, data: dict) -> dict:
        try:
            row = self.session.get(TaxonomyCategoryModel, data["code"])
            if row is None:
                row = TaxonomyCategoryModel(
                    code=data["code"],
                    label_en=data.get("label_en", data["code"]),
                    label_zh=data.get("label_zh", data.get("label_en", data["code"])),
                    color_from=data.get("color_from", "#4f46e5"),
                    color_to=data.get("color_to", "#64748b"),
                    sort_order=data.get("sort_order", 0),
                    active=data.get("active", True),
                )
                self.session.add(row)
            else:
                for field in ["label_en", "label_zh", "color_from", "color_to", "sort_order", "active"]:
                    if field in data:
                        setattr(row, field, data[field])
            self.session.flush()
            self._commit_if_needed()
            return self._category_dict(row)
        finally:
            self._finish()

    def delete_taxonomy_category(self, code: str) -> bool:
        try:
            row = self.session.get(TaxonomyCategoryModel, code)
            if row is None:
                return False
            self.session.query(AudienceCategoryModel).filter(AudienceCategoryModel.category_code == code).delete()
            self.session.delete(row)
            self.session.flush()
            self._commit_if_needed()
            return True
        finally:
            self._finish()

    def list_audiences(self) -> list[dict]:
        try:
            rows = self.session.scalars(select(AudienceModel).order_by(AudienceModel.sort_order, AudienceModel.code)).all()
            return [self._audience_dict(row) for row in rows]
        finally:
            self._finish()

    def upsert_audience(self, data: dict) -> dict:
        try:
            if data.get("is_default"):
                self.session.query(AudienceModel).update({"is_default": False})
            row = self.session.get(AudienceModel, data["code"])
            if row is None:
                row = AudienceModel(
                    code=data["code"],
                    label_en=data.get("label_en", data["code"]),
                    label_zh=data.get("label_zh", data.get("label_en", data["code"])),
                    is_default=data.get("is_default", False),
                    sort_order=data.get("sort_order", 0),
                )
                self.session.add(row)
            else:
                for field in ["label_en", "label_zh", "is_default", "sort_order"]:
                    if field in data:
                        setattr(row, field, data[field])
            self.session.flush()
            self._commit_if_needed()
            return self._audience_dict(row)
        finally:
            self._finish()

    def delete_audience(self, code: str) -> bool:
        try:
            row = self.session.get(AudienceModel, code)
            count = self.session.scalar(select(func.count()).select_from(AudienceModel)) or 0
            if row is None or row.is_default or count <= 1:
                return False
            default_code = self._default_audience_code()
            self.session.query(UserModel).filter(UserModel.audience_code == code).update({"audience_code": default_code})
            self.session.query(AudienceCategoryModel).filter(AudienceCategoryModel.audience_code == code).delete()
            self.session.delete(row)
            self.session.flush()
            self._commit_if_needed()
            return True
        finally:
            self._finish()

    def set_audience_categories(self, audience_code: str, categories: list[str]) -> dict:
        try:
            if self.session.get(AudienceModel, audience_code) is None:
                raise KeyError(audience_code)
            for code in categories:
                if self.session.get(TaxonomyCategoryModel, code) is None:
                    raise KeyError(code)
            self.session.query(AudienceCategoryModel).filter(AudienceCategoryModel.audience_code == audience_code).delete()
            for position, code in enumerate(dict.fromkeys(categories)):
                self.session.add(AudienceCategoryModel(audience_code=audience_code, category_code=code, position=position))
            self.session.flush()
            self._commit_if_needed()
            return self.taxonomy_for_audience(audience_code)
        finally:
            self._finish()

    def taxonomy_for_audience(self, audience_code: str | None = None, locale: str = "en") -> dict:
        try:
            selected = audience_code if audience_code and self.session.get(AudienceModel, audience_code) else self._default_audience_code()
            audience = self.session.get(AudienceModel, selected)
            rows = self.session.scalars(
                select(TaxonomyCategoryModel)
                .join(AudienceCategoryModel, AudienceCategoryModel.category_code == TaxonomyCategoryModel.code)
                .where(AudienceCategoryModel.audience_code == selected, TaxonomyCategoryModel.active.is_(True))
                .order_by(AudienceCategoryModel.position, TaxonomyCategoryModel.sort_order)
            ).all()
            audiences = self.session.scalars(select(AudienceModel).order_by(AudienceModel.sort_order, AudienceModel.code)).all()
            return {
                "categories": [self._localized_category(self._category_dict(row), locale) for row in rows],
                "audience": {**self._localized_audience(self._audience_dict(audience), locale), "categories": [row.code for row in rows]},
                "audiences": [self._localized_audience(self._audience_dict(row), locale) for row in audiences],
            }
        finally:
            self._finish()

    def _default_audience_code(self) -> str:
        row = self.session.scalars(select(AudienceModel).where(AudienceModel.is_default.is_(True))).first()
        if row:
            return row.code
        row = self.session.scalars(select(AudienceModel).order_by(AudienceModel.sort_order, AudienceModel.code)).first()
        if row:
            return row.code
        # Allows tests using Base.metadata.create_all without Alembic seeds.
        for data in DEFAULT_CATEGORIES:
            self.session.merge(TaxonomyCategoryModel(**data))
        for data in DEFAULT_AUDIENCES:
            self.session.merge(AudienceModel(**data))
        for audience in DEFAULT_AUDIENCES:
            for position, category in enumerate(DEFAULT_CATEGORIES):
                self.session.merge(AudienceCategoryModel(audience_code=audience["code"], category_code=category["code"], position=position))
        self.session.flush()
        return "general"

    @staticmethod
    def _category_dict(row: TaxonomyCategoryModel) -> dict:
        return {"code": row.code, "label_en": row.label_en, "label_zh": row.label_zh, "color_from": row.color_from, "color_to": row.color_to, "sort_order": row.sort_order, "active": row.active}

    @staticmethod
    def _audience_dict(row: AudienceModel) -> dict:
        return {"code": row.code, "label_en": row.label_en, "label_zh": row.label_zh, "is_default": row.is_default, "sort_order": row.sort_order}

    @staticmethod
    def _localized_category(row: dict, locale: str) -> dict:
        return {**row, "label": row["label_zh"] if locale == "zh" else row["label_en"]}

    @staticmethod
    def _localized_audience(row: dict, locale: str) -> dict:
        return {**row, "label": row["label_zh"] if locale == "zh" else row["label_en"]}


repository = InMemoryL3Repository()


def get_repository() -> L3Repository:
    if os.getenv("L3_REPOSITORY_BACKEND", "memory").lower() == "sqlalchemy":
        from .db import get_sessionmaker

        return SqlAlchemyL3Repository(get_sessionmaker()(), autocommit=True, close_on_commit=True)
    return repository
