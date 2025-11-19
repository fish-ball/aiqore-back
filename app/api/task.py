"""任务状态查询API"""
from fastapi import APIRouter, HTTPException
from app.celery_app import celery_app
from app.config import settings
from app.tasks.task_names import get_task_display_name, get_task_category
import logging
from typing import List, Dict, Any
import redis

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
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=False  # 需要二进制模式来扫描
            )
            
            # 扫描Redis中的任务键（Celery存储格式：celery-task-meta-{task_id}）
            cursor = 0
            pattern = "celery-task-meta-*"
            max_tasks = 100  # 最多获取100个最近的任务
            
            while len(all_task_ids) < max_tasks:
                cursor, keys = r.scan(cursor, match=pattern, count=50)
                for key in keys:
                    # 提取任务ID（从键名中）
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    if key_str.startswith("celery-task-meta-"):
                        task_id = key_str.replace("celery-task-meta-", "")
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
                task = celery_app.AsyncResult(task_id)
                
                # 获取任务名称（优先使用从inspect获取的名称，因为更准确）
                task_name = task_name_map.get(task_id)
                if not task_name:
                    if hasattr(task, 'name') and task.name:
                        task_name = task.name
                    elif hasattr(task, 'task') and task.task:
                        task_name = task.task
                
                # 使用任务名称映射获取友好名称
                display_name = get_task_display_name(task_name) if task_name else "未知任务"
                category = get_task_category(task_name) if task_name else "其他"
                
                task_info = {
                    "task_id": task_id,
                    "state": task.state,
                    "name": task_name or "未知任务",
                    "display_name": display_name,
                    "category": category
                }
                
                if task.state == "PENDING":
                    task_info.update({
                        "status": "等待中",
                        "current": 0,
                        "total": 0,
                        "progress": 0
                    })
                elif task.state == "PROGRESS":
                    meta = task.info or {}
                    current = meta.get("current", 0)
                    total = meta.get("total", 0)
                    progress = int((current / total * 100)) if total > 0 else 0
                    task_info.update({
                        "status": meta.get("status", "处理中"),
                        "current": current,
                        "total": total,
                        "progress": progress
                    })
                elif task.state == "SUCCESS":
                    result = task.result if hasattr(task, 'result') else task.info
                    task_info.update({
                        "status": "完成",
                        "progress": 100,
                        "result": result if isinstance(result, dict) else {}
                    })
                elif task.state == "FAILURE":
                    error_info = task.info
                    task_info.update({
                        "status": "失败",
                        "error": str(error_info) if error_info else "未知错误",
                        "progress": 0
                    })
                else:
                    task_info.update({
                        "status": task.state,
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
        task = celery_app.AsyncResult(task_id)
        
        # 获取任务名称
        task_name = None
        if hasattr(task, 'name') and task.name:
            task_name = task.name
        elif hasattr(task, 'task') and task.task:
            task_name = task.task
        
        # 使用任务名称映射获取友好名称
        display_name = get_task_display_name(task_name) if task_name else "未知任务"
        category = get_task_category(task_name) if task_name else "其他"
        
        if task.state == "PENDING":
            response = {
                "task_id": task_id,
                "state": task.state,
                "name": task_name or "未知任务",
                "display_name": display_name,
                "category": category,
                "status": "等待中",
                "current": 0,
                "total": 0,
                "progress": 0
            }
        elif task.state == "PROGRESS":
            meta = task.info or {}
            current = meta.get("current", 0)
            total = meta.get("total", 0)
            progress = int((current / total * 100)) if total > 0 else 0
            response = {
                "task_id": task_id,
                "state": task.state,
                "name": task_name or "未知任务",
                "display_name": display_name,
                "category": category,
                "status": meta.get("status", "处理中"),
                "current": current,
                "total": total,
                "progress": progress
            }
        elif task.state == "SUCCESS":
            # Celery在SUCCESS状态下，task.info直接是返回值
            result = task.result if hasattr(task, 'result') else task.info
            
            # 如果任务返回的是字典，直接使用
            if isinstance(result, dict):
                result_data = result
            else:
                result_data = {}
            
            response = {
                "task_id": task_id,
                "state": task.state,
                "name": task_name or "未知任务",
                "display_name": display_name,
                "category": category,
                "status": "完成",
                "result": result_data,
                "progress": 100
            }
        elif task.state == "FAILURE":
            error_info = task.info
            response = {
                "task_id": task_id,
                "state": task.state,
                "name": task_name or "未知任务",
                "display_name": display_name,
                "category": category,
                "status": "失败",
                "error": str(error_info) if error_info else "未知错误",
                "progress": 0
            }
        else:
            response = {
                "task_id": task_id,
                "state": task.state,
                "name": task_name or "未知任务",
                "display_name": display_name,
                "category": category,
                "status": task.state,
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

