"""证券信息服务"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import logging
from app.models.security import Security
from app.services.qmt_service import qmt_service

logger = logging.getLogger(__name__)


class SecurityService:
    """证券信息服务"""
    
    def __init__(self):
        self.qmt = qmt_service
    
    def update_securities_from_qmt(self, db: Session, market: Optional[str] = None) -> Dict[str, Any]:
        """
        从QMT更新证券基础信息
        
        Args:
            db: 数据库会话
            market: 市场代码，'SH' 或 'SZ'，None表示全部
            
        Returns:
            更新结果统计
        """
        try:
            # 获取QMT股票列表
            stocks = self.qmt.get_stock_list(market)
            
            if not stocks:
                return {
                    "success": False,
                    "message": "未获取到股票列表，请检查QMT连接",
                    "total": 0,
                    "created": 0,
                    "updated": 0
                }
            
            logger.info(f"开始更新证券信息，共 {len(stocks)} 只股票")
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            # 批量获取股票名称（每批100个）
            batch_size = 100
            symbols_batch = []
            names_map = {}
            
            # 先批量获取所有股票的名称
            for i, stock_data in enumerate(stocks):
                symbol = stock_data.get("symbol")
                if not symbol:
                    continue
                
                symbols_batch.append(symbol)
                
                # 每批处理一次
                if len(symbols_batch) >= batch_size or i == len(stocks) - 1:
                    try:
                        # 使用get_instrument_detail批量获取名称
                        if hasattr(self.qmt, 'qmt') and hasattr(self.qmt.qmt, 'get_instrument_detail'):
                            from xtquant import xtdata
                            for sym in symbols_batch:
                                try:
                                    detail = xtdata.get_instrument_detail(sym)
                                    if detail and isinstance(detail, dict):
                                        instrument_name = detail.get("InstrumentName", "")
                                        if instrument_name:
                                            names_map[sym] = instrument_name
                                except:
                                    pass
                    except Exception as e:
                        logger.debug(f"批量获取名称失败: {e}")
                    
                    symbols_batch = []
            
            # 如果批量获取失败，尝试从实时行情获取（但这样会很慢）
            if not names_map and len(stocks) > 0:
                logger.info("尝试从实时行情获取名称...")
                # 只获取前100个作为示例
                sample_symbols = [s.get("symbol") for s in stocks[:100] if s.get("symbol")]
                if sample_symbols:
                    quotes = self.qmt.get_realtime_quote(sample_symbols)
                    if quotes:
                        for sym, quote in quotes.items():
                            if quote.get("name"):
                                names_map[sym] = quote.get("name")
            
            # 处理每个股票
            for idx, stock_data in enumerate(stocks):
                symbol = stock_data.get("symbol")
                if not symbol:
                    continue
                
                try:
                    # 查询是否已存在
                    security = db.query(Security).filter(Security.symbol == symbol).first()
                    
                    # 获取名称（优先从批量获取的map中取，否则使用代码）
                    name = names_map.get(symbol, symbol)
                    
                    # 如果还是没有名称，尝试单独获取
                    if name == symbol:
                        try:
                            from xtquant import xtdata
                            if hasattr(xtdata, 'get_instrument_detail'):
                                detail = xtdata.get_instrument_detail(symbol)
                                if detail and isinstance(detail, dict):
                                    instrument_name = detail.get("InstrumentName", "")
                                    if instrument_name:
                                        name = instrument_name
                        except:
                            pass
                    
                    market_code = stock_data.get("market", "SH" if symbol.endswith(".SH") else "SZ")
                    
                    if security:
                        # 更新现有记录
                        if security.name != name or security.market != market_code:
                            security.name = name
                            security.market = market_code
                            security.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        # 创建新记录
                        security = Security(
                            symbol=symbol,
                            name=name,
                            market=market_code,
                            security_type="股票",
                            is_active=1
                        )
                        db.add(security)
                        created_count += 1
                    
                    # 每100条提交一次，避免事务过大
                    if (created_count + updated_count) % 100 == 0:
                        db.commit()
                        logger.info(f"已处理 {created_count + updated_count} 条记录...")
                        
                except Exception as e:
                    error_count += 1
                    logger.warning(f"处理股票 {symbol} 失败: {e}")
                    continue
            
            # 最终提交
            db.commit()
            
            logger.info(f"更新完成: 总计 {len(stocks)}, 新增 {created_count}, 更新 {updated_count}, 错误 {error_count}")
            
            return {
                "success": True,
                "message": "更新成功",
                "total": len(stocks),
                "created": created_count,
                "updated": updated_count,
                "errors": error_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新证券信息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0
            }
    
    def search_securities(
        self, 
        db: Session, 
        keyword: str, 
        limit: int = 50
    ) -> List[Security]:
        """
        搜索证券
        
        Args:
            db: 数据库会话
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            证券列表
        """
        try:
            keyword_upper = keyword.upper()
            securities = db.query(Security).filter(
                Security.is_active == 1,
                or_(
                    Security.symbol.like(f"%{keyword_upper}%"),
                    Security.name.like(f"%{keyword}%"),
                    Security.pinyin.like(f"%{keyword_upper}%")
                )
            ).limit(limit).all()
            
            return securities
        except Exception as e:
            logger.error(f"搜索证券失败: {e}")
            return []
    
    def get_security_by_symbol(self, db: Session, symbol: str) -> Optional[Security]:
        """
        根据代码获取证券信息
        
        Args:
            db: 数据库会话
            symbol: 证券代码
            
        Returns:
            证券对象
        """
        try:
            return db.query(Security).filter(Security.symbol == symbol).first()
        except Exception as e:
            logger.error(f"获取证券信息失败: {e}")
            return None
    
    def get_securities_by_market(
        self, 
        db: Session, 
        market: str, 
        limit: int = 100
    ) -> List[Security]:
        """
        根据市场获取证券列表
        
        Args:
            db: 数据库会话
            market: 市场代码
            limit: 返回数量限制
            
        Returns:
            证券列表
        """
        try:
            return db.query(Security).filter(
                Security.market == market,
                Security.is_active == 1
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"获取证券列表失败: {e}")
            return []


# 全局证券服务实例
security_service = SecurityService()

