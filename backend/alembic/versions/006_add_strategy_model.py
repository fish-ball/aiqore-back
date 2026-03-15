"""add_strategy_model

Revision ID: 006
Revises: 005
Create Date: 2026-03-15 00:00:00.000000

策略管理表：策略名称、策略类型（枚举，当前仅 backtrader）、代码 script。
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    if "strategies" in existing_tables:
        return
    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="策略名称"),
        sa.Column("strategy_type", sa.String(length=32), nullable=False, comment="策略类型: backtrader 等"),
        sa.Column("script", sa.Text(), nullable=True, comment="策略代码 script"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_strategies_strategy_type", "strategies", ["strategy_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_strategies_strategy_type", table_name="strategies")
    op.drop_table("strategies")
