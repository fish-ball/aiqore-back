# -*- coding: utf-8 -*-
"""
回测 API：发起回测、列表、详情、删除；图表与明细按约定路径 backend/data/backtest/{task_id}/ 提供。
"""
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.backtest_task import BackTestTask
from app.models.strategy import Strategy, STRATEGY_TYPE_BACKTRADER
from app.models.security import Security
from app.config import settings
from app.tasks.backtest_tasks import task_run_backtest

router = APIRouter(prefix="", tags=["回测"])


# ---------- Pydantic ----------


class BacktestRunBody(BaseModel):
    """发起回测请求体"""
    strategy_id: str = Field(..., description="策略 ID（UUID）")
    symbol: str = Field(..., min_length=1, description="证券代码")
    start_date: str = Field(..., description="回测开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="回测结束日期 YYYY-MM-DD")
    initial_cash: Optional[float] = Field(None, description="初始资金，默认 1000000")
    commission: Optional[float] = Field(None, description="手续费，默认 0.0002")
    position_pct: Optional[int] = Field(None, description="仓位比例，默认 95")
    security_id: Optional[int] = Field(None, description="证券 ID，可选，用于解析证券大类 security_type（Equity/Future/Option）")


def _task_to_item(t: BackTestTask, strategy_name: Optional[str] = None) -> dict:
    """BackTestTask 转响应字典，可选带入策略名称"""
    item = {
        "id": t.id,
        "strategy_id": t.strategy_id,
        "strategy_name": strategy_name,
        "security_id": t.security_id,
        "security_symbol": t.security_symbol,
        "security_name": t.security_name,
        "start_date": t.start_date,
        "end_date": t.end_date,
        "initial_cash": t.initial_cash,
        "commission": t.commission,
        "position_pct": t.position_pct,
        "status": t.status,
        "celery_task_id": t.celery_task_id,
        "result": t.result,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
    return item


@router.post("/run")
async def run_backtest(body: BacktestRunBody, db: Session = Depends(get_db)):
    """根据策略发起回测，创建 BackTestTask 并提交 Celery 执行，返回 backtest_task_id。"""
    strategy = db.query(Strategy).filter(Strategy.id == body.strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.strategy_type != STRATEGY_TYPE_BACKTRADER:
        raise HTTPException(status_code=400, detail="当前仅支持 strategy_type=backtrader 的策略")

    security_id = body.security_id
    security_name: Optional[str] = None
    if security_id is not None:
        sec = db.query(Security).filter(Security.id == security_id).first()
        if sec:
            security_name = sec.name
    if security_name is None:
        sec = db.query(Security).filter(Security.symbol == body.symbol).first()
        if sec:
            security_id = sec.id
            security_name = sec.name

    task = BackTestTask(
        strategy_id=strategy.id,
        security_id=security_id,
        security_symbol=body.symbol.strip(),
        security_name=security_name or body.symbol.strip(),
        start_date=body.start_date.strip(),
        end_date=body.end_date.strip(),
        initial_cash=body.initial_cash if body.initial_cash is not None else 1000000.0,
        commission=body.commission if body.commission is not None else 0.0002,
        position_pct=body.position_pct if body.position_pct is not None else 95,
        script=strategy.script,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    async_result = task_run_backtest.delay(str(task.id))
    task.celery_task_id = async_result.id
    db.commit()

    return {"backtest_task_id": task.id, "celery_task_id": async_result.id}


@router.get("/tasks")
async def list_backtest_tasks(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    strategy: Optional[str] = Query(None, description="按策略 ID 筛选"),
    db: Session = Depends(get_db),
):
    """回测任务列表，分页，可选按 status、strategy（策略 ID）筛选。"""
    q = db.query(BackTestTask).order_by(BackTestTask.created_at.desc())
    if status is not None:
        q = q.filter(BackTestTask.status == status)
    if strategy is not None:
        q = q.filter(BackTestTask.strategy_id == strategy)
    total = q.count()
    offset = (page - 1) * page_size
    rows = q.offset(offset).limit(page_size).all()
    strategy_ids = list({r.strategy_id for r in rows if r.strategy_id})
    strategy_names = {}
    if strategy_ids:
        for s in db.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all():
            strategy_names[s.id] = s.name
    results = [_task_to_item(r, strategy_names.get(r.strategy_id)) for r in rows]
    return {"results": results, "count": total}


@router.get("/tasks/{task_id}")
async def get_backtest_task(task_id: str, db: Session = Depends(get_db)):
    """回测任务详情。"""
    task = db.query(BackTestTask).filter(BackTestTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="回测任务不存在")
    strategy_name = None
    if task.strategy_id:
        s = db.query(Strategy).filter(Strategy.id == task.strategy_id).first()
        if s:
            strategy_name = s.name
    return _task_to_item(task, strategy_name)


@router.get("/tasks/{task_id}/trades")
async def get_backtest_trades(task_id: str) -> dict:
    """获取回测任务的交易明细（由回测引擎以 trades.csv 形式输出）。"""
    output_dir = settings.BACKTEST_OUTPUT_ROOT / task_id
    csv_path = output_dir / "trades.csv"
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="未找到该任务的交易明细文件")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.exception("读取交易明细失败 task_id=%s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="读取交易明细失败")
    records: List[Dict[str, Any]] = df.to_dict(orient="records")
    return records


@router.delete("/tasks/{task_id}")
async def delete_backtest_task(task_id: str, db: Session = Depends(get_db)):
    """删除回测任务记录，并删除对应产出目录（若存在）。"""
    task = db.query(BackTestTask).filter(BackTestTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="回测任务不存在")
    db.delete(task)
    db.commit()
    output_dir = Path(settings.BACKTEST_OUTPUT_ROOT) / task_id
    if output_dir.is_dir():
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            logger.warning("删除回测产出目录失败 task_id=%s: %s", task_id, e)
    return {"deleted": True, "id": task_id}


@router.get("/output/{task_id}/{filename}")
async def get_backtest_output(task_id: str, filename: str):
    """按约定路径返回回测产出文件（如图表）。路径为 backend/data/backtest/{task_id}/{filename}。"""
    root = settings.BACKTEST_OUTPUT_ROOT
    path = Path(root) / task_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=filename)
