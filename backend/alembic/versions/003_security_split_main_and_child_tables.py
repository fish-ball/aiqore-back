"""security_split_main_and_child_tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

证券模型拆分：主表保留身份与基础信息；QMT 标识迁入 security_source_qmt；
交易规则、行情快照、类型扩展迁入 8 张子表；最后从主表删除已迁出列。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def _raw_data_type():
    try:
        op.get_bind().dialect.name
    except Exception:
        return sa.Text()
    try:
        conn = op.get_bind()
        if conn.dialect.name == 'postgresql':
            return postgresql.JSON(astext_type=sa.Text())
    except Exception:
        pass
    return sa.Text()


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    is_sqlite = dialect_name == 'sqlite'
    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. 创建数据源外表 security_source_qmt（若上次部分失败可能已存在）
    raw_data_col = postgresql.JSON(astext_type=sa.Text()) if dialect_name == 'postgresql' else sa.Text()
    if 'security_source_qmt' not in existing_tables:
        op.create_table(
            'security_source_qmt',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('instrument_type', sa.String(50), nullable=True, comment='标的类型（InstrumentType）'),
            sa.Column('exchange_id', sa.String(20), nullable=True, comment='交易所代码（ExchangeID）'),
            sa.Column('product_id', sa.String(50), nullable=True, comment='产品代码（ProductID）'),
            sa.Column('currency_id', sa.String(10), nullable=True, comment='货币代码（CurrencyID）'),
            sa.Column('raw_data', raw_data_col, nullable=True, comment='QMT get_instrument_detail 完整返回 JSON'),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True, comment='该数据源最后同步时间'),
        )
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('security_source_qmt')} if 'security_source_qmt' in existing_tables else set()
    if 'idx_security_source_qmt_instrument_type' not in existing_indexes:
        op.create_index('idx_security_source_qmt_instrument_type', 'security_source_qmt', ['instrument_type'])
    if 'idx_security_source_qmt_exchange_id' not in existing_indexes:
        op.create_index('idx_security_source_qmt_exchange_id', 'security_source_qmt', ['exchange_id'])

    # 2. 创建 8 张子表（若已存在则跳过，便于从部分失败中恢复）
    existing_tables = inspector.get_table_names()
    if 'security_trading_rules' not in existing_tables:
        op.create_table(
            'security_trading_rules',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('tick_size', sa.Numeric(10, 4), nullable=True, comment='最小变动单位（TickSize）'),
            sa.Column('lot_size', sa.Integer(), nullable=True, comment='交易单位（LotSize），每手数量'),
            sa.Column('price_tick', sa.Numeric(10, 4), nullable=True, comment='价格精度（PriceTick）'),
        )
    if 'security_quote_snapshot' not in existing_tables:
        op.create_table(
            'security_quote_snapshot',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('upper_limit', sa.Numeric(10, 4), nullable=True),
            sa.Column('lower_limit', sa.Numeric(10, 4), nullable=True),
            sa.Column('pre_settlement_price', sa.Numeric(10, 4), nullable=True),
            sa.Column('pre_close_price', sa.Numeric(10, 4), nullable=True),
            sa.Column('open_price', sa.Numeric(10, 4), nullable=True),
            sa.Column('last_price', sa.Numeric(10, 4), nullable=True),
            sa.Column('volume', sa.Integer(), nullable=True),
            sa.Column('amount', sa.Numeric(20, 2), nullable=True),
            sa.Column('open_interest', sa.Integer(), nullable=True),
        )
    if 'security_stock' not in existing_tables:
        op.create_table(
            'security_stock',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
        )
    if 'security_fund' not in existing_tables:
        op.create_table(
            'security_fund',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('fund_type', sa.String(50), nullable=True),
            sa.Column('nav', sa.Numeric(10, 4), nullable=True),
            sa.Column('accumulated_nav', sa.Numeric(10, 4), nullable=True),
        )
    if 'security_bond' not in existing_tables:
        op.create_table(
            'security_bond',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('interest_rate', sa.Numeric(10, 4), nullable=True),
            sa.Column('maturity_date', sa.DateTime(), nullable=True),
            sa.Column('face_value', sa.Numeric(10, 4), nullable=True),
        )
    if 'security_convertible' not in existing_tables:
        op.create_table(
            'security_convertible',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('underlying_symbol', sa.String(20), nullable=True),
            sa.Column('conversion_ratio', sa.Numeric(10, 4), nullable=True),
        )
    if 'security_option' not in existing_tables:
        op.create_table(
            'security_option',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('strike_price', sa.Numeric(10, 4), nullable=True),
            sa.Column('expiry_date', sa.DateTime(), nullable=True),
            sa.Column('underlying_symbol', sa.String(20), nullable=True),
        )
    if 'security_future' not in existing_tables:
        op.create_table(
            'security_future',
            sa.Column('security_id', sa.Integer(), sa.ForeignKey('securities.id', ondelete='CASCADE'), primary_key=True, comment='证券主表 id'),
            sa.Column('expiry_date', sa.DateTime(), nullable=True),
        )

    # 3. 数据迁移：从当前 securities 表拷贝到新表（此时主表仍含旧列）
    # 使用 connection 执行 SELECT 再 INSERT，以兼容不同数据库
    from sqlalchemy import text
    from sqlalchemy import inspect
    inspector = inspect(conn)
    sec_columns = [c['name'] for c in inspector.get_columns('securities')]

    def has_col(name):
        return name in sec_columns

    # 3.1 security_source_qmt
    if all(has_col(c) for c in ['instrument_type', 'exchange_id', 'product_id', 'currency_id', 'raw_data']):
        if is_sqlite:
            conn.execute(text("""
                INSERT OR IGNORE INTO security_source_qmt (security_id, instrument_type, exchange_id, product_id, currency_id, raw_data, updated_at)
                SELECT id, instrument_type, exchange_id, product_id, currency_id, raw_data, updated_at FROM securities
                WHERE instrument_type IS NOT NULL OR exchange_id IS NOT NULL OR product_id IS NOT NULL OR currency_id IS NOT NULL OR raw_data IS NOT NULL
            """))
        else:
            conn.execute(text("""
                INSERT INTO security_source_qmt (security_id, instrument_type, exchange_id, product_id, currency_id, raw_data, updated_at)
                SELECT id, instrument_type, exchange_id, product_id, currency_id, raw_data, updated_at FROM securities
                WHERE instrument_type IS NOT NULL OR exchange_id IS NOT NULL OR product_id IS NOT NULL OR currency_id IS NOT NULL OR raw_data IS NOT NULL
                ON CONFLICT (security_id) DO NOTHING
            """))

    # 3.2 security_trading_rules
    if all(has_col(c) for c in ['tick_size', 'lot_size', 'price_tick']):
        if is_sqlite:
            conn.execute(text("""
                INSERT OR IGNORE INTO security_trading_rules (security_id, tick_size, lot_size, price_tick)
                SELECT id, tick_size, lot_size, price_tick FROM securities
                WHERE tick_size IS NOT NULL OR lot_size IS NOT NULL OR price_tick IS NOT NULL
            """))
        else:
            conn.execute(text("""
                INSERT INTO security_trading_rules (security_id, tick_size, lot_size, price_tick)
                SELECT id, tick_size, lot_size, price_tick FROM securities
                WHERE tick_size IS NOT NULL OR lot_size IS NOT NULL OR price_tick IS NOT NULL
                ON CONFLICT (security_id) DO NOTHING
            """))

    # 3.3 security_quote_snapshot
    quote_cols = ['upper_limit', 'lower_limit', 'pre_settlement_price', 'pre_close_price', 'open_price', 'last_price', 'volume', 'amount', 'open_interest']
    if all(has_col(c) for c in quote_cols):
        if is_sqlite:
            conn.execute(text("""
                INSERT OR IGNORE INTO security_quote_snapshot (security_id, upper_limit, lower_limit, pre_settlement_price, pre_close_price, open_price, last_price, volume, amount, open_interest)
                SELECT id, upper_limit, lower_limit, pre_settlement_price, pre_close_price, open_price, last_price, volume, amount, open_interest FROM securities
                WHERE upper_limit IS NOT NULL OR lower_limit IS NOT NULL OR pre_settlement_price IS NOT NULL OR pre_close_price IS NOT NULL OR open_price IS NOT NULL OR last_price IS NOT NULL OR volume IS NOT NULL OR amount IS NOT NULL OR open_interest IS NOT NULL
            """))
        else:
            conn.execute(text("""
                INSERT INTO security_quote_snapshot (security_id, upper_limit, lower_limit, pre_settlement_price, pre_close_price, open_price, last_price, volume, amount, open_interest)
                SELECT id, upper_limit, lower_limit, pre_settlement_price, pre_close_price, open_price, last_price, volume, amount, open_interest FROM securities
                WHERE upper_limit IS NOT NULL OR lower_limit IS NOT NULL OR pre_settlement_price IS NOT NULL OR pre_close_price IS NOT NULL OR open_price IS NOT NULL OR last_price IS NOT NULL OR volume IS NOT NULL OR amount IS NOT NULL OR open_interest IS NOT NULL
                ON CONFLICT (security_id) DO NOTHING
            """))

    # 3.4 按 security_type 写入类型子表（仅插入 security_id）
    type_map = [('\u80a1\u7968', 'security_stock'), ('\u57fa\u91d1', 'security_fund'), ('\u503a\u5238', 'security_bond'), ('\u53ef\u8f6c\u503a', 'security_convertible'), ('\u671f\u6743', 'security_option'), ('\u671f\u8d27', 'security_future')]
    if has_col('security_type'):
        for type_cn, table in type_map:
            if is_sqlite:
                conn.execute(text("INSERT OR IGNORE INTO " + table + " (security_id) SELECT id FROM securities WHERE security_type = :t"), {"t": type_cn})
            else:
                conn.execute(text("INSERT INTO " + table + " (security_id) SELECT id FROM securities WHERE security_type = :t ON CONFLICT (security_id) DO NOTHING"), {"t": type_cn})

    # 3.5 补全类型子表专属字段
    if has_col('fund_type') and has_col('nav'):
        t = '\u57fa\u91d1'
        if is_sqlite:
            conn.execute(text("INSERT OR REPLACE INTO security_fund (security_id, fund_type, nav, accumulated_nav) SELECT id, fund_type, nav, accumulated_nav FROM securities WHERE security_type = :t AND (fund_type IS NOT NULL OR nav IS NOT NULL OR accumulated_nav IS NOT NULL)"), {"t": t})
        else:
            conn.execute(text("INSERT INTO security_fund (security_id, fund_type, nav, accumulated_nav) SELECT id, fund_type, nav, accumulated_nav FROM securities WHERE security_type = :t AND (fund_type IS NOT NULL OR nav IS NOT NULL OR accumulated_nav IS NOT NULL) ON CONFLICT (security_id) DO UPDATE SET fund_type = EXCLUDED.fund_type, nav = EXCLUDED.nav, accumulated_nav = EXCLUDED.accumulated_nav"), {"t": t})
    if has_col('interest_rate') and has_col('face_value'):
        t = '\u503a\u5238'
        if is_sqlite:
            conn.execute(text("INSERT OR REPLACE INTO security_bond (security_id, interest_rate, maturity_date, face_value) SELECT id, interest_rate, maturity_date, face_value FROM securities WHERE security_type = :t"), {"t": t})
        else:
            conn.execute(text("INSERT INTO security_bond (security_id, interest_rate, maturity_date, face_value) SELECT id, interest_rate, maturity_date, face_value FROM securities WHERE security_type = :t ON CONFLICT (security_id) DO UPDATE SET interest_rate = EXCLUDED.interest_rate, maturity_date = EXCLUDED.maturity_date, face_value = EXCLUDED.face_value"), {"t": t})
    if has_col('underlying_symbol') and has_col('conversion_ratio'):
        t = '\u53ef\u8f6c\u503a'
        if is_sqlite:
            conn.execute(text("INSERT OR REPLACE INTO security_convertible (security_id, underlying_symbol, conversion_ratio) SELECT id, underlying_symbol, conversion_ratio FROM securities WHERE security_type = :t"), {"t": t})
        else:
            conn.execute(text("INSERT INTO security_convertible (security_id, underlying_symbol, conversion_ratio) SELECT id, underlying_symbol, conversion_ratio FROM securities WHERE security_type = :t ON CONFLICT (security_id) DO UPDATE SET underlying_symbol = EXCLUDED.underlying_symbol, conversion_ratio = EXCLUDED.conversion_ratio"), {"t": t})
    if has_col('strike_price') and has_col('expiry_date'):
        t = '\u671f\u6743'
        if is_sqlite:
            conn.execute(text("INSERT OR REPLACE INTO security_option (security_id, strike_price, expiry_date, underlying_symbol) SELECT id, strike_price, expiry_date, underlying_symbol FROM securities WHERE security_type = :t"), {"t": t})
        else:
            conn.execute(text("INSERT INTO security_option (security_id, strike_price, expiry_date, underlying_symbol) SELECT id, strike_price, expiry_date, underlying_symbol FROM securities WHERE security_type = :t ON CONFLICT (security_id) DO UPDATE SET strike_price = EXCLUDED.strike_price, expiry_date = EXCLUDED.expiry_date, underlying_symbol = EXCLUDED.underlying_symbol"), {"t": t})
    if has_col('expiry_date'):
        t = '\u671f\u8d27'
        if is_sqlite:
            conn.execute(text("INSERT OR REPLACE INTO security_future (security_id, expiry_date) SELECT id, expiry_date FROM securities WHERE security_type = :t AND expiry_date IS NOT NULL"), {"t": t})
        else:
            conn.execute(text("INSERT INTO security_future (security_id, expiry_date) SELECT id, expiry_date FROM securities WHERE security_type = :t AND expiry_date IS NOT NULL ON CONFLICT (security_id) DO UPDATE SET expiry_date = EXCLUDED.expiry_date"), {"t": t})

    # 4. 从主表删除已迁出列
    cols_to_drop = [
        'instrument_type', 'exchange_id', 'product_id', 'currency_id', 'raw_data',
        'tick_size', 'lot_size', 'price_tick',
        'upper_limit', 'lower_limit', 'pre_settlement_price', 'pre_close_price',
        'open_price', 'last_price', 'volume', 'amount', 'open_interest',
        'strike_price', 'expiry_date', 'underlying_symbol', 'conversion_ratio',
        'interest_rate', 'maturity_date', 'face_value', 'fund_type', 'nav', 'accumulated_nav',
    ]
    for col in cols_to_drop:
        if not has_col(col):
            continue
        if is_sqlite:
            with op.batch_alter_table('securities', schema=None) as batch_op:
                batch_op.drop_column(col)
        else:
            op.drop_column('securities', col)


def downgrade() -> None:
    """回滚：主表加回列（nullable，不回填），再删除子表与数据源表。"""
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    is_sqlite = dialect_name == 'sqlite'
    raw_data_col = postgresql.JSON(astext_type=sa.Text()) if dialect_name == 'postgresql' else sa.Text()
    cols = [
        ('instrument_type', sa.String(50)), ('exchange_id', sa.String(20)), ('product_id', sa.String(50)), ('currency_id', sa.String(10)), ('raw_data', raw_data_col),
        ('tick_size', sa.Numeric(10, 4)), ('lot_size', sa.Integer()), ('price_tick', sa.Numeric(10, 4)),
        ('upper_limit', sa.Numeric(10, 4)), ('lower_limit', sa.Numeric(10, 4)), ('pre_settlement_price', sa.Numeric(10, 4)), ('pre_close_price', sa.Numeric(10, 4)),
        ('open_price', sa.Numeric(10, 4)), ('last_price', sa.Numeric(10, 4)), ('volume', sa.Integer()), ('amount', sa.Numeric(20, 2)), ('open_interest', sa.Integer()),
        ('strike_price', sa.Numeric(10, 4)), ('expiry_date', sa.DateTime()), ('underlying_symbol', sa.String(20)), ('conversion_ratio', sa.Numeric(10, 4)),
        ('interest_rate', sa.Numeric(10, 4)), ('maturity_date', sa.DateTime()), ('face_value', sa.Numeric(10, 4)), ('fund_type', sa.String(50)), ('nav', sa.Numeric(10, 4)), ('accumulated_nav', sa.Numeric(10, 4)),
    ]
    for col_name, col_type in cols:
        if is_sqlite:
            with op.batch_alter_table('securities', schema=None) as batch_op:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=True))
        else:
            op.add_column('securities', sa.Column(col_name, col_type, nullable=True))
    for table in ['security_future', 'security_option', 'security_convertible', 'security_bond', 'security_fund', 'security_stock', 'security_quote_snapshot', 'security_trading_rules', 'security_source_qmt']:
        op.drop_table(table)