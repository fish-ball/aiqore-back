# -*- coding: utf-8 -*-
"""sectors：移除 metadata，增加 source 与 asset_class，联合唯一 (source, alias)。"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "002_sectors_refactor"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "sectors" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("sectors")}

    if "source" not in cols:
        op.add_column("sectors", sa.Column("source", sa.String(length=32), nullable=True))
    if "asset_class" not in cols:
        op.add_column(
            "sectors",
            sa.Column("asset_class", sa.String(length=32), nullable=True),
        )

    op.execute(
        sa.text(
            "UPDATE sectors SET source = COALESCE(source, 'qmt'), "
            "asset_class = COALESCE(asset_class, 'Equity')"
        )
    )

    op.alter_column("sectors", "source", nullable=False)
    op.alter_column("sectors", "asset_class", nullable=False)

    insp2 = inspect(bind)
    for uq in insp2.get_unique_constraints("sectors"):
        cnames = tuple(uq.get("column_names") or ())
        if cnames == ("alias",):
            op.drop_constraint(uq["name"], "sectors", type_="unique")

    has_pair = any(
        tuple(uq.get("column_names") or ()) == ("source", "alias")
        for uq in inspect(bind).get_unique_constraints("sectors")
    )
    if not has_pair:
        op.create_unique_constraint(
            "uq_sectors_source_alias",
            "sectors",
            ["source", "alias"],
        )

    cols3 = {c["name"] for c in inspect(bind).get_columns("sectors")}
    if "metadata" in cols3:
        op.drop_column("sectors", "metadata")


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "sectors" not in insp.get_table_names():
        return

    for uq in insp.get_unique_constraints("sectors"):
        if uq["name"] == "uq_sectors_source_alias":
            op.drop_constraint("uq_sectors_source_alias", "sectors", type_="unique")

    op.create_unique_constraint("sectors_alias_key", "sectors", ["alias"])

    op.add_column("sectors", sa.Column("metadata", sa.JSON(), nullable=True))
    op.drop_column("sectors", "source")
    op.drop_column("sectors", "asset_class")
