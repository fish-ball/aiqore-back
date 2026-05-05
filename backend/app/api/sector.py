"""板块信息 API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
from urllib.parse import unquote

from pydantic import BaseModel

from app.database import get_db
from app.services.sector_service import sector_service, sector_to_public_dict, sector_stats

router = APIRouter(prefix="/api/sector", tags=["板块信息"])
logger = logging.getLogger(__name__)


class SectorRemarkBody(BaseModel):
    """更新板块用户备注"""

    remark: Optional[str] = None


@router.post("/sync")
async def sync_sectors():
    """从 QMT 同步板块列表到数据库"""
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
        logger.error("同步板块失败: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/list")
async def get_sectors(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=500, description="每页条数"),
    category: Optional[str] = Query(None, description="板块分类（metadata.stats.category）"),
    market: Optional[str] = Query(None, description="市场代码，__cross__ 表示仅跨市场板块"),
    is_active: Optional[int] = Query(1, description="是否有效（metadata.stats.is_active）"),
    db: Session = Depends(get_db),
):
    """获取板块列表（分页）"""
    try:
        if market == "__cross__":
            sectors = sector_service.get_sectors(db, category, None, is_active)
            sectors = [s for s in sectors if not sector_stats(s).get("market")]
        else:
            sectors = sector_service.get_sectors(db, category, market, is_active)

        items = [sector_to_public_dict(s) for s in sectors]

        total = len(items)
        offset = (page - 1) * page_size
        results = items[offset : offset + page_size]
        return {"results": results, "count": total}
    except Exception as e:
        logger.error("获取板块列表失败: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/statistics")
async def get_sector_statistics(db: Session = Depends(get_db)):
    """获取板块统计信息"""
    try:
        return sector_service.get_sector_statistics(db)
    except Exception as e:
        logger.error("获取统计信息失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.patch("/{sector_alias:path}")
async def patch_sector(
    sector_alias: str,
    body: SectorRemarkBody,
    db: Session = Depends(get_db),
):
    """更新板块用户备注（不影响 metadata 与同步统计）。"""
    try:
        alias = unquote(sector_alias).strip()
        remark = (body.remark or "").strip() or None
        row = sector_service.update_sector_remark(db, alias, remark)
        if not row:
            raise HTTPException(status_code=404, detail="板块不存在")
        return sector_to_public_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新板块备注失败: %s", e)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/{sector_alias:path}")
async def get_sector(
    sector_alias: str,
    db: Session = Depends(get_db),
):
    """
    获取板块详情（含 children 摘要）。
    sector_alias 一般为 QMT 板块键，需 URL 编码。
    """
    try:
        alias = unquote(sector_alias).strip()
        sector = sector_service.get_sector_by_alias(db, alias)
        if not sector:
            raise HTTPException(status_code=404, detail="板块不存在")

        return sector_to_public_dict(sector, include_children=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取板块详情失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")
