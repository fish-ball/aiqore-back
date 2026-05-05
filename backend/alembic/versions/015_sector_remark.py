# -*- coding: utf-8 -*-
"""sectors 表增加 remark（用户备注）"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "sectors" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sectors")}
    if "remark" not in cols:
        op.add_column(
            "sectors",
            sa.Column("remark", sa.Text(), nullable=True, comment="用户备注"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "sectors" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sectors")}
    if "remark" in cols:
        op.drop_column("sectors", "remark")
