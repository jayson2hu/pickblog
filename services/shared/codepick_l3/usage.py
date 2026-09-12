from dataclasses import dataclass, field
from datetime import date, timedelta
from fastapi import Header, HTTPException
import hashlib
import os
import secrets
import time
from typing import Protocol

from .config import get_settings


@dataclass
class ApiKeyRecord:
    key_hash: str
    prefix: str
    owner_user_id: int
    scopes: list[str] = field(default_factory=lambda: ["read"])
    rate_limit_rpm: int = 20
    daily_quota: int = 200
    status: str = "active"


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RateWindow:
    def __init__(self) -> None:
        self.minute: dict[str, tuple[int, int]] = {}

    def check(self, key_hash: str, rpm: int) -> None:
        current_window = int(time.time() // 60)
        window, count = self.minute.get(key_hash, (current_window, 0))
        if window != current_window:
            window, count = current_window, 0
        count += 1
        self.minute[key_hash] = (window, count)
        if count > rpm:
            reset_seconds = max(1, 60 - int(time.time() % 60))
            raise HTTPException(status_code=429, detail={"error": "rate_limit_exceeded", "reset_seconds": reset_seconds})


rate_window = RateWindow()


class InMemoryQuotaStore:
    def __init__(self) -> None:
        self.keys: dict[str, ApiKeyRecord] = {}
        self.daily: dict[tuple[str, date], int] = {}

    def add_key(self, raw_key: str, owner_user_id: int = 1, daily_quota: int | None = None, rpm: int | None = None) -> ApiKeyRecord:
        settings = get_settings()
        record = ApiKeyRecord(
            key_hash=hash_key(raw_key),
            prefix=raw_key[:8],
            owner_user_id=owner_user_id,
            daily_quota=daily_quota or settings.api_quota_free_day,
            rate_limit_rpm=rpm or settings.api_rate_free_rpm,
        )
        self.keys[record.key_hash] = record
        return record

    def list_for_owner(self, owner_user_id: int) -> list[ApiKeyRecord]:
        return [record for record in self.keys.values() if record.owner_user_id == owner_user_id]

    def revoke(self, owner_user_id: int, key_hash_or_prefix: str) -> bool:
        for record in self.keys.values():
            if record.owner_user_id == owner_user_id and key_hash_or_prefix in {record.key_hash, record.prefix}:
                record.status = "revoked"
                return True
        return False

    def check(self, raw_key: str) -> ApiKeyRecord:
        record = self.keys.get(hash_key(raw_key))
        if not record or record.status != "active":
            raise HTTPException(status_code=401, detail="invalid api key")
        if "read" not in record.scopes:
            raise HTTPException(status_code=403, detail="read scope required")
        rate_window.check(record.key_hash, record.rate_limit_rpm)
        today = date.today()
        key = (record.key_hash, today)
        count = self.daily.get(key, 0) + 1
        self.daily[key] = count
        if count > record.daily_quota:
            raise HTTPException(status_code=429, detail={"error": "daily_quota_exceeded", "reset_seconds": 86400})
        return record


quota_store = InMemoryQuotaStore()
quota_store.add_key("cp_test_key", daily_quota=200, rpm=20)


class QuotaStore(Protocol):
    def check(self, raw_key: str) -> ApiKeyRecord: ...


class SqlAlchemyQuotaStore:
    def check(self, raw_key: str) -> ApiKeyRecord:
        from sqlalchemy import select

        from .db import get_sessionmaker
        from .models import ApiKeyModel, ApiUsageDailyModel

        session = get_sessionmaker()()
        try:
            row = session.scalars(select(ApiKeyModel).where(ApiKeyModel.key_hash == hash_key(raw_key))).first()
            if row is None or row.status != "active":
                raise HTTPException(status_code=401, detail="invalid api key")
            if "read" not in row.scopes:
                raise HTTPException(status_code=403, detail="read scope required")
            rate_window.check(row.key_hash, row.rate_limit_rpm)

            today = date.today()
            usage = session.get(ApiUsageDailyModel, {"key_id": row.id, "day": today})
            if usage is None:
                usage = ApiUsageDailyModel(key_id=row.id, day=today, count=1)
                session.add(usage)
            else:
                usage.count += 1

            if usage.count > row.daily_quota:
                session.commit()
                raise HTTPException(status_code=429, detail={"error": "daily_quota_exceeded", "reset_seconds": 86400})

            session.commit()
            return ApiKeyRecord(
                key_hash=row.key_hash,
                prefix=row.prefix,
                owner_user_id=row.owner_user_id,
                scopes=list(row.scopes),
                rate_limit_rpm=row.rate_limit_rpm,
                daily_quota=row.daily_quota,
                status=row.status,
            )
        except HTTPException:
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_quota_store() -> QuotaStore:
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        return SqlAlchemyQuotaStore()
    return quota_store


def _new_raw_key() -> str:
    return f"cp_{secrets.token_urlsafe(24)}"


def _api_key_response(record: ApiKeyRecord, raw_key: str | None = None) -> dict:
    data = {
        "prefix": record.prefix,
        "scopes": record.scopes,
        "rate_limit_rpm": record.rate_limit_rpm,
        "daily_quota": record.daily_quota,
        "status": record.status,
    }
    if raw_key is not None:
        data["key"] = raw_key
    return data


def create_api_key(owner_user_id: int, scopes: list[str] | None = None) -> dict:
    settings = get_settings()
    raw_key = _new_raw_key()
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        from .db import get_sessionmaker
        from .models import ApiKeyModel

        session = get_sessionmaker()()
        try:
            row = ApiKeyModel(
                owner_user_id=owner_user_id,
                key_hash=hash_key(raw_key),
                prefix=raw_key[:8],
                scopes=scopes or ["read"],
                rate_limit_rpm=settings.api_rate_free_rpm,
                daily_quota=settings.api_quota_free_day,
                status="active",
            )
            session.add(row)
            session.commit()
            return _api_key_response(
                ApiKeyRecord(
                    key_hash=row.key_hash,
                    prefix=row.prefix,
                    owner_user_id=row.owner_user_id,
                    scopes=list(row.scopes),
                    rate_limit_rpm=row.rate_limit_rpm,
                    daily_quota=row.daily_quota,
                    status=row.status,
                ),
                raw_key=raw_key,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    record = quota_store.add_key(raw_key, owner_user_id=owner_user_id, daily_quota=settings.api_quota_free_day, rpm=settings.api_rate_free_rpm)
    record.scopes = scopes or ["read"]
    return _api_key_response(record, raw_key=raw_key)


def list_api_keys(owner_user_id: int) -> list[dict]:
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        from sqlalchemy import select

        from .db import get_sessionmaker
        from .models import ApiKeyModel

        session = get_sessionmaker()()
        try:
            rows = session.scalars(select(ApiKeyModel).where(ApiKeyModel.owner_user_id == owner_user_id)).all()
            return [
                _api_key_response(
                    ApiKeyRecord(
                        key_hash=row.key_hash,
                        prefix=row.prefix,
                        owner_user_id=row.owner_user_id,
                        scopes=list(row.scopes),
                        rate_limit_rpm=row.rate_limit_rpm,
                        daily_quota=row.daily_quota,
                        status=row.status,
                    )
                )
                for row in rows
            ]
        finally:
            session.close()

    return [_api_key_response(record) for record in quota_store.list_for_owner(owner_user_id)]


def api_key_usage_days(owner_user_id: int, window: int = 7) -> dict:
    today = date.today()
    days = [today - timedelta(days=offset) for offset in range(window - 1, -1, -1)]
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        from sqlalchemy import select

        from .db import get_sessionmaker
        from .models import ApiKeyModel, ApiUsageDailyModel

        session = get_sessionmaker()()
        try:
            key_ids = [row.id for row in session.scalars(select(ApiKeyModel).where(ApiKeyModel.owner_user_id == owner_user_id)).all()]
            counts = {day: 0 for day in days}
            if key_ids:
                rows = session.scalars(select(ApiUsageDailyModel).where(ApiUsageDailyModel.key_id.in_(key_ids)).where(ApiUsageDailyModel.day.in_(days))).all()
                for row in rows:
                    counts[row.day] += row.count
            return {"days": [{"day": day.isoformat(), "count": counts[day]} for day in days], "window": window}
        finally:
            session.close()

    owner_hashes = {record.key_hash for record in quota_store.list_for_owner(owner_user_id)}
    counts = {day: 0 for day in days}
    for (key_hash, day), count in quota_store.daily.items():
        if key_hash in owner_hashes and day in counts:
            counts[day] += count
    return {"days": [{"day": day.isoformat(), "count": counts[day]} for day in days], "window": window}


def revoke_api_key(owner_user_id: int, key_hash_or_prefix: str) -> bool:
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        from sqlalchemy import select

        from .db import get_sessionmaker
        from .models import ApiKeyModel

        session = get_sessionmaker()()
        try:
            row = session.scalars(
                select(ApiKeyModel).where(ApiKeyModel.owner_user_id == owner_user_id).where((ApiKeyModel.key_hash == key_hash_or_prefix) | (ApiKeyModel.prefix == key_hash_or_prefix))
            ).first()
            if row is None:
                return False
            row.status = "revoked"
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return quota_store.revoke(owner_user_id, key_hash_or_prefix)


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> ApiKeyRecord:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing api key")
    return get_quota_store().check(x_api_key)


def require_api_key_identity(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> ApiKeyRecord:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing api key")

    key_hash = hash_key(x_api_key)
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() == "sqlalchemy":
        from sqlalchemy import select

        from .db import get_sessionmaker
        from .models import ApiKeyModel

        session = get_sessionmaker()()
        try:
            row = session.scalars(select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)).first()
            if row is None or row.status != "active":
                raise HTTPException(status_code=401, detail="invalid api key")
            if "read" not in row.scopes:
                raise HTTPException(status_code=403, detail="read scope required")
            return ApiKeyRecord(
                key_hash=row.key_hash,
                prefix=row.prefix,
                owner_user_id=row.owner_user_id,
                scopes=list(row.scopes),
                rate_limit_rpm=row.rate_limit_rpm,
                daily_quota=row.daily_quota,
                status=row.status,
            )
        finally:
            session.close()

    record = quota_store.keys.get(key_hash)
    if not record or record.status != "active":
        raise HTTPException(status_code=401, detail="invalid api key")
    if "read" not in record.scopes:
        raise HTTPException(status_code=403, detail="read scope required")
    return record
