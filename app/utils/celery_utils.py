"""Celery工具函数

用于从Celery任务注册表中获取任务信息
"""
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

# 任务名称到任务对象的映射缓存
_task_cache = {}


def _load_task_objects():
    """加载所有任务对象到缓存"""
    if _task_cache:
        return
    
    try:
        # 导入所有任务模块，确保任务被注册
        from app.tasks import security_tasks
        
        # 从任务模块中获取所有任务对象
        for attr_name in dir(security_tasks):
            attr = getattr(security_tasks, attr_name)
            if hasattr(attr, 'name') and hasattr(attr, 'apply_async'):  # 是Celery任务
                task_name = attr.name
                _task_cache[task_name] = attr
                # 也缓存完整路径
                if hasattr(attr, '__module__') and hasattr(attr, '__name__'):
                    full_path = f"{attr.__module__}.{attr.__name__}"
                    _task_cache[full_path] = attr
    except Exception as e:
        logger.warning(f"加载任务对象失败: {e}")


def get_task_display_name_from_registry(task_name: str) -> str:
    """
    从任务注册表中获取任务的显示名称
    
    Args:
        task_name: 任务名称
    
    Returns:
        任务的显示名称，如果找不到则返回None
    """
    if not task_name:
        return None
    
    # 加载任务对象
    _load_task_objects()
    
    # 从缓存中查找
    if task_name in _task_cache:
        task_obj = _task_cache[task_name]
        if hasattr(task_obj, 'display_name'):
            return task_obj.display_name
        return None
    
    # 从Celery注册表中查找
    if task_name in celery_app.tasks:
        task_obj = celery_app.tasks[task_name]
        if hasattr(task_obj, 'display_name'):
            return task_obj.display_name
        return None
    
    # 遍历所有注册的任务
    for registered_name, task_obj in celery_app.tasks.items():
        if hasattr(task_obj, 'name') and task_obj.name == task_name:
            if hasattr(task_obj, 'display_name'):
                return task_obj.display_name
            return None
    
    return None


def get_task_category_from_registry(task_name: str) -> str:
    """
    从任务注册表中获取任务的分类
    
    Args:
        task_name: 任务名称
    
    Returns:
        任务的分类，如果找不到则返回"其他"
    """
    if not task_name:
        return "其他"
    
    # 加载任务对象
    _load_task_objects()
    
    # 从缓存中查找
    if task_name in _task_cache:
        task_obj = _task_cache[task_name]
        if hasattr(task_obj, 'category'):
            return task_obj.category
        return "其他"
    
    # 从Celery注册表中查找
    if task_name in celery_app.tasks:
        task_obj = celery_app.tasks[task_name]
        if hasattr(task_obj, 'category'):
            return task_obj.category
        return "其他"
    
    # 遍历所有注册的任务
    for registered_name, task_obj in celery_app.tasks.items():
        if hasattr(task_obj, 'name') and task_obj.name == task_name:
            if hasattr(task_obj, 'category'):
                return task_obj.category
            return "其他"
    
    return "其他"


def get_task_name_from_registry(task_name: str) -> str:
    """
    从Celery任务注册表中获取任务名称
    
    如果任务名称是完整路径（如 app.tasks.security_tasks.update_securities_task），
    会尝试从注册表中查找对应的任务，并返回其定义的名称（如 update_securities）
    
    Args:
        task_name: 任务名称（可能是完整路径或简短名称）
    
    Returns:
        任务定义的名称，如果找不到则返回原始名称
    """
    if not task_name:
        return None
    
    # 加载任务对象
    _load_task_objects()
    
    # 如果任务名称已经在缓存中，直接返回其定义的名称
    if task_name in _task_cache:
        task_obj = _task_cache[task_name]
        return task_obj.name if hasattr(task_obj, 'name') else task_name
    
    # 尝试从Celery注册表中查找
    if task_name in celery_app.tasks:
        task_obj = celery_app.tasks[task_name]
        # 返回任务定义的名称（@celery_app.task(name="...") 中的name参数）
        return task_obj.name if hasattr(task_obj, 'name') else task_name
    
    # 遍历所有注册的任务，查找匹配的
    for registered_name, task_obj in celery_app.tasks.items():
        # 检查任务定义的名称是否匹配
        if hasattr(task_obj, 'name') and task_obj.name == task_name:
            return task_obj.name
        # 检查完整路径是否匹配
        if hasattr(task_obj, '__module__') and hasattr(task_obj, '__name__'):
            full_path = f"{task_obj.__module__}.{task_obj.__name__}"
            if full_path == task_name or task_name.endswith(task_obj.__name__):
                return task_obj.name if hasattr(task_obj, 'name') else registered_name
    
    # 如果都没找到，返回原始名称
    return task_name


def get_task_by_name(task_name: str):
    """
    从Celery任务注册表中获取任务对象
    
    Args:
        task_name: 任务名称
    
    Returns:
        任务对象，如果找不到则返回None
    """
    if not task_name:
        return None
    
    # 加载任务对象
    _load_task_objects()
    
    # 从缓存中查找
    if task_name in _task_cache:
        return _task_cache[task_name]
    
    # 直接查找
    if task_name in celery_app.tasks:
        return celery_app.tasks[task_name]
    
    # 尝试通过名称匹配
    for registered_name, task_obj in celery_app.tasks.items():
        if hasattr(task_obj, 'name') and task_obj.name == task_name:
            return task_obj
        if registered_name == task_name:
            return task_obj
    
    return None

