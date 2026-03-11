"""extend_security_symbol_length

Revision ID: 005
Revises: 004
Create Date: 2026-03-11 00:00:00.000000

将 securities.symbol 从 VARCHAR(20) 扩展为 VARCHAR(64)，以兼容更长的标的代码。
"""
from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "sqlite":
        # SQLite 需要使用 batch_alter_table
        with op.batch_alter_table("securities", schema=None) as batch_op:
            batch_op.alter_column("symbol", type_=sa.String(64))
    else:
        op.alter_column("securities", "symbol", type_=sa.String(64))


def downgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "sqlite":
        with op.batch_alter_table("securities", schema=None) as batch_op:
            batch_op.alter_column("symbol", type_=sa.String(20))
    else:
        op.alter_column("securities", "symbol", type_=sa.String(20))

