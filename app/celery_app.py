"""Celery应用配置"""
from celery import Celery
from app.config import settings

# 构建数据库结果后端URL（celery-results格式：db+postgresql://...）
# 将 postgresql:// 替换为 db+postgresql://
database_backend_url = settings.DATABASE_URL.replace("postgresql://", "db+postgresql://", 1)

# 创建Celery应用
celery_app = Celery(
    "aiqore",
    broker=settings.REDIS_URL,  # 仍然使用Redis作为消息代理
    backend=database_backend_url,  # 使用数据库作为结果后端
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
    # celery-results 配置
    result_backend=database_backend_url,
    result_extended=True,  # 启用扩展结果（包含任务名称等信息）
    result_persistent=True,  # 持久化结果
)

