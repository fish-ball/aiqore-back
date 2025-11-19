"""Celery应用配置"""
from celery import Celery
from app.config import settings

# 创建Celery应用
# 使用Redis作为消息代理和结果后端（推荐，性能更好且无需额外数据库表）
celery_app = Celery(
    "aiqore",
    broker=settings.REDIS_URL,  # Redis作为消息代理
    backend=settings.REDIS_URL,  # Redis作为结果后端
    include=["app.tasks"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,  # 跟踪任务启动，确保任务开始时就在后端创建记录
    task_time_limit=3600,  # 任务超时时间（秒）
    task_soft_time_limit=3300,  # 软超时时间
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Redis结果后端配置
    result_backend=settings.REDIS_URL,
    result_expires=3600,  # 结果过期时间（秒），1小时
    result_persistent=True,  # 持久化结果
    # 确保任务状态立即保存到后端
    task_always_eager=False,  # 异步执行
    task_store_eager_result=True,  # 即使任务失败也保存结果
)

