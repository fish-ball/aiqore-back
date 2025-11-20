"""板块信息服务"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime
import logging
from app.models.sector import Sector
from app.services.qmt_service import qmt_service

logger = logging.getLogger(__name__)


class SectorService:
    """板块信息服务"""
    
    def __init__(self):
        self.qmt = qmt_service
    
    def sync_sectors_from_qmt(self, db: Session) -> Dict[str, Any]:
        """
        从QMT同步板块列表到数据库
        
        Args:
            db: 数据库会话
            
        Returns:
            同步结果统计
        """
        try:
            if not qmt_service.connected:
                if not qmt_service.connect():
                    return {
                        "success": False,
                        "message": "QMT连接失败",
                        "total": 0,
                        "created": 0,
                        "updated": 0,
                        "errors": 0
                    }
            
            # 获取所有板块列表
            try:
                from xtquant import xtdata
                if not hasattr(xtdata, 'get_sector_list'):
                    return {
                        "success": False,
                        "message": "QMT不支持get_sector_list方法",
                        "total": 0,
                        "created": 0,
                        "updated": 0,
                        "errors": 0
                    }
                
                sectors = xtdata.get_sector_list()
                if not sectors:
                    return {
                        "success": False,
                        "message": "未获取到板块列表",
                        "total": 0,
                        "created": 0,
                        "updated": 0,
                        "errors": 0
                    }
            except Exception as e:
                logger.error(f"获取板块列表失败: {e}")
                return {
                    "success": False,
                    "message": f"获取板块列表失败: {str(e)}",
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "errors": 0
                }
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            # 板块分类映射
            category_keywords = {
                "股票": ["A股", "B股", "创业板"],
                "基金": ["基金", "ETF", "LOF"],
                "债券": ["债券", "转债", "国债", "企业债", "公司债"],
                "期货": ["期货", "上期所", "大商所", "郑商所", "中金所", "能源中心"],
                "期权": ["期权"],
                "指数": ["指数"],
            }
            
            def get_category(sector_name: str) -> str:
                """根据板块名称判断分类"""
                for category, keywords in category_keywords.items():
                    for keyword in keywords:
                        if keyword in sector_name:
                            return category
                return "其他"
            
            def get_market(sector_name: str) -> Optional[str]:
                """根据板块名称判断市场"""
                if "沪市" in sector_name or "上证" in sector_name:
                    return "SH"
                elif "深市" in sector_name or "深证" in sector_name:
                    return "SZ"
                elif "北交所" in sector_name or "BJ" in sector_name:
                    return "BJ"
                elif "沪深" in sector_name:
                    return None  # 跨市场
                return None
            
            # 处理每个板块
            for sector_name in sectors:
                if not sector_name or not isinstance(sector_name, str):
                    continue
                
                try:
                    # 查询是否已存在
                    sector = db.query(Sector).filter(Sector.name == sector_name).first()
                    
                    # 获取板块内证券数量
                    security_count = 0
                    try:
                        securities = xtdata.get_stock_list_in_sector(sector_name)
                        if securities:
                            security_count = len(securities)
                    except Exception as e:
                        logger.debug(f"获取板块 {sector_name} 证券数量失败: {e}")
                    
                    category = get_category(sector_name)
                    market = get_market(sector_name)
                    
                    if sector:
                        # 更新现有记录
                        needs_update = False
                        if sector.security_count != security_count:
                            sector.security_count = security_count
                            needs_update = True
                        if sector.category != category:
                            sector.category = category
                            needs_update = True
                        if sector.market != market:
                            sector.market = market
                            needs_update = True
                        if needs_update:
                            sector.last_sync_at = datetime.now()
                            sector.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        # 创建新记录
                        sector = Sector(
                            name=sector_name,
                            display_name=sector_name,
                            category=category,
                            market=market,
                            security_count=security_count,
                            is_active=1,
                            last_sync_at=datetime.now()
                        )
                        db.add(sector)
                        created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.warning(f"处理板块 {sector_name} 失败: {e}")
                    continue
            
            # 提交更改
            db.commit()
            
            logger.info(f"板块同步完成: 总计 {len(sectors)}, 新增 {created_count}, 更新 {updated_count}, 错误 {error_count}")
            
            return {
                "success": True,
                "message": "同步成功",
                "total": len(sectors),
                "created": created_count,
                "updated": updated_count,
                "errors": error_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"同步板块失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"同步失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0
            }
    
    def get_sectors(
        self,
        db: Session,
        category: Optional[str] = None,
        market: Optional[str] = None,
        is_active: Optional[int] = None
    ) -> List[Sector]:
        """
        获取板块列表
        
        Args:
            db: 数据库会话
            category: 板块分类过滤
            market: 市场过滤
            is_active: 是否有效过滤
            
        Returns:
            板块列表
        """
        try:
            query = db.query(Sector)
            
            if category:
                query = query.filter(Sector.category == category)
            if market:
                query = query.filter(Sector.market == market)
            if is_active is not None:
                query = query.filter(Sector.is_active == is_active)
            
            return query.order_by(Sector.category, Sector.name).all()
        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return []
    
    def get_sector_by_name(self, db: Session, name: str) -> Optional[Sector]:
        """
        根据名称获取板块
        
        Args:
            db: 数据库会话
            name: 板块名称
            
        Returns:
            板块对象
        """
        try:
            return db.query(Sector).filter(Sector.name == name).first()
        except Exception as e:
            logger.error(f"获取板块失败: {e}")
            return None
    
    def get_sector_statistics(self, db: Session) -> Dict[str, Any]:
        """
        获取板块统计信息
        
        Args:
            db: 数据库会话
            
        Returns:
            统计信息字典
        """
        try:
            total_sectors = db.query(Sector).filter(Sector.is_active == 1).count()
            total_securities = db.query(Sector).filter(Sector.is_active == 1).with_entities(
                func.sum(Sector.security_count)
            ).scalar() or 0
            
            # 按分类统计
            category_stats = {}
            sectors = db.query(Sector).filter(Sector.is_active == 1).all()
            for sector in sectors:
                category = sector.category or "其他"
                if category not in category_stats:
                    category_stats[category] = {
                        "count": 0,
                        "securities": 0
                    }
                category_stats[category]["count"] += 1
                category_stats[category]["securities"] += sector.security_count or 0
            
            return {
                "total_sectors": total_sectors,
                "total_securities": total_securities,
                "category_stats": category_stats
            }
        except Exception as e:
            logger.error(f"获取板块统计失败: {e}")
            return {
                "total_sectors": 0,
                "total_securities": 0,
                "category_stats": {}
            }


# 全局板块服务实例
sector_service = SectorService()

