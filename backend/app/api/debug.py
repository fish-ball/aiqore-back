"""调试API - 用于查看QMT实际返回的数据结构"""
from fastapi import APIRouter, Query, HTTPException
import logging
from app.libs.data_source.adapter.qmt import ensure_xtdata
from app.config import settings

router = APIRouter(prefix="/api/debug", tags=["调试"])

logger = logging.getLogger(__name__)


@router.get("/qmt-quote")
async def debug_qmt_quote(symbols: str = Query(..., description="证券代码，多个用逗号分隔")):
    """
    调试接口：查看QMT get_full_tick 实际返回的数据结构
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        xtdata = ensure_xtdata(settings.XT_QUANT_PATH)
        if not xtdata:
            raise HTTPException(status_code=503, detail="xtquant 未加载")
        quotes_raw = xtdata.get_full_tick(symbol_list)
        result = {"raw_type": str(type(quotes_raw)), "raw_data": {}}
        if quotes_raw:
            for symbol in symbol_list:
                if symbol in quotes_raw:
                    tick = quotes_raw[symbol]
                    result["raw_data"][symbol] = {"type": str(type(tick)), "data": {}}
                    if isinstance(tick, dict):
                        result["raw_data"][symbol]["data"] = tick
                        result["raw_data"][symbol]["keys"] = list(tick.keys())
                    elif hasattr(tick, "__dict__"):
                        result["raw_data"][symbol]["data"] = tick.__dict__
                        result["raw_data"][symbol]["attributes"] = [a for a in dir(tick) if not a.startswith("_")]
                    else:
                        result["raw_data"][symbol]["data"] = str(tick)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调试接口失败: {e}")
        import traceback
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}\n{traceback.format_exc()}")
