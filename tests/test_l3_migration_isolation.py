from contextlib import closing
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from scripts import l3_migration_smoke


def _sentinel_database(path: Path) -> tuple[str, bytes]:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES (1, 'preserve this data')")
        connection.commit()
    return f"sqlite:///{path.as_posix()}", path.read_bytes()


def _table_names(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as connection:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_default_migration_smoke_ignores_runtime_database_url(tmp_path, monkeypatch) -> None:
    sentinel_path = tmp_path / "runtime.db"
    sentinel_url, original_bytes = _sentinel_database(sentinel_path)
    monkeypatch.setenv("DATABASE_URL", sentinel_url)
    try:
        report = l3_migration_smoke.run_migration_smoke()
        assert report["status"] == "ok"
        assert report["database_url"] != sentinel_url
        assert set(report["created_tables"]) == l3_migration_smoke.EXPECTED_TABLES
    finally:
        assert sentinel_path.read_bytes() == original_bytes


def test_explicit_migration_smoke_database_takes_priority(tmp_path, monkeypatch, capsys) -> None:
    sentinel_path = tmp_path / "runtime.db"
    sentinel_url, original_bytes = _sentinel_database(sentinel_path)
    smoke_path = tmp_path / "explicit-smoke.db"
    monkeypatch.setenv("DATABASE_URL", sentinel_url)
    monkeypatch.setenv("L3_MIGRATION_SMOKE_DATABASE_URL", f"sqlite:///{smoke_path.as_posix()}")
    try:
        l3_migration_smoke.main()
        assert "L3 MIGRATION: PASS" in capsys.readouterr().out
        assert smoke_path.exists()
        assert _table_names(smoke_path) == {"alembic_version"}
    finally:
        assert sentinel_path.read_bytes() == original_bytes


def test_normal_alembic_migrations_still_use_runtime_database_url(tmp_path, monkeypatch) -> None:
    runtime_path = tmp_path / "runtime.db"
    unused_path = tmp_path / "unused-config.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{runtime_path.as_posix()}")
    config = Config(str(l3_migration_smoke.ROOT / "db" / "alembic.ini"))
    config.set_main_option("script_location", str(l3_migration_smoke.ROOT / "db" / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{unused_path.as_posix()}")
    command.upgrade(config, "head")
    assert _table_names(runtime_path) == l3_migration_smoke.EXPECTED_TABLES | {"alembic_version"}
    assert not unused_path.exists()
    command.downgrade(config, "base")
    assert _table_names(runtime_path) == {"alembic_version"}