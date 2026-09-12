from __future__ import annotations

import os
from pathlib import Path
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "subscriptions",
    "user_interests",
    "user_follows",
    "reading_events",
    "briefs",
    "bookmarks",
    "api_keys",
    "api_usage_daily",
    "companion_usage",
    "taxonomy_categories",
    "audiences",
    "audience_categories",
}


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "db" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "db" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def run_migration_smoke(database_url: str | None = None) -> dict:
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if database_url is None:
        temp_dir = tempfile.TemporaryDirectory()
        database_url = f"sqlite:///{Path(temp_dir.name) / 'l3_migration_smoke.db'}"

    try:
        config = _config(database_url)
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        try:
            tables_after_upgrade = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        missing = EXPECTED_TABLES - tables_after_upgrade
        if missing:
            raise RuntimeError(f"migration missing tables: {sorted(missing)}")

        command.downgrade(config, "base")
        engine = create_engine(database_url)
        try:
            tables_after_downgrade = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        remaining_owned = EXPECTED_TABLES & tables_after_downgrade
        if remaining_owned:
            raise RuntimeError(f"downgrade left L3 tables behind: {sorted(remaining_owned)}")

        return {
            "status": "ok",
            "database_url": database_url,
            "created_tables": sorted(EXPECTED_TABLES),
        }
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def main() -> None:
    database_url = os.getenv("L3_MIGRATION_SMOKE_DATABASE_URL")
    report = run_migration_smoke(database_url)
    print("L3 MIGRATION: PASS")
    print(f"created_tables={','.join(report['created_tables'])}")


if __name__ == "__main__":
    main()
