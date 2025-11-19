"""调试API - 用于查看QMT实际返回的数据结构"""
from fastapi import APIRouter, Query
from typing import List
import logging
import json
from app.services.qmt_service import qmt_service

router = APIRouter(prefix="/api/debug", tags=["调试"])

logger = logging.getLogger(__name__)


@router.get("/qmt-quote")
async def debug_qmt_quote(symbols: str = Query(..., description="证券代码，多个用逗号分隔")):
    """
    调试接口：查看QMT get_full_tick 实际返回的数据结构
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        if not qmt_service.connected:
            qmt_service.connect()
        
        # 调用QMT接口
        quotes = None
        
        if not quotes:
            # 直接调用xtdata
            try:
                from xtquant import xtdata
                quotes_raw = xtdata.get_full_tick(symbol_list)
                
                # 转换为可序列化的格式
                result = {
                    "raw_type": str(type(quotes_raw)),
                    "raw_data": {}
                }
                
                if quotes_raw:
                    for symbol in symbol_list:
                        if symbol in quotes_raw:
                            tick = quotes_raw[symbol]
                            result["raw_data"][symbol] = {
                                "type": str(type(tick)),
                                "data": {}
                            }
                            
                            if isinstance(tick, dict):
                                result["raw_data"][symbol]["data"] = tick
                                result["raw_data"][symbol]["keys"] = list(tick.keys())
                            elif hasattr(tick, '__dict__'):
                                result["raw_data"][symbol]["data"] = tick.__dict__
                                result["raw_data"][symbol]["attributes"] = [attr for attr in dir(tick) if not attr.startswith('_')]
                            else:
                                result["raw_data"][symbol]["data"] = str(tick)
                
                return {
                    "code": 0,
                    "data": result,
                    "message": "success"
                }
            except Exception as e:
                return {
                    "code": 1,
                    "data": None,
                    "message": f"调用QMT失败: {str(e)}"
                }
        
        return {
            "code": 0,
            "data": quotes,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"调试接口失败: {e}")
        import traceback
        return {
            "code": 1,
            "data": None,
            "message": f"错误: {str(e)}\n{traceback.format_exc()}"
        }

