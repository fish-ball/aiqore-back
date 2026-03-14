"""证券相关异步任务"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import time

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
    get_existing_ticks_dates,
    get_security_dir,
    get_divid_factors_path,
    read_meta,
    write_meta,
    rebuild_weekly_monthly_from_daily,
)
from app.services.data_source.sync import _resolve_config
from app.services.security_service import security_service
from app.utils.task_lock import TaskLock

logger = logging.getLogger(__name__)


def _elapsed(t0: float) -> str:
    """将 perf_counter 起始点转为耗时描述，如 1.23s。"""
    return "%.2fs" % (time.perf_counter() - t0)


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
        t0 = time.perf_counter()
        logger.info("批量同步证券基础信息: 启动, source_type=%s, source_id=%s, market=%s, sector=%s",
                    source_type, source_id, market, sector)
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
        logger.info("批量同步证券基础信息: 同步完成, success=%s, total=%s, created=%s, updated=%s, errors=%s, 耗时 %s",
                    result.get("success"), result.get("total"), result.get("created"), result.get("updated"), result.get("errors"), _elapsed(t0))

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
        t0 = time.perf_counter()
        logger.info("分笔抓取: symbol=%s, trade_date=%s, force_update=%s", symbol, trade_date, force_update)
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            logger.warning("分笔抓取: 配置解析失败 symbol=%s, err=%s", symbol, err)
            result = _build_error_result(err, {"symbol": symbol, "trade_date": str(trade_date)})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        rows = get_ticks(security_type, symbol, trade_date, force_update=force_update, adapter=adapter)
        logger.info("分笔抓取: 完成 symbol=%s, trade_date=%s, rows=%s, 耗时 %s", symbol, trade_date, len(rows), _elapsed(t0))
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
    """仅抓取日线；周线/月线不再从数据源拉取，仅根据日线重建。"""
    if period == "1d":
        logger.info("K线抓取: 开始日线 symbol=%s, start_date=%s, end_date=%s, force_update=%s",
                    symbol, start_date, end_date, force_update)
        t0 = time.perf_counter()
        rows = get_daily(security_type, symbol, start_date, end_date, force_update=force_update, adapter=adapter)
        logger.info("K线抓取: 日线完成 symbol=%s, rows=%s, 耗时 %s", symbol, len(rows), _elapsed(t0))
        # 日线抓取完成后清除周 K、月 K 缓存并由日线重新生成 weekly/monthly.parquet
        logger.info("K线抓取: 根据日线重建周/月 symbol=%s", symbol)
        t1 = time.perf_counter()
        rebuild_weekly_monthly_from_daily(security_type, symbol)
        logger.info("K线抓取: 周/月重建完成 symbol=%s, 耗时 %s", symbol, _elapsed(t1))
        return {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "period": period,
            "rows": len(rows),
        }
    if period in ("1w", "1M"):
        # 周/月仅做从日线重建，不发起数据源请求
        logger.info("K线抓取: 从日线重建周/月 symbol=%s, period=%s", symbol, period)
        t0 = time.perf_counter()
        rebuild_weekly_monthly_from_daily(security_type, symbol)
        rows = (
            get_weekly(security_type, symbol, start_date, end_date, force_update=False, adapter=None)
            if period == "1w"
            else get_monthly(security_type, symbol, start_date, end_date, force_update=False, adapter=None)
        )
        logger.info("K线抓取: 周/月完成 symbol=%s, period=%s, rows=%s, 耗时 %s", symbol, period, len(rows), _elapsed(t0))
        return {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "period": period,
            "rows": len(rows),
        }
    return _build_error_result(f"不支持的周期: {period}", {"symbol": symbol})


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
        t0 = time.perf_counter()
        logger.info("任务 K线更新: symbol=%s, period=%s, start_date=%s, end_date=%s", symbol, period, start_date, end_date)
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            logger.warning("任务 K线更新: 配置解析失败 symbol=%s, err=%s", symbol, err)
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
        logger.info("任务 K线更新: 完成 symbol=%s, period=%s, rows=%s, 总耗时 %s", symbol, period, result.get("rows", 0), _elapsed(t0))
        self.update_state(state="SUCCESS", meta={"status": result.get("message", ""), "result": result})
        return result
    except Exception as e:
        logger.error(f"更新 K 线失败: {symbol}, {period}, {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()


def _update_single_security_tick_last_day_core(
    adapter: Any,
    security_type: str,
    symbol: str,
    force_update: bool,
) -> Dict[str, Any]:
    """仅拉取 kline 中最后一个交易日的 tick（用于单证券/全量列表联动更新，默认只抓最后一天）。"""
    dates_all = get_dates_from_daily_parquet(security_type, symbol)
    if not dates_all:
        return {"success": True, "message": "更新完成", "symbol": symbol, "ticks_dates": 0}
    last_date = dates_all[-1]
    rows = get_ticks(security_type, symbol, last_date, force_update=force_update, adapter=adapter)
    n = 1 if rows else 0
    logger.info("分时最后一天: symbol=%s, date=%s, rows=%s, 落盘=%s", symbol, last_date, len(rows) if rows else 0, n)
    return {
        "success": True,
        "message": "更新完成",
        "symbol": symbol,
        "ticks_dates": n,
    }


def _update_single_security_tick_full_core(
    adapter: Any,
    security_type: str,
    symbol: str,
    force_update: bool,
) -> Dict[str, Any]:
    """全日期扫描 kline 的交易日，对未落盘的日期拉取 tick；已存在且非 force 时跳过。不做区间截断。"""
    t0 = time.perf_counter()
    dates_all = get_dates_from_daily_parquet(security_type, symbol)
    existing = get_existing_ticks_dates(security_type, symbol)
    if force_update:
        dates_to_fetch = list(dates_all)
    else:
        dates_to_fetch = [d for d in dates_all if d not in existing]
    logger.info(
        "分时全量补全: symbol=%s, 日线交易日数=%s, 已落盘=%s, 待补全=%s, force_update=%s",
        symbol, len(dates_all), len(existing), len(dates_to_fetch), force_update,
    )
    new_count = 0
    for i, d in enumerate(dates_to_fetch):
        try:
            rows = get_ticks(security_type, symbol, d, force_update=force_update, adapter=adapter)
            if rows:
                new_count += 1
            if (i + 1) % 100 == 0 or i == len(dates_to_fetch) - 1:
                logger.info(
                    "分时全量补全: symbol=%s, 进度 %s/%s, 本次新落盘 %s 天, 已耗时 %s",
                    symbol, i + 1, len(dates_to_fetch), new_count, _elapsed(t0),
                )
        except Exception as e:
            logger.warning("拉取分时 %s %s 失败: %s", symbol, d, e)
    tick_count_total = len(existing) + new_count
    logger.info(
        "分时全量补全: 完成 symbol=%s, 已有=%s, 本次新落盘=%s, 合计有分笔=%s 天, 总耗时 %s",
        symbol, len(existing), new_count, tick_count_total, _elapsed(t0),
    )
    return {
        "success": True,
        "message": "更新完成",
        "symbol": symbol,
        "dates": len(dates_all),
        "ticks_dates": tick_count_total,
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
    """按 kline 全日期扫描补全该证券分时：遍历所有交易日，目录中已存在 tick 文件且非 force 时跳过，不做区间截断。"""
    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        logger.info("任务分时全量补全: 启动 symbol=%s (全日期扫描)", symbol)
        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            logger.warning("任务分时全量补全: 配置解析失败 symbol=%s, err=%s", symbol, err)
            result = _build_error_result(err, {"symbol": symbol})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        result = _update_single_security_tick_full_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            force_update=force_update,
        )
        logger.info("任务分时全量补全: 完成 symbol=%s, ticks_dates=%s, 总耗时 %s", symbol, result.get("ticks_dates", 0), _elapsed(t0))
        self.update_state(state="SUCCESS", meta={"status": result.get("message", ""), "result": result})
        return result
    except Exception as e:
        logger.error("补全分时失败: %s, %s", symbol, e)
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

        t_total = time.perf_counter()
        # 仅抓取日线；周线/月线在日线更新后由 rebuild_weekly_monthly_from_daily 根据日线合并生成
        t_daily = time.perf_counter()
        daily_result = _update_single_security_kdata_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            period="1d",
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        logger.info("全量更新: symbol=%s, 日线完成 rows=%s, 耗时 %s", symbol, daily_result.get("rows", 0), _elapsed(t_daily))
        # 周/月行数从重建后的 parquet 统计（日线更新时已触发重建）
        weekly_result = {"rows": len(get_weekly(security_type, symbol, None, None, force_update=False, adapter=None))}
        monthly_result = {"rows": len(get_monthly(security_type, symbol, None, None, force_update=False, adapter=None))}

        t_ticks = time.perf_counter()
        # 默认只联动抓最后一天的 tick，不再全量补全
        tick_result = _update_single_security_tick_last_day_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            force_update=force_update,
        )
        logger.info("全量更新: symbol=%s, 分时(最后一天) ticks_dates=%s, 耗时 %s", symbol, tick_result.get("ticks_dates", 0), _elapsed(t_ticks))

        # 除权数据：全量更新时一并拉取除权信息，写入 divid_factors.parquet
        t_divid = time.perf_counter()
        divid_result = _update_single_security_divid_factors_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        logger.info("全量更新: symbol=%s, 除权完成 rows=%s, 耗时 %s", symbol, divid_result.get("rows", 0) if divid_result.get("success") else 0, _elapsed(t_divid))
        logger.info("全量更新: symbol=%s, 全部完成, 总耗时 %s", symbol, _elapsed(t_total))

        return {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "security_type": security_type,
            "daily": daily_result.get("rows", 0),
            "weekly": weekly_result.get("rows", 0),
            "monthly": monthly_result.get("rows", 0),
            "ticks_dates": tick_result.get("ticks_dates", 0),
            "divid_rows": divid_result.get("rows", 0) if divid_result.get("success") else 0,
        }
    finally:
        db.close()


def _update_single_security_divid_factors_core(
    adapter: Any,
    security_type: str,
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    force_update: bool,
) -> Dict[str, Any]:
    """
    更新单个证券的除权数据，并写入对应目录的 divid_factors.parquet。
    目前策略较简单：每次调用都会直接从数据源获取并整体覆盖本地文件。
    """
    try:
        t0 = time.perf_counter()
        df = None
        if hasattr(adapter, "get_divid_factors"):
            df = adapter.get_divid_factors(symbol, start_time=start_date, end_time=end_date)
        if df is None:
            return _build_error_result("数据源未返回除权数据", {"symbol": symbol})

        try:
            import pandas as pd  # noqa: F401
        except ImportError:
            return _build_error_result("pandas 未安装，无法写入除权数据 parquet", {"symbol": symbol})

        if getattr(df, "empty", False):
            rows_count = 0
        else:
            rows_count = int(len(df))

        security_dir = get_security_dir(security_type, symbol)
        path = get_divid_factors_path(security_dir)
        security_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)

        # 在 metadata 中记录除权数据的更新时间和行数，方便后续拓展使用
        meta = read_meta(security_dir)
        divid_meta = meta.get("divid_factors") or {}
        divid_meta.update(
            {
                "rows": rows_count,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        meta["divid_factors"] = divid_meta
        write_meta(security_dir, meta, merge=False)
        logger.info("除权抓取: 完成 symbol=%s, rows=%s, 耗时 %s", symbol, rows_count, _elapsed(t0))
        return {
            "success": True,
            "message": "更新完成",
            "symbol": symbol,
            "rows": rows_count,
        }
    except Exception as e:
        logger.error("更新除权数据失败: %s, %s", symbol, e)
        import traceback

        logger.error(traceback.format_exc())
        return _build_error_result("更新除权数据异常", {"symbol": symbol})


@celery_app.task(bind=True, name="task_update_single_security_divid_factors")
def task_update_single_security_divid_factors(
    self,
    symbol: str,
    source_type: str = "qmt",
    source_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_update: bool = False,
):
    """
    拉取并落盘单个证券的除权数据。
    - 数据来源：xtdata.get_divid_factors，经 QMTAdapter 封装。
    - 目标路径：对应证券数据目录下的 divid_factors.parquet。
    """
    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        security = security_service.get_security_by_symbol(db, symbol)
        if not security:
            result = _build_error_result("证券不存在", {"symbol": symbol})
            self.update_state(state="SUCCESS", meta={"status": "证券不存在", "result": result})
            return result

        security_type = security.security_type or "股票"

        adapter, err = _resolve_adapter(db, source_type, source_id)
        if err is not None:
            result = _build_error_result(err, {"symbol": symbol})
            self.update_state(state="SUCCESS", meta={"status": "配置解析失败", "result": result})
            return result

        # 默认不指定时间范围时，数据源会返回全部除权数据
        result = _update_single_security_divid_factors_core(
            adapter=adapter,
            security_type=security_type,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            force_update=force_update,
        )
        logger.info("任务除权更新: 完成 symbol=%s, rows=%s, 总耗时 %s", symbol, result.get("rows", 0), _elapsed(t0))
        status = result.get("message", "")
        self.update_state(state="SUCCESS", meta={"status": status, "result": result})
        return result
    except Exception as e:
        logger.error("更新除权数据任务失败: %s, %s", symbol, e)
        import traceback

        logger.error(traceback.format_exc())
        raise
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
        t0 = time.perf_counter()
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
        logger.info("任务全量更新: 完成 symbol=%s, success=%s, 总耗时 %s", symbol, result.get("success"), _elapsed(t0))
        self.update_state(
            state="SUCCESS",
            meta={"status": status, "result": result},
        )
        return result
    except Exception as e:
        logger.error("更新单个证券所有数据失败: %s, %s", symbol, e)
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
        t_batch = time.perf_counter()
        if symbols is None:
            from app.models.security import Security

            q = db.query(Security).filter(
                Security.is_active == 1,
                Security.security_type == security_type,
            )
            symbols = [s.symbol for s in q.all()]

        total = len(symbols)
        logger.info("批量全量更新: 启动 security_type=%s, total=%s", security_type, total)
        current = 0
        for symbol in symbols:
            current += 1
            t_one = time.perf_counter()
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
            logger.info("批量全量更新: 单券完成 %s/%s symbol=%s, 耗时 %s", current, total, symbol, _elapsed(t_one))

        logger.info("批量全量更新: 全部完成 security_type=%s, total=%s, 总耗时 %s", security_type, total, _elapsed(t_batch))
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
        logger.error("批量更新所有数据失败: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()