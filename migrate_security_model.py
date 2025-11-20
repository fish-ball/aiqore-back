"""执行 Security 模型扩展迁移"""
from app.database import engine, Base
from app.models.security import Security
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def execute_migration():
    """执行迁移"""
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        if 'securities' not in inspector.get_table_names():
            logger.info("securities 表不存在，将创建新表...")
            Base.metadata.create_all(bind=engine, tables=[Security.__table__])
            logger.info("securities 表创建完成！")
            return
        
        # 需要添加的字段列表
        columns_to_add = [
            ('instrument_type', 'VARCHAR(50)', '标的类型（InstrumentType），如 Stock, Fund, Bond, Future, Option 等'),
            ('exchange_id', 'VARCHAR(20)', '交易所代码（ExchangeID），如 SSE, SZSE 等'),
            ('product_id', 'VARCHAR(50)', '产品代码（ProductID）'),
            ('currency_id', 'VARCHAR(10)', '货币代码（CurrencyID），如 CNY, USD 等'),
            ('tick_size', 'NUMERIC(10,4)', '最小变动单位（TickSize）'),
            ('lot_size', 'INTEGER', '交易单位（LotSize），每手数量'),
            ('price_tick', 'NUMERIC(10,4)', '价格精度（PriceTick）'),
            ('upper_limit', 'NUMERIC(10,4)', '涨停价（UpperLimit）'),
            ('lower_limit', 'NUMERIC(10,4)', '跌停价（LowerLimit）'),
            ('pre_settlement_price', 'NUMERIC(10,4)', '昨结算价（PreSettlementPrice）'),
            ('pre_close_price', 'NUMERIC(10,4)', '昨收盘价（PreClosePrice）'),
            ('open_price', 'NUMERIC(10,4)', '开盘价（OpenPrice）'),
            ('last_price', 'NUMERIC(10,4)', '最新价（LastPrice）'),
            ('volume', 'INTEGER', '成交量（Volume）'),
            ('amount', 'NUMERIC(20,2)', '成交额（Amount）'),
            ('open_interest', 'INTEGER', '持仓量（OpenInterest），期货/期权用'),
            ('strike_price', 'NUMERIC(10,4)', '行权价（StrikePrice），期权用'),
            ('expiry_date', 'TIMESTAMP', '到期日（ExpiryDate），期货/期权用'),
            ('underlying_symbol', 'VARCHAR(20)', '标的证券代码（UnderlyingSymbol），期权/可转债用'),
            ('conversion_ratio', 'NUMERIC(10,4)', '转股比例（ConversionRatio），可转债用'),
            ('interest_rate', 'NUMERIC(10,4)', '利率（InterestRate），债券用'),
            ('maturity_date', 'TIMESTAMP', '到期日（MaturityDate），债券用'),
            ('face_value', 'NUMERIC(10,4)', '面值（FaceValue），债券用'),
            ('fund_type', 'VARCHAR(50)', '基金类型（FundType），如 ETF, LOF, 封闭式基金 等'),
            ('nav', 'NUMERIC(10,4)', '净值（NAV），基金用'),
            ('accumulated_nav', 'NUMERIC(10,4)', '累计净值（AccumulatedNAV），基金用'),
        ]
        
        # 根据数据库类型选择合适的数据类型
        db_type = engine.dialect.name
        
        if db_type == 'postgresql':
            raw_data_type = 'JSONB'
        elif db_type == 'mysql':
            raw_data_type = 'JSON'
        else:
            raw_data_type = 'TEXT'  # SQLite 等使用 TEXT
        
        # 添加 raw_data 字段
        columns_to_add.append(('raw_data', raw_data_type, '原始数据 JSON，保存完整的 QMT get_instrument_detail 返回数据'))
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                added_count = 0
                
                # 添加每个字段
                for col_name, col_type, comment in columns_to_add:
                    if not column_exists('securities', col_name):
                        # 根据数据库类型调整 SQL
                        if db_type == 'postgresql':
                            if col_type == 'JSONB':
                                sql = f'ALTER TABLE securities ADD COLUMN {col_name} {col_type}'
                            else:
                                sql = f'ALTER TABLE securities ADD COLUMN {col_name} {col_type}'
                            if comment:
                                sql += f"; COMMENT ON COLUMN securities.{col_name} IS '{comment}'"
                        elif db_type == 'mysql':
                            sql = f'ALTER TABLE securities ADD COLUMN {col_name} {col_type}'
                            if comment:
                                sql += f" COMMENT '{comment}'"
                        else:  # SQLite
                            sql = f'ALTER TABLE securities ADD COLUMN {col_name} {col_type}'
                        
                        conn.execute(text(sql))
                        logger.info(f"✓ 已添加字段: {col_name}")
                        added_count += 1
                    else:
                        logger.info(f"- 字段已存在: {col_name}")
                
                # 创建索引
                try:
                    if not column_exists('securities', 'instrument_type') or not any(
                        idx['name'] == 'idx_instrument_type' 
                        for idx in inspector.get_indexes('securities')
                    ):
                        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_instrument_type ON securities(instrument_type)'))
                        logger.info("✓ 已创建索引: idx_instrument_type")
                except Exception as e:
                    logger.warning(f"创建索引 idx_instrument_type 失败（可能已存在）: {e}")
                
                try:
                    if not column_exists('securities', 'exchange_id') or not any(
                        idx['name'] == 'idx_exchange_id' 
                        for idx in inspector.get_indexes('securities')
                    ):
                        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_exchange_id ON securities(exchange_id)'))
                        logger.info("✓ 已创建索引: idx_exchange_id")
                except Exception as e:
                    logger.warning(f"创建索引 idx_exchange_id 失败（可能已存在）: {e}")
                
                # 提交事务
                trans.commit()
                
                if added_count > 0:
                    logger.info(f"\n✓ 迁移完成！共添加 {added_count} 个新字段")
                else:
                    logger.info("\n✓ 所有字段已存在，无需迁移")
                    
            except Exception as e:
                trans.rollback()
                logger.error(f"迁移失败: {e}")
                raise
                
    except Exception as e:
        logger.error(f"执行迁移时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    logger.info("开始执行 Security 模型扩展迁移...")
    execute_migration()
    logger.info("迁移执行完成！")

