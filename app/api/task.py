"""任务状态查询API"""
from fastapi import APIRouter, HTTPException
from app.celery_app import celery_app
import logging

router = APIRouter(prefix="/api/task", tags=["任务"])

logger = logging.getLogger(__name__)


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
    """
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            response = {
                "task_id": task_id,
                "state": task.state,
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
                "status": "完成",
                "result": result_data,
                "progress": 100
            }
        elif task.state == "FAILURE":
            error_info = task.info
            response = {
                "task_id": task_id,
                "state": task.state,
                "status": "失败",
                "error": str(error_info) if error_info else "未知错误",
                "progress": 0
            }
        else:
            response = {
                "task_id": task_id,
                "state": task.state,
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

