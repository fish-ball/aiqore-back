# -*- coding: utf-8 -*-
"""板块相关 Celery 任务（adapter 指定数据源实现，默认 qmt）。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.data_source_service import sync_sectors
from app.utils.task_lock import TaskLock

logger = logging.getLogger(__name__)


def _elapsed(t0: float) -> str:
    return "%.2fs" % (time.perf_counter() - t0)


@celery_app.task(bind=True, name="task_sync_sectors")
def task_sync_sectors(
    self,
    *,
    source_id: int,
):
    """从数据源同步板块列表及统计信息到数据库。"""
    task_name = "task_sync_sectors"
    task_lock = TaskLock(task_name, timeout=3600)

    if not task_lock.acquire():
        error_msg = f"任务 '{task_name}' 已在运行中，无法重复执行"
        logger.warning(error_msg)
        result: Dict[str, Any] = {
            "success": False,
            "message": error_msg,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
        self.update_state(
            state="SUCCESS",
            meta={"status": "任务冲突", "result": result},
        )
        return result

    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        logger.info("板块同步任务: 启动 source_id=%s", source_id)
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 0,
                "status": "任务已启动，正在拉取板块列表...",
            },
        )

        result = sync_sectors(db, source_id=source_id)
        logger.info(
            "板块同步任务: 完成 success=%s total=%s created=%s updated=%s errors=%s 耗时 %s",
            result.get("success"),
            result.get("total"),
            result.get("created"),
            result.get("updated"),
            result.get("errors"),
            _elapsed(t0),
        )

        if result.get("success"):
            total = int(result.get("total") or 0)
            self.update_state(
                state="SUCCESS",
                meta={
                    "current": total,
                    "total": total,
                    "status": "同步完成",
                    "result": result,
                },
            )
        else:
            self.update_state(
                state="SUCCESS",
                meta={"status": "同步失败", "result": result},
            )
        return result
    except Exception as e:
        logger.error("板块同步任务异常: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        task_lock.release()
        db.close()
