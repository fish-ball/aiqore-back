"""任务状态查询API"""
from fastapi import APIRouter, HTTPException
from app.celery_app import celery_app
from app.config import settings
from app.utils.celery_utils import (
    get_task_name_from_registry,
    get_task_display_name_from_registry,
    get_task_category_from_registry
)
import logging

router = APIRouter(prefix="/api/task", tags=["任务"])

logger = logging.getLogger(__name__)


@router.get("/list")
async def get_active_tasks():
    """
    获取所有活动任务列表
    
    返回所有正在运行、等待中或最近完成的任务
    """
    try:
        all_task_ids = set()
        
        # 1. 获取活动任务（正在运行的任务）
        task_name_map = {}  # 存储任务ID到任务名称的映射
        try:
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            
            # 从活动任务中提取任务ID和名称
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name') or task.get('task')
                    if task_id:
                        all_task_ids.add(task_id)
                        if task_name:
                            task_name_map[task_id] = task_name
        except Exception as e:
            logger.warning(f"获取活动任务失败: {e}")
        
        # 2. 获取已注册的任务（等待中的任务）
        try:
            inspect = celery_app.control.inspect()
            scheduled_tasks = inspect.scheduled() or {}
            
            # 从计划任务中提取任务ID和名称
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    request = task.get('request', {})
                    task_id = request.get('id')
                    task_name = request.get('task') or request.get('name')
                    if task_id:
                        all_task_ids.add(task_id)
                        if task_name:
                            task_name_map[task_id] = task_name
        except Exception as e:
            logger.warning(f"获取计划任务失败: {e}")
        
        # 3. 从Redis中获取最近的任务（包括已完成的任务）
        try:
            import redis
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            
            # 扫描Redis中的任务键（Celery存储格式：celery-task-meta-{task_id}）
            cursor = 0
            pattern = "celery-task-meta-*"
            max_tasks = 100  # 最多获取100个最近的任务
            
            while len(all_task_ids) < max_tasks:
                cursor, keys = r.scan(cursor, match=pattern, count=50)
                for key in keys:
                    # 提取任务ID（从键名中）
                    if key.startswith("celery-task-meta-"):
                        task_id = key.replace("celery-task-meta-", "")
                        all_task_ids.add(task_id)
                        
                        if len(all_task_ids) >= max_tasks:
                            break
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"从Redis获取任务失败: {e}")
        
        # 获取每个任务的状态
        task_list = []
        for task_id in all_task_ids:
            try:
                # AsyncResult 对象，表示任务的结果
                result = celery_app.AsyncResult(task_id)
                
                # 获取任务名称（从inspect获取）
                raw_task_name = task_name_map.get(task_id)
                
                # 从Celery任务注册表中获取规范化的任务名称（对应Task定义中的name）
                task_name = get_task_name_from_registry(raw_task_name) if raw_task_name else None
                
                # 从任务对象获取显示名称和分类（从装饰器传入）
                display_name = get_task_display_name_from_registry(task_name) if task_name else "未知任务"
                category = get_task_category_from_registry(task_name) if task_name else "其他"
                
                # name字段应该是完整名称（原始名称或规范化后的名称）
                full_task_name = raw_task_name or task_name or "未知任务"
                
                task_info = {
                    "task_id": task_id,
                    "state": result.state,  # 使用 result.state
                    "name": full_task_name,  # 完整任务名称
                    "display_name": display_name,  # 友好显示名称
                    "category": category
                }
                
                if result.state == "PENDING":
                    task_info.update({
                        "status": "等待中",
                        "current": 0,
                        "total": 0,
                        "progress": 0
                    })
                elif result.state == "PROGRESS":
                    meta = result.info or {}
                    current = meta.get("current", 0)
                    total = meta.get("total", 0)
                    progress = int((current / total * 100)) if total > 0 else 0
                    task_info.update({
                        "status": meta.get("status", "处理中"),
                        "current": current,
                        "total": total,
                        "progress": progress
                    })
                elif result.state == "SUCCESS":
                    # 在SUCCESS状态下，result.info 是任务的返回值
                    task_result = result.result if hasattr(result, 'result') else result.info
                    task_info.update({
                        "status": "完成",
                        "progress": 100,
                        "result": task_result if isinstance(task_result, dict) else {}
                    })
                elif result.state == "FAILURE":
                    error_info = result.info
                    task_info.update({
                        "status": "失败",
                        "error": str(error_info) if error_info else "未知错误",
                        "progress": 0
                    })
                else:
                    task_info.update({
                        "status": result.state,
                        "progress": 0
                    })
                
                task_list.append(task_info)
            except Exception as e:
                logger.warning(f"获取任务 {task_id} 状态失败: {e}")
                continue
        
        # 按状态排序：PROGRESS > PENDING > FAILURE > SUCCESS
        state_order = {"PROGRESS": 0, "PENDING": 1, "FAILURE": 2, "SUCCESS": 3}
        task_list.sort(key=lambda x: (state_order.get(x["state"], 99), x.get("task_id", "")))
        
        return {
            "code": 0,
            "data": {
                "tasks": task_list,
                "total": len(task_list)
            },
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
    """
    try:
        # AsyncResult 对象，表示任务的结果
        result = celery_app.AsyncResult(task_id)
        
        # 获取任务名称
        # 对于单个任务查询，尝试从inspect获取任务名称
        raw_task_name = None
        try:
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            scheduled_tasks = inspect.scheduled() or {}
            
            # 从活动任务中查找
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    if task.get('id') == task_id:
                        raw_task_name = task.get('name') or task.get('task')
                        break
                if raw_task_name:
                    break
            
            # 从计划任务中查找
            if not raw_task_name:
                for worker, tasks in scheduled_tasks.items():
                    for task in tasks:
                        request = task.get('request', {})
                        if request.get('id') == task_id:
                            raw_task_name = request.get('task') or request.get('name')
                            break
                    if raw_task_name:
                        break
        except Exception as e:
            logger.debug(f"从inspect获取任务名称失败: {e}")
        
        # 从Celery任务注册表中获取规范化的任务名称
        task_name = get_task_name_from_registry(raw_task_name) if raw_task_name else None
        
        # 从任务对象获取显示名称和分类（从装饰器传入）
        display_name = get_task_display_name_from_registry(task_name) if task_name else "未知任务"
        category = get_task_category_from_registry(task_name) if task_name else "其他"
        
        # name字段应该是完整名称
        full_task_name = raw_task_name or task_name or "未知任务"
        
        if result.state == "PENDING":
            response = {
                "task_id": task_id,
                "state": result.state,
                "name": full_task_name,
                "display_name": display_name,
                "category": category,
                "status": "等待中",
                "current": 0,
                "total": 0,
                "progress": 0
            }
        elif result.state == "PROGRESS":
            meta = result.info or {}
            current = meta.get("current", 0)
            total = meta.get("total", 0)
            progress = int((current / total * 100)) if total > 0 else 0
            response = {
                "task_id": task_id,
                "state": result.state,
                "name": full_task_name,
                "display_name": display_name,
                "category": category,
                "status": meta.get("status", "处理中"),
                "current": current,
                "total": total,
                "progress": progress
            }
        elif result.state == "SUCCESS":
            # 在SUCCESS状态下，result.info 是任务的返回值
            task_result = result.result if hasattr(result, 'result') else result.info
            
            # 如果任务返回的是字典，直接使用
            if isinstance(task_result, dict):
                result_data = task_result
            else:
                result_data = {}
            
            response = {
                "task_id": task_id,
                "state": result.state,
                "name": full_task_name,
                "display_name": display_name,
                "category": category,
                "status": "完成",
                "result": result_data,
                "progress": 100
            }
        elif result.state == "FAILURE":
            error_info = result.info
            response = {
                "task_id": task_id,
                "state": result.state,
                "name": full_task_name,
                "display_name": display_name,
                "category": category,
                "status": "失败",
                "error": str(error_info) if error_info else "未知错误",
                "progress": 0
            }
        else:
            response = {
                "task_id": task_id,
                "state": result.state,
                "name": full_task_name,
                "display_name": display_name,
                "category": category,
                "status": result.state,
                "progress": 0
            }
        
        return {
            "code": 0,
            "data": response,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

