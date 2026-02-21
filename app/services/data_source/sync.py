"""
证券同步统一入口：按 source_type/source_id 解析连接，通过 adapter 包抽象接口取数并写库。
不在本模块依赖具体 Adapter 实现，仅通过 data_source 模型 source_type 枚举路由到适配器。
"""
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.data_source_connection import DataSourceConnection
from app.config import settings
from app.services.data_source.adapter import get_adapter

logger = logging.getLogger(__name__)


def _connection_to_config(conn: DataSourceConnection) -> Dict[str, Any]:
    """将 ORM 连接转为适配器所需 config 字典。QMT 使用 xt_quant_path、xt_quant_acct；其余为兼容保留。"""
    return {
        "host": conn.host,
        "port": conn.port,
        "user": conn.user,
        "password": conn.password,
        "xt_quant_path": conn.xt_quant_path,
        "xt_quant_acct": conn.xt_quant_acct,
    }


def get_adapter_for_connection(conn: DataSourceConnection):
    """根据连接记录的 source_type 字段路由到对应数据源适配器（用于连接测试等）。"""
    config = _connection_to_config(conn) if conn.source_type == "qmt" else {}
    return get_adapter(conn.source_type, config)


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

    adapter = get_adapter(source_type, config)
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
    from app.services.security_service import security_service
    return security_service.update_securities_from_data(db, with_details)


def _resolve_config(
    db: Session,
    source_type: str,
    source_id: Optional[int],
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    根据 source_type/source_id 解析出适配器所需 config。
    返回 (config_dict, error_message)；若成功则 error_message 为 None。
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
                return None, f"未找到 id={source_id} 的启用 QMT 连接"
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
                return None, f"未找到 id={source_id} 的启用 {source_type} 连接"
        config = {}
    else:
        return None, f"不支持的 source_type: {source_type}"
    return config, None


def sync_single_security(
    db: Session,
    symbol: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    从指定数据源同步单个证券到数据库（同步执行，供单证券更新使用）。
    symbol 可为带后缀的 000001.SZ 或 000001，market 从后缀推断，无则默认 SH。
    """
    resolved, err = _resolve_config(db, source_type, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 1,
        }
    config = resolved
    adapter = get_adapter(source_type, config)
    detail = adapter.get_instrument_detail(symbol)
    if symbol.endswith(".SH") or symbol.endswith(".SZ"):
        market = "SH" if symbol.endswith(".SH") else "SZ"
    else:
        market = "SH"
    with_details = [
        {
            "symbol": symbol,
            "market": market,
            "sector": "",
            "detail": detail,
        }
    ]
    from app.services.security_service import security_service
    return security_service.update_securities_from_data(db, with_details)
