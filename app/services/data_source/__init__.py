"""
数据源抽象层：证券列表同步统一入口，支持 QMT、聚宽、tushare 等。
"""
from app.services.data_source.sync import sync_securities

__all__ = ["sync_securities"]
