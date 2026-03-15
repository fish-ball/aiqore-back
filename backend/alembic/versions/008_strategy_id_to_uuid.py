"""strategy_id_to_uuid

Revision ID: 008
Revises: 007
Create Date: 2026-03-15 00:00:00.000000

将 strategies 主键 id 从 Integer 改为 String(36) UUID；backtest_tasks.strategy_id 同步改为 String(36)。
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "strategies" not in tables:
        return

    # 1. strategies: 添加临时列 id_uuid
    op.add_column("strategies", sa.Column("id_uuid", sa.String(36), nullable=True))
    if dialect_name == "postgresql":
        conn.execute(sa.text("UPDATE strategies SET id_uuid = gen_random_uuid()::text"))
    else:
        # SQLite 等：用原 id 转字符串，保证唯一
        conn.execute(sa.text("UPDATE strategies SET id_uuid = 'strategy-' || id"))

    op.alter_column("strategies", "id_uuid", nullable=False)

    # 2. backtest_tasks: 添加临时列 strategy_id_uuid
    if "backtest_tasks" in tables:
        op.add_column("backtest_tasks", sa.Column("strategy_id_uuid", sa.String(36), nullable=True))
        if dialect_name == "postgresql":
            conn.execute(sa.text("""
                UPDATE backtest_tasks bt
                SET strategy_id_uuid = s.id_uuid
                FROM strategies s
                WHERE s.id = bt.strategy_id
            """))
        else:
            conn.execute(sa.text("""
                UPDATE backtest_tasks
                SET strategy_id_uuid = (SELECT id_uuid FROM strategies WHERE strategies.id = backtest_tasks.strategy_id)
            """))

        # 删除 backtest_tasks 对 strategies 的外键与旧列
        fks = [f for f in inspector.get_foreign_keys("backtest_tasks") if f["referred_table"] == "strategies"]
        for fk in fks:
            op.drop_constraint(fk["name"], "backtest_tasks", type_="foreignkey")
        # 索引名可能因数据库不同而不同，若存在则删除
        try:
            op.drop_index("idx_backtest_tasks_strategy_id", table_name="backtest_tasks", if_exists=True)
        except Exception:
            pass
        op.drop_column("backtest_tasks", "strategy_id")
        op.alter_column("backtest_tasks", "strategy_id_uuid", new_column_name="strategy_id")
        op.create_index("idx_backtest_tasks_strategy_id", "backtest_tasks", ["strategy_id"], unique=False)

    # 3. strategies: 主键改为 id_uuid
    op.drop_constraint("strategies_pkey", "strategies", type_="primary")
    op.drop_column("strategies", "id")
    op.alter_column("strategies", "id_uuid", new_column_name="id")
    op.create_primary_key("strategies_pkey", "strategies", ["id"])

    # 4. backtest_tasks: 重新建立外键
    if "backtest_tasks" in tables:
        op.create_foreign_key(
            "backtest_tasks_strategy_id_fkey",
            "backtest_tasks",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """回退后 strategies.id 为 Integer，backtest_tasks.strategy_id 为 Integer 但会置空（UUID 无法还原为原整数）。"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "backtest_tasks" in tables:
        fks = [f for f in inspector.get_foreign_keys("backtest_tasks") if f["referred_table"] == "strategies"]
        for fk in fks:
            op.drop_constraint(fk["name"], "backtest_tasks", type_="foreignkey")
        op.drop_index("idx_backtest_tasks_strategy_id", table_name="backtest_tasks")
        op.add_column("backtest_tasks", sa.Column("strategy_id_int", sa.Integer(), nullable=True))
        op.drop_column("backtest_tasks", "strategy_id")
        op.rename_column("backtest_tasks", "strategy_id_int", "strategy_id")
        op.create_index("idx_backtest_tasks_strategy_id", "backtest_tasks", ["strategy_id"], unique=False)

    op.drop_constraint("strategies_pkey", "strategies", type_="primary")
    op.add_column("strategies", sa.Column("id_int", sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE strategies SET id_int = row_number() OVER (ORDER BY id)"))
    op.alter_column("strategies", "id_int", nullable=False)
    op.drop_column("strategies", "id")
    op.rename_column("strategies", "id_int", "id")
    op.create_primary_key("strategies_pkey", "strategies", ["id"])

    if "backtest_tasks" in tables:
        op.create_foreign_key(
            "backtest_tasks_strategy_id_fkey",
            "backtest_tasks",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="SET NULL",
        )
