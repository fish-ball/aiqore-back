"""normalize security_type to Equity Future Option

Revision ID: 009
Revises: 008
Create Date: 2026-05-02 00:00:00.000000

将 securities.security_type 从中文细分类统一为三大类：Equity、Future、Option。
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("""
            UPDATE securities SET security_type = 'Future'
            WHERE security_type IN ('期货')
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET security_type = 'Option'
            WHERE security_type IN ('期权')
        """)
    )
    conn.execute(
        text("""
            UPDATE securities SET security_type = 'Equity'
            WHERE security_type NOT IN ('Equity', 'Future', 'Option')
        """)
    )


def downgrade() -> None:
    conn = op.get_bind()
    # 无法还原基金、债券等细分类，仅恢复为未来/期权/股票三类表述
    conn.execute(
        text("""
            UPDATE securities SET security_type = CASE security_type
                WHEN 'Future' THEN '期货'
                WHEN 'Option' THEN '期权'
                ELSE '股票'
            END
            WHERE security_type IN ('Equity', 'Future', 'Option')
        """)
    )
