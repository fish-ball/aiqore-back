"""
数据源适配器子包：与 DataSource.source_type 枚举解耦的抽象实现。
不依赖 app / FastAPI，可独立运行与测试。
通过 source_type 字符串（与模型字段一致）路由到具体 Adapter 类。
"""
from typing import Any, Dict, Optional, Type

from .base import DataSourceAdapter
from .joinquant import JoinQuantDataSourceAdapter
from .qmt.adapter import QMTDataSourceAdapter
from .tushare import TushareDataSourceAdapter

# 与 DataSource.source_type 字段取值一致
_ADAPTER_REGISTRY: Dict[str, Type[DataSourceAdapter]] = {
    "qmt": QMTDataSourceAdapter,
    "joinquant": JoinQuantDataSourceAdapter,
    "tushare": TushareDataSourceAdapter,
}


def get_adapter(source_type: str, config: Optional[Dict[str, Any]] = None) -> DataSourceAdapter:
    """
    根据 source_type（与 DataSource.source_type 一致）返回对应适配器实例。
    不在 sync 中依赖具体 Adapter 实现，仅通过本方法触发同步能力。
    """
    key = (source_type or "").strip().lower()
    cfg: Dict[str, Any] = dict(config or {})
    cls = _ADAPTER_REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"不支持的 source_type: {source_type}，可选: {list(_ADAPTER_REGISTRY.keys())}")
    return cls(cfg)


__all__ = [
    "DataSourceAdapter",
    "get_adapter",
    "QMTDataSourceAdapter",
    "JoinQuantDataSourceAdapter",
    "TushareDataSourceAdapter",
]
