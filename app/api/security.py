"""证券信息API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import logging
from app.database import get_db
from app.services.security_service import security_service
from app.models.security import Security


class UpdateSecuritiesBody(BaseModel):
    """从数据源更新证券列表请求体"""
    market: Optional[str] = None
    sector: Optional[str] = None
    source_type: Optional[str] = "qmt"
    source_id: Optional[int] = None


class UpdateOneBody(BaseModel):
    """从数据源更新单个证券请求体"""
    symbol: str
    source_type: Optional[str] = "qmt"
    source_id: Optional[int] = None


class UpdateDataBody(BaseModel):
    """拉取并补全单个证券本地缓存数据请求体"""
    symbol: str
    source_type: Optional[str] = "qmt"
    source_id: Optional[int] = None


router = APIRouter(prefix="/api/security", tags=["证券信息"])
logger = logging.getLogger(__name__)


@router.post("/update")
async def update_securities(body: UpdateSecuritiesBody):
    """
    从数据源更新证券基础信息（异步任务，经抽象层，可指定数据源连接）
    """
    try:
        from app.tasks.security_tasks import update_securities_task
        from app.utils.task_lock import check_task_lock

        task_name = "update_securities"
        is_locked, lock_message = check_task_lock(task_name)

        if is_locked:
            raise HTTPException(
                status_code=409,
                detail=lock_message or f"任务 '{task_name}' 正在运行中，请等待完成后再试"
            )

        task = update_securities_task.delay(
            body.market, body.sector, body.source_type or "qmt", body.source_id
        )
        
        return {
            "code": 0,
            "data": {
                "task_id": task.id,
                "status": "PENDING"
            },
            "message": "任务已提交，正在后台处理"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交更新任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.post("/update-one")
async def update_single_security(body: UpdateOneBody, db: Session = Depends(get_db)):
    """
    从数据源更新单个证券基础信息（同步执行，适用于列表行内更新）
    """
    try:
        from app.services.data_source.sync import sync_single_security
        result = sync_single_security(
            db, symbol=body.symbol, source_type=body.source_type or "qmt", source_id=body.source_id
        )
        if result.get("success"):
            return {"code": 0, "data": result, "message": "更新成功"}
        return {"code": 1, "data": result, "message": result.get("message", "更新失败")}
    except Exception as e:
        logger.error(f"更新单证券失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_securities(
    market: Optional[str] = Query(None, description="市场代码"),
    sector: Optional[str] = Query(None, description="板块名称"),
    security_type: Optional[str] = Query(None, description="证券类型"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取证券列表
    
    Args:
        market: 市场代码
        sector: 板块名称（需要通过板块服务查询该板块的证券）
        security_type: 证券类型
        limit: 返回数量
        offset: 偏移量
    """
    try:
        query = db.query(Security).filter(Security.is_active == 1)
        
        if market:
            query = query.filter(Security.market == market)
        
        if security_type:
            query = query.filter(Security.security_type == security_type)
        
        # 如果指定了板块，通过 QMT 服务获取该板块的证券列表（不直接依赖 xtdata）
        if sector:
            try:
                from app.services.data_source import get_default_qmt_adapter
                qmt = get_default_qmt_adapter()
                sector_list = qmt.get_stock_list_in_sector(sector, market=None)
                if sector_list:
                    symbols = [s["symbol"] for s in sector_list if s.get("symbol")]
                    if symbols:
                        query = query.filter(Security.symbol.in_(symbols))
                    else:
                        return {
                            "code": 0,
                            "data": {"items": [], "total": 0, "limit": limit, "offset": offset},
                            "message": "success"
                        }
                else:
                    return {
                        "code": 0,
                        "data": {"items": [], "total": 0, "limit": limit, "offset": offset},
                        "message": "success"
                    }
            except Exception as e:
                logger.warning(f"获取板块 '{sector}' 证券列表失败: {e}")
                return {
                    "code": 0,
                    "data": {"items": [], "total": 0, "limit": limit, "offset": offset},
                    "message": "success"
                }
        
        total = query.count()
        securities = query.order_by(Security.symbol).offset(offset).limit(limit).all()
        
        # 转换为字典格式，确保可以序列化
        items = []
        for sec in securities:
            items.append({
                "id": sec.id,
                "symbol": sec.symbol,
                "name": sec.name,
                "market": sec.market,
                "security_type": sec.security_type,
                "industry": sec.industry,
                "is_active": sec.is_active,
                "abbreviation": sec.abbreviation,
                "created_at": sec.created_at.isoformat() if sec.created_at else None,
                "updated_at": sec.updated_at.isoformat() if sec.updated_at else None
            })
        
        return {
            "code": 0,
            "data": {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            "message": "success"
        }
    except Exception as e:
        import traceback
        logger.error(f"获取列表失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.post("/update-data")
async def update_security_data(body: UpdateDataBody, db: Session = Depends(get_db)):
    """
    按指定数据源拉取并补全单个证券的本地缓存数据：全量日线、周线、月线（按 metadata.yaml 补全尚未下载的区间），
    以及全量分时（按日线交易日列表，补全尚未下载的 ticks/YYYYMMDD.parquet）。接口执行后 data 目录下会产生对应 parquet 与 metadata.yaml。
    """
    from datetime import datetime
    from app.services.data_source.cache import (
        get_daily,
        get_weekly,
        get_monthly,
        get_ticks,
        get_security_dir,
        get_dates_from_daily_parquet,
    )
    from app.services.data_source.sync import _resolve_config
    from app.services.data_source.adapter import get_adapter
    from app.services.security_service import security_service
    from app.config import settings

    symbol = body.symbol
    source_type = body.source_type or "qmt"
    source_id = body.source_id

    security = security_service.get_security_by_symbol(db, symbol)
    if not security:
        raise HTTPException(status_code=404, detail="证券不存在")
    security_type = security.security_type or "股票"
    list_dt = security.list_date
    if list_dt:
        start_date = list_dt.strftime("%Y-%m-%d")
    else:
        start_date = "1990-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    config, err = _resolve_config(db, source_type or "qmt", source_id)
    if err is not None:
        raise HTTPException(status_code=400, detail=err)
    adapter = get_adapter(source_type or "qmt", config)

    # 确保 data 根目录与标的目录存在
    data_root = settings.DATA_ROOT_PATH
    data_root.mkdir(parents=True, exist_ok=True)
    security_dir = get_security_dir(security_type, symbol)
    security_dir.mkdir(parents=True, exist_ok=True)

    result = {"symbol": symbol, "daily": 0, "weekly": 0, "monthly": 0, "ticks_dates": 0}
    try:
        # 按 meta 补全日线、周线、月线（不强制全量，只拉缺失区间）
        daily_rows = get_daily(security_type, symbol, start_date, end_date, force_update=False, adapter=adapter)
        result["daily"] = len(daily_rows)
        weekly_rows = get_weekly(security_type, symbol, start_date, end_date, force_update=False, adapter=adapter)
        result["weekly"] = len(weekly_rows)
        monthly_rows = get_monthly(security_type, symbol, start_date, end_date, force_update=False, adapter=adapter)
        result["monthly"] = len(monthly_rows)
    except Exception as e:
        logger.exception("拉取 K 线失败: %s", e)
        raise HTTPException(status_code=500, detail=f"拉取 K 线失败: {str(e)}")

    # 按日线 parquet 中的交易日补全分时（仅补尚未下载的日期）
    try:
        dates = get_dates_from_daily_parquet(security_type, symbol)
        tick_count = 0
        for d in dates:
            try:
                rows = get_ticks(security_type, symbol, d, force_update=False, adapter=adapter)
                if rows:
                    tick_count += 1
            except Exception as e:
                logger.warning("拉取分时 %s 失败: %s", d, e)
        result["ticks_dates"] = tick_count
    except Exception as e:
        logger.warning("补全分时失败: %s", e)

    # 若未拉到任何 K 线，在 data 中带提示，前端可据此提示用户
    total_kline = result["daily"] + result["weekly"] + result["monthly"]
    if total_kline == 0:
        result["hint"] = "未获取到任何 K 线数据，请确认数据源（QMT）已连接且标的代码正确（如 300760.SZ）"
    return {"code": 0, "data": result, "message": "success"}


@router.get("/search")
async def search_securities(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    搜索证券
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量限制
    """
    securities = security_service.search_securities(db, keyword, limit)
    
    # 转换为字典格式
    items = []
    for sec in securities:
        items.append({
            "id": sec.id,
            "symbol": sec.symbol,
            "name": sec.name,
            "market": sec.market,
            "security_type": sec.security_type,
            "industry": sec.industry,
            "is_active": sec.is_active,
            "abbreviation": sec.abbreviation
        })
    
    return {
        "code": 0,
        "data": items,
        "message": "success"
    }


@router.get("/{symbol}")
async def get_security(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    获取证券详情
    
    Args:
        symbol: 证券代码
    """
    try:
        security = security_service.get_security_by_symbol(db, symbol)
        if not security:
            raise HTTPException(status_code=404, detail="证券不存在")
        
        # 转换为字典格式
        security_dict = {
            "id": security.id,
            "symbol": security.symbol,
            "name": security.name,
            "market": security.market,
            "security_type": security.security_type,
            "industry": security.industry,
            "list_date": security.list_date.isoformat() if security.list_date else None,
            "delist_date": security.delist_date.isoformat() if security.delist_date else None,
            "is_active": security.is_active,
            "pinyin": security.pinyin,
            "abbreviation": security.abbreviation,
            "description": security.description,
            "created_at": security.created_at.isoformat() if security.created_at else None,
            "updated_at": security.updated_at.isoformat() if security.updated_at else None
        }
        
        return {
            "code": 0,
            "data": security_dict,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")

