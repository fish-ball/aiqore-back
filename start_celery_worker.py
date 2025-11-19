"""启动Celery Worker"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()

