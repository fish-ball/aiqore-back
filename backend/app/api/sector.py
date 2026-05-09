"""板块信息 API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
from urllib.parse import unquote

from pydantic import BaseModel, Field

from app.database import get_db
from app.services.data_source_service import sync_sectors as sync_sectors_from_data_source
from app.services.sector_service import sector_service, sector_to_public_dict

router = APIRouter(prefix="/api/sector", tags=["板块信息"])
logger = logging.getLogger(__name__)


class SectorRemarkBody(BaseModel):
    """更新板块用户备注"""

    remark: Optional[str] = None


class SectorSyncBody(BaseModel):
    """从指定数据源连接同步板块"""

    source_id: int = Field(..., ge=1, description="数据源连接 id（data_sources.id）")


@router.post("/sync")
async def sync_sectors(body: SectorSyncBody):
    """从指定启用中的数据源连接同步板块列表到数据库。"""
    try:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            result = sync_sectors_from_data_source(db, source_id=body.source_id)
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
        logger.exception("同步板块失败: %s", e)
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/list")
async def get_sectors(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=500, description="每页条数"),
    source: Optional[str] = Query(None, description="数据源：qmt / joinquant / tushare"),
    asset_class: Optional[str] = Query(None, description="资产大类，与 AssetClass.value 一致"),
    instrument_type: Optional[str] = Query(
        None, description="标的类型，与 InstrumentType.value 一致（如 STOCK、ETF）"
    ),
    db: Session = Depends(get_db),
):
    """获取板块列表（分页）"""
    try:
        sectors = sector_service.get_sectors(
            db, source=source, asset_class=asset_class, instrument_type=instrument_type
        )
        items = [sector_to_public_dict(s) for s in sectors]

        total = len(items)
        offset = (page - 1) * page_size
        results = items[offset : offset + page_size]
        return {"results": results, "count": total}
    except Exception as e:
        logger.exception("获取板块列表失败: %s", e)
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
    source: str = Query("qmt", description="数据源键，与 Sector.source 一致"),
    db: Session = Depends(get_db),
):
    """更新板块用户备注。"""
    try:
        alias = unquote(sector_alias).strip()
        remark = (body.remark or "").strip() or None
        row = sector_service.update_sector_remark(db, source, alias, remark)
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
    source: str = Query("qmt", description="数据源键，与 Sector.source 一致"),
    db: Session = Depends(get_db),
):
    """
    获取板块详情（含 children 摘要）。
    sector_alias 一般为数据源侧板块键，需 URL 编码。
    """
    try:
        alias = unquote(sector_alias).strip()
        sector = sector_service.get_sector(db, source, alias)
        if not sector:
            raise HTTPException(status_code=404, detail="板块不存在")

        return sector_to_public_dict(sector, include_children=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取板块详情失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")
