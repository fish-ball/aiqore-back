"""标的信息 API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
from pydantic import BaseModel
import logging

from app.database import get_db
from app.services.instrument_service import instrument_service
from app.models.instrument import (
    Instrument,
    InstrumentType,
    instrument_type_to_market_layer,
    parse_market_suffix_from_code,
)
from app.libs.data_source.models.enums import MarketLayer
from app.constants.exchanges import exchange_brief_dict
from app.utils.task_manager import save_task_info


class UpdateInstrumentsBody(BaseModel):
    """从数据源更新标的列表请求体"""

    market: Optional[str] = None
    sector: Optional[str] = None
    adapter: Optional[str] = "qmt"
    source_id: Optional[int] = None


class UpdateOneBody(BaseModel):
    """从数据源更新单个标的请求体"""

    code: str
    adapter: Optional[str] = "qmt"
    source_id: Optional[int] = None


class UpdateDataBody(BaseModel):
    """拉取并补全单个标的本地缓存数据请求体"""

    code: str
    adapter: Optional[str] = "qmt"
    source_id: Optional[int] = None


router = APIRouter(prefix="/api/instrument", tags=["证券信息"])
logger = logging.getLogger(__name__)


def _instrument_to_list_item(sec: Instrument) -> Dict[str, Any]:
    return {
        "code": sec.code,
        "name": sec.name,
        "market": parse_market_suffix_from_code(sec.code),
        "exchange_code": sec.exchange_code,
        "exchange": exchange_brief_dict(sec.exchange_code),
        "asset_class": sec.asset_class,
        "instrument_type": sec.instrument_type,
        "last_price": float(sec.last_price) if sec.last_price is not None else None,
        "is_active": sec.is_active,
        "abbreviation": sec.abbreviation,
        "created_at": sec.created_at.isoformat() if sec.created_at else None,
        "updated_at": sec.updated_at.isoformat() if sec.updated_at else None,
    }


@router.post("/update")
async def update_instruments(body: UpdateInstrumentsBody):
    """
    从数据源更新证券基础信息（异步任务，经抽象层，可指定数据源连接）
    """
    try:
        from app.tasks.instrument_tasks import task_update_bulk_instrument_info
        from app.utils.task_lock import check_task_lock

        task_name = "task_update_bulk_instrument_info"
        is_locked, lock_message = check_task_lock(task_name)

        if is_locked:
            raise HTTPException(
                status_code=409,
                detail=lock_message or f"任务 '{task_name}' 正在运行中，请等待完成后再试",
            )

        task = task_update_bulk_instrument_info.delay(
            body.market, body.sector, body.adapter or "qmt", body.source_id
        )

        save_task_info(
            task_id=task.id,
            task_name="update_bulk_instrument_info",
            celery_name="task_update_bulk_instrument_info",
            params={
                "market": body.market,
                "sector": body.sector,
                "adapter": body.adapter or "qmt",
                "source_id": body.source_id,
            },
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交更新任务失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.post("/update-one")
async def update_single_instrument(body: UpdateOneBody, db: Session = Depends(get_db)):
    """
    从数据源更新单个标的基础信息（同步执行，适用于列表行内更新）
    """
    try:
        from app.services.data_source_service import sync_single_instrument

        result = sync_single_instrument(
            db, symbol=body.code.strip(), adapter=body.adapter or "qmt", source_id=body.source_id
        )
        if result.get("success"):
            return result
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "更新失败"),
        )
    except Exception as e:
        logger.error(f"更新单证券失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_instruments(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(100, ge=1, le=500, description="每页条数"),
    market: Optional[str] = Query(None, description="市场后缀 SH/SZ/BJ（按代码后缀筛选）"),
    sector: Optional[str] = Query(None, description="板块名称"),
    market_layer: Optional[MarketLayer] = Query(
        None, description="行情三大类筛选：Equity/Future/Option（按 instrument_type 推导）"
    ),
    exchange_code: Optional[str] = Query(None, description="交易所规范代码，如 SSE、SHFE"),
    instrument_type: Optional[str] = Query(
        None, description="标的类型，如 STOCK、ETF、FUTURE、OPTION（与 instruments.instrument_type 一致）"
    ),
    db: Session = Depends(get_db),
):
    """获取标的列表"""
    try:
        offset = (page - 1) * page_size
        limit = page_size
        query = db.query(Instrument).filter(Instrument.is_active.is_(True))

        if instrument_type is not None and instrument_type.strip():
            it = instrument_type.strip().upper()
            allowed = {m.value for m in InstrumentType}
            if it not in allowed:
                raise HTTPException(status_code=400, detail=f"不支持的 instrument_type: {it}")
            query = query.filter(Instrument.instrument_type == it)

        if market:
            suffix = f".{market.strip().upper()}"
            query = query.filter(Instrument.code.endswith(suffix))

        if exchange_code is not None and exchange_code.strip():
            query = query.filter(Instrument.exchange_code == exchange_code.strip().upper())

        if market_layer is not None:
            query = instrument_service.filter_by_market_layer(query, market_layer)

        if sector:
            try:
                from app.services.data_source_service import get_default_qmt_adapter

                qmt = get_default_qmt_adapter()
                sector_list = qmt.get_stock_list_in_sector(sector, market=None)
                if sector_list:
                    codes = [s["symbol"] for s in sector_list if s.get("symbol")]
                    if codes:
                        query = query.filter(Instrument.code.in_(codes))
                    else:
                        return {"results": [], "count": 0}
                else:
                    return {"results": [], "count": 0}
            except Exception as e:
                logger.warning(f"获取板块 '{sector}' 证券列表失败: {e}")
                return {"results": [], "count": 0}

        total = query.count()
        rows = query.order_by(Instrument.code).offset(offset).limit(limit).all()

        items = [_instrument_to_list_item(sec) for sec in rows]

        return {"results": items, "count": total}
    except Exception as e:
        import traceback

        logger.error(f"获取列表失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.post("/update-data")
def update_instrument_cache_data(body: UpdateDataBody, db: Session = Depends(get_db)):
    """
    按指定数据源拉取并补全单个标的的本地缓存数据（异步任务）。
    """
    try:
        from app.tasks.instrument_tasks import task_update_single_instrument_all_data
        from app.utils.task_lock import check_task_lock

        code = body.code.strip()
        adapter = body.adapter or "qmt"
        source_id = body.source_id

        sec = instrument_service.get_instrument_by_code(db, code)
        if not sec:
            raise HTTPException(status_code=404, detail="标的不存在")

        task_name = f"task_update_single_instrument_all_data:{code}"
        is_locked, lock_message = check_task_lock(task_name)
        if is_locked:
            raise HTTPException(
                status_code=409,
                detail=lock_message or f"任务 '{task_name}' 正在运行中，请等待完成后再试",
            )

        task = task_update_single_instrument_all_data.delay(
            symbol=code,
            adapter=adapter,
            source_id=source_id,
            force_update=False,
        )

        save_task_info(
            task_id=task.id,
            task_name="update_single_instrument_all_data",
            celery_name="task_update_single_instrument_all_data",
            params={
                "code": code,
                "adapter": adapter,
                "source_id": source_id,
                "force_update": False,
            },
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交单证券数据更新任务失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """根据 Celery task_id 查询任务状态与进度。"""
    from app.celery_app import celery_app

    async_result = celery_app.AsyncResult(task_id)
    state = async_result.state
    info = async_result.info
    meta = info if isinstance(info, dict) else {"result": info}

    return {
        "task_id": task_id,
        "state": state,
        "meta": meta,
    }


@router.get("/search")
async def search_instruments(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """搜索标的"""
    rows = instrument_service.search_instruments(db, keyword, limit)

    return [_instrument_to_list_item(sec) for sec in rows]


@router.get("/{code}")
async def get_instrument(
    code: str,
    db: Session = Depends(get_db),
):
    """获取标的详情"""
    try:
        inst = instrument_service.get_instrument_by_code(db, code)
        if not inst:
            raise HTTPException(status_code=404, detail="标的不存在")

        out = {
            "code": inst.code,
            "name": inst.name,
            "exchange_code": inst.exchange_code,
            "exchange": exchange_brief_dict(inst.exchange_code),
            "asset_class": inst.asset_class,
            "instrument_type": inst.instrument_type,
            "open_date": inst.open_date.isoformat() if inst.open_date else None,
            "expire_date": inst.expire_date.isoformat() if inst.expire_date else None,
            "is_active": inst.is_active,
            "abbreviation": inst.abbreviation,
            "last_price": float(inst.last_price) if inst.last_price is not None else None,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
            "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
        }
        from app.libs.data_source.cache import get_metadata_for_instrument

        cat = instrument_type_to_market_layer(inst.instrument_type)
        out["metadata"] = get_metadata_for_instrument(cat, inst.code)

        return out
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")
