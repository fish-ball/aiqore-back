"""
数据源抽象层：证券列表同步统一入口，支持 QMT、聚宽、tushare 等。
"""
from app.config import settings
from app.services.data_source.sync import sync_securities
from app.services.data_source.qmt_adapter import QMTAdapter

_default_qmt_adapter = None


def get_default_qmt_adapter() -> QMTAdapter:
    """返回默认 QMT 适配器（使用 settings 配置），供 market/trade/sector/security 等使用。"""
    global _default_qmt_adapter
    if _default_qmt_adapter is None:
        _default_qmt_adapter = QMTAdapter({
            "xt_quant_path": settings.XT_QUANT_PATH,
            "xt_quant_acct": settings.XT_QUANT_ACCT,
        })
    return _default_qmt_adapter


__all__ = ["sync_securities", "get_default_qmt_adapter"]
