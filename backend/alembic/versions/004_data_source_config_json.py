# -*- coding: utf-8 -*-
"""data_sources：合并为 JSON config，删除行情/交易角色与分散连接字段。"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "004_data_source_config_json"
down_revision = "003_sectors_instrument_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "data_sources" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("data_sources")}
    if "config" in cols:
        return

    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.add_column(sa.Column("config", sa.JSON(), nullable=True))

    conn = bind
    result = conn.execute(
        text(
            "SELECT id, host, port, \"user\", password, xt_quant_path, xt_quant_acct "
            "FROM data_sources"
        )
    )
    for row in result.mappings().all():
        rid = row["id"]
        cfg: dict = {}
        for key in ("host", "port", "user", "password", "xt_quant_path", "xt_quant_acct"):
            v = row.get(key)
            if v is not None:
                cfg[key] = v
        conn.execute(
            text("UPDATE data_sources SET config = :cfg WHERE id = :id"),
            {"cfg": json.dumps(cfg), "id": rid},
        )

    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.alter_column("config", nullable=False)

    drops = [
        "is_quote_source",
        "is_trading_source",
        "host",
        "port",
        "user",
        "password",
        "xt_quant_path",
        "xt_quant_acct",
    ]
    with op.batch_alter_table("data_sources") as batch_op:
        for c in drops:
            if c in cols:
                batch_op.drop_column(c)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "data_sources" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("data_sources")}
    if "config" not in cols:
        return

    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.add_column(sa.Column("is_quote_source", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("is_trading_source", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("host", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("port", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("user", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("password", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("xt_quant_path", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("xt_quant_acct", sa.String(50), nullable=True))

    conn = bind
    res = conn.execute(text("SELECT id, config FROM data_sources"))
    for row in res.mappings().all():
        rid, raw_cfg = row["id"], row["config"]
        cfg = raw_cfg if isinstance(raw_cfg, dict) else (json.loads(raw_cfg) if raw_cfg else {})
        conn.execute(
            text(
                "UPDATE data_sources SET host=:h, port=:p, \"user\"=:u, password=:pw, "
                "xt_quant_path=:xq, xt_quant_acct=:xa WHERE id=:id"
            ),
            {
                "h": cfg.get("host"),
                "p": cfg.get("port"),
                "u": cfg.get("user"),
                "pw": cfg.get("password"),
                "xq": cfg.get("xt_quant_path"),
                "xa": cfg.get("xt_quant_acct"),
                "id": rid,
            },
        )

    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.drop_column("config")
