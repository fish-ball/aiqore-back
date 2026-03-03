"""异步任务模块

导入具体任务模块，以便 Celery 能够发现并注册其中定义的任务。
"""

from . import security_tasks  # noqa: F401

__all__ = ["security_tasks"]
