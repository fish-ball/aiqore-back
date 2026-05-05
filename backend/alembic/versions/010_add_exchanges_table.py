"""add exchanges table and seed China exchanges

Revision ID: 010
Revises: 009
Create Date: 2026-05-02

交易所主表及中国大陆常见交易所初始数据。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

_SEED_ROWS = [
    {"code": "SSE", "name": "上海证券交易所", "short_name": "上交所", "market_code": "SH", "country_region": "CN", "sort_order": 10, "is_active": 1},
    {"code": "SZSE", "name": "深圳证券交易所", "short_name": "深交所", "market_code": "SZ", "country_region": "CN", "sort_order": 20, "is_active": 1},
    {"code": "BSE", "name": "北京证券交易所", "short_name": "北交所", "market_code": "BJ", "country_region": "CN", "sort_order": 30, "is_active": 1},
    {"code": "SHFE", "name": "上海期货交易所", "short_name": "上期所", "market_code": None, "country_region": "CN", "sort_order": 40, "is_active": 1},
    {"code": "DCE", "name": "大连商品交易所", "short_name": "大商所", "market_code": None, "country_region": "CN", "sort_order": 50, "is_active": 1},
    {"code": "CZCE", "name": "郑州商品交易所", "short_name": "郑商所", "market_code": None, "country_region": "CN", "sort_order": 60, "is_active": 1},
    {"code": "GFEX", "name": "广州期货交易所", "short_name": "广期所", "market_code": None, "country_region": "CN", "sort_order": 70, "is_active": 1},
    {"code": "CFFEX", "name": "中国金融期货交易所", "short_name": "中金所", "market_code": None, "country_region": "CN", "sort_order": 80, "is_active": 1},
    {"code": "INE", "name": "上海国际能源交易中心", "short_name": "上期能源", "market_code": None, "country_region": "CN", "sort_order": 90, "is_active": 1},
]


def _seed_exchanges_on_conflict_ignore() -> None:
    """已存在 exchanges 表时补种子，冲突则跳过（与 uq_exchanges_code 一致）。"""
    conn = op.get_bind()
    sql = text(
        """
        INSERT INTO exchanges (code, name, short_name, market_code, country_region, sort_order, is_active)
        VALUES (:code, :name, :short_name, :market_code, :country_region, :sort_order, :is_active)
        ON CONFLICT (code) DO NOTHING
        """
    )
    for r in _SEED_ROWS:
        conn.execute(
            sql,
            {
                "code": r["code"],
                "name": r["name"],
                "short_name": r["short_name"],
                "market_code": r["market_code"],
                "country_region": r["country_region"],
                "sort_order": r["sort_order"],
                "is_active": r["is_active"],
            },
        )


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = set(insp.get_table_names())

    if "exchanges" not in table_names:
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
        op.bulk_insert(exchanges, _SEED_ROWS)
    else:
        # 表已由 create_all 或其它方式存在：只补索引与缺失种子
        idx_names = {i["name"] for i in insp.get_indexes("exchanges")}
        if "idx_exchanges_is_active" not in idx_names:
            op.create_index("idx_exchanges_is_active", "exchanges", ["is_active"], unique=False)
        if "idx_exchanges_sort_order" not in idx_names:
            op.create_index("idx_exchanges_sort_order", "exchanges", ["sort_order"], unique=False)
        _seed_exchanges_on_conflict_ignore()


def downgrade() -> None:
    op.drop_index("idx_exchanges_sort_order", table_name="exchanges")
    op.drop_index("idx_exchanges_is_active", table_name="exchanges")
    op.drop_table("exchanges")
