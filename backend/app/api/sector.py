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
            if not result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=result.get("message", "同步失败"),
                )
            return result
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步板块失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/list")
async def get_sectors(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=500, description="每页条数"),
    category: Optional[str] = Query(None, description="板块分类"),
    market: Optional[str] = Query(None, description="市场代码，__cross__ 表示仅跨市场板块"),
    is_active: Optional[int] = Query(1, description="是否有效"),
    db: Session = Depends(get_db),
):
    """
    获取板块列表（分页）
    """
    try:
        if market == "__cross__":
            sectors = sector_service.get_sectors(db, category, None, is_active)
            sectors = [s for s in sectors if not s.market]
        else:
            sectors = sector_service.get_sectors(db, category, market, is_active)

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

        total = len(items)
        offset = (page - 1) * page_size
        results = items[offset:offset + page_size]
        return {"results": results, "count": total}
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
        return stats
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

        return sector_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取板块详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")
