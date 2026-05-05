"""
数据源抽象层（原子子模块）：适配器、领域模型与本地缓存。
数据库连接解析见 app.services.data_source_resolve；默认 QMT / 标的同步见
app.services.data_source_facade；Celery 任务见 app.tasks.instrument_tasks。
"""
from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.connection import get_adapter_for_connection

__all__ = ["get_adapter", "get_adapter_for_connection"]
