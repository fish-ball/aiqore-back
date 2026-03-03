"""板块信息API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
from app.database import get_db
from app.services.sector_service import sector_service
from app.models.sector import Sector

router = APIRouter(prefix="/api/sector", tags=["板块信息"])
logger = logging.getLogger(__name__)


@router.post("/sync")
async def sync_sectors():
    """
    从QMT同步板块列表到数据库
    """
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            result = sector_service.sync_sectors_from_qmt(db)
            return {
                "code": 0 if result.get("success") else 1,
                "data": result,
                "message": result.get("message", "同步完成")
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"同步板块失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/list")
async def get_sectors(
    category: Optional[str] = Query(None, description="板块分类"),
    market: Optional[str] = Query(None, description="市场代码"),
    is_active: Optional[int] = Query(1, description="是否有效"),
    db: Session = Depends(get_db)
):
    """
    获取板块列表
    
    Args:
        category: 板块分类
        market: 市场代码
        is_active: 是否有效
    """
    try:
        sectors = sector_service.get_sectors(db, category, market, is_active)
        
        # 转换为字典格式
        items = []
        for sector in sectors:
            items.append({
                "id": sector.id,
                "name": sector.name,
                "display_name": sector.display_name or sector.name,
                "category": sector.category,
                "market": sector.market,
                "description": sector.description,
                "security_count": sector.security_count or 0,
                "is_active": sector.is_active,
                "last_sync_at": sector.last_sync_at.isoformat() if sector.last_sync_at else None,
                "created_at": sector.created_at.isoformat() if sector.created_at else None,
                "updated_at": sector.updated_at.isoformat() if sector.updated_at else None
            })
        
        return {
            "code": 0,
            "data": {
                "items": items,
                "total": len(items)
            },
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取板块列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/statistics")
async def get_sector_statistics(db: Session = Depends(get_db)):
    """
    获取板块统计信息
    """
    try:
        stats = sector_service.get_sector_statistics(db)
        return {
            "code": 0,
            "data": stats,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/{sector_name}")
async def get_sector(
    sector_name: str,
    db: Session = Depends(get_db)
):
    """
    获取板块详情
    
    Args:
        sector_name: 板块名称
    """
    try:
        sector = sector_service.get_sector_by_name(db, sector_name)
        if not sector:
            raise HTTPException(status_code=404, detail="板块不存在")
        
        # 转换为字典格式
        sector_dict = {
            "id": sector.id,
            "name": sector.name,
            "display_name": sector.display_name or sector.name,
            "category": sector.category,
            "market": sector.market,
            "description": sector.description,
            "security_count": sector.security_count or 0,
            "is_active": sector.is_active,
            "last_sync_at": sector.last_sync_at.isoformat() if sector.last_sync_at else None,
            "created_at": sector.created_at.isoformat() if sector.created_at else None,
            "updated_at": sector.updated_at.isoformat() if sector.updated_at else None
        }
        
        return {
            "code": 0,
            "data": sector_dict,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取板块详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")

