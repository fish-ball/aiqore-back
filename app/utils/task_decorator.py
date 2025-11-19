"""任务装饰器

提供自定义的任务装饰器，支持显示名称和分类
"""
from app.celery_app import celery_app


def task(display_name=None, category=None, **kwargs):
    """
    自定义Celery任务装饰器
    
    支持通过参数指定显示名称和分类
    
    Args:
        display_name: 任务的友好显示名称（必需）
        category: 任务分类（可选）
        **kwargs: 传递给celery_app.task的其他参数
    
    Example:
        @task(display_name="同步证券列表", category="证券管理", name="update_securities")
        def update_securities_task(self, market=None):
            ...
    """
    def decorator(func):
        # 使用Celery的task装饰器
        celery_task = celery_app.task(**kwargs)(func)
        
        # 将显示名称和分类附加到任务对象上
        celery_task.display_name = display_name
        celery_task.category = category
        
        return celery_task
    
    return decorator

