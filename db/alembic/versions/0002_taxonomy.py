"""add l3 taxonomy tables

Revision ID: 0002_taxonomy
Revises: 0001_l3_owned_tables
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_taxonomy"
down_revision = "0001_l3_owned_tables"
branch_labels = None
depends_on = None


DEFAULT_CATEGORIES = [
    {"code": "ai", "label_en": "AI", "label_zh": "AI", "color_from": "#4f46e5", "color_to": "#14b8a6", "sort_order": 0},
    {"code": "data", "label_en": "Data", "label_zh": "数据", "color_from": "#0f766e", "color_to": "#2563eb", "sort_order": 1},
    {"code": "infra", "label_en": "Infrastructure", "label_zh": "基础设施", "color_from": "#334155", "color_to": "#4f46e5", "sort_order": 2},
    {"code": "product", "label_en": "Product", "label_zh": "产品", "color_from": "#7c3aed", "color_to": "#db2777", "sort_order": 3},
]

DEFAULT_AUDIENCES = [
    {"code": "general", "label_en": "General readers", "label_zh": "通用读者", "is_default": True, "sort_order": 0},
    {"code": "engineering-leads", "label_en": "Engineering leads", "label_zh": "工程负责人", "is_default": False, "sort_order": 1},
    {"code": "builders", "label_en": "Builders", "label_zh": "构建者", "is_default": False, "sort_order": 2},
]


def upgrade() -> None:
    op.create_table(
        "taxonomy_categories",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("label_en", sa.String(length=120), nullable=False),
        sa.Column("label_zh", sa.String(length=120), nullable=False),
        sa.Column("color_from", sa.String(length=32), nullable=False),
        sa.Column("color_to", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "audiences",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("label_en", sa.String(length=120), nullable=False),
        sa.Column("label_zh", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "audience_categories",
        sa.Column("audience_code", sa.String(length=64), sa.ForeignKey("audiences.code"), primary_key=True),
        sa.Column("category_code", sa.String(length=64), sa.ForeignKey("taxonomy_categories.code"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("audience_code", sa.String(length=64), nullable=True))

    category_table = sa.table(
        "taxonomy_categories",
        sa.column("code", sa.String),
        sa.column("label_en", sa.String),
        sa.column("label_zh", sa.String),
        sa.column("color_from", sa.String),
        sa.column("color_to", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("active", sa.Boolean),
    )
    audience_table = sa.table(
        "audiences",
        sa.column("code", sa.String),
        sa.column("label_en", sa.String),
        sa.column("label_zh", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    mapping_table = sa.table(
        "audience_categories",
        sa.column("audience_code", sa.String),
        sa.column("category_code", sa.String),
        sa.column("position", sa.Integer),
    )
    op.bulk_insert(category_table, [{**row, "active": True} for row in DEFAULT_CATEGORIES])
    op.bulk_insert(audience_table, DEFAULT_AUDIENCES)
    op.bulk_insert(
        mapping_table,
        [
            {"audience_code": audience["code"], "category_code": category["code"], "position": index}
            for audience in DEFAULT_AUDIENCES
            for index, category in enumerate(DEFAULT_CATEGORIES)
        ],
    )


def downgrade() -> None:
    op.drop_column("users", "audience_code")
    op.drop_column("users", "is_admin")
    op.drop_table("audience_categories")
    op.drop_table("audiences")
    op.drop_table("taxonomy_categories")
