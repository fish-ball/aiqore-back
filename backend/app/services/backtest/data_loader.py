# -*- coding: utf-8 -*-
"""
回测数据加载：从平台 data 目录读日线，可选前复权，转为 Backtrader 所需 DataFrame。
不依赖 FastAPI；供 Celery 回测任务与引擎调用。
"""
from pathlib import Path
from typing import Optional, List, Any, Dict

import pandas as pd

from app.services.data_source.cache import get_daily, get_security_dir, get_daily_path


def _read_parquet_kline(path: Path) -> List[Dict[str, Any]]:
    """读取日线 parquet 为 list of dict（与 cache 内 K 线格式一致）。"""
    if not path.is_file():
        return []
    try:
        df = pd.read_parquet(path)
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        return []


def _time_ms_to_date_str(time_ms: Any) -> Optional[str]:
    """UNIX 毫秒时间戳 -> YYYY-MM-DD。"""
    if time_ms is None:
        return None
    try:
        from datetime import datetime
        t = int(float(time_ms)) / 1000.0
        return datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def _filter_rows_by_date(
    rows: List[Dict[str, Any]],
    start_date: Optional[str],
    end_date: Optional[str],
) -> List[Dict[str, Any]]:
    """按 time 推导日期，与 start_date/end_date（YYYY-MM-DD）过滤。"""
    if not start_date and not end_date:
        return rows
    out = []
    for r in rows:
        d = _time_ms_to_date_str(r.get("time"))
        if d is None:
            continue
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        out.append(r)
    return out


def load_daily_for_backtest(
    security_type: str,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust_type: str = "forward",
) -> pd.DataFrame:
    """
    从平台 data 目录加载日 K 线，可选前复权，转为 Backtrader 所需 DataFrame。

    参数:
        security_type: 证券类型，如 "股票"
        symbol: 证券代码，如 "600519.SH"
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        adjust_type: "forward" 前复权，"none" 不复权

    返回:
        DataFrame，datetime 索引，列 open/high/low/close/volume，供 bt.feeds.PandasData 使用。

    异常:
        ValueError: 无数据或过滤后为空
    """
    # 仅读本地 parquet，不触发拉取（adapter=None）
    rows = get_daily(security_type, symbol, start_date, end_date, force_update=False, adapter=None)
    if not rows:
        # 若 get_daily 因 meta 未覆盖等返回空，尝试直接读 parquet 再过滤
        security_dir = get_security_dir(security_type, symbol)
        path = get_daily_path(security_dir)
        rows = _read_parquet_kline(path)
        rows = _filter_rows_by_date(rows, start_date, end_date)
    if not rows:
        raise ValueError(f"未找到 {symbol} 在 {start_date} ~ {end_date} 的日线数据，请先拉取或检查 data 目录")

    if adjust_type == "forward":
        from app.api.market import _apply_forward_adjust_for_daily
        rows = _apply_forward_adjust_for_daily(rows, security_type, symbol)

    # 转为 DataFrame：time(ms) -> datetime 索引，列 ohlcv
    df = pd.DataFrame(rows)
    if "time" not in df.columns:
        raise ValueError("日线数据缺少 time 列")
    df["datetime"] = pd.to_datetime(df["time"], unit="ms")
    df = df.set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            df[col] = 0.0
    feed_df = df[["open", "high", "low", "close", "volume"]].astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )
    return feed_df
