"""Use SQLite rowid-compatible types for generated L3 primary keys.

Revision ID: 0003_sqlite_generated_ids
Revises: 0002_taxonomy

SQLite generates an omitted primary key only when its declared type is exactly
INTEGER, not BIGINT. PostgreSQL already generates the original BIGSERIAL keys;
it must not be changed. Existing IDs and referencing rows are copied unchanged.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_sqlite_generated_ids"
down_revision = "0002_taxonomy"
branch_labels = None
depends_on = None

GENERATED_ID_TABLES = (
    "users",
    "subscriptions",
    "user_follows",
    "reading_events",
    "briefs",
    "api_keys",
)


def _rebuild_sqlite_ids(target_type: sa.types.TypeEngine) -> None:
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        return
    context = op.get_context()
    if context.as_sql:
        raise RuntimeError(
            "SQLite generated-ID migration requires an online connection"
        )

    foreign_keys = bool(connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
    if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
        raise RuntimeError(
            "Refusing to rebuild SQLite tables with existing foreign-key violations"
        )

    def set_foreign_keys(enabled: bool) -> None:
        # SQLite ignores this PRAGMA inside a transaction. Alembic's documented
        # block commits preceding revisions before temporarily disabling checks.
        with context.autocommit_block():
            connection.exec_driver_sql(
                f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}"
            )
            actual = bool(
                connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
            )
            if actual != enabled:
                raise RuntimeError(
                    "Unable to change SQLite foreign-key enforcement for migration"
                )

    if foreign_keys:
        set_foreign_keys(False)
    try:
        # Explicit SAVEPOINT also makes SQLite's legacy-driver DDL transactional:
        # a failed copy/check rolls back all six rebuilds, not just the last one.
        with connection.begin_nested():
            for table in GENERATED_ID_TABLES:
                with op.batch_alter_table(table, recreate="always") as batch:
                    batch.alter_column("id", type_=target_type, existing_nullable=False)
            if (
                connection.exec_driver_sql("PRAGMA foreign_key_check").first()
                is not None
            ):
                raise RuntimeError(
                    "SQLite generated-ID migration would break foreign keys"
                )
    finally:
        if foreign_keys:
            set_foreign_keys(True)


def upgrade() -> None:
    _rebuild_sqlite_ids(sa.Integer())


def downgrade() -> None:
    _rebuild_sqlite_ids(sa.BigInteger())
