# -*- coding: utf-8 -*-
"""
回测异步任务：根据 BackTestTask 记录加载数据、执行 Backtrader 回测、写回结果。
"""
import logging
from typing import Any, Dict

from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.models.backtest_task import BackTestTask
from app.models.security import Security
from app.models.security import SecurityType
from app.services.backtest.data_loader import load_daily_for_backtest
from app.services.backtest.backtrader_engine import BacktraderEngine

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="task_run_backtest")
def task_run_backtest(self, backtest_task_id: str) -> Dict[str, Any]:
    """
    执行回测任务：从 DB 读取 BackTestTask，加载日线并前复权，用 Backtrader 执行策略脚本，写回 result 与 status。
    """
    db = SessionLocal()
    try:
        task = db.query(BackTestTask).filter(BackTestTask.id == backtest_task_id).first()
        if not task:
            logger.warning("回测任务不存在: %s", backtest_task_id)
            return {"success": False, "message": "任务不存在"}
        if task.status != "pending":
            logger.warning("回测任务状态非 pending，跳过: %s status=%s", backtest_task_id, task.status)
            return {"success": False, "message": f"状态为 {task.status}，无法执行"}

        task.status = "running"
        task.celery_task_id = self.request.id
        db.commit()

        symbol = task.security_symbol or ""
        if not symbol:
            task.status = "failure"
            task.result = {"error": "缺少证券代码"}
            db.commit()
            return {"success": False, "message": "缺少证券代码"}

        security_type = SecurityType.Equity.value
        if task.security_id is not None:
            sec = db.query(Security).filter(Security.id == task.security_id).first()
            if sec and sec.security_type:
                security_type = sec.security_type

        df = load_daily_for_backtest(
            security_type=security_type,
            symbol=symbol,
            start_date=task.start_date,
            end_date=task.end_date,
            adjust_type="forward",
        )

        output_dir = str(settings.BACKTEST_OUTPUT_ROOT / backtest_task_id)
        params = {
            "initial_cash": task.initial_cash,
            "commission": task.commission,
            "position_pct": task.position_pct,
            "symbol": symbol,
        }
        engine = BacktraderEngine()
        result = engine.run(
            strategy_source=task.script or "",
            data_df=df,
            params=params,
            output_dir=output_dir,
        )
        task.status = "success"
        task.result = result
        db.commit()
        logger.info("回测任务完成: %s", backtest_task_id)
        return {"success": True, "backtest_task_id": backtest_task_id, "result": result}
    except Exception as e:
        logger.exception("回测任务失败: %s", backtest_task_id)
        try:
            t = db.query(BackTestTask).filter(BackTestTask.id == backtest_task_id).first()
            if t:
                t.status = "failure"
                t.result = {"error": str(e)}
                db.commit()
        except Exception:
            pass
        return {"success": False, "message": str(e), "backtest_task_id": backtest_task_id}
    finally:
        db.close()
