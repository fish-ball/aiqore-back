"""行情API"""
import logging
from datetime import datetime

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
from sqlalchemy.orm import Session
from app.database import get_db
from app.libs.data_source.adapter.base import DataSourceAdapter
from app.models.instrument import parse_market_suffix_from_code
from app.services.data_source_service import resolve_adapter_for_data_source_id
from app.services.instrument_service import instrument_service
from app.utils.task_manager import save_task_info
from app.libs.data_source.cache import instrument_type_to_quote_cache_layer

router = APIRouter(prefix="/api/market", tags=["行情"])
logger = logging.getLogger(__name__)


def _quote_adapter_or_raise(db: Session, data_source_id: int) -> DataSourceAdapter:
    """由启用中的数据源连接 id 得到 DataSourceAdapter；失败时 HTTP 400。"""
    adapter, err = resolve_adapter_for_data_source_id(db, data_source_id)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return adapter


def _quote_obj_as_dict(obj: Any) -> Dict[str, Any]:
    """将 Pydantic 模型或 dict 转为 dict。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}


def _quote_name_from_obj(q: Any) -> str:
    """从实时行情对象或 dict 取名称。"""
    if hasattr(q, "model_dump"):
        return str(q.model_dump().get("name", "") or "")
    if isinstance(q, dict):
        return str(q.get("name", "") or "")
    return ""


def _realtime_quotes_formatted(
    adapter: DataSourceAdapter,
    symbols: List[str],
    db: Optional[Session] = None,
) -> Dict[str, Dict[str, Any]]:
    """调用适配器拉取实时行情并格式化为接口返回结构。"""
    try:
        quotes = adapter.get_realtime_quote(symbols)
        if quotes is None:
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        for symbol, quote in quotes.items():
            qd = _quote_obj_as_dict(quote)
            name = str(qd.get("name", "") or "")
            if not name and db:
                inst = instrument_service.get_instrument_by_code(db, symbol)
                if inst:
                    name = inst.name or ""

            pre_close = float(qd.get("pre_close", 0))
            last_price = float(qd.get("last_price", 0))
            change = last_price - pre_close
            change_pct = (change / pre_close * 100) if pre_close > 0 else 0

            result[symbol] = {
                "symbol": symbol,
                "name": name or symbol,
                "last_price": last_price,
                "open": float(qd.get("open", 0)),
                "high": float(qd.get("high", 0)),
                "low": float(qd.get("low", 0)),
                "pre_close": pre_close,
                "volume": int(qd.get("volume", 0)),
                "amount": float(qd.get("amount", 0)),
                "change": change,
                "change_percent": change_pct,
                "time": qd.get("time", datetime.now().isoformat()),
            }
        return result
    except Exception as e:
        logger.error("获取实时行情失败: %s", e)
        return {}


def _kline_rows_from_adapter(
    adapter: DataSourceAdapter,
    symbol: str,
    period: str = "1d",
    count: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """调用适配器拉取 K 线并格式化为接口行列表。"""
    import pandas as pd

    try:
        start_time = None
        end_time = None
        if start_date:
            start_time = f"{start_date} 00:00:00"
        if end_date:
            end_time = f"{end_date} 23:59:59"

        data = adapter.get_klines_data(symbol, period, count, start_time, end_time)
        if data is None:
            return []

        result: List[Dict[str, Any]] = []
        for item in data:
            row = _quote_obj_as_dict(item)
            time_val = row.get("time", "")
            if isinstance(time_val, int):
                time_str = datetime.fromtimestamp(time_val / 1000).strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(time_val, datetime):
                time_str = time_val.strftime("%Y-%m-%d %H:%M:%S")
            elif hasattr(time_val, "strftime"):
                time_str = time_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = str(time_val or "")

            result.append(
                {
                    "time": time_str,
                    "date": time_str[:10] if len(time_str) >= 10 else time_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(row.get("volume", 0)),
                    "amount": float(row.get("amount", 0)),
                }
            )

        if start_date or end_date:
            df = pd.DataFrame(result)
            if "time" in df.columns and len(df) > 0:
                df["time"] = pd.to_datetime(df["time"], errors="coerce")
                if start_date:
                    df = df[df["time"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["time"] <= pd.to_datetime(end_date)]
                result = df.to_dict("records")

        return result
    except Exception as e:
        logger.error("获取K线数据失败: %s", e)
        return []


def _search_stocks_via_adapter(
    adapter: DataSourceAdapter,
    keyword: str,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """数据库优先搜索，必要时走适配器并补全名称。"""
    try:
        results: List[Dict[str, Any]] = []
        symbols_to_fetch_name: List[str] = []

        if db:
            securities = instrument_service.search_instruments(db, keyword, limit=50)
            for security in securities:
                name = security.name
                code = security.code
                if not name or name == code or name.strip() == "":
                    symbols_to_fetch_name.append(code)
                    name = ""

                results.append(
                    {
                        "code": code,
                        "name": name,
                        "market": parse_market_suffix_from_code(code),
                    }
                )

        if not results:
            adapter_results = adapter.search_stocks(keyword)
            for stock in adapter_results:
                sd = _quote_obj_as_dict(stock)
                symbol = sd.get("symbol", "")
                name = sd.get("name", "")
                if not name or name == symbol or name.strip() == "":
                    symbols_to_fetch_name.append(symbol)
                    name = ""

                results.append(
                    {
                        "code": symbol,
                        "name": name,
                        "market": sd.get("market", ""),
                    }
                )

        if symbols_to_fetch_name:
            try:
                batch_size = 10
                for i in range(0, len(symbols_to_fetch_name), batch_size):
                    batch_symbols = symbols_to_fetch_name[i : i + batch_size]
                    quotes = adapter.get_realtime_quote(batch_symbols)
                    if quotes:
                        for result in results:
                            if not result.get("name") or result["name"] == result["code"]:
                                code = result["code"]
                                if code in quotes:
                                    quote_name = _quote_name_from_obj(quotes[code])
                                    if quote_name and quote_name != code and quote_name.strip():
                                        result["name"] = quote_name

                                if (not result.get("name") or result["name"] == code) and db:
                                    security = instrument_service.get_instrument_by_code(db, code)
                                    if (
                                        security
                                        and security.name
                                        and security.name != code
                                        and security.name.strip()
                                    ):
                                        result["name"] = security.name
            except Exception as e:
                logger.warning("获取证券名称失败: %s", e)

        return results
    except Exception as e:
        logger.error("搜索股票失败: %s", e)
        return []


def _load_divid_factors(market_layer: str, symbol: str) -> Optional["pd.DataFrame"]:
    """
    加载单个证券的除权除息因子（divid_factors.parquet）。
    返回 DataFrame，若不存在或为空则返回 None。
    """
    from pathlib import Path
    import pandas as pd
    from app.libs.data_source.cache import get_instrument_dir, get_divid_factors_path

    security_dir = get_instrument_dir(market_layer, symbol)
    path = get_divid_factors_path(security_dir)
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        return None

    df = pd.read_parquet(path)
    if df is None or df.empty:
        return None
    return df


def _time_ms_to_date_str(time_ms: Any) -> Optional[str]:
    """UNIX 毫秒时间戳 -> YYYY-MM-DD。"""
    from datetime import datetime
    if time_ms is None:
        return None
    try:
        t = int(float(time_ms)) / 1000.0
        return datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    except Exception:
        return None


def _build_divid_params_by_date(divid_df: "pd.DataFrame") -> Dict[str, Dict[str, float]]:
    """
    从除权除息表按日期聚合，得到每个除权日的参数字典。
    使用 interest, stockBonus, stockGift, allotNum, allotPrice 计算，不使用 dr。
    同一天多条记录：interest/stockBonus/stockGift/allotNum 求和；allot 金额为 sum(allotPrice*allotNum)。
    返回: { "YYYY-MM-DD": {"interest", "stockBonus", "stockGift", "allotNum", "allotAmount"}, ... }
    """
    if divid_df is None or divid_df.empty:
        return {}

    need = ["time", "interest", "stockBonus", "stockGift", "allotNum", "allotPrice"]
    for c in need:
        if c not in divid_df.columns:
            return {}

    df = divid_df.copy()
    df["date"] = df["time"].map(_time_ms_to_date_str)
    df = df[df["date"].notna()].copy()
    if df.empty:
        return {}

    df["allotAmount"] = df["allotNum"].astype(float) * df["allotPrice"].astype(float)
    agg = df.groupby("date").agg(
        interest=("interest", "sum"),
        stockBonus=("stockBonus", "sum"),
        stockGift=("stockGift", "sum"),
        allotNum=("allotNum", "sum"),
        allotAmount=("allotAmount", "sum"),
    ).to_dict("index")

    return {str(k): v for k, v in agg.items()}


def _calc_forward_price(v: float, d: Dict[str, float]) -> float:
    """
    前复权单次除权公式（与迅投官方 process_forward 一致）：
    calc_front(v, d) = (v - interest + allotPrice*allotNum) / (1 + allotNum + stockBonus + stockGift)
    """
    interest = float(d.get("interest") or 0)
    stock_bonus = float(d.get("stockBonus") or 0)
    stock_gift = float(d.get("stockGift") or 0)
    allot_num = float(d.get("allotNum") or 0)
    allot_amount = float(d.get("allotAmount") or 0)
    denom = 1.0 + allot_num + stock_bonus + stock_gift
    if denom <= 0:
        return v
    return (v - interest + allot_amount) / denom


def _apply_forward_adjust_for_daily(
    daily_rows: List[Dict[str, Any]],
    market_layer: str,
    symbol: str,
) -> List[Dict[str, Any]]:
    """
    对日 K 线做前复权，逻辑与迅投官方 process_forward 一致：
    对每个交易日，按时间顺序对该日之后的所有除权日依次应用：
    v = (v - interest + allotPrice*allotNum) / (1 + allotNum + stockBonus + stockGift)
    送转配时成交量按累计股本扩张比放大；成交额按复权价与复权量一致调整。
    """
    if not daily_rows:
        return []

    divid_df = _load_divid_factors(market_layer, symbol)
    if divid_df is None or divid_df.empty:
        return daily_rows

    divid_params = _build_divid_params_by_date(divid_df)
    if not divid_params:
        return daily_rows

    # 除权日列表按日期升序，便于对每个交易日按“之后发生的除权”顺序递推
    ex_dates_sorted = sorted(divid_params.keys())

    result: List[Dict[str, Any]] = []
    for row in daily_rows:
        date_str = _time_ms_to_date_str(row.get("time"))
        if not date_str:
            result.append(row)
            continue

        # 该日之后发生的除权（ex_date > date_str），按时间顺序
        future_divids = [divid_params[ex] for ex in ex_dates_sorted if ex > date_str]

        new_row = dict(row)

        for col in ("open", "high", "low", "close"):
            if col not in new_row:
                continue
            v = float(new_row[col])
            for d in future_divids:
                v = _calc_forward_price(v, d)
            new_row[col] = round(v, 2)

        # 成交量：送转配使 1 股变 (1+allotNum+stockBonus+stockGift) 股，历史量需乘累计扩张比
        vol_factor = 1.0
        if future_divids and "volume" in new_row:
            for d in future_divids:
                expand = 1.0 + float(d.get("allotNum") or 0) + float(d.get("stockBonus") or 0) + float(d.get("stockGift") or 0)
                if expand > 0:
                    vol_factor *= expand
            new_row["volume"] = int(round(float(new_row["volume"]) * vol_factor, 0))

        # 成交额：复权后与 复权价*复权量 一致，即 amount_adj = amount_orig * (close_adj/close_orig) * (vol_adj/vol_orig)
        if "amount" in new_row:
            orig_close = float(row.get("close") or 0)
            orig_vol = float(row.get("volume") or 0)
            if orig_close > 0 and orig_vol > 0:
                new_row["amount"] = round(
                    float(new_row["amount"]) * (new_row["close"] / orig_close) * (float(new_row.get("volume", 0)) / orig_vol),
                    2,
                )
            elif orig_close > 0:
                new_row["amount"] = round(float(new_row["amount"]) * (new_row["close"] / orig_close), 2)

        result.append(new_row)

    return result


def _aggregate_daily_to_period(
    daily_rows: List[Dict[str, Any]],
    period: str,
) -> List[Dict[str, Any]]:
    """
    将日 K（已前复权）合成为周 / 月 K。接口层始终据此由日线重建返回。
    周线用自然周（W-SUN），月线用自然月（M）。

    合成规则：
    - time：该周期最后一个交易日的 time；
    - open：该周期第一个交易日的 open；
    - close：该周期最后一个交易日的 close；
    - high/low：周期内 high 最大 / low 最小；
    - volume/amount：周期内求和。
    """
    import pandas as pd
    from datetime import datetime

    if not daily_rows:
        return []

    df = pd.DataFrame(daily_rows)
    if "time" not in df.columns:
        return daily_rows

    df = df.copy()
    df["datetime"] = df["time"].map(
        lambda t: datetime.fromtimestamp(int(float(t)) / 1000.0)
    )
    df = df.sort_values("datetime").reset_index(drop=True)

    if period == "1w":
        # 自然周（周一至周日，按周结束日分组）
        grouper = pd.Grouper(key="datetime", freq="W-SUN")
    elif period == "1M":
        # 自然月
        grouper = pd.Grouper(key="datetime", freq="M")
    else:
        return daily_rows

    groups = df.groupby(grouper, sort=True)
    result: List[Dict[str, Any]] = []

    for _, g in groups:
        if g.empty:
            continue
        g = g.sort_values("datetime")
        row: Dict[str, Any] = {}
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


@router.get("/quote")
async def get_realtime_quote(
    symbols: str = Query(..., description="证券代码，多个用逗号分隔"),
    data_source_id: int = Query(..., ge=1, description="数据源连接 ID（data_sources.id）"),
    db: Session = Depends(get_db),
):
    """
    获取实时行情
    
    Args:
        symbols: 证券代码，如 '000001.SZ,600000.SH'
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    adapter = _quote_adapter_or_raise(db, data_source_id)
    quotes = _realtime_quotes_formatted(adapter, symbol_list, db)
    return list(quotes.values())


@router.get("/kline")
async def get_kline(
    symbol: str = Query(..., description="证券代码"),
    data_source_id: int = Query(..., ge=1, description="数据源连接 ID（data_sources.id）"),
    period: str = Query("1d", description="周期：1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M"),
    count: int = Query(100, description="数据条数"),
    adjust_type: str = Query("none", description="复权方式：none=不复权, forward=前复权"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    force_update: bool = Query(False, description="是否从数据源拉取并更新本地 parquet，默认直接读 parquet"),
    db: Session = Depends(get_db),
):
    """
    获取K线/分时数据。
    - 当 `force_update=false` 时：直接读取本地 data 目录下的 parquet（1d/1w/1M 为 daily/weekly/monthly.parquet，1m 单日为 ticks/YYYYMMDD.parquet）；
    - 当 `force_update=true` 时：提交对应 Celery 任务更新数据并返回 task_id，由前端轮询任务状态后再调用本接口获取数据。
    """
    from datetime import datetime, timedelta
    from app.libs.data_source.cache import get_daily, get_ticks
    from app.tasks.instrument_tasks import (
        task_update_single_instrument_kdata,
        task_update_single_instrument_tick_for_date,
    )

    # 缺省 start_date/end_date 时返回全部 K 线，由前端控制显示范围
    end_d = end_date
    start_d = start_date
    if start_d is not None or end_d is not None:
        if not end_d:
            end_d = datetime.now().strftime("%Y-%m-%d")
        if not start_d and period in ("1d", "1w", "1M"):
            end_dt = datetime.strptime(end_d, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=min(365 * 2, max(1, count)))
            start_d = start_dt.strftime("%Y-%m-%d")

    # 日/周/月 K 线
    if period in ("1d", "1w", "1M"):
        market_layer = instrument_type_to_quote_cache_layer(None)
        inst = instrument_service.get_instrument_by_code(db, symbol)
        if inst:
            market_layer = instrument_type_to_quote_cache_layer(inst.instrument_type)

        if force_update:
            task = task_update_single_instrument_kdata.delay(
                symbol=symbol,
                market_layer=market_layer,
                period=period,
                start_date=start_d,
                end_date=end_d,
                source_id=data_source_id,
                force_update=False,
            )

            # 记录任务信息
            save_task_info(
                task_id=task.id,
                task_name="update_single_instrument_kdata",
                celery_name="task_update_single_instrument_kdata",
                params={
                    "symbol": symbol,
                    "market_layer": market_layer,
                    "period": period,
                    "start_date": start_d,
                    "end_date": end_d,
                    "source_id": data_source_id,
                    "force_update": False,
                },
            )

            return {
                "task_id": task.id,
                "status": "PENDING",
            }

        adapter, _err = resolve_adapter_for_data_source_id(db, data_source_id)
        if _err:
            raise HTTPException(status_code=400, detail=_err)
        # 日线：从缓存/数据源读取；周/月：接口层始终根据日线合并返回（自然周、自然月）
        if period == "1d":
            base_daily = get_daily(market_layer, symbol, start_d, end_d, force_update=False, adapter=adapter)
            if adjust_type == "forward":
                base_daily = _apply_forward_adjust_for_daily(base_daily, market_layer, symbol)
            data = base_daily
        else:
            # 1w/1M 始终由日线重建：取日线后可选前复权，再聚合为周/月
            base_daily = get_daily(market_layer, symbol, start_d, end_d, force_update=False, adapter=adapter)
            if adjust_type == "forward":
                base_daily = _apply_forward_adjust_for_daily(base_daily, market_layer, symbol)
            data = _aggregate_daily_to_period(base_daily, period)

        return data

    # 1 分钟分时（按单日 ticks）
    if period == "1m":
        trade_date = (end_d or start_d or datetime.now().strftime("%Y-%m-%d")) if (start_d or end_d) else datetime.now().strftime("%Y-%m-%d")
        market_layer = instrument_type_to_quote_cache_layer(None)
        inst = instrument_service.get_instrument_by_code(db, symbol)
        if inst:
            market_layer = instrument_type_to_quote_cache_layer(inst.instrument_type)

        if force_update:
            task = task_update_single_instrument_tick_for_date.delay(
                symbol=symbol,
                trade_date=trade_date,
                market_layer=market_layer,
                source_id=data_source_id,
                force_update=False,
            )

            # 记录任务信息
            save_task_info(
                task_id=task.id,
                task_name="update_single_instrument_tick_for_date",
                celery_name="task_update_single_instrument_tick_for_date",
                params={
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "market_layer": market_layer,
                    "source_id": data_source_id,
                    "force_update": False,
                },
            )

            return {
                "task_id": task.id,
                "status": "PENDING",
            }

        adapter, _err = resolve_adapter_for_data_source_id(db, data_source_id)
        if _err:
            raise HTTPException(status_code=400, detail=_err)
        data = get_ticks(market_layer, symbol, trade_date, force_update=False, adapter=adapter)
        return data

    adapter = _quote_adapter_or_raise(db, data_source_id)
    data = _kline_rows_from_adapter(adapter, symbol, period, count, start_date, end_date)
    return data


def _ticks_to_jsonable(rows: list) -> list:
    """将 tick 列表中的 numpy/pandas 类型转为 Python 原生类型，便于 JSON 序列化。"""
    import numpy as np
    result = []
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        out = {}
        for k, v in rec.items():
            if v is None:
                out[k] = None
            elif isinstance(v, np.ndarray):
                out[k] = [_scalar_to_native(x) for x in v]
            elif isinstance(v, list):
                out[k] = [_scalar_to_native(x) for x in v]
            elif hasattr(v, "item") and getattr(v, "ndim", 0) == 0:
                out[k] = v.item()
            else:
                out[k] = _scalar_to_native(v)
        result.append(out)
    return result


def _scalar_to_native(x):
    """单个值转为 Python 原生类型（仅处理标量，不处理数组）。"""
    import numpy as np
    if x is None:
        return None
    if isinstance(x, np.ndarray):
        return [_scalar_to_native(y) for y in x]
    if hasattr(x, "item") and getattr(x, "ndim", 0) == 0:
        return x.item()
    if isinstance(x, (np.integer, np.int64, np.int32)):
        return int(x)
    if isinstance(x, (np.floating, np.float64, np.float32)):
        return float(x)
    return x


@router.get("/ticks")
async def get_ticks(
    symbol: str = Query(..., description="证券代码"),
    data_source_id: int = Query(..., ge=1, description="数据源连接 ID（data_sources.id）"),
    trade_date: str = Query(..., description="交易日，格式：YYYY-MM-DD 或 YYYYMMDD"),
    force_update: bool = Query(False, description="是否从数据源拉取并更新本地 parquet"),
    db: Session = Depends(get_db),
):
    """
    获取指定交易日的分笔数据。
    - 当 `force_update=false` 时：直接从本地 parquet 读取并返回。
    - 当 `force_update=true` 时：提交 Celery 任务拉取并写入 parquet，返回 task_id。
    """
    from app.libs.data_source.cache import get_ticks as cache_get_ticks
    from app.tasks.instrument_tasks import task_update_single_instrument_tick_for_date

    market_layer = instrument_type_to_quote_cache_layer(None)
    inst = instrument_service.get_instrument_by_code(db, symbol)
    if inst:
        market_layer = instrument_type_to_quote_cache_layer(inst.instrument_type)

    if force_update:
        task = task_update_single_instrument_tick_for_date.delay(
            symbol=symbol,
            trade_date=trade_date,
            market_layer=market_layer,
            source_id=data_source_id,
            force_update=False,
        )

        # 记录任务信息
        save_task_info(
            task_id=task.id,
            task_name="update_single_instrument_tick_for_date",
            celery_name="task_update_single_instrument_tick_for_date",
            params={
                "symbol": symbol,
                "trade_date": trade_date,
                "market_layer": market_layer,
                "source_id": data_source_id,
                "force_update": False,
            },
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
        }

    adapter, _err = resolve_adapter_for_data_source_id(db, data_source_id)
    if _err:
        raise HTTPException(status_code=400, detail=_err)
    data = cache_get_ticks(market_layer, symbol, trade_date, force_update=False, adapter=adapter)
    data = _ticks_to_jsonable(data)
    return data


@router.get("/divid-factors")
async def get_divid_factors(
    symbol: str = Query(..., description="证券代码"),
    db: Session = Depends(get_db),
):
    """
    获取单个证券的除权除息数据。
    - 数据来源：本地 data 目录下对应证券目录中的 divid_factors.parquet；
    - 若文件不存在，则返回空列表。
    """
    from pathlib import Path
    from app.libs.data_source.cache import get_instrument_dir, get_divid_factors_path

    market_layer = instrument_type_to_quote_cache_layer(None)
    inst = instrument_service.get_instrument_by_code(db, symbol)
    if inst:
        market_layer = instrument_type_to_quote_cache_layer(inst.instrument_type)

    security_dir = get_instrument_dir(market_layer, symbol)
    path = get_divid_factors_path(security_dir)
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        return []

    try:
        import pandas as pd

        df = pd.read_parquet(path)
        if df is None or df.empty:
            data = []
        else:
            data = df.to_dict("records")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取除权数据失败: {e}")


@router.get("/search")
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词"),
    data_source_id: int = Query(..., ge=1, description="数据源连接 ID（data_sources.id）"),
    db: Session = Depends(get_db),
):
    """
    搜索股票
    """
    adapter = _quote_adapter_or_raise(db, data_source_id)
    stocks = _search_stocks_via_adapter(adapter, keyword, db)
    return stocks

