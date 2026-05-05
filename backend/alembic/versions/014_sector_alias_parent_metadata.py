"""sectors：显示名 name、唯一 alias、parent_id、metadata；移除旧扩展列

Revision ID: 014
Revises: 013
Create Date: 2026-05-03

旧 name（数据源键）迁入 alias；显示名取原 display_name 或旧 name。
原 category/market/security_count 等写入 metadata.stats。
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = inspect(conn)
    if "sectors" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("sectors")}

    if "alias" not in cols:
        op.add_column("sectors", sa.Column("alias", sa.String(length=100), nullable=True))
    if "parent_id" not in cols:
        op.add_column(
            "sectors",
            sa.Column("parent_id", sa.Integer(), nullable=True, comment="父板块 id"),
        )
    if "metadata" not in cols:
        json_type = sa.JSON().with_variant(sa.Text(), "sqlite")
        op.add_column("sectors", sa.Column("metadata", json_type, nullable=True))

    cols_old = {"display_name", "category", "market", "description", "security_count", "is_active", "last_sync_at"}
    if not cols_old.intersection(cols):
        # 已是新结构（例如已从本迁移升级过的库）
        insp_f = inspect(conn)
        idx_f = {i["name"] for i in insp_f.get_indexes("sectors")}
        if "idx_sectors_alias" not in idx_f:
            op.create_index("idx_sectors_alias", "sectors", ["alias"], unique=True)
        fk_f = {fk["name"] for fk in insp_f.get_foreign_keys("sectors")}
        if "fk_sectors_parent_id" not in fk_f:
            op.create_foreign_key(
                "fk_sectors_parent_id",
                "sectors",
                "sectors",
                ["parent_id"],
                ["id"],
                ondelete="SET NULL",
            )
        return

    rows = conn.execute(
        text(
            "SELECT id, name, display_name, category, market, description, "
            "security_count, is_active, last_sync_at FROM sectors"
        )
    ).mappings().all()

    for r in rows:
        old_key = r["name"]
        disp = r.get("display_name") or old_key
        stats = {
            "category": r.get("category"),
            "market": r.get("market"),
            "security_count": r.get("security_count") or 0,
            "is_active": r.get("is_active"),
            "last_sync_at": r["last_sync_at"].isoformat() if r.get("last_sync_at") else None,
        }
        if r.get("description"):
            stats["description"] = r["description"]
        meta = {"stats": stats, "sources": {"qmt": {"sector_key": old_key}}}
        payload = json.dumps(meta, ensure_ascii=False)
        if dialect == "postgresql":
            conn.execute(
                text(
                    "UPDATE sectors SET alias = :alias, name = :name, "
                    "metadata = CAST(:meta AS JSON) WHERE id = :id"
                ),
                {"alias": old_key, "name": disp, "meta": payload, "id": r["id"]},
            )
        else:
            conn.execute(
                text("UPDATE sectors SET alias = :alias, name = :name, metadata = :meta WHERE id = :id"),
                {"alias": old_key, "name": disp, "meta": payload, "id": r["id"]},
            )

    idx_names = {i["name"] for i in inspector.get_indexes("sectors")}
    if "idx_sectors_name" in idx_names:
        op.drop_index("idx_sectors_name", table_name="sectors")

    for uc in inspector.get_unique_constraints("sectors"):
        if uc.get("column_names") == ["name"]:
            cname = uc.get("name")
            if cname:
                op.drop_constraint(cname, "sectors", type_="unique")

    insp_mid = inspect(conn)
    mid_idx = {i["name"] for i in insp_mid.get_indexes("sectors")}
    if "idx_sectors_alias" not in mid_idx:
        op.create_index("idx_sectors_alias", "sectors", ["alias"], unique=True)

    drop_cols = [
        "display_name",
        "category",
        "market",
        "description",
        "security_count",
        "is_active",
        "last_sync_at",
    ]
    insp_cols = inspect(conn)
    existing = {c["name"] for c in insp_cols.get_columns("sectors")}
    to_drop = [c for c in drop_cols if c in existing]

    if dialect == "sqlite":
        with op.batch_alter_table("sectors") as batch_op:
            for c in to_drop:
                batch_op.drop_column(c)
            batch_op.alter_column(
                "alias",
                existing_type=sa.String(100),
                nullable=False,
            )
    else:
        for c in to_drop:
            op.drop_column("sectors", c)
        op.alter_column(
            "sectors",
            "alias",
            existing_type=sa.String(length=100),
            nullable=False,
        )

    insp_fk = inspect(conn)
    fk_names = {fk["name"] for fk in insp_fk.get_foreign_keys("sectors")}
    if "fk_sectors_parent_id" not in fk_names:
        op.create_foreign_key(
            "fk_sectors_parent_id",
            "sectors",
            "sectors",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )

    insp_end = inspect(conn)
    idx_end = {i["name"] for i in insp_end.get_indexes("sectors")}
    if "idx_sectors_name" not in idx_end:
        op.create_index("idx_sectors_name", "sectors", ["name"], unique=False)

    for obsolete in ("idx_sectors_category", "idx_sectors_market", "idx_sectors_is_active"):
        if obsolete in idx_end:
            op.drop_index(obsolete, table_name="sectors")


def downgrade() -> None:
    raise NotImplementedError("014 迁移不可逆")
