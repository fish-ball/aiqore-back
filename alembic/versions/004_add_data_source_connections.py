"""add_data_source_connections

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000

数据源连接表：QMT 等连接参数化配置，支持行情源/交易源角色。
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    if "data_source_connections" in existing_tables:
        return
    op.create_table(
        "data_source_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="显示名称"),
        sa.Column("source_type", sa.String(length=32), nullable=False, comment="数据源类型: qmt, joinquant, tushare"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否启用"),
        sa.Column("is_quote_source", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否作为行情源"),
        sa.Column("is_trading_source", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否作为交易驱动源"),
        sa.Column("host", sa.String(length=255), nullable=True, comment="QMT 主机"),
        sa.Column("port", sa.Integer(), nullable=True, comment="QMT 端口"),
        sa.Column("user", sa.String(length=100), nullable=True, comment="QMT 用户"),
        sa.Column("password", sa.String(length=255), nullable=True, comment="QMT 密码"),
        sa.Column("xt_quant_path", sa.String(length=500), nullable=True, comment="QMT xtquant 路径"),
        sa.Column("xt_quant_acct", sa.String(length=50), nullable=True, comment="QMT 资金账号"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_data_source_connections_source_type", "data_source_connections", ["source_type"], unique=False)
    op.create_index("idx_data_source_connections_is_active", "data_source_connections", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_data_source_connections_is_active", table_name="data_source_connections")
    op.drop_index("idx_data_source_connections_source_type", table_name="data_source_connections")
    op.drop_table("data_source_connections")
