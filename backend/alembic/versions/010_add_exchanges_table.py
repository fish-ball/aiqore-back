"""add exchanges table and seed China exchanges

Revision ID: 010
Revises: 009
Create Date: 2026-05-02

交易所主表及中国大陆常见交易所初始数据。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=80), nullable=True),
        sa.Column("market_code", sa.String(length=10), nullable=True),
        sa.Column("country_region", sa.String(length=20), nullable=False, server_default="CN"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_exchanges_code"),
    )
    op.create_index("idx_exchanges_is_active", "exchanges", ["is_active"], unique=False)
    op.create_index("idx_exchanges_sort_order", "exchanges", ["sort_order"], unique=False)

    exchanges = sa.table(
        "exchanges",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("short_name", sa.String),
        sa.column("market_code", sa.String),
        sa.column("country_region", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Integer),
    )
    op.bulk_insert(
        exchanges,
        [
            {"code": "SSE", "name": "上海证券交易所", "short_name": "上交所", "market_code": "SH", "country_region": "CN", "sort_order": 10, "is_active": 1},
            {"code": "SZSE", "name": "深圳证券交易所", "short_name": "深交所", "market_code": "SZ", "country_region": "CN", "sort_order": 20, "is_active": 1},
            {"code": "BSE", "name": "北京证券交易所", "short_name": "北交所", "market_code": "BJ", "country_region": "CN", "sort_order": 30, "is_active": 1},
            {"code": "SHFE", "name": "上海期货交易所", "short_name": "上期所", "market_code": None, "country_region": "CN", "sort_order": 40, "is_active": 1},
            {"code": "DCE", "name": "大连商品交易所", "short_name": "大商所", "market_code": None, "country_region": "CN", "sort_order": 50, "is_active": 1},
            {"code": "CZCE", "name": "郑州商品交易所", "short_name": "郑商所", "market_code": None, "country_region": "CN", "sort_order": 60, "is_active": 1},
            {"code": "GFEX", "name": "广州期货交易所", "short_name": "广期所", "market_code": None, "country_region": "CN", "sort_order": 70, "is_active": 1},
            {"code": "CFFEX", "name": "中国金融期货交易所", "short_name": "中金所", "market_code": None, "country_region": "CN", "sort_order": 80, "is_active": 1},
            {"code": "INE", "name": "上海国际能源交易中心", "short_name": "上期能源", "market_code": None, "country_region": "CN", "sort_order": 90, "is_active": 1},
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_exchanges_sort_order", table_name="exchanges")
    op.drop_index("idx_exchanges_is_active", table_name="exchanges")
    op.drop_table("exchanges")
