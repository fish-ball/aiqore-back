"""securities.exchange_code replaces FK exchanges; drop exchanges table

Revision ID: 012
Revises: 011
Create Date: 2026-05-02

交易所改为代码内静态目录；证券主表使用 exchange_code；删除 exchanges 表。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("securities", sa.Column("exchange_code", sa.String(length=32), nullable=True))
    op.create_index(op.f("ix_securities_exchange_code"), "securities", ["exchange_code"], unique=False)

    conn = op.get_bind()

    conn.execute(
        text("""
            UPDATE securities AS s
            SET exchange_code = e.code
            FROM exchanges AS e
            WHERE s.exchange_id = e.id
        """)
    )

    # 主表 exchange_id 为空但 QMT 外表有 ExchangeID 时，对齐别名后写入规范 code
    conn.execute(
        text("""
            UPDATE securities AS s
            SET exchange_code = CASE upper(trim(sq.exchange_id))
              WHEN 'XSHG' THEN 'SSE'
              WHEN 'XSHE' THEN 'SZSE'
              WHEN 'NQ' THEN 'NEEQ'
              WHEN 'CFE' THEN 'CFFEX'
              ELSE upper(trim(sq.exchange_id))
            END
            FROM security_source_qmt AS sq
            WHERE s.id = sq.security_id
              AND s.exchange_code IS NULL
              AND sq.exchange_id IS NOT NULL
              AND trim(sq.exchange_id) <> ''
        """)
    )

    conn.execute(
        text("""
            UPDATE securities SET exchange_code = 'SSE'
            WHERE exchange_code IS NULL AND upper(trim(market)) = 'SH'
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET exchange_code = 'SZSE'
            WHERE exchange_code IS NULL AND upper(trim(market)) = 'SZ'
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET exchange_code = 'BSE'
            WHERE exchange_code IS NULL AND upper(trim(market)) = 'BJ'
        """)
    )

    conn.execute(
        text("""
            UPDATE securities SET exchange_code = 'SHFE'
            WHERE exchange_code IS NULL AND security_type = 'Future'
        """)
    )

    conn.execute(text("UPDATE securities SET exchange_code = 'SSE' WHERE exchange_code IS NULL"))

    op.alter_column("securities", "exchange_code", existing_type=sa.String(length=32), nullable=False)

    op.drop_constraint("fk_securities_exchange_id", "securities", type_="foreignkey")
    op.drop_index(op.f("ix_securities_exchange_id"), table_name="securities")
    op.drop_column("securities", "exchange_id")

    op.drop_index("idx_exchanges_sort_order", table_name="exchanges")
    op.drop_index("idx_exchanges_is_active", table_name="exchanges")
    op.drop_table("exchanges")


def downgrade() -> None:
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

    op.add_column("securities", sa.Column("exchange_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_securities_exchange_id"), "securities", ["exchange_id"], unique=False)
    op.create_foreign_key(
        "fk_securities_exchange_id",
        "securities",
        "exchanges",
        ["exchange_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    conn = op.get_bind()
    conn.execute(
        text("""
            INSERT INTO exchanges (code, name, short_name, market_code, country_region, sort_order, is_active)
            SELECT 'SSE', '上海证券交易所', '上交所', 'SH', 'CN', 10, 1
            WHERE NOT EXISTS (SELECT 1 FROM exchanges WHERE code = 'SSE')
        """)
    )
    conn.execute(
        text("""
            UPDATE securities AS s
            SET exchange_id = e.id
            FROM exchanges AS e
            WHERE s.exchange_code = e.code AND s.exchange_id IS NULL
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges ORDER BY id ASC LIMIT 1)
            WHERE exchange_id IS NULL
        """)
    )

    op.alter_column("securities", "exchange_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index(op.f("ix_securities_exchange_code"), table_name="securities")
    op.drop_column("securities", "exchange_code")
