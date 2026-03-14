"""通用任务管理 API

提供基于 Celery 的任务管理能力：
1. 获取当前注册的任务规格（说明/参数 schema）；
2. 异步调用某个任务，返回 task_id；
3. 查询任务状态与元数据/进度；
4. 停止一个任务；
5. 查看任务列表。
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.celery_app import celery_app
from app.tasks.specs import TaskSpec, get_task_spec, list_task_specs
from app.utils.task_manager import delete_task, get_task_info, list_tasks, mark_task_state, save_task_info


router = APIRouter(prefix="/api/tasks", tags=["任务管理"])


class RunTaskBody(BaseModel):
    """通用任务调用请求体。"""

    task_name: str
    params: Dict[str, Any] = {}


@router.get("/specs")
async def get_task_specs() -> Dict[str, Any]:
    """获取当前已注册的任务规格列表。"""
    specs: List[TaskSpec] = list_task_specs()
    data = [spec.model_dump() for spec in specs]
    return {"code": 0, "data": data, "message": "success"}


def _build_kwargs_from_spec(spec: TaskSpec, params: Dict[str, Any]) -> Dict[str, Any]:
    """根据任务规格与传入参数构造实际调用参数，并做最基本的必填校验。"""
    provided_keys = set(params.keys())
    allowed_keys = {p.name for p in spec.params}

    # 检查未知参数，避免前端传参拼写错误等
    unknown_keys = provided_keys - allowed_keys
    if unknown_keys:
        raise HTTPException(status_code=400, detail=f"存在未定义的参数: {', '.join(sorted(unknown_keys))}")

    kwargs: Dict[str, Any] = {}
    for p in spec.params:
        if p.name in params:
            kwargs[p.name] = params[p.name]
        elif p.default is not None:
            kwargs[p.name] = p.default
        elif p.required:
            raise HTTPException(status_code=422, detail=f"缺少必填参数: {p.name}")

    return kwargs


@router.post("/run")
async def run_task(body: RunTaskBody) -> Dict[str, Any]:
    """根据任务名称异步调用指定任务，返回 task_id。"""
    spec = get_task_spec(body.task_name)
    if not spec:
        raise HTTPException(status_code=404, detail=f"任务未注册: {body.task_name}")

    celery_task = celery_app.tasks.get(spec.celery_name)
    if not celery_task:
        raise HTTPException(status_code=500, detail=f"后端未注册 Celery 任务: {spec.celery_name}")

    params = body.params or {}
    kwargs = _build_kwargs_from_spec(spec, params)

    async_result = celery_task.delay(**kwargs)

    # 记录任务元数据，便于后续列表/查询
    save_task_info(
        task_id=async_result.id,
        task_name=spec.name,
        celery_name=spec.celery_name,
        params=kwargs,
    )

    return {
        "code": 0,
        "data": {"task_id": async_result.id, "state": "PENDING"},
        "message": "任务已提交，正在后台处理",
    }


@router.get("")
async def list_tasks_api(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """查看任务列表（按创建时间倒序）。"""
    items, total = list_tasks(limit=limit, offset=offset, with_celery_state=True)
    return {
        "code": 0,
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        "message": "success",
    }


@router.get("/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """查询单个任务状态及元数据。"""
    info = get_task_info(task_id, with_celery_state=True)
    if not info:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return {
        "code": 0,
        "data": info,
        "message": "success",
    }


@router.post("/{task_id}/stop")
async def stop_task(task_id: str) -> Dict[str, Any]:
    """停止指定任务（revoke）。"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        # 在本地任务记录中标记为 REVOKED
        mark_task_state(task_id, "REVOKED")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")

    return {
        "code": 0,
        "data": {"task_id": task_id, "state": "REVOKED"},
        "message": "任务已请求停止",
    }


@router.delete("/{task_id}")
async def delete_task_api(task_id: str) -> Dict[str, Any]:
    """从任务列表中删除指定任务记录（仅删除本地 Redis 记录，不影响 Celery 后端）。"""
    ok = delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除任务记录失败")

    return {
        "code": 0,
        "data": {"task_id": task_id},
        "message": "已删除",
    }


