"""add_backtest_task

Revision ID: 007
Revises: 006
Create Date: 2026-03-15 00:00:00.000000

回测任务表：UUID 主键，外键 Strategy/证券，回测参数与 script 快照，result JSON。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    if "backtest_tasks" in existing_tables:
        return

    result_col = postgresql.JSON() if conn.dialect.name == "postgresql" else sa.JSON()
    op.create_table(
        "backtest_tasks",
        sa.Column("id", sa.String(36), nullable=False, comment="UUID 主键"),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, comment="策略 ID，删除策略后可空"),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="SET NULL"), nullable=True, comment="证券 ID，可空"),
        sa.Column("security_symbol", sa.String(64), nullable=True, comment="证券代码缓存"),
        sa.Column("security_name", sa.String(100), nullable=True, comment="证券名称缓存"),
        sa.Column("start_date", sa.String(10), nullable=False, comment="回测开始日期 YYYY-MM-DD"),
        sa.Column("end_date", sa.String(10), nullable=False, comment="回测结束日期 YYYY-MM-DD"),
        sa.Column("initial_cash", sa.Float(), nullable=False, server_default=sa.text("1000000.0"), comment="初始资金"),
        sa.Column("commission", sa.Float(), nullable=False, server_default=sa.text("0.0002"), comment="手续费"),
        sa.Column("position_pct", sa.Integer(), nullable=False, server_default=sa.text("95"), comment="仓位比例，如 95 表示 95%"),
        sa.Column("script", sa.Text(), nullable=True, comment="策略代码快照，创建时从 Strategy.script 复制"),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), comment="pending/running/success/failure"),
        sa.Column("celery_task_id", sa.String(255), nullable=True, comment="Celery 任务 ID"),
        sa.Column("result", result_col, nullable=True, comment="回测结果或错误信息 JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_backtest_tasks_strategy_id", "backtest_tasks", ["strategy_id"], unique=False)
    op.create_index("idx_backtest_tasks_security_id", "backtest_tasks", ["security_id"], unique=False)
    op.create_index("idx_backtest_tasks_status", "backtest_tasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_backtest_tasks_status", table_name="backtest_tasks")
    op.drop_index("idx_backtest_tasks_security_id", table_name="backtest_tasks")
    op.drop_index("idx_backtest_tasks_strategy_id", table_name="backtest_tasks")
    op.drop_table("backtest_tasks")
