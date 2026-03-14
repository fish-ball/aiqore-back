# -*- coding: utf-8 -*-
"""
证券数据本地缓存：按证券类型/编码组织，parquet 存储日/周/月 K 线与分时，metadata.yaml 维护进度。
不依赖 FastAPI；由上层或 adapter 封装调用。时间/日期按数据源原样写入 parquet，不做任何转换。
"""
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

# 证券类型（中文，与 DB security_type 一致）-> 英文目录名
SECURITY_TYPE_TO_DIR: Dict[str, str] = {
    "股票": "stock",
    "基金": "fund",
    "债券": "bond",
    "可转债": "convertible",
    "期权": "option",
    "期货": "future",
    "指数": "index",
    "权证": "warrant",
}
DEFAULT_TYPE_DIR = "stock"

# K 线 parquet 列名：与 data_schema 一致；adapter 子类在 get_klines_data 内完成格式转换，此处仅作列约定
from app.services.data_source.data_schema import KLINE_ROW_FIELDS
KLINE_COLUMNS = KLINE_ROW_FIELDS

logger = logging.getLogger(__name__)


def _get_data_root() -> Path:
    """获取缓存根目录（延迟导入避免循环依赖）。"""
    from app.config import settings
    return settings.DATA_ROOT_PATH


def security_type_to_dir(security_type: Optional[str]) -> str:
    """证券类型中文 -> 英文目录名；未知或空返回 stock。"""
    if not (security_type or "").strip():
        return DEFAULT_TYPE_DIR
    return SECURITY_TYPE_TO_DIR.get((security_type or "").strip(), DEFAULT_TYPE_DIR)


def get_security_dir(security_type: Optional[str], symbol: str) -> Path:
    """标的缓存目录：data/{type_dir}/{symbol}"""
    root = _get_data_root()
    type_dir = security_type_to_dir(security_type)
    return root / type_dir / symbol


def get_daily_path(security_dir: Path) -> Path:
    return security_dir / "daily.parquet"


def get_weekly_path(security_dir: Path) -> Path:
    return security_dir / "weekly.parquet"


def get_monthly_path(security_dir: Path) -> Path:
    return security_dir / "monthly.parquet"


def get_ticks_dir(security_dir: Path) -> Path:
    return security_dir / "ticks"


def _date_to_yyyy_mm_dd(value: Any) -> Optional[str]:
    """将 YYYYMMDD 或 YYYY-MM-DD 转为 YYYY-MM-DD。"""
    if value is None:
        return None
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    return None


def _normalize_ticks_meta(ticks_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 ticks 元数据统一为 start_date / end_date（YYYY-MM-DD）。
    兼容旧字段 date_min / date_max（YYYYMMDD），读入后转为 start_date / end_date。
    返回仅含 start_date、end_date、updated_at 的字典。
    """
    if not ticks_dict:
        return {}
    out: Dict[str, Any] = {}
    start = ticks_dict.get("start_date") or ticks_dict.get("date_min")
    end = ticks_dict.get("end_date") or ticks_dict.get("date_max")
    if start is not None:
        out["start_date"] = _date_to_yyyy_mm_dd(start) or str(start)[:10]
    if end is not None:
        out["end_date"] = _date_to_yyyy_mm_dd(end) or str(end)[:10]
    if ticks_dict.get("updated_at") is not None:
        out["updated_at"] = ticks_dict["updated_at"]
    return out


def get_metadata_for_security(security_type: Optional[str], symbol: str) -> Dict[str, Any]:
    """
    读取该证券的 metadata.yaml。K 线统一为 kline（日线区间）；ticks 统一为 start_date/end_date。
    供获取单个证券接口附加返回。不再返回 daily/weekly/monthly 旧键。
    """
    security_dir = get_security_dir(security_type, symbol)
    meta = read_meta(security_dir)
    if not meta:
        return {}
    result = dict(meta)
    result["kline"] = meta.get("kline") or meta.get("daily") or {}
    for key in ("daily", "weekly", "monthly"):
        result.pop(key, None)
    if result.get("ticks") is not None:
        result["ticks"] = _normalize_ticks_meta(result["ticks"])
    return result


def get_ticks_path(security_dir: Path, trade_date_yyyymmdd: str) -> Path:
    """分时按日存储：ticks/YYYYMMDD.parquet"""
    return get_ticks_dir(security_dir) / f"{trade_date_yyyymmdd}.parquet"


def get_divid_factors_path(security_dir: Path) -> Path:
    """除权数据文件路径：divid_factors.parquet。"""
    return security_dir / "divid_factors.parquet"


def get_meta_path(security_dir: Path) -> Path:
    return security_dir / "metadata.yaml"


def read_meta(security_dir: Path) -> Dict[str, Any]:
    """读取 metadata.yaml；不存在则尝试 meta.yaml；解析失败返回空 dict。"""
    meta_path = get_meta_path(security_dir)
    if not meta_path.is_file():
        legacy = security_dir / "meta.yaml"
        if legacy.is_file():
            meta_path = legacy
        else:
            return {}
    try:
        import yaml
        with open(meta_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("读取 metadata 失败 %s: %s", meta_path, e)
        return {}


def write_meta(security_dir: Path, meta_dict: Dict[str, Any], merge: bool = True) -> None:
    """写入 metadata.yaml；merge=True 时先读现有再合并，原样存储。"""
    meta_path = get_meta_path(security_dir)
    security_dir.mkdir(parents=True, exist_ok=True)
    current = read_meta(security_dir) if merge and meta_path.is_file() else {}
    for k, v in meta_dict.items():
        current[k] = v
    try:
        import yaml
        with open(meta_path, "w", encoding="utf-8") as f:
            yaml.dump(current, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.warning("写入 metadata 失败 %s: %s", meta_path, e)


def _read_parquet_kline(path: Path) -> List[Dict[str, Any]]:
    """读取 K 线 parquet，仅保证列与 KLINE_COLUMNS 一致（缺列补 0），adapter 外不做格式整理。"""
    if not path.is_file():
        return []
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        if df is None or df.empty:
            return []
        for col in KLINE_COLUMNS:
            if col not in df.columns:
                df[col] = 0
        df = df[KLINE_COLUMNS]
        return df.to_dict("records")
    except Exception as e:
        logger.warning("读取 parquet 失败 %s: %s", path, e)
        return []


def _time_ms_to_date_str(time_ms: Any) -> Optional[str]:
    """UNIX 毫秒时间戳 -> YYYY-MM-DD。"""
    if time_ms is None:
        return None
    try:
        t = int(float(time_ms)) / 1000
        return datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def get_dates_from_daily_parquet(security_type: Optional[str], symbol: str) -> List[str]:
    """从日线 parquet 按 time 列推导已有交易日列表，用于按 meta 补全分时。返回排序后的 YYYY-MM-DD 列表。"""
    security_dir = get_security_dir(security_type, symbol)
    path = get_daily_path(security_dir)
    rows = _read_parquet_kline(path)
    dates = sorted(set(d for r in rows for d in [_time_ms_to_date_str(r.get("time"))] if d is not None))
    return dates


def get_existing_ticks_dates(security_type: Optional[str], symbol: str) -> set:
    """返回已落盘分笔的交易日集合（YYYY-MM-DD），用于分时补全时跳过已有日期。"""
    security_dir = get_security_dir(security_type, symbol)
    ticks_dir = get_ticks_dir(security_dir)
    if not ticks_dir.is_dir():
        return set()
    out = set()
    for p in ticks_dir.iterdir():
        if p.suffix.lower() == ".parquet":
            stem = p.stem
            if len(stem) == 8 and stem.isdigit():
                out.add(f"{stem[:4]}-{stem[4:6]}-{stem[6:8]}")
    return out


# 日 K 线（daily.parquet）整理：价格类 6 位小数，成交额 4 位小数；周/月线写入时不再做舍入
DAILY_KLINE_PRICE_DECIMALS = 6
DAILY_KLINE_AMOUNT_DECIMALS = 4
DAILY_KLINE_PRICE_COLUMNS = ("open", "high", "low", "close", "preClose")


def _round_daily_kline_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """仅对日 K 线写入前整理：open/high/low/close/preClose 6 位小数，amount 4 位小数。返回新列表。"""
    if not rows:
        return rows
    result = []
    for r in rows:
        new_row = dict(r)
        for col in DAILY_KLINE_PRICE_COLUMNS:
            if col not in new_row:
                continue
            v = new_row[col]
            if isinstance(v, float) and v == v:
                new_row[col] = round(v, DAILY_KLINE_PRICE_DECIMALS)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                try:
                    new_row[col] = round(float(v), DAILY_KLINE_PRICE_DECIMALS)
                except (TypeError, ValueError):
                    pass
        if "amount" in new_row:
            v = new_row["amount"]
            if isinstance(v, float) and v == v:
                new_row["amount"] = round(v, DAILY_KLINE_AMOUNT_DECIMALS)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                try:
                    new_row["amount"] = round(float(v), DAILY_KLINE_AMOUNT_DECIMALS)
                except (TypeError, ValueError):
                    pass
        result.append(new_row)
    return result


def _write_parquet_kline(path: Path, rows: List[Dict[str, Any]]) -> None:
    """写入 K 线 parquet，仅写入 KLINE_COLUMNS。不做舍入（日线舍入在 _get_kline 写入前单独做，周/月不转换）。"""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd
        out = [{col: r.get(col, 0) for col in KLINE_COLUMNS} for r in rows]
        df = pd.DataFrame(out, columns=KLINE_COLUMNS)
        df.to_parquet(path, index=False)
    except Exception as e:
        logger.warning("写入 parquet 失败 %s: %s", path, e)


def _merge_kline_rows(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 time（UNIX 毫秒）合并、去重，保留新数据同 time 覆盖旧，再按 time 排序；仅取 KLINE_COLUMNS。"""
    import pandas as pd
    if not existing and not new:
        return []
    all_rows = [{col: r.get(col, 0) for col in KLINE_COLUMNS} for r in existing + new]
    df = pd.DataFrame(all_rows, columns=KLINE_COLUMNS)
    df = df.drop_duplicates(subset=["time"], keep="last")
    df = df.sort_values("time").reset_index(drop=True)
    return df.to_dict("records")


def _day_before(date_str: str) -> str:
    """YYYY-MM-DD 前一日。"""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d") - timedelta(days=1)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def _day_after(date_str: str) -> str:
    """YYYY-MM-DD 后一日。"""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d") + timedelta(days=1)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def _compute_missing_ranges(
    request_start: Optional[str],
    request_end: Optional[str],
    meta_start: Optional[str],
    meta_end: Optional[str],
) -> List[Tuple[Optional[str], Optional[str]]]:
    """
    根据请求区间与 meta 已有区间，计算需要拉取的缺失区间列表（只拉缺口）。
    无 meta 则返回 [(request_start, request_end)] 表示全量。
    """
    req_s = request_start
    req_e = request_end
    m_s = meta_start
    m_e = meta_end
    if not m_s and not m_e:
        return [(req_s, req_e)] if (req_s or req_e) else []
    if not req_s and not req_e:
        return []
    req_s = req_s or m_s
    req_e = req_e or m_e
    if not req_s or not req_e:
        return [(req_s, req_e)]
    missing = []
    # 缺口在前：请求开始早于已有开始
    if req_s < m_s:
        end = _day_before(m_s) if m_s else req_e
        if req_e and end > req_e:
            end = req_e
        missing.append((req_s, end))
    # 缺口在后：请求结束晚于已有结束
    if req_e > m_e:
        start = _day_after(m_e) if m_e else req_s
        if req_s and start < req_s:
            start = req_s
        missing.append((start, req_e))
    return missing


def _filter_rows_by_date(rows: List[Dict[str, Any]], start_date: Optional[str], end_date: Optional[str]) -> List[Dict[str, Any]]:
    """按 time（UNIX 毫秒）推导日期，与 start_date/end_date（YYYY-MM-DD）比较过滤。"""
    if not start_date and not end_date:
        return rows
    out = []
    for r in rows:
        d_compare = _time_ms_to_date_str(r.get("time"))
        if d_compare is None:
            continue
        if start_date and d_compare < start_date:
            continue
        if end_date and d_compare > end_date:
            continue
        out.append(r)
    return out


def _aggregate_daily_to_period(daily_rows: List[Dict[str, Any]], period: str) -> List[Dict[str, Any]]:
    """
    将日 K 合成为周 K（自然周）或月 K（自然月）。
    周：自然周（pd.Grouper freq='W-SUN'）；月：自然月（freq='M'）。
    聚合规则：time=周期内最后交易日 time；open=首日 open；close=末日 close；high/low=周期内最大/最小；volume/amount=求和。
    其余 KLINE 列补 0。
    """
    if not daily_rows:
        return []
    try:
        import pandas as pd
    except ImportError:
        logger.warning("pandas 未安装，无法聚合周/月 K")
        return []

    df = pd.DataFrame(daily_rows)
    if "time" not in df.columns:
        return []
    df = df.copy()
    df["_dt"] = df["time"].map(lambda t: datetime.fromtimestamp(int(float(t)) / 1000.0))
    df = df.sort_values("_dt").reset_index(drop=True)

    if period == "1w":
        grouper = pd.Grouper(key="_dt", freq="W-SUN")
    elif period == "1M":
        grouper = pd.Grouper(key="_dt", freq="M")
    else:
        return []

    result: List[Dict[str, Any]] = []
    for _, g in df.groupby(grouper, sort=True):
        if g.empty:
            continue
        g = g.sort_values("_dt")
        row: Dict[str, Any] = {col: 0 for col in KLINE_COLUMNS}
        row["time"] = int(g.iloc[-1]["time"])
        row["open"] = float(g.iloc[0]["open"])
        row["close"] = float(g.iloc[-1]["close"])
        row["high"] = float(g["high"].max())
        row["low"] = float(g["low"].min())
        if "volume" in g.columns:
            row["volume"] = int(g["volume"].sum())
        if "amount" in g.columns:
            row["amount"] = float(g["amount"].sum())
        result.append(row)
    return result


def rebuild_weekly_monthly_from_daily(security_type: Optional[str], symbol: str) -> None:
    """
    清除周 K、月 K 缓存文件，并根据日线 parquet 重新聚合生成 weekly.parquet 与 monthly.parquet。
    周线用自然周（W-SUN），月线用自然月（M）。周/月由日线生成，不再写入 meta（仅 kline 存日线区间）。
    """
    security_dir = get_security_dir(security_type, symbol)
    daily_path = get_daily_path(security_dir)
    weekly_path = get_weekly_path(security_dir)
    monthly_path = get_monthly_path(security_dir)

    if weekly_path.is_file():
        try:
            weekly_path.unlink()
        except OSError as e:
            logger.warning("删除周 K 缓存失败 %s: %s", weekly_path, e)
    if monthly_path.is_file():
        try:
            monthly_path.unlink()
        except OSError as e:
            logger.warning("删除月 K 缓存失败 %s: %s", monthly_path, e)

    daily_rows = _read_parquet_kline(daily_path)
    if not daily_rows:
        return

    weekly_rows = _aggregate_daily_to_period(daily_rows, "1w")
    monthly_rows = _aggregate_daily_to_period(daily_rows, "1M")

    if weekly_rows:
        _write_parquet_kline(weekly_path, weekly_rows)
    if monthly_rows:
        _write_parquet_kline(monthly_path, monthly_rows)
    # 周/月由日线生成，不再单独写入 meta，仅日线区间存于 kline


def _get_kline_meta_key() -> str:
    """K 线元数据统一使用 kline（仅存日线区间，周/月由日线生成）。"""
    return "kline"


def get_daily(
    security_type: Optional[str],
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    *,
    force_update: bool = False,
    adapter: Any = None,
) -> List[Dict[str, Any]]:
    """
    获取日线：先读 meta，若不 force 且缓存已覆盖则从 parquet 返回；否则拉取缺失区间，合并写 parquet，更新 meta。
    adapter 需实现 get_klines_data(symbol, period, count, start_time, end_time)，返回格式见 data_schema。
    """
    return _get_kline(security_type, symbol, "1d", start_date, end_date, force_update=force_update, adapter=adapter)


def get_weekly(
    security_type: Optional[str],
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    *,
    force_update: bool = False,
    adapter: Any = None,
) -> List[Dict[str, Any]]:
    """
    获取周线。不从数据源抓取，仅从本地 weekly.parquet 读取（该文件由日线合并生成）。
    若 weekly.parquet 不存在则先根据日线重建再返回。
    """
    security_dir = get_security_dir(security_type, symbol)
    path = get_weekly_path(security_dir)
    if not path.is_file():
        rebuild_weekly_monthly_from_daily(security_type, symbol)
    rows = _read_parquet_kline(path)
    return _filter_rows_by_date(rows, start_date, end_date)


def get_monthly(
    security_type: Optional[str],
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    *,
    force_update: bool = False,
    adapter: Any = None,
) -> List[Dict[str, Any]]:
    """
    获取月线。不从数据源抓取，仅从本地 monthly.parquet 读取（该文件由日线合并生成）。
    若 monthly.parquet 不存在则先根据日线重建再返回。
    """
    security_dir = get_security_dir(security_type, symbol)
    path = get_monthly_path(security_dir)
    if not path.is_file():
        rebuild_weekly_monthly_from_daily(security_type, symbol)
    rows = _read_parquet_kline(path)
    return _filter_rows_by_date(rows, start_date, end_date)


def _get_kline(
    security_type: Optional[str],
    symbol: str,
    period: str,
    start_date: Optional[str],
    end_date: Optional[str],
    *,
    force_update: bool = False,
    adapter: Any = None,
) -> List[Dict[str, Any]]:
    """K 线：仅日线走此逻辑并读写 meta，周/月由 get_weekly/get_monthly 直接读 parquet。"""
    security_dir = get_security_dir(security_type, symbol)
    if period == "1d":
        path = get_daily_path(security_dir)
    elif period == "1w":
        path = get_weekly_path(security_dir)
    else:
        path = get_monthly_path(security_dir)

    meta = read_meta(security_dir)
    # 统一使用 kline；兼容旧版 daily
    meta_key = _get_kline_meta_key()
    type_meta = meta.get(meta_key) or meta.get("daily") or {}
    meta_start = type_meta.get("start_date")
    meta_end = type_meta.get("end_date")
    # meta 中可能原样存 int，比较前转为 YYYY-MM-DD 字符串
    if isinstance(meta_start, (int, float)):
        try:
            meta_start = datetime.fromtimestamp(meta_start / 1000).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            meta_start = None
    elif meta_start is not None:
        meta_start = str(meta_start)[:10]
    if isinstance(meta_end, (int, float)):
        try:
            meta_end = datetime.fromtimestamp(meta_end / 1000).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            meta_end = None
    elif meta_end is not None:
        meta_end = str(meta_end)[:10]

    if not force_update and meta_start and meta_end:
        # 检查缓存是否已覆盖请求区间
        req_s = start_date or meta_start
        req_e = end_date or meta_end
        if req_s >= meta_start and req_e <= meta_end:
            rows = _read_parquet_kline(path)
            return _filter_rows_by_date(rows, start_date, end_date)

    # 需要拉取：计算缺失区间
    if force_update:
        ranges_to_fetch = [(start_date, end_date)] if (start_date or end_date) else [(meta_start, meta_end)]
    else:
        ranges_to_fetch = _compute_missing_ranges(start_date, end_date, meta_start, meta_end)
        if not ranges_to_fetch and (start_date or end_date):
            ranges_to_fetch = [(start_date, end_date)]

    existing = _read_parquet_kline(path)
    all_new: List[Dict[str, Any]] = []

    if adapter and hasattr(adapter, "get_klines_data") and ranges_to_fetch:
        for r_start, r_end in ranges_to_fetch:
            if not r_start and not r_end:
                continue
            st = f"{r_start} 00:00:00" if r_start else None
            et = f"{r_end} 23:59:59" if r_end else None
            count = 5000
            raw = adapter.get_klines_data(symbol, period=period, count=count, start_time=st, end_time=et)
            if raw:
                all_new.extend(raw)

    merged = _merge_kline_rows(existing, all_new)
    if merged and period == "1d":
        merged = _round_daily_kline_rows(merged)
    if merged:
        _write_parquet_kline(path, merged)
        dates = [_time_ms_to_date_str(r.get("time")) for r in merged if r.get("time") is not None]
        dates = sorted(set(dates) - {None})
        if dates:
            new_type_meta = {
                "start_date": dates[0],
                "end_date": dates[-1],
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            type_meta.update(new_type_meta)
            meta[meta_key] = type_meta
            for old_key in ("daily", "weekly", "monthly"):
                meta.pop(old_key, None)
            write_meta(security_dir, meta, merge=False)

    # 返回请求区间内的数据
    result = _filter_rows_by_date(merged if merged else existing, start_date, end_date)
    return result


# 分笔（tick）数据整理：价格 6 位小数，成交额 4 位；askPrice/bidPrice/askVol/bidVol 统一为浮点数组 6 位小数
TICK_PRICE_DECIMALS = 6
TICK_AMOUNT_DECIMALS = 4


def _normalize_tick_data(raw: Any) -> Any:
    """
    对 tick 数据按表独立整理，抓取后写入前调用。
    - lastPrice / open / high / low / lastClose：6 位小数舍入
    - amount：4 位小数舍入
    - askPrice / bidPrice / askVol / bidVol：统一为浮点数组，逐元素 6 位小数舍入
    支持 pandas.DataFrame，返回新 DataFrame。
    """
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return raw
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        return raw
    df = raw.copy()

    for col in ("lastPrice", "open", "high", "low", "lastClose"):
        if col in df.columns and np.issubdtype(df[col].dtype, np.floating):
            df[col] = df[col].round(TICK_PRICE_DECIMALS)
    if "amount" in df.columns and np.issubdtype(df["amount"].dtype, np.floating):
        df["amount"] = df["amount"].round(TICK_AMOUNT_DECIMALS)

    def round_float_list(val):
        if val is None or (isinstance(val, float) and val != val):
            return val
        if isinstance(val, (list, np.ndarray)):
            out = []
            for x in val:
                try:
                    out.append(round(float(x), TICK_PRICE_DECIMALS))
                except (TypeError, ValueError):
                    out.append(0.0)
            return out
        return val

    for col in ("askPrice", "bidPrice", "askVol", "bidVol"):
        if col in df.columns:
            df[col] = df[col].apply(round_float_list)

    return df


def get_ticks(
    security_type: Optional[str],
    symbol: str,
    trade_date: Any,
    *,
    force_update: bool = False,
    adapter: Any = None,
) -> List[Dict[str, Any]]:
    """
    获取分笔：trade_date 为 YYYYMMDD、YYYY-MM-DD 或 int/float（毫秒时间戳）。
    若本地已有 ticks/YYYYMMDD.parquet 且非 force 则直接读；否则调 adapter.get_ticks_data 写入并更新 meta。
    抓取后按 tick 表规则整理（价格 6 位、amount 4 位、ask/bid 数组处理）再落盘。
    返回 list of dict（每行一条），字段与 data_schema.TICK_DF_* 一致。
    """
    if isinstance(trade_date, (int, float)):
        trade_date = datetime.fromtimestamp(trade_date / 1000).strftime("%Y-%m-%d")
    trade_date_flat = str(trade_date).replace("-", "")[:8]
    if len(trade_date_flat) != 8:
        return []

    security_dir = get_security_dir(security_type, symbol)
    ticks_path = get_ticks_path(security_dir, trade_date_flat)

    if not force_update and ticks_path.is_file():
        try:
            import pandas as pd
            df = pd.read_parquet(ticks_path)
            if df is not None and not df.empty:
                # 读回时 parquet 的 list 列会变成 ndarray，再做一次整理保证 ask/bid 数组为 list of float
                df = _normalize_tick_data(df)
                return df.to_dict("records")
        except Exception as e:
            logger.warning("读取分笔 parquet 失败 %s: %s", ticks_path, e)

    rows: List[Dict[str, Any]] = []
    if adapter and hasattr(adapter, "get_ticks_data"):
        raw = adapter.get_ticks_data(symbol, trade_date)
        if raw is not None:
            try:
                import pandas as pd
                if isinstance(raw, pd.DataFrame) and not raw.empty:
                    raw = _normalize_tick_data(raw)
                    get_ticks_dir(security_dir).mkdir(parents=True, exist_ok=True)
                    raw.to_parquet(ticks_path, index=False)
                    rows = raw.to_dict("records")
                    meta = read_meta(security_dir)
                    ticks_meta = _normalize_ticks_meta(meta.get("ticks") or {})
                    trade_date_norm = _date_to_yyyy_mm_dd(trade_date_flat) or f"{trade_date_flat[:4]}-{trade_date_flat[4:6]}-{trade_date_flat[6:8]}"
                    start_date = ticks_meta.get("start_date") or trade_date_norm
                    end_date = ticks_meta.get("end_date") or trade_date_norm
                    if trade_date_norm < start_date:
                        start_date = trade_date_norm
                    if trade_date_norm > end_date:
                        end_date = trade_date_norm
                    meta["ticks"] = {
                        "start_date": start_date,
                        "end_date": end_date,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    write_meta(security_dir, meta, merge=True)
            except Exception as e:
                logger.warning("写入分笔 parquet 失败 %s: %s", ticks_path, e)

    return rows
