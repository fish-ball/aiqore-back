"""Celery应用配置"""
from celery import Celery
from app.config import settings

# 创建Celery应用
celery_app = Celery(
    "aiqore",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 任务超时时间（秒）
    task_soft_time_limit=3300,  # 软超时时间
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

