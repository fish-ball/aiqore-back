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
                    "message": "未获取到股票列表",
                    "total": 0,
                    "created": 0,
                    "updated": 0
                }
            
            created_count = 0
            updated_count = 0
            
            for stock_data in stocks:
                symbol = stock_data.get("symbol")
                if not symbol:
                    continue
                
                # 查询是否已存在
                security = db.query(Security).filter(Security.symbol == symbol).first()
                
                # 获取股票详细信息
                stock_info = self.qmt.get_stock_info(symbol)
                if not stock_info:
                    continue
                
                # 获取实时行情以获取名称
                quote = self.qmt.get_realtime_quote([symbol])
                name = symbol
                if quote and symbol in quote:
                    name = quote[symbol].get("name", symbol)
                
                if security:
                    # 更新现有记录
                    security.name = name
                    security.market = stock_data.get("market", "SH" if symbol.endswith(".SH") else "SZ")
                    security.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    security = Security(
                        symbol=symbol,
                        name=name,
                        market=stock_data.get("market", "SH" if symbol.endswith(".SH") else "SZ"),
                        security_type="股票",
                        is_active=1
                    )
                    db.add(security)
                    created_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "message": "更新成功",
                "total": len(stocks),
                "created": created_count,
                "updated": updated_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新证券信息失败: {e}")
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0
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

