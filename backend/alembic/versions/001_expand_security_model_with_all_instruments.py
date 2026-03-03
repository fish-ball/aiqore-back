"""expand_security_model_with_all_instruments

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加新字段到 securities 表
    op.add_column('securities', sa.Column('instrument_type', sa.String(length=50), nullable=True, comment='标的类型（InstrumentType），如 Stock, Fund, Bond, Future, Option 等'))
    op.add_column('securities', sa.Column('exchange_id', sa.String(length=20), nullable=True, comment='交易所代码（ExchangeID），如 SSE, SZSE 等'))
    op.add_column('securities', sa.Column('product_id', sa.String(length=50), nullable=True, comment='产品代码（ProductID）'))
    op.add_column('securities', sa.Column('currency_id', sa.String(length=10), nullable=True, comment='货币代码（CurrencyID），如 CNY, USD 等'))
    op.add_column('securities', sa.Column('tick_size', sa.Numeric(precision=10, scale=4), nullable=True, comment='最小变动单位（TickSize）'))
    op.add_column('securities', sa.Column('lot_size', sa.Integer(), nullable=True, comment='交易单位（LotSize），每手数量'))
    op.add_column('securities', sa.Column('price_tick', sa.Numeric(precision=10, scale=4), nullable=True, comment='价格精度（PriceTick）'))
    op.add_column('securities', sa.Column('upper_limit', sa.Numeric(precision=10, scale=4), nullable=True, comment='涨停价（UpperLimit）'))
    op.add_column('securities', sa.Column('lower_limit', sa.Numeric(precision=10, scale=4), nullable=True, comment='跌停价（LowerLimit）'))
    op.add_column('securities', sa.Column('pre_settlement_price', sa.Numeric(precision=10, scale=4), nullable=True, comment='昨结算价（PreSettlementPrice）'))
    op.add_column('securities', sa.Column('pre_close_price', sa.Numeric(precision=10, scale=4), nullable=True, comment='昨收盘价（PreClosePrice）'))
    op.add_column('securities', sa.Column('open_price', sa.Numeric(precision=10, scale=4), nullable=True, comment='开盘价（OpenPrice）'))
    op.add_column('securities', sa.Column('last_price', sa.Numeric(precision=10, scale=4), nullable=True, comment='最新价（LastPrice）'))
    op.add_column('securities', sa.Column('volume', sa.Integer(), nullable=True, comment='成交量（Volume）'))
    op.add_column('securities', sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交额（Amount）'))
    op.add_column('securities', sa.Column('open_interest', sa.Integer(), nullable=True, comment='持仓量（OpenInterest），期货/期权用'))
    op.add_column('securities', sa.Column('strike_price', sa.Numeric(precision=10, scale=4), nullable=True, comment='行权价（StrikePrice），期权用'))
    op.add_column('securities', sa.Column('expiry_date', sa.DateTime(), nullable=True, comment='到期日（ExpiryDate），期货/期权用'))
    op.add_column('securities', sa.Column('underlying_symbol', sa.String(length=20), nullable=True, comment='标的证券代码（UnderlyingSymbol），期权/可转债用'))
    op.add_column('securities', sa.Column('conversion_ratio', sa.Numeric(precision=10, scale=4), nullable=True, comment='转股比例（ConversionRatio），可转债用'))
    op.add_column('securities', sa.Column('interest_rate', sa.Numeric(precision=10, scale=4), nullable=True, comment='利率（InterestRate），债券用'))
    op.add_column('securities', sa.Column('maturity_date', sa.DateTime(), nullable=True, comment='到期日（MaturityDate），债券用'))
    op.add_column('securities', sa.Column('face_value', sa.Numeric(precision=10, scale=4), nullable=True, comment='面值（FaceValue），债券用'))
    op.add_column('securities', sa.Column('fund_type', sa.String(length=50), nullable=True, comment='基金类型（FundType），如 ETF, LOF, 封闭式基金 等'))
    op.add_column('securities', sa.Column('nav', sa.Numeric(precision=10, scale=4), nullable=True, comment='净值（NAV），基金用'))
    op.add_column('securities', sa.Column('accumulated_nav', sa.Numeric(precision=10, scale=4), nullable=True, comment='累计净值（AccumulatedNAV），基金用'))
    
    # 添加 JSON 字段用于保存原始数据
    # 根据数据库类型选择合适的数据类型
    try:
        op.add_column('securities', sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='原始数据 JSON，保存完整的 QMT get_instrument_detail 返回数据'))
    except:
        # 如果不是 PostgreSQL，使用 Text 类型
        op.add_column('securities', sa.Column('raw_data', sa.Text(), nullable=True, comment='原始数据 JSON，保存完整的 QMT get_instrument_detail 返回数据'))
    
    # 创建索引
    op.create_index('idx_instrument_type', 'securities', ['instrument_type'])
    op.create_index('idx_exchange_id', 'securities', ['exchange_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_exchange_id', table_name='securities')
    op.drop_index('idx_instrument_type', table_name='securities')
    
    # 删除字段
    op.drop_column('securities', 'raw_data')
    op.drop_column('securities', 'accumulated_nav')
    op.drop_column('securities', 'nav')
    op.drop_column('securities', 'fund_type')
    op.drop_column('securities', 'face_value')
    op.drop_column('securities', 'maturity_date')
    op.drop_column('securities', 'interest_rate')
    op.drop_column('securities', 'conversion_ratio')
    op.drop_column('securities', 'underlying_symbol')
    op.drop_column('securities', 'expiry_date')
    op.drop_column('securities', 'strike_price')
    op.drop_column('securities', 'open_interest')
    op.drop_column('securities', 'amount')
    op.drop_column('securities', 'volume')
    op.drop_column('securities', 'last_price')
    op.drop_column('securities', 'open_price')
    op.drop_column('securities', 'pre_close_price')
    op.drop_column('securities', 'pre_settlement_price')
    op.drop_column('securities', 'lower_limit')
    op.drop_column('securities', 'upper_limit')
    op.drop_column('securities', 'price_tick')
    op.drop_column('securities', 'lot_size')
    op.drop_column('securities', 'tick_size')
    op.drop_column('securities', 'currency_id')
    op.drop_column('securities', 'product_id')
    op.drop_column('securities', 'exchange_id')
    op.drop_column('securities', 'instrument_type')

