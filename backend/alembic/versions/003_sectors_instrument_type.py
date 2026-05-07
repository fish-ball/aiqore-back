# -*- coding: utf-8 -*-
"""sectors：增加 instrument_type，与 instruments.instrument_type 枚举一致。"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "003_sectors_instrument_type"
down_revision = "002_sectors_refactor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "sectors" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("sectors")}
    if "instrument_type" in cols:
        return

    op.add_column(
        "sectors",
        sa.Column("instrument_type", sa.String(length=20), nullable=True),
    )
    op.execute(sa.text("UPDATE sectors SET instrument_type = 'STOCK' WHERE instrument_type IS NULL"))
    op.alter_column("sectors", "instrument_type", nullable=False)

    bind = op.get_bind()
    insp2 = inspect(bind)
    idx_names = {ix["name"] for ix in insp2.get_indexes("sectors")}
    if "idx_sectors_instrument_type" not in idx_names:
        op.create_index("idx_sectors_instrument_type", "sectors", ["instrument_type"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "sectors" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("sectors")}
    if "instrument_type" not in cols:
        return

    for ix in insp.get_indexes("sectors"):
        if ix["name"] == "idx_sectors_instrument_type":
            op.drop_index("idx_sectors_instrument_type", table_name="sectors")
            break

    op.drop_column("sectors", "instrument_type")
