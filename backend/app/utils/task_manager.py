"""通用任务管理工具

基于 Redis 记录/查询任务元数据，配合 Celery 任务状态用于：
- 任务列表展示
- 查看单个任务详情
- 任务状态与进度查询
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import redis

from app.config import settings
from app.celery_app import celery_app


_TASK_KEY_PREFIX = "task_manager:task:"
_TASK_ZSET_KEY = "task_manager:tasks"


def _get_redis_client() -> "redis.Redis":
    """获取 Redis 客户端实例。"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
    )


def _now_iso() -> str:
    """获取当前时间（UTC）ISO 字符串。"""
    return datetime.utcnow().isoformat()


def _task_key(task_id: str) -> str:
    """构造任务信息 Redis key。"""
    return f"{_TASK_KEY_PREFIX}{task_id}"


def save_task_info(
    task_id: str,
    task_name: str,
    celery_name: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """保存任务的基础信息到 Redis。

    Args:
        task_id: Celery 任务 ID
        task_name: 逻辑任务名称（对前端友好）
        celery_name: Celery 内部任务名称
        params: 提交任务时的参数
    """
    info: Dict[str, Any] = {
        "task_id": task_id,
        "task_name": task_name,
        "celery_name": celery_name,
        "params": params or {},
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    try:
        r = _get_redis_client()
        key = _task_key(task_id)
        # 任务信息保留 7 天，避免 Redis 长期膨胀
        r.set(key, json.dumps(info, ensure_ascii=False), ex=7 * 24 * 3600)
        # 使用 ZSET 记录任务 ID，score 为创建时间戳，用于排序
        r.zadd(_TASK_ZSET_KEY, {task_id: datetime.utcnow().timestamp()})
    except Exception:
        # 记录失败不影响任务本身执行，因此这里静默失败
        pass

    return info


def _merge_celery_state(info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """合并 Celery 当前状态/结果到任务信息中。"""
    try:
        async_result = celery_app.AsyncResult(task_id)
        state = async_result.state
        celery_info = async_result.info

        info["state"] = state
        if isinstance(celery_info, dict):
            info["meta"] = celery_info
        elif celery_info is not None:
            info["meta"] = {"result": celery_info}
        else:
            info.setdefault("meta", {})
    except Exception:
        # Celery 无法访问时，仅返回已有信息
        info.setdefault("state", "UNKNOWN")
    return info


def get_task_info(task_id: str, with_celery_state: bool = True) -> Optional[Dict[str, Any]]:
    """获取单个任务的信息。

    如果 Redis 中没有记录，会尽量从 Celery 后端补充状态信息。
    """
    info: Optional[Dict[str, Any]] = None

    try:
        r = _get_redis_client()
        raw = r.get(_task_key(task_id))
        if raw:
            info = json.loads(raw)
    except Exception:
        info = None

    if info is None:
        # Redis 中没有记录时，仍然尝试从 Celery 获取状态
        if not with_celery_state:
            return None
        try:
            async_result = celery_app.AsyncResult(task_id)
            state = async_result.state
            celery_info = async_result.info
            meta: Dict[str, Any]
            if isinstance(celery_info, dict):
                meta = celery_info
            elif celery_info is not None:
                meta = {"result": celery_info}
            else:
                meta = {}
            return {
                "task_id": task_id,
                "task_name": None,
                "celery_name": None,
                "params": {},
                "created_at": None,
                "updated_at": None,
                "state": state,
                "meta": meta,
            }
        except Exception:
            return None

    if with_celery_state:
        info = _merge_celery_state(info, task_id)
    return info


def list_tasks(
    limit: int = 50,
    offset: int = 0,
    with_celery_state: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """按创建时间倒序返回任务列表。

    Args:
        limit: 返回条数
        offset: 偏移量
        with_celery_state: 是否合并 Celery 实时状态
    """
    items: List[Dict[str, Any]] = []
    total = 0

    try:
        r = _get_redis_client()
        total = int(r.zcard(_TASK_ZSET_KEY))
        if total == 0:
            return [], 0

        # 倒序：最近的任务排在前面
        start = offset
        end = offset + limit - 1
        task_ids = r.zrevrange(_TASK_ZSET_KEY, start, end)

        for task_id in task_ids:
            info = get_task_info(task_id, with_celery_state=with_celery_state)
            if info:
                items.append(info)
    except Exception:
        # Redis 故障时返回空列表，不影响接口可用性
        return [], 0

    return items, total


def mark_task_state(task_id: str, state: str) -> None:
    """在 Redis 中标记任务状态（例如手动停止后标记为 REVOKED）。

    仅更新本地记录，不影响 Celery 实际状态。
    """
    try:
        r = _get_redis_client()
        key = _task_key(task_id)
        raw = r.get(key)
        if not raw:
            return
        info = json.loads(raw)
        info["state"] = state
        info["updated_at"] = _now_iso()
        r.set(key, json.dumps(info, ensure_ascii=False), ex=7 * 24 * 3600)
    except Exception:
        # 标记失败不影响主流程
        pass

