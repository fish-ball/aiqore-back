"""异步任务模块：导入任务包以便 Celery 发现并注册。"""

import app.tasks.instrument_tasks  # noqa: F401
import app.tasks.sector_tasks  # noqa: F401
from . import backtest_tasks  # noqa: F401

__all__ = ["backtest_tasks"]
