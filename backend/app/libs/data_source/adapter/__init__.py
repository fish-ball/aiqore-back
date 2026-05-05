"""
数据源适配器子包：与 DataSourceConnection.source_type 枚举解耦的抽象实现。
不依赖 app / FastAPI，可独立运行与测试。
通过 source_type 字符串（与模型字段一致）路由到具体 Adapter 类。
"""
from typing import Dict, Any, Optional, Type

from .base import SecuritiesDataSourceAdapter
from .qmt import QMTAdapter
from .joinquant import JoinQuantAdapter
from .tushare import TushareAdapter

# 与 DataSourceConnection.source_type 字段取值一致
_ADAPTER_REGISTRY: Dict[str, Type[SecuritiesDataSourceAdapter]] = {
    "qmt": QMTAdapter,
    "joinquant": JoinQuantAdapter,
    "tushare": TushareAdapter,
}


def get_adapter(source_type: str, config: Optional[Dict[str, Any]] = None) -> SecuritiesDataSourceAdapter:
    """
    根据 source_type（与 DataSourceConnection.source_type 一致）返回对应适配器实例。
    不在 sync 中依赖具体 Adapter 实现，仅通过本方法触发同步能力。
    """
    cls = _ADAPTER_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"不支持的 source_type: {source_type}，可选: {list(_ADAPTER_REGISTRY.keys())}")
    return cls(config or {})


__all__ = [
    "SecuritiesDataSourceAdapter",
    "get_adapter",
    "QMTAdapter",
    "JoinQuantAdapter",
    "TushareAdapter",
]
