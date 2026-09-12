"""create l3 owned tables

Revision ID: 0001_l3_owned_tables
Revises:
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_l3_owned_tables"
down_revision = None
branch_labels = None
depends_on = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
ArrayTextType = sa.JSON().with_variant(postgresql.ARRAY(sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("nickname", sa.String(length=120)),
        sa.Column("locale", sa.String(length=12), nullable=False, server_default="en"),
        sa.Column("plan", sa.String(length=24), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_ref", sa.String(length=160), nullable=False),
    )
    op.create_table("user_interests", sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("tag_code", sa.String(length=64), primary_key=True), sa.Column("weight", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("user_follows", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False), sa.Column("target_type", sa.String(length=32), nullable=False), sa.Column("target_id", sa.String(length=160), nullable=False))
    op.create_table("reading_events", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False), sa.Column("content_id", sa.String(length=160), nullable=False), sa.Column("type", sa.String(length=48), nullable=False), sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("briefs", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id")), sa.Column("vertical_code", sa.String(length=64)), sa.Column("brief_date", sa.Date(), nullable=False), sa.Column("items", JsonType, nullable=False), sa.Column("channels", JsonType, nullable=False), sa.Column("status", sa.String(length=32), nullable=False))
    op.create_table("bookmarks", sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("content_id", sa.String(length=160), primary_key=True), sa.Column("note", sa.Text()), sa.Column("highlights", JsonType, nullable=False))
    op.create_table("api_keys", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("owner_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False), sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True), sa.Column("prefix", sa.String(length=16), nullable=False), sa.Column("scopes", ArrayTextType, nullable=False), sa.Column("rate_limit_rpm", sa.Integer(), nullable=False), sa.Column("daily_quota", sa.Integer(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False))
    op.create_table("api_usage_daily", sa.Column("key_id", sa.BigInteger(), sa.ForeignKey("api_keys.id"), primary_key=True), sa.Column("day", sa.Date(), primary_key=True), sa.Column("count", sa.Integer(), nullable=False))
    op.create_table("companion_usage", sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("day", sa.Date(), primary_key=True), sa.Column("count", sa.Integer(), nullable=False))


def downgrade() -> None:
    for table in ["companion_usage", "api_usage_daily", "api_keys", "bookmarks", "briefs", "reading_events", "user_follows", "user_interests", "subscriptions", "users"]:
        op.drop_table(table)
