from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from codepick_l3.config import reset_settings_cache
from codepick_l3.db import get_engine, get_sessionmaker
from codepick_l3.repository import get_repository
from codepick_l3.schemas import Brief
from codepick_l3.usage import get_quota_store
from fastapi.testclient import TestClient
from reader_api.main import app
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "0002_taxonomy"
CURRENT = "0003_sqlite_generated_ids"
GENERATED_TABLES = (
    "users",
    "subscriptions",
    "user_follows",
    "reading_events",
    "briefs",
    "api_keys",
)
LEGACY_ID = 2**40 + 17  # SQLite INTEGER must retain 64-bit IDs, not narrow them.


def config_for(url: str, output: StringIO | None = None) -> Config:
    config = Config(str(ROOT / "db/alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "db/alembic"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["database_url_explicit"] = True
    return config


@pytest.fixture(params=[False, True], ids=["foreign_keys_off", "foreign_keys_on"])
def foreign_key_mode(request):
    enabled = request.param
    closed_states = []

    def configure(connection, _record):
        if isinstance(connection, sqlite3.Connection):
            connection.execute(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}")

    def check_on_close(connection, _record):
        if isinstance(connection, sqlite3.Connection):
            closed_states.append(
                bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
            )

    sa.event.listen(Engine, "connect", configure)
    sa.event.listen(Engine, "close", check_on_close)
    try:
        yield enabled
        assert closed_states
        assert all(state == enabled for state in closed_states)
    finally:
        sa.event.remove(Engine, "connect", configure)
        sa.event.remove(Engine, "close", check_on_close)


def snapshot(engine):
    metadata = sa.MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        return {
            name: [
                dict(row)
                for row in connection.execute(
                    sa.select(table).order_by(*table.primary_key.columns)
                ).mappings()
            ]
            for name, table in sorted(metadata.tables.items())
            if name != "alembic_version"
        }


def foreign_keys(engine):
    inspector = sa.inspect(engine)
    return {
        name: inspector.get_foreign_keys(name) for name in inspector.get_table_names()
    }


def assert_primary_key_types(engine, expected: str) -> None:
    inspector = sa.inspect(engine)
    for name in GENERATED_TABLES:
        column = next(
            column for column in inspector.get_columns(name) if column["name"] == "id"
        )
        assert str(column["type"]) == expected, name
        assert inspector.get_pk_constraint(name)["constrained_columns"] == ["id"]


def seed_legacy(engine) -> None:
    metadata = sa.MetaData()
    metadata.reflect(engine)
    day = date(2026, 9, 17)
    rows = {
        "users": {
            "id": LEGACY_ID,
            "email": "legacy@example.com",
            "nickname": "保留用户",
            "locale": "zh",
            "plan": "pro",
            "is_admin": True,
            "audience_code": "builders",
        },
        "subscriptions": {
            "id": LEGACY_ID + 1,
            "user_id": LEGACY_ID,
            "plan": "pro",
            "status": "active",
            "provider": "sandbox",
            "provider_ref": "keep-subscription",
        },
        "user_interests": {
            "user_id": LEGACY_ID,
            "tag_code": "agent-engineering",
            "weight": 7,
        },
        "user_follows": {
            "id": LEGACY_ID + 2,
            "user_id": LEGACY_ID,
            "target_type": "source",
            "target_id": "keep-source",
        },
        "reading_events": {
            "id": LEGACY_ID + 3,
            "user_id": LEGACY_ID,
            "content_id": "keep-content",
            "type": "deep_read",
            "ts": datetime(2026, 9, 17, 12, tzinfo=UTC),
        },
        "briefs": {
            "id": LEGACY_ID + 4,
            "user_id": LEGACY_ID,
            "vertical_code": "ai-coding",
            "brief_date": day,
            "items": [{"title": "保留摘要"}],
            "channels": {"web": True},
            "status": "generated",
        },
        "bookmarks": {
            "user_id": LEGACY_ID,
            "content_id": "keep-content",
            "note": "保留笔记",
            "highlights": ["keep highlight"],
        },
        "api_keys": {
            "id": LEGACY_ID + 5,
            "owner_user_id": LEGACY_ID,
            "key_hash": "keep-key-hash",
            "prefix": "cp_keep",
            "scopes": ["read"],
            "rate_limit_rpm": 20,
            "daily_quota": 200,
            "status": "active",
        },
        "api_usage_daily": {"key_id": LEGACY_ID + 5, "day": day, "count": 11},
        "companion_usage": {"user_id": LEGACY_ID, "day": day, "count": 3},
    }
    with engine.begin() as connection:
        for name, values in rows.items():
            connection.execute(metadata.tables[name].insert().values(**values))
    sa.Index(
        "ix_preserved_reading_owner", metadata.tables["reading_events"].c.user_id
    ).create(engine)


def test_migration_preserves_all_rows_and_constraints_in_both_directions(
    tmp_path, foreign_key_mode
) -> None:
    url = f"sqlite:///{tmp_path / 'round-trip.db'}"
    config = config_for(url)
    command.upgrade(config, PREVIOUS)
    engine = sa.create_engine(url)
    try:
        seed_legacy(engine)
        before = snapshot(engine)
        original_fks = foreign_keys(engine)
        original_indexes = sa.inspect(engine).get_indexes("reading_events")
        assert_primary_key_types(engine, "BIGINT")
        for direction, revision, expected in [
            (command.upgrade, "head", "INTEGER"),
            (command.downgrade, PREVIOUS, "BIGINT"),
            (command.upgrade, "head", "INTEGER"),
        ]:
            direction(config, revision)
            assert snapshot(engine) == before
            assert foreign_keys(engine) == original_fks
            assert sa.inspect(engine).get_indexes("reading_events") == original_indexes
            assert_primary_key_types(engine, expected)
            with engine.connect() as connection:
                assert (
                    connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
                )
                assert (
                    bool(connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
                    == foreign_key_mode
                )
        # Unique constraints must still protect the copied parent data.
        with engine.begin() as connection:
            with pytest.raises(sa.exc.IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO users (email) VALUES ('legacy@example.com')"
                )
            with pytest.raises(sa.exc.IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO api_keys (owner_user_id,key_hash,prefix,scopes,rate_limit_rpm,daily_quota,status) "
                    "VALUES (?, 'keep-key-hash', 'cp_copy', '[]', 20, 200, 'active')",
                    (LEGACY_ID,),
                )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "with_legacy_data", [False, True], ids=["fresh", "upgraded_data"]
)
def test_alembic_database_supports_real_application_inserts(
    tmp_path, monkeypatch, foreign_key_mode, with_legacy_data
) -> None:
    url = f"sqlite:///{tmp_path / 'application.db'}"
    config = config_for(url)
    command.upgrade(config, PREVIOUS)
    engine = sa.create_engine(url)
    if with_legacy_data:
        seed_legacy(engine)
    before = snapshot(engine)
    command.upgrade(config, "head")
    for key, value in {
        "DATABASE_URL": url,
        "L3_REPOSITORY_BACKEND": "sqlalchemy",
        "L3_QUOTA_BACKEND": "sqlalchemy",
        "L3_USE_STUB_L2": "true",
        "L3_AUTH_LOGIN_MODE": "development",
        "EMAIL_PROVIDER": "mock",
        "BILLING_ENVIRONMENT": "sandbox",
    }.items():
        monkeypatch.setenv(key, value)
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()
    reset_settings_cache()
    try:
        client = TestClient(app)
        login = client.post(
            "/api/auth/login", json={"email": "migrated@example.com", "locale": "zh"}
        )
        assert login.status_code == 200, login.text
        user_id = login.json()["user"]["id"]
        assert user_id > (LEGACY_ID if with_legacy_data else 0)
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        assert (
            client.post(
                "/api/auth/login", json={"email": "migrated@example.com"}
            ).json()["user"]["id"]
            == user_id
        )
        follow = client.post(
            "/api/follow",
            json={"target_type": "source", "target_id": "real-migrated-source"},
            headers=headers,
        )
        assert follow.status_code == 200, follow.text
        event = client.post(
            "/api/events",
            json={"content_id": "cp-001", "type": "deep_read"},
            headers=headers,
        )
        assert event.status_code == 200, event.text
        bookmark = client.post(
            "/api/bookmarks",
            json={"content_id": "cp-001", "note": "真实迁移后写入"},
            headers=headers,
        )
        assert bookmark.status_code == 200, bookmark.text
        key = client.post("/api/api-keys", json={"scopes": ["read"]}, headers=headers)
        assert key.status_code == 200, key.text
        assert get_quota_store().check(key.json()["key"]).owner_user_id == user_id
        repository = get_repository()
        repository.set_subscription_plan(user_id, "pro")
        repository.save_brief(
            Brief(
                id="temporary",
                user_id=user_id,
                vertical_code="ai-coding",
                brief_date="2026-09-17",
                items=[],
                channels={"web": True},
            )
        )
        assert (
            repository.increment_companion_usage(user_id, datetime.now(UTC).date()) == 1
        )
        after = snapshot(engine)
        for table in GENERATED_TABLES:
            new_rows = [row for row in after[table] if row not in before[table]]
            assert new_rows, table
            old_max = max((row["id"] for row in before[table]), default=0)
            assert all(
                isinstance(row["id"], int) and row["id"] > old_max for row in new_rows
            )
        for table, rows in before.items():
            assert all(row in after[table] for row in rows), table
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert (
            client.get("/api/bookmarks", headers=headers).json()["items"][0]["note"]
            == "真实迁移后写入"
        )
    finally:
        if get_engine.cache_info().currsize:
            get_engine().dispose()
        get_sessionmaker.cache_clear()
        get_engine.cache_clear()
        reset_settings_cache()
        engine.dispose()


def test_failed_rebuild_rolls_back_every_table_and_preserves_data(
    tmp_path, foreign_key_mode
) -> None:
    url = f"sqlite:///{tmp_path / 'rollback.db'}"
    config = config_for(url)
    command.upgrade(config, PREVIOUS)
    engine = sa.create_engine(url)
    seed_legacy(engine)
    before = snapshot(engine)

    def fail_last_copy(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ):
        if statement.startswith("INSERT INTO _alembic_tmp_api_keys"):
            raise RuntimeError("injected final-table copy failure")

    sa.event.listen(Engine, "before_cursor_execute", fail_last_copy)
    try:
        with pytest.raises(RuntimeError, match="final-table copy failure"):
            command.upgrade(config, "head")
    finally:
        sa.event.remove(Engine, "before_cursor_execute", fail_last_copy)
    try:
        assert snapshot(engine) == before
        assert_primary_key_types(engine, "BIGINT")
        assert not any(
            name.startswith("_alembic_tmp")
            for name in sa.inspect(engine).get_table_names()
        )
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == PREVIOUS
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        command.upgrade(config, "head")
        assert snapshot(engine) == before
        assert_primary_key_types(engine, "INTEGER")
    finally:
        engine.dispose()


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_postgresql_revision_has_no_schema_changes_or_connection(direction) -> None:
    output = StringIO()
    config = config_for(
        "postgresql+psycopg://unused:unused@127.0.0.1/never_connect", output
    )
    if direction == "upgrade":
        command.upgrade(config, f"{PREVIOUS}:{CURRENT}", sql=True)
    else:
        command.downgrade(config, f"{CURRENT}:{PREVIOUS}", sql=True)
    sql = output.getvalue().upper()
    assert "UPDATE ALEMBIC_VERSION" in sql
    assert "ALTER TABLE" not in sql
    assert "CREATE TABLE" not in sql
    assert "DROP TABLE" not in sql
    assert "PRAGMA" not in sql
