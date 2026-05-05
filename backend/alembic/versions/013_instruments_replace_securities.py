"""instruments 单表替代 securities 及子表；backtest_tasks 改为 instrument_code

Revision ID: 013
Revises: 012
Create Date: 2026-05-03

将证券主表与子表合并为 instruments（code 主键）；回测任务关联改为 instrument_code。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

_CHILD_TABLES = (
    "security_source_qmt",
    "security_trading_rules",
    "security_quote_snapshot",
    "security_stock",
    "security_fund",
    "security_bond",
    "security_convertible",
    "security_option",
    "security_future",
)


def _instrument_type_from_qmt(instr: str | None, sec_type: str | None) -> str:
    if not instr:
        if sec_type == "Future":
            return "FUTURE"
        if sec_type == "Option":
            return "OPTION"
        return "STOCK"
    u = instr.upper()
    if "CONVERTIBLE" in u:
        return "BOND"
    if "FUTURE" in u:
        return "FUTURE"
    if "OPTION" in u:
        return "OPTION"
    if "ETF" in u:
        return "ETF"
    if "LOF" in u or "FUND" in u:
        return "FUND"
    if "BOND" in u:
        return "BOND"
    if "INDEX" in u:
        return "INDEX"
    if "STOCK" in u:
        return "STOCK"
    return "STOCK"


def _asset_class(inst_type: str, sec_type: str | None) -> str:
    if inst_type == "FUTURE" or sec_type == "Future":
        return "COMMODITY"
    if inst_type == "OPTION" or sec_type == "Option":
        return "EQUITY"
    if inst_type == "BOND":
        return "FIXED_INCOME"
    return "EQUITY"


def _ensure_instruments_table_and_indexes(dialect: str, inspector, tables: set[str]) -> None:
    """创建 instruments 表及索引；若表已存在则仅补建缺失索引。"""
    if "instruments" not in tables:
        op.create_table(
            "instruments",
            sa.Column("code", sa.String(length=64), nullable=False, comment="标的代码，如 601888.SH"),
            sa.Column("name", sa.String(length=100), nullable=False, comment="证券名称"),
            sa.Column(
                "exchange_code",
                sa.String(length=32),
                nullable=False,
                comment="所属交易所规范代码",
            ),
            sa.Column("asset_class", sa.String(length=20), nullable=False, comment="资产大类"),
            sa.Column("instrument_type", sa.String(length=20), nullable=False, comment="标的类型"),
            sa.Column("open_date", sa.DateTime(), nullable=True, comment="上市或合约开始日期"),
            sa.Column("expire_date", sa.DateTime(), nullable=True, comment="退市或合约结束日期"),
            sa.Column("abbreviation", sa.String(length=50), nullable=True, comment="拼音简写"),
            sa.Column("last_price", sa.Numeric(precision=18, scale=6), nullable=True, comment="最新价"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否可交易"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()") if dialect == "postgresql" else sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
                comment="创建时间",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()") if dialect == "postgresql" else sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
                comment="更新时间",
            ),
            sa.PrimaryKeyConstraint("code"),
        )
        op.create_index(op.f("ix_instruments_exchange_code"), "instruments", ["exchange_code"], unique=False)
        op.create_index("idx_instruments_name", "instruments", ["name"], unique=False)
        op.create_index("idx_instruments_asset_class", "instruments", ["asset_class"], unique=False)
        op.create_index("idx_instruments_instrument_type", "instruments", ["instrument_type"], unique=False)
        op.create_index("idx_instruments_is_active", "instruments", ["is_active"], unique=False)
        op.create_index("idx_instruments_abbreviation", "instruments", ["abbreviation"], unique=False)
        return

    idx_names = {i["name"] for i in inspector.get_indexes("instruments")}
    if op.f("ix_instruments_exchange_code") not in idx_names:
        op.create_index(op.f("ix_instruments_exchange_code"), "instruments", ["exchange_code"], unique=False)
    if "idx_instruments_name" not in idx_names:
        op.create_index("idx_instruments_name", "instruments", ["name"], unique=False)
    if "idx_instruments_asset_class" not in idx_names:
        op.create_index("idx_instruments_asset_class", "instruments", ["asset_class"], unique=False)
    if "idx_instruments_instrument_type" not in idx_names:
        op.create_index("idx_instruments_instrument_type", "instruments", ["instrument_type"], unique=False)
    if "idx_instruments_is_active" not in idx_names:
        op.create_index("idx_instruments_is_active", "instruments", ["is_active"], unique=False)
    if "idx_instruments_abbreviation" not in idx_names:
        op.create_index("idx_instruments_abbreviation", "instruments", ["abbreviation"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    _ensure_instruments_table_and_indexes(dialect, inspector, tables)

    if "securities" in tables:
        # 合并子表到期日（若有）
        sql_select = """
            SELECT s.symbol, s.name, COALESCE(s.exchange_code, '') AS exchange_code,
                   s.security_type, s.list_date, s.delist_date, s.abbreviation,
                   s.is_active, s.created_at, s.updated_at,
                   sq.instrument_type, qs.last_price,
                   so.expiry_date AS opt_expiry, sf.expiry_date AS fut_expiry
            FROM securities s
            LEFT JOIN security_source_qmt sq ON sq.security_id = s.id
            LEFT JOIN security_quote_snapshot qs ON qs.security_id = s.id
            LEFT JOIN security_option so ON so.security_id = s.id
            LEFT JOIN security_future sf ON sf.security_id = s.id
        """
        try:
            rows = conn.execute(text(sql_select)).mappings().all()
        except Exception:
            rows = []

        for r in rows:
            sym = r["symbol"]
            if not sym:
                continue
            it = _instrument_type_from_qmt(r.get("instrument_type"), r.get("security_type"))
            ac = _asset_class(it, r.get("security_type"))
            delist = r.get("delist_date")
            opt_e = r.get("opt_expiry")
            fut_e = r.get("fut_expiry")
            expire_date = delist or opt_e or fut_e
            lp = r.get("last_price")
            ia = bool(r.get("is_active")) if r.get("is_active") is not None else True
            if isinstance(r.get("is_active"), int):
                ia = r["is_active"] == 1

            conn.execute(
                text(
                    """
                    INSERT INTO instruments (
                        code, name, exchange_code, asset_class, instrument_type,
                        open_date, expire_date, abbreviation, last_price, is_active,
                        created_at, updated_at
                    ) VALUES (
                        :code, :name, :ec, :ac, :it,
                        :od, :ed, :abbr, :lp, :ia,
                        :ca, :ua
                    )
                    ON CONFLICT (code) DO NOTHING
                    """
                ),
                {
                    "code": sym,
                    "name": r.get("name") or sym,
                    "ec": r.get("exchange_code") or "",
                    "ac": ac,
                    "it": it,
                    "od": r.get("list_date"),
                    "ed": expire_date,
                    "abbr": r.get("abbreviation"),
                    "lp": lp,
                    "ia": ia,
                    "ca": r.get("created_at"),
                    "ua": r.get("updated_at"),
                },
            )

    if "backtest_tasks" in tables:
        insp_bt = inspect(conn)
        bt_cols = {c["name"] for c in insp_bt.get_columns("backtest_tasks")}
        if "instrument_code" not in bt_cols:
            op.add_column(
                "backtest_tasks",
                sa.Column("instrument_code", sa.String(length=64), nullable=True, comment="标的代码"),
            )
            conn.execute(
                text(
                    """
                    UPDATE backtest_tasks
                    SET instrument_code = COALESCE(
                        (SELECT s.symbol FROM securities s WHERE s.id = backtest_tasks.security_id),
                        security_symbol
                    )
                    """
                )
            )
            insp_bt = inspect(conn)
            bt_cols = {c["name"] for c in insp_bt.get_columns("backtest_tasks")}

        if "security_id" in bt_cols:
            for ix in insp_bt.get_indexes("backtest_tasks"):
                if ix.get("column_names") == ["security_id"]:
                    op.drop_index(ix["name"], table_name="backtest_tasks")
            if dialect == "sqlite":
                with op.batch_alter_table("backtest_tasks") as batch_op:
                    batch_op.drop_column("security_id")
            else:
                for fk in insp_bt.get_foreign_keys("backtest_tasks"):
                    cols = fk.get("constrained_columns") or []
                    if "security_id" in cols:
                        cname = fk.get("name")
                        if cname:
                            op.drop_constraint(cname, "backtest_tasks", type_="foreignkey")
                op.drop_column("backtest_tasks", "security_id")
            insp_bt = inspect(conn)

        idx_bt = {i["name"] for i in insp_bt.get_indexes("backtest_tasks")}
        if "idx_backtest_tasks_instrument_code" not in idx_bt:
            op.create_index("idx_backtest_tasks_instrument_code", "backtest_tasks", ["instrument_code"], unique=False)

        fk_names = {
            fk.get("name")
            for fk in insp_bt.get_foreign_keys("backtest_tasks")
            if fk.get("name")
        }
        if "fk_backtest_tasks_instrument_code" not in fk_names:
            op.create_foreign_key(
                "fk_backtest_tasks_instrument_code",
                "backtest_tasks",
                "instruments",
                ["instrument_code"],
                ["code"],
                ondelete="SET NULL",
            )

    for tbl in _CHILD_TABLES:
        if tbl in tables:
            op.drop_table(tbl)

    if "securities" in tables:
        op.drop_table("securities")


def downgrade() -> None:
    raise NotImplementedError("013 迁移不可逆：请从数据库备份恢复")
