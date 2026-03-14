"""行情API"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
from sqlalchemy.orm import Session
from app.services.market_service import market_service
from app.database import get_db
from app.utils.task_manager import save_task_info

router = APIRouter(prefix="/api/market", tags=["行情"])


def _load_divid_factors(security_type: str, symbol: str) -> Optional["pd.DataFrame"]:
    """
    加载单个证券的除权除息因子（divid_factors.parquet）。
    返回 DataFrame，若不存在或为空则返回 None。
    """
    from pathlib import Path
    import pandas as pd
    from app.services.data_source.cache import get_security_dir, get_divid_factors_path

    security_dir = get_security_dir(security_type, symbol)
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
    import pandas as pd

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
    security_type: str,
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

    divid_df = _load_divid_factors(security_type, symbol)
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
    db: Session = Depends(get_db)
):
    """
    获取实时行情
    
    Args:
        symbols: 证券代码，如 '000001.SZ,600000.SH'
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    quotes = market_service.get_realtime_quote(symbol_list, db)
    return {"code": 0, "data": list(quotes.values()), "message": "success"}


@router.get("/kline")
async def get_kline(
    symbol: str = Query(..., description="证券代码"),
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
    from app.services.data_source.cache import get_daily, get_ticks
    from app.services.data_source import get_default_qmt_adapter
    from app.services.security_service import security_service
    from app.tasks.security_tasks import (
        task_update_single_security_kdata,
        task_update_single_security_tick_for_date,
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
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type

        if force_update:
            task = task_update_single_security_kdata.delay(
                symbol=symbol,
                security_type=security_type,
                period=period,
                start_date=start_d,
                end_date=end_d,
                source_type="qmt",
                source_id=None,
                force_update=False,
            )

            # 记录任务信息
            save_task_info(
                task_id=task.id,
                task_name="update_single_security_kdata",
                celery_name="task_update_single_security_kdata",
                params={
                    "symbol": symbol,
                    "security_type": security_type,
                    "period": period,
                    "start_date": start_d,
                    "end_date": end_d,
                    "source_type": "qmt",
                    "source_id": None,
                    "force_update": False,
                },
            )

            return {
                "code": 0,
                "data": {
                    "task_id": task.id,
                    "status": "PENDING",
                },
                "message": "任务已提交，正在后台处理",
            }

        adapter = get_default_qmt_adapter()
        # 日线：从缓存/数据源读取；周/月：接口层始终根据日线合并返回（自然周、自然月）
        if period == "1d":
            base_daily = get_daily(security_type, symbol, start_d, end_d, force_update=False, adapter=adapter)
            if adjust_type == "forward":
                base_daily = _apply_forward_adjust_for_daily(base_daily, security_type, symbol)
            data = base_daily
        else:
            # 1w/1M 始终由日线重建：取日线后可选前复权，再聚合为周/月
            base_daily = get_daily(security_type, symbol, start_d, end_d, force_update=False, adapter=adapter)
            if adjust_type == "forward":
                base_daily = _apply_forward_adjust_for_daily(base_daily, security_type, symbol)
            data = _aggregate_daily_to_period(base_daily, period)

        return {"code": 0, "data": data, "message": "success"}

    # 1 分钟分时（按单日 ticks）
    if period == "1m":
        trade_date = (end_d or start_d or datetime.now().strftime("%Y-%m-%d")) if (start_d or end_d) else datetime.now().strftime("%Y-%m-%d")
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type

        if force_update:
            task = task_update_single_security_tick_for_date.delay(
                symbol=symbol,
                trade_date=trade_date,
                security_type=security_type,
                source_type="qmt",
                source_id=None,
                force_update=False,
            )

            # 记录任务信息
            save_task_info(
                task_id=task.id,
                task_name="update_single_security_tick_for_date",
                celery_name="task_update_single_security_tick_for_date",
                params={
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "security_type": security_type,
                    "source_type": "qmt",
                    "source_id": None,
                    "force_update": False,
                },
            )

            return {
                "code": 0,
                "data": {
                    "task_id": task.id,
                    "status": "PENDING",
                },
                "message": "任务已提交，正在后台处理",
            }

        adapter = get_default_qmt_adapter()
        data = get_ticks(security_type, symbol, trade_date, force_update=False, adapter=adapter)
        return {"code": 0, "data": data, "message": "success"}

    data = market_service.get_kline_data(symbol, period, count, start_date, end_date)
    return {"code": 0, "data": data, "message": "success"}


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
    trade_date: str = Query(..., description="交易日，格式：YYYY-MM-DD 或 YYYYMMDD"),
    force_update: bool = Query(False, description="是否从数据源拉取并更新本地 parquet"),
    db: Session = Depends(get_db),
):
    """
    获取指定交易日的分笔数据。
    - 当 `force_update=false` 时：直接从本地 parquet 读取并返回。
    - 当 `force_update=true` 时：提交 Celery 任务拉取并写入 parquet，返回 task_id。
    """
    from app.services.data_source.cache import get_ticks as cache_get_ticks
    from app.services.data_source import get_default_qmt_adapter
    from app.services.security_service import security_service
    from app.tasks.security_tasks import task_update_single_security_tick_for_date

    security_type = "股票"
    sec = security_service.get_security_by_symbol(db, symbol)
    if sec and sec.security_type:
        security_type = sec.security_type

    if force_update:
        task = task_update_single_security_tick_for_date.delay(
            symbol=symbol,
            trade_date=trade_date,
            security_type=security_type,
            source_type="qmt",
            source_id=None,
            force_update=False,
        )

        # 记录任务信息
        save_task_info(
            task_id=task.id,
            task_name="update_single_security_tick_for_date",
            celery_name="task_update_single_security_tick_for_date",
            params={
                "symbol": symbol,
                "trade_date": trade_date,
                "security_type": security_type,
                "source_type": "qmt",
                "source_id": None,
                "force_update": False,
            },
        )

        return {
            "code": 0,
            "data": {
                "task_id": task.id,
                "status": "PENDING",
            },
            "message": "任务已提交，正在后台处理",
        }

    adapter = get_default_qmt_adapter()
    data = cache_get_ticks(security_type, symbol, trade_date, force_update=False, adapter=adapter)
    data = _ticks_to_jsonable(data)
    return {"code": 0, "data": data, "message": "success"}


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
    from app.services.data_source.cache import get_security_dir, get_divid_factors_path
    from app.services.security_service import security_service

    security_type = "股票"
    sec = security_service.get_security_by_symbol(db, symbol)
    if sec and sec.security_type:
        security_type = sec.security_type

    security_dir = get_security_dir(security_type, symbol)
    path = get_divid_factors_path(security_dir)
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        return {"code": 0, "data": [], "message": "success"}

    try:
        import pandas as pd

        df = pd.read_parquet(path)
        if df is None or df.empty:
            data = []
        else:
            data = df.to_dict("records")
        return {"code": 0, "data": data, "message": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取除权数据失败: {e}")


@router.get("/search")
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """
    搜索股票
    """
    stocks = market_service.search_stocks(keyword, db)
    return {"code": 0, "data": stocks, "message": "success"}

