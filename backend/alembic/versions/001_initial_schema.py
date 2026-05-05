# -*- coding: utf-8 -*-
"""初始 schema（由历史 001–015 迁移折叠而成，与当前 ORM 模型一致）

全新库：直接 alembic upgrade head。
若数据库已由旧迁移链建表且结构已对齐，可执行 alembic stamp 001_initial 标记版本，勿重复 upgrade。
"""
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401  # 注册所有 ORM 表到 Base.metadata

    from app.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import app.models  # noqa: F401

    from app.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
