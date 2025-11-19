"""任务名称映射配置

统一管理所有异步任务的名称映射，将任务标识符映射到友好的中文名称
"""

# 任务名称映射：任务标识符 -> 友好名称
TASK_NAME_MAP = {
    # 证券相关任务
    "update_securities": "同步证券列表",
    "app.tasks.security_tasks.update_securities_task": "同步证券列表",
    
    # 可以在这里添加更多任务映射
    # "task_identifier": "任务友好名称",
}

# 任务分类
TASK_CATEGORIES = {
    "update_securities": "证券管理",
    "app.tasks.security_tasks.update_securities_task": "证券管理",
}


def get_task_display_name(task_name: str) -> str:
    """
    获取任务的友好显示名称
    
    Args:
        task_name: 任务标识符（可能是完整路径或简短名称）
    
    Returns:
        友好的中文名称，如果未找到则返回原始名称
    """
    if not task_name:
        return "未知任务"
    
    # 直接匹配
    if task_name in TASK_NAME_MAP:
        return TASK_NAME_MAP[task_name]
    
    # 尝试匹配完整路径
    for key, value in TASK_NAME_MAP.items():
        if task_name.endswith(key) or key in task_name:
            return value
    
    # 如果都没匹配到，返回原始名称
    return task_name


def get_task_category(task_name: str) -> str:
    """
    获取任务的分类
    
    Args:
        task_name: 任务标识符
    
    Returns:
        任务分类名称
    """
    if not task_name:
        return "其他"
    
    # 直接匹配
    if task_name in TASK_CATEGORIES:
        return TASK_CATEGORIES[task_name]
    
    # 尝试匹配完整路径
    for key, value in TASK_CATEGORIES.items():
        if task_name.endswith(key) or key in task_name:
            return value
    
    return "其他"

