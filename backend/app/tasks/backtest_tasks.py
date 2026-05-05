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
from app.models.instrument import Instrument, instrument_type_to_market_layer
from app.libs.backtest.data_loader import load_daily_for_backtest
from app.libs.backtest.backtrader_engine import BacktraderEngine

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

        symbol = (task.security_symbol or task.instrument_code or "").strip()
        if not symbol:
            task.status = "failure"
            task.result = {"error": "缺少标的代码"}
            db.commit()
            return {"success": False, "message": "缺少标的代码"}

        market_layer = instrument_type_to_market_layer(None)
        code_key = (task.instrument_code or symbol).strip()
        if code_key:
            sec = db.query(Instrument).filter(Instrument.code == code_key).first()
            if sec:
                market_layer = instrument_type_to_market_layer(sec.instrument_type)

        df = load_daily_for_backtest(
            market_layer=market_layer,
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
    except Exception:
        logger.exception("回测任务失败: %s", backtest_task_id)
        raise
    finally:
        db.close()
