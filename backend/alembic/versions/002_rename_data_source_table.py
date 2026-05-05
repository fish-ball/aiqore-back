# -*- coding: utf-8 -*-
"""统一数据源配置表名为 data_source_connections（与 ORM DataSource 一致）

若仅有新表名 data_sources（例如曾执行过旧版 002 或仅用 create_all 建表），则重命名为 data_source_connections。
若已是 data_source_connections，则跳过。
"""
from alembic import op
from sqlalchemy import inspect

revision = "002_rename_data_sources"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    names = set(inspect(bind).get_table_names())
    if "data_sources" in names and "data_source_connections" not in names:
        op.rename_table("data_sources", "data_source_connections")


def downgrade() -> None:
    bind = op.get_bind()
    names = set(inspect(bind).get_table_names())
    if "data_source_connections" in names and "data_sources" not in names:
        op.rename_table("data_source_connections", "data_sources")
