# -*- coding: utf-8 -*-
"""初始 schema（单迁移折叠）：与当前 ORM 一致，并统一数据源表名为 data_sources

upgrade 顺序：
1. 若仍存在旧表 data_source_connections 且尚无 data_sources，则重命名表（不丢数据）。
2. Base.metadata.create_all 补建缺失表/结构。

全新库：无旧表则仅 create_all。已对齐的库可 stamp 001_initial 跳过 DDL。
"""
from alembic import op
from sqlalchemy import inspect

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    names = set(inspect(bind).get_table_names())
    if "data_source_connections" in names and "data_sources" not in names:
        op.rename_table("data_source_connections", "data_sources")

    import app.models  # noqa: F401  # 注册所有 ORM 表到 Base.metadata

    from app.database import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import app.models  # noqa: F401

    from app.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
