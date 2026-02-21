"""
证券同步统一入口：按 source_type/source_id 解析连接，调用适配器取数并写库。
"""
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.data_source_connection import DataSourceConnection
from app.services.data_source.base import SecuritiesDataSourceAdapter
from app.services.data_source.qmt_adapter import QMTAdapter
from app.services.data_source.joinquant_adapter import JoinQuantAdapter
from app.services.data_source.tushare_adapter import TushareAdapter
from app.services.security_service import security_service
from app.config import settings

logger = logging.getLogger(__name__)


def _connection_to_config(conn: DataSourceConnection) -> Dict[str, Any]:
    """将 ORM 连接转为 QMT 适配器所需 config 字典"""
    return {
        "host": conn.host,
        "port": conn.port,
        "user": conn.user,
        "password": conn.password,
        "xt_quant_path": conn.xt_quant_path,
        "xt_quant_acct": conn.xt_quant_acct,
    }


def _get_adapter(source_type: str, config: Optional[Dict[str, Any]]) -> SecuritiesDataSourceAdapter:
    """根据 source_type 和配置返回适配器实例"""
    if source_type == "qmt":
        return QMTAdapter(config or {})
    if source_type == "joinquant":
        return JoinQuantAdapter(config)
    if source_type == "tushare":
        return TushareAdapter(config)
    raise ValueError(f"不支持的 source_type: {source_type}")


def _get_default_qmt_config() -> Dict[str, Any]:
    """无连接记录时从 settings 构造默认 QMT 配置"""
    return {
        "host": settings.QMT_HOST,
        "port": settings.QMT_PORT,
        "user": settings.QMT_USER,
        "password": settings.QMT_PASSWORD,
        "xt_quant_path": settings.XT_QUANT_PATH,
        "xt_quant_acct": settings.XT_QUANT_ACCT,
    }


def sync_securities(
    db: Session,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    market: Optional[str] = None,
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    从指定数据源同步证券到数据库。
    使用抽象层适配器取数，再调用 security_service.update_securities_from_data 写库。
    """
    config: Optional[Dict[str, Any]] = None
    if source_type == "qmt":
        if source_id is not None:
            conn = db.query(DataSourceConnection).filter(
                DataSourceConnection.id == source_id,
                DataSourceConnection.source_type == "qmt",
                DataSourceConnection.is_active == True,
            ).first()
            if conn:
                config = _connection_to_config(conn)
            else:
                return {
                    "success": False,
                    "message": f"未找到 id={source_id} 的启用 QMT 连接",
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "errors": 0,
                }
        if config is None:
            conn = db.query(DataSourceConnection).filter(
                DataSourceConnection.source_type == "qmt",
                DataSourceConnection.is_active == True,
            ).order_by(DataSourceConnection.is_quote_source.desc(), DataSourceConnection.id).first()
            if conn:
                config = _connection_to_config(conn)
            else:
                config = _get_default_qmt_config()
    elif source_type in ("joinquant", "tushare"):
        if source_id is not None:
            conn = db.query(DataSourceConnection).filter(
                DataSourceConnection.id == source_id,
                DataSourceConnection.source_type == source_type,
                DataSourceConnection.is_active == True,
            ).first()
            if not conn:
                return {
                    "success": False,
                    "message": f"未找到 id={source_id} 的启用 {source_type} 连接",
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "errors": 0,
                }
        config = {}
    else:
        return {
            "success": False,
            "message": f"不支持的 source_type: {source_type}",
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }

    adapter = _get_adapter(source_type, config)
    securities = adapter.get_stock_list(market=market, sector=sector)
    if not securities:
        return {
            "success": False,
            "message": "未获取到证券列表",
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    logger.info(f"数据源 {source_type} 获取到 {len(securities)} 只证券，开始补全详情并写库")
    with_details = []
    for sec in securities:
        symbol = sec.get("symbol")
        if not symbol:
            continue
        detail = adapter.get_instrument_detail(symbol)
        with_details.append({
            "symbol": symbol,
            "market": sec.get("market", "SH" if symbol.endswith(".SH") else "SZ"),
            "sector": sec.get("sector", ""),
            "detail": detail,
        })
    return security_service.update_securities_from_data(db, with_details)
