"""securities.exchange_id FK to exchanges

Revision ID: 011
Revises: 010
Create Date: 2026-05-02

为证券主表增加交易所外键，并按 market / QMT exchange_id / 合约后缀回填。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    # 1) 现货：market 与 exchanges.market_code 对齐
    conn.execute(
        text("""
            UPDATE securities AS s
            SET exchange_id = e.id
            FROM exchanges AS e
            WHERE s.exchange_id IS NULL
              AND e.market_code IS NOT NULL
              AND upper(trim(s.market)) = upper(trim(e.market_code))
        """)
    )

    # 2) QMT 外表字符串 ExchangeID 与 exchanges.code 对齐
    conn.execute(
        text("""
            UPDATE securities AS s
            SET exchange_id = e.id
            FROM security_source_qmt AS sq
            JOIN exchanges AS e ON upper(trim(sq.exchange_id)) = upper(trim(e.code))
            WHERE s.id = sq.security_id
              AND s.exchange_id IS NULL
              AND sq.exchange_id IS NOT NULL
              AND trim(sq.exchange_id) <> ''
        """)
    )

    # 3) 合约后缀（小写）-> 交易所代码
    suffix_map = (
        ("sf", "SHFE"),
        ("df", "DCE"),
        ("zf", "CZCE"),
        ("gf", "GFEX"),
        ("ine", "INE"),
        ("cffex", "CFFEX"),
        ("cfe", "CFFEX"),
    )
    for suf, code in suffix_map:
        conn.execute(
            text("""
                UPDATE securities AS s
                SET exchange_id = e.id
                FROM exchanges AS e
                WHERE s.exchange_id IS NULL
                  AND e.code = :code
                  AND lower(split_part(s.symbol, '.', 2)) = :suf
            """),
            {"code": code, "suf": suf},
        )

    # 4) 仍为空：按 market 映射 SSE/SZSE/BSE
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges WHERE code = 'SSE' LIMIT 1)
            WHERE exchange_id IS NULL AND upper(trim(market)) = 'SH'
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges WHERE code = 'SZSE' LIMIT 1)
            WHERE exchange_id IS NULL AND upper(trim(market)) = 'SZ'
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges WHERE code = 'BSE' LIMIT 1)
            WHERE exchange_id IS NULL AND upper(trim(market)) = 'BJ'
        """)
    )

    # 5) 期货大类仍未命中：上期所
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges WHERE code = 'SHFE' LIMIT 1)
            WHERE exchange_id IS NULL AND security_type = 'Future'
        """)
    )

    # 6) 最后兜底：表中第一条交易所
    conn.execute(
        text("""
            UPDATE securities SET exchange_id = (SELECT id FROM exchanges ORDER BY id ASC LIMIT 1)
            WHERE exchange_id IS NULL
        """)
    )

    op.alter_column("securities", "exchange_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_securities_exchange_id", "securities", type_="foreignkey")
    op.drop_index(op.f("ix_securities_exchange_id"), table_name="securities")
    op.drop_column("securities", "exchange_id")
