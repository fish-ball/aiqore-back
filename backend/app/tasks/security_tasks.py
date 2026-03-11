"""证券相关异步任务"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.data_source import sync_securities
from app.services.data_source.adapter import get_adapter
from app.services.data_source.cache import (
    get_daily,
    get_weekly,
    get_monthly,
    get_ticks,
    get_dates_from_daily_parquet,
)
from app.services.data_source.sync import _resolve_config
from app.services.security_service import security_service
from app.utils.task_lock import TaskLock

logger = logging.getLogger(__name__)


def _build_error_result(message: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"success": False, "message": message}
    if extra:
        data.update(extra)
    return data


def _resolve_adapter(db, source_type: str, source_id: Optional[int]):
    """根据 source_type/source_id 解析并创建数据源适配器。"""
    config, err = _resolve_config(db, source_type, source_id)
    if err is not None:
        return None, err
    adapter = get_adapter(source_type, config)
    return adapter, None


@celery_app.task(bind=True, name="task_update_bulk_security_info")
def task_update_bulk_security_info(
    self,
    market: Optional[str] = None,
    sector: Optional[str] = None,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
):
    """批量同步证券基础信息（证券列表 + 详情）到数据库。"""
    task_name = "task_update_bulk_security_info"
    task_lock = TaskLock(task_name, timeout=7200)  # 2小时超时

    if not task_lock.acquire():
        error_msg = f"任务 '{task_name}' 已在运行中，无法重复执行"
        logger.warning(error_msg)
        result = {
            "success": False,
            "message": error_msg,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "任务冲突",
                "result": result,
            },
        )
        return result

    db = SessionLocal()
    try:
        # 任务启动时立即更新状态，确保在 Redis 中创建任务记录
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 0,
                "status": "任务已启动，开始获取证券列表...",
            },
        )

        # 经数据源抽象层同步（按 source_type/source_id 选择连接）
        result = sync_securities(db, source_type=source_type, source_id=source_id, market=market, sector=sector)

        # 更新最终状态
        if result.get("success"):
            total = result.get("total", 0)
            self.update_state(
                state="SUCCESS",
                meta={
                    "current": total,
                    "total": total,
                    "status": "更新完成",
                    "result": result,
                },
            )
        else:
            self.update_state(
                state="SUCCESS",
                meta={
                    "status": "更新失败",
                    "result": result,
                },
            )

        return result

    except Exception as e:
        logger.error(f"批量更新证券信息失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        task_lock.release()
        db.close()


@celery_app.task(bind=True, name="task_update_single_security_tick_for_date")
def task_update_single_security_tick_for_date(
    self,
    symbol: str,
    trade_date: Any,
    security_type: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
):
    """拉取并落盘单个证券指定交易日的分笔数据。"""
    db = SessionLocal()
    try:
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            result = _build_error_result(err, {"symbol": symbol, "trade_date": str(trade_date)})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        rows = get_ticks(security_type, symbol, trade_date, force_update=force_update, adapter=adapter)
        result = {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "trade_date": str(trade_date),
            "rows": len(rows),
        }
        self.update_state(state="SUCCESS", meta={"status": "更新完成", "result": result})
        return result
    except Exception as e:
        logger.error(f"更新分笔数据失败: {symbol}, {trade_date}, {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()


def _update_single_security_kdata_core(
    adapter: Any,
    security_type: str,
    symbol: str,
    period: str,
    start_date: Optional[str],
    end_date: Optional[str],
    force_update: bool,
) -> Dict[str, Any]:
    if period == "1d":
        rows = get_daily(security_type, symbol, start_date, end_date, force_update=force_update, adapter=adapter)
    elif period == "1w":
        rows = get_weekly(security_type, symbol, start_date, end_date, force_update=force_update, adapter=adapter)
    elif period == "1M":
        rows = get_monthly(security_type, symbol, start_date, end_date, force_update=force_update, adapter=adapter)
    else:
        return _build_error_result(f"不支持的周期: {period}", {"symbol": symbol})

    return {
        "success": True,
        "message": "更新完成",
        "symbol": symbol,
        "period": period,
        "rows": len(rows),
    }


@celery_app.task(bind=True, name="task_update_single_security_kdata")
def task_update_single_security_kdata(
    self,
    symbol: str,
    security_type: str,
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
):
    """更新单个证券指定周期的 K 线数据。"""
    db = SessionLocal()
    try:
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            result = _build_error_result(err, {"symbol": symbol, "period": period})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        result = _update_single_security_kdata_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        self.update_state(state="SUCCESS", meta={"status": result.get("message", ""), "result": result})
        return result
    except Exception as e:
        logger.error(f"更新 K 线失败: {symbol}, {period}, {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()


def _update_single_security_tick_full_core(
    adapter: Any,
    security_type: str,
    symbol: str,
    force_update: bool,
) -> Dict[str, Any]:
    dates = get_dates_from_daily_parquet(security_type, symbol)
    tick_count = 0
    for d in dates:
        try:
            rows = get_ticks(security_type, symbol, d, force_update=force_update, adapter=adapter)
            if rows:
                tick_count += 1
        except Exception as e:
            logger.warning(f"拉取分时 {symbol} {d} 失败: {e}")
    return {
        "success": True,
        "message": "更新完成",
        "symbol": symbol,
        "dates": len(dates),
        "ticks_dates": tick_count,
    }


@celery_app.task(bind=True, name="task_update_single_security_tick_full")
def task_update_single_security_tick_full(
    self,
    symbol: str,
    security_type: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
):
    """按日线 parquet 中的交易日补全该证券所有分时数据。"""
    db = SessionLocal()
    try:
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            result = _build_error_result(err, {"symbol": symbol})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        result = _update_single_security_tick_full_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            force_update=force_update,
        )
        self.update_state(state="SUCCESS", meta={"status": result.get("message", ""), "result": result})
        return result
    except Exception as e:
        logger.error(f"补全分时失败: {symbol}, {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()


def _update_single_security_all_data_core(
    symbol: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
) -> Dict[str, Any]:
    """单个证券全量数据更新核心逻辑（供 Celery 任务与串行调用复用，不直接更新任务状态）。"""
    db = SessionLocal()
    try:
        security = security_service.get_security_by_symbol(db, symbol)
        if not security:
            return _build_error_result("证券不存在", {"symbol": symbol})

        security_type = security.security_type or "股票"
        list_dt = security.list_date
        if list_dt:
            start_date = list_dt.strftime("%Y-%m-%d")
        else:
            start_date = "1990-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")

        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            return _build_error_result(err, {"symbol": symbol})

        daily_result = _update_single_security_kdata_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            period="1d",
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        weekly_result = _update_single_security_kdata_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            period="1w",
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        monthly_result = _update_single_security_kdata_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            period="1M",
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )

        tick_result = _update_single_security_tick_full_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            force_update=force_update,
        )

        return {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "security_type": security_type,
            "daily": daily_result.get("rows", 0),
            "weekly": weekly_result.get("rows", 0),
            "monthly": monthly_result.get("rows", 0),
            "ticks_dates": tick_result.get("ticks_dates", 0),
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="task_update_single_security_all_data")
def task_update_single_security_all_data(
    self,
    symbol: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
):
    """单个证券的全量数据更新（K 线 + 分时，带任务进度）。"""
    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 0, "status": "开始更新 K 线与分时数据..."},
        )

        result = _update_single_security_all_data_core(
            symbol=symbol,
            source_type=source_type,
            source_id=source_id,
            force_update=force_update,
        )

        status = "更新完成" if result.get("success") else "更新失败"
        self.update_state(
            state="SUCCESS",
            meta={"status": status, "result": result},
        )
        return result
    except Exception as e:
        logger.error(f"更新单个证券所有数据失败: {symbol}, {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="task_update_bulk_security_all_data")
def task_update_bulk_security_all_data(
    self,
    security_type: str,
    symbols: Optional[List[str]] = None,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    force_update: bool = False,
):
    """批量更新一批证券的所有数据。"""
    db = SessionLocal()
    try:
        if symbols is None:
            from app.models.security import Security

            q = db.query(Security).filter(
                Security.is_active == 1,
                Security.security_type == security_type,
            )
            symbols = [s.symbol for s in q.all()]

        total = len(symbols)
        current = 0
        for symbol in symbols:
            current += 1
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total,
                    "status": f"正在更新 {symbol} ({current}/{total})",
                },
            )
            # 在当前 worker 中串行执行单证券更新（调用核心逻辑，避免嵌套 Celery 状态存储导致 task_id 为空）
            _update_single_security_all_data_core(
                symbol=symbol,
                source_type=source_type,
                source_id=source_id,
                force_update=force_update,
            )

        result = {
            "success": True,
            "message": "批量更新完成",
            "security_type": security_type,
            "total": total,
        }
        self.update_state(
            state="SUCCESS",
            meta={"status": "批量更新完成", "result": result},
        )
        return result
    except Exception as e:
        logger.error(f"批量更新所有数据失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()