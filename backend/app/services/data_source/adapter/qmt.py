"""
QMT/miniQMT 数据源适配器：直接调用 xtquant API。
仅依赖 config 字典（xt_quant_path、xt_quant_acct），不依赖 app/FastAPI，adapter 包可独立运行。
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import time
import logging
from datetime import datetime

from .base import SecuritiesDataSourceAdapter

logger = logging.getLogger(__name__)

# 进程内首次使用的 path 会加入 sys.path，后续共用同一 xtdata
_xtdata = None
_xtdata_path_loaded: Optional[str] = None


def _ensure_xtdata(xt_quant_path: Optional[str]) -> Any:
    """
    确保 xtdata 已加载；使用传入的 xt_quant_path 加入 sys.path 后导入。
    不依赖 app.config，调用方需传入有效路径。
    """
    global _xtdata, _xtdata_path_loaded
    path = (xt_quant_path or "").strip() or None
    if _xtdata is not None:
        return _xtdata
    if not path:
        return None
    base = Path(path)
    if base.is_dir():
        datadir = base / "datadir"
        if datadir.is_dir():
            datadir_str = str(datadir)
            if datadir_str not in sys.path:
                sys.path.insert(0, datadir_str)
                _xtdata_path_loaded = datadir_str
    try:
        from xtquant import xtdata as _xt
        _xtdata = _xt
        return _xtdata
    except ImportError as e:
        logger.warning("xtquant 未安装或不可用: %s", e)
        return None


def _to_xtdata_time(s: Optional[str]) -> Optional[str]:
    """
    将 YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD 转为 xtdata 所需格式 YYYYMMDD 或 YYYYMMDDhhmmss。
    xtdata 文档：start_time/end_time 为 8 位日期或 YYYYMMDDhhmmss，不接受带横杠和空格的格式。
    """
    if not s or not isinstance(s, str):
        return s
    s = s.strip()
    if not s:
        return s
    # 去掉空格和横杠，得到连续数字
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) >= 14:
        return digits[:14]
    if len(digits) >= 8:
        return digits[:8]
    return s


def _to_xtdata_period(period: str) -> str:
    """将上层 period 1d/1w/1M 转为 xtdata 周期：1d/1w/1mon。"""
    if period == "1M":
        return "1mon"
    return period


def _xt_row_to_kline(row) -> Dict[str, Any]:
    """xtquant 单行（DataFrame row）转为标准 11 字段 K 线，在 adapter 内闭环。"""
    t = row.get("time")
    try:
        time_ms = int(float(t)) if t is not None else 0
    except (TypeError, ValueError):
        time_ms = 0

    def _f(key: str, default: float = 0):
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0):
        v = row.get(key)
        if v is None:
            return default
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    vol = row.get("volume", row.get("vol"))
    vol = int(float(vol)) if vol is not None else 0
    return {
        "time": time_ms,
        "open": _f("open"),
        "high": _f("high"),
        "low": _f("low"),
        "close": _f("close"),
        "volume": vol,
        "amount": _f("amount"),
        "settle": _f("settle"),
        "openInterest": _i("openInterest"),
        "preClose": _f("preClose"),
        "suspendFlag": _i("suspendFlag"),
    }


def _rows_from_symbol_df(df) -> List[Dict[str, Any]]:
    """从 xtquant 单标的 DataFrame 转为标准 K 线行列表。"""
    return [_xt_row_to_kline(row) for _, row in df.iterrows()]


def _tick_scalar(val: Any) -> Any:
    """numpy 标量转 Python 原生。"""
    if hasattr(val, "item"):
        return val.item()
    return val


def _tick_ndarray_to_rows(arr, trade_date_flat: str) -> List[Dict[str, Any]]:
    """
    将 xtdata period=tick 返回的 ndarray（按 time 增序）转为统一分笔行列表。
    tick 字段：time, lastPrice, open, high, low, lastClose, amount, volume, askPrice, bidPrice, askVol, bidVol, transactionNum 等。
    """
    result = []
    date_str = f"{trade_date_flat[:4]}-{trade_date_flat[4:6]}-{trade_date_flat[6:8]}"
    names = getattr(arr.dtype, "names", None) if hasattr(arr, "dtype") else None
    if names:
        for i in range(len(arr)):
            row = {n: _tick_scalar(arr[n][i]) for n in names}
            result.append(_tick_row_to_standard(row, date_str))
    elif getattr(arr, "shape", None) == (0,) or len(arr) == 0:
        pass
    else:
        for i in range(len(arr)):
            rec = arr[i]
            names_i = getattr(rec.dtype, "names", None) if hasattr(rec, "dtype") else None
            if names_i:
                row = {n: _tick_scalar(rec[n]) for n in names_i}
            else:
                row = {}
            result.append(_tick_row_to_standard(row, date_str))
    return result


def _tick_list_to_rows(items: List[Any], trade_date_flat: str) -> List[Dict[str, Any]]:
    """将 list 形式的分笔数据转为统一行列表。"""
    date_str = f"{trade_date_flat[:4]}-{trade_date_flat[4:6]}-{trade_date_flat[6:8]}"
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(_tick_row_to_standard(item, date_str))
        else:
            result.append(_tick_row_to_standard({}, date_str))
    return result


def _tick_row_to_standard(row: Dict[str, Any], date_str: str) -> Dict[str, Any]:
    """
    单笔 tick 行转为统一字段。保留 time(毫秒)、date、open、high、low、close(=lastPrice)、volume、amount；
    可选 lastClose、askPrice、bidPrice、askVol、bidVol、transactionNum。
    """
    def _f(key: str, default: float = 0):
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(_tick_scalar(v))
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0):
        v = row.get(key)
        if v is None:
            return default
        try:
            return int(float(_tick_scalar(v)))
        except (TypeError, ValueError):
            return default

    t = row.get("time")
    try:
        time_ms = int(float(t)) if t is not None else 0
    except (TypeError, ValueError):
        time_ms = 0
    try:
        time_str = datetime.fromtimestamp(time_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if time_ms else ""
    except (OSError, ValueError):
        time_str = ""
    out = {
        "time": time_ms,
        "date": date_str,
        "open": _f("open"),
        "high": _f("high"),
        "low": _f("low"),
        "close": _f("lastPrice", _f("close")),
        "volume": _i("volume"),
        "amount": _f("amount"),
    }
    for k in ("lastClose", "askPrice", "bidPrice", "askVol", "bidVol", "transactionNum"):
        if k in row and row[k] is not None:
            out[k] = _f(k) if k in ("lastClose", "askPrice", "bidPrice") else _i(k)
    return out


# 预定义板块（与原 qmt_service 一致）
DEFAULT_SECTORS = [
    "沪深A股", "沪深B股", "沪深ETF", "深市ETF", "沪市ETF", "沪深基金", "深市基金", "沪市基金",
    "沪深转债", "沪深债券", "沪市债券", "沪深指数", "沪市指数", "创业板", "上证A股", "上证B股",
    "上证期权", "上证转债",
]


class QMTAdapter(SecuritiesDataSourceAdapter):
    """QMT 适配器：直接调用 xtquant.xtdata 实现行情与证券列表。"""

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}
        self._xt_quant_path = self._config.get("xt_quant_path") or None
        self._xt_quant_acct = self._config.get("xt_quant_acct") or None

    def _get_xtdata(self):
        xtdata = _ensure_xtdata(self._xt_quant_path)
        if xtdata is None:
            raise RuntimeError("xtquant 未安装或不可用，请确保已安装 miniQMT 并配置 xt_quant_path")
        return xtdata

    def test_connection(self) -> tuple[bool, str]:
        base = Path(self._xt_quant_path) if self._xt_quant_path else None
        if not base or not base.is_dir():
            return False, "xtquant 路径不存在或不可用"
        acct = (self._xt_quant_acct or "").strip()
        if acct:
            acct_dir = base / "users" / acct
            if not acct_dir.is_dir():
                return False, f"账号 {acct} 在配置路径下不存在对应文件夹，视作连接失败"
        try:
            xtdata = _ensure_xtdata(self._xt_quant_path)
            if xtdata is None:
                return False, "xtquant 未安装或不可用，请确保已安装 miniQMT 并将 xtquant 路径配置正确"
            if hasattr(xtdata, "get_sector_list"):
                xtdata.get_sector_list()
            elif hasattr(xtdata, "get_stock_list_in_sector"):
                xtdata.get_stock_list_in_sector("沪深A股")
            else:
                return False, "当前 xtquant 版本无可用探测接口"
            return True, "连接成功"
        except Exception as e:
            logger.exception("QMT 连接测试异常")
            return False, str(e)

    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        if sector:
            return self.get_stock_list_in_sector(sector, market)
        xtdata = self._get_xtdata()
        all_securities = []
        seen_symbols = set()
        sectors = []
        try:
            if hasattr(xtdata, "get_sector_list"):
                s = xtdata.get_sector_list()
                if s:
                    sectors = list(s)
        except Exception:
            pass
        if not sectors:
            sectors = DEFAULT_SECTORS
        for sec_name in sectors:
            try:
                securities = xtdata.get_stock_list_in_sector(sec_name)
                if securities:
                    for sec in securities:
                        if isinstance(sec, str) and sec not in seen_symbols:
                            m = "SH" if sec.endswith(".SH") else "SZ" if sec.endswith(".SZ") else "BJ" if sec.endswith(".BJ") else "SH"
                            if market is None or m == market:
                                all_securities.append({"symbol": sec, "market": m, "sector": sec_name})
                                seen_symbols.add(sec)
            except Exception:
                continue
        try:
            if hasattr(xtdata, "get_instrument_list"):
                for exchange in ["SSE", "SZSE", "BSE"]:
                    try:
                        instruments = xtdata.get_instrument_list(exchange)
                        if instruments:
                            for inst in instruments:
                                if isinstance(inst, str) and inst not in seen_symbols:
                                    m = "SH" if inst.endswith(".SH") else "SZ" if inst.endswith(".SZ") else "BJ" if inst.endswith(".BJ") else "SH"
                                    if market is None or m == market:
                                        all_securities.append({"symbol": inst, "market": m, "sector": "全部标的"})
                                        seen_symbols.add(inst)
                    except Exception:
                        continue
        except Exception:
            pass
        return all_securities

    def get_stock_list_in_sector(self, sector: str, market: Optional[str] = None) -> List[Dict[str, Any]]:
        xtdata = self._get_xtdata()
        try:
            securities = xtdata.get_stock_list_in_sector(sector)
            if not securities:
                return []
            result = []
            for sec in securities:
                if isinstance(sec, str):
                    m = "SH" if sec.endswith(".SH") else "SZ" if sec.endswith(".SZ") else "BJ" if sec.endswith(".BJ") else "SH"
                    if market is None or m == market:
                        result.append({"symbol": sec, "market": m, "sector": sector})
            return result
        except Exception as e:
            logger.error("获取板块 '%s' 证券列表失败: %s", sector, e)
            return []

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        xtdata = self._get_xtdata()
        try:
            if hasattr(xtdata, "get_instrument_detail"):
                return xtdata.get_instrument_detail(symbol)
        except Exception:
            pass
        return None

    def get_sector_list(self) -> List[str]:
        """获取板块列表（供 sector_service 等使用）。"""
        xtdata = self._get_xtdata()
        try:
            if hasattr(xtdata, "get_sector_list"):
                s = xtdata.get_sector_list()
                return list(s) if s else []
        except Exception:
            pass
        return DEFAULT_SECTORS.copy()

    def get_klines_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        K 线数据，在 adapter 内将 xtquant 格式转为标准 11 字段后返回。
        """
        xtdata = self._get_xtdata()
        st = _to_xtdata_time(start_time)
        et = _to_xtdata_time(end_time)
        xt_period = _to_xtdata_period(period)
        try:
            if hasattr(xtdata, "download_history_data"):
                try:
                    xtdata.download_history_data(
                        symbol, period=xt_period,
                        start_time=st or "", end_time=et or "",
                    )
                except Exception as dl_e:
                    logger.warning("download_history_data 失败（继续尝试获取）: %s", dl_e)
            data = xtdata.get_market_data(
                stock_list=[symbol], period=xt_period, count=count,
                start_time=st or "", end_time=et or "",
            )
            if not data:
                logger.debug("get_klines_data 无数据: symbol=%s period=%s start=%s end=%s", symbol, xt_period, st, et)
                return []
            if symbol in data:
                df = data[symbol]
                if df is not None and not df.empty:
                    return _rows_from_symbol_df(df)
            time_df = data.get("time")
            if time_df is None or not hasattr(time_df, "loc"):
                logger.debug("get_klines_data 无 time 字段: symbol=%s data_keys=%s", symbol, list(data.keys()) if isinstance(data, dict) else type(data))
                return []
            if symbol not in time_df.index:
                logger.debug("get_klines_data 无该标的: symbol=%s period=%s", symbol, xt_period)
                return []
            time_series = time_df.loc[symbol]
            result = []
            for t_idx, time_val in time_series.items():
                def _v(field: str, default=0):
                    d = data.get(field)
                    if d is None or symbol not in d.index:
                        return default
                    try:
                        return d.loc[symbol, t_idx]
                    except Exception:
                        return default
                try:
                    time_ms = int(float(time_val))
                except (TypeError, ValueError):
                    time_ms = 0
                vol = _v("volume", _v("vol", 0))
                vol = int(float(vol)) if vol is not None else 0
                result.append({
                    "time": time_ms,
                    "open": float(_v("open", 0)),
                    "high": float(_v("high", 0)),
                    "low": float(_v("low", 0)),
                    "close": float(_v("close", 0)),
                    "volume": vol,
                    "amount": float(_v("amount", 0)),
                    "settle": float(_v("settle", 0)),
                    "openInterest": int(float(_v("openInterest", 0))),
                    "preClose": float(_v("preClose", 0)),
                    "suspendFlag": int(float(_v("suspendFlag", 0))),
                })
            return result
        except Exception as e:
            logger.error("获取 K 线数据失败 %s: %s", symbol, e)
            return None

    def get_ticks_data(self, symbol: str, trade_date: str) -> Optional[Any]:
        """
        按交易日拉取分笔数据。使用 get_market_data_ex(period='tick', dividend_type='none', fill_data=False)，
        不传 count，仅返回历史行情。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        返回 XT 原始 DataFrame，列见 data_schema.TICK_DF_*；否则返回 None。
        """
        trade_date_flat = trade_date.replace("-", "")[:8]
        if len(trade_date_flat) != 8:
            return None
        st = f"{trade_date_flat[:4]}{trade_date_flat[4:6]}{trade_date_flat[6:8]}000000"
        et = f"{trade_date_flat[:4]}{trade_date_flat[4:6]}{trade_date_flat[6:8]}235959"
        xtdata = self._get_xtdata()
        if not xtdata:
            return None
        try:
            if hasattr(xtdata, "download_history_data"):
                try:
                    xtdata.download_history_data(
                        symbol, period="tick",
                        start_time=st, end_time=et,
                    )
                except Exception as dl_e:
                    logger.warning("download_history_data tick 失败（继续尝试获取）: %s", dl_e)
            if not hasattr(xtdata, "get_market_data_ex"):
                logger.warning("当前 xtdata 无 get_market_data_ex，无法拉取分笔")
                return None
            data = xtdata.get_market_data_ex(
                stock_list=[symbol],
                period="tick",
                dividend_type="none",
                fill_data=False,
                start_time=st,
                end_time=et,
            )
            if not data or symbol not in data:
                return None
            arr = data[symbol]
            if arr is None:
                return None
            try:
                import pandas as pd
                if isinstance(arr, pd.DataFrame):
                    return arr
            except ImportError:
                pass
            return None
        except Exception as e:
            logger.error("获取分笔数据失败 %s %s: %s", symbol, trade_date_flat, e)
            return None

    def get_divid_factors(
        self,
        symbol: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[Any]:
        """
        获取除权数据，直接封装 xtdata.get_divid_factors。
        start_time/end_time 支持 YYYY-MM-DD 或 YYYYMMDD，内部转换为 xtdata 需要的格式。
        """
        xtdata = self._get_xtdata()
        if not hasattr(xtdata, "get_divid_factors"):
            logger.warning("当前 xtdata 版本不支持 get_divid_factors，无法获取除权数据")
            return None
        st = _to_xtdata_time(start_time) if start_time else ""
        et = _to_xtdata_time(end_time) if end_time else ""
        try:
            df = xtdata.get_divid_factors(symbol, start_time=st or "", end_time=et or "")
            return df
        except Exception as e:
            logger.error("获取除权数据失败 %s: %s", symbol, e)
            return None

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
        xtdata = self._get_xtdata()
        try:
            quotes = xtdata.get_full_tick(symbols)
            names = {}
            if hasattr(xtdata, "get_instrument_detail"):
                for symbol in symbols:
                    try:
                        detail = xtdata.get_instrument_detail(symbol)
                        if detail and isinstance(detail, dict):
                            n = detail.get("InstrumentName", "")
                            if n:
                                names[symbol] = n
                    except Exception:
                        pass
            result = {}
            for symbol in symbols:
                name = names.get(symbol, "")
                if quotes and symbol in quotes:
                    tick = quotes[symbol]
                    if isinstance(tick, dict):
                        last_price = float(tick.get("lastPrice", 0))
                        open_p = float(tick.get("open", 0))
                        high = float(tick.get("high", 0))
                        low = float(tick.get("low", 0))
                        pre_close = float(tick.get("lastClose", 0))
                        volume = int(tick.get("volume", 0))
                        amount = float(tick.get("amount", 0))
                    else:
                        last_price = open_p = high = low = pre_close = amount = 0.0
                        volume = 0
                    result[symbol] = {
                        "symbol": symbol, "name": name, "last_price": last_price,
                        "open": open_p, "high": high, "low": low, "pre_close": pre_close,
                        "volume": volume, "amount": amount, "time": datetime.now().isoformat(),
                    }
                else:
                    result[symbol] = {
                        "symbol": symbol, "name": name, "last_price": 0.0,
                        "open": 0.0, "high": 0.0, "low": 0.0, "pre_close": 0.0,
                        "volume": 0, "amount": 0.0, "time": datetime.now().isoformat(),
                    }
            return result
        except Exception as e:
            logger.error("获取实时行情失败: %s", e)
            return None

    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        xtdata = self._get_xtdata()
        all_stocks = self.get_stock_list()
        results = []
        keyword_upper = keyword.upper()
        matched_symbols = []
        for stock in all_stocks:
            symbol = stock.get("symbol", "")
            if keyword_upper in symbol.upper():
                matched_symbols.append(symbol)
                results.append({"symbol": symbol, "name": "", "market": stock.get("market", "")})
        if matched_symbols and hasattr(xtdata, "get_instrument_detail"):
            for symbol in matched_symbols:
                try:
                    detail = xtdata.get_instrument_detail(symbol)
                    if detail and isinstance(detail, dict):
                        n = detail.get("InstrumentName", "")
                        if n:
                            for r in results:
                                if r["symbol"] == symbol:
                                    r["name"] = n
                                    break
                except Exception:
                    pass
        return results[:50]

    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        # TODO: 使用 xttrader 实现
        return {
            "account_id": account_id,
            "balance": 100000.0, "available": 50000.0, "frozen": 0.0,
            "market_value": 50000.0, "total_asset": 100000.0,
        }

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """通过 xttrader 查询指定资金账号的股票持仓。"""
        base = Path(self._xt_quant_path) if self._xt_quant_path else None
        if not base or not base.is_dir():
            logger.warning("QMT 路径未配置或不可用，无法查询持仓")
            return []
        try:
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount
        except ImportError as e:
            logger.warning("xtquant.xttrader 不可用: %s", e)
            return []
        trader = XtQuantTrader(self._xt_quant_path, int(time.time()))
        try:
            trader.start()
            account = StockAccount(account_id, "STOCK")
            if trader.connect() != 0:
                logger.warning("xttrader 连接失败，无法查询持仓")
                return []
            positions = trader.query_stock_positions(account)
            if not positions:
                return []
            result = []
            for pos in positions:
                result.append({
                    "symbol": getattr(pos, "stock_code", ""),
                    "volume": int(getattr(pos, "volume", 0)),
                    "can_use_volume": int(getattr(pos, "can_use_volume", 0)),
                    "open_price": float(getattr(pos, "open_price", 0)),
                    "market_value": float(getattr(pos, "market_value", 0)),
                    "frozen_volume": int(getattr(pos, "frozen_volume", 0)),
                    "on_road_volume": int(getattr(pos, "on_road_volume", 0)),
                    "yesterday_volume": int(getattr(pos, "yesterday_volume", 0)),
                    "avg_price": float(getattr(pos, "avg_price", 0)),
                    "last_price": float(getattr(pos, "last_price", 0)),
                    "profit_rate": float(getattr(pos, "profit_rate", 0)),
                    "secu_account": getattr(pos, "secu_account", ""),
                    "instrument_name": getattr(pos, "instrument_name", ""),
                })
            return result
        except Exception as e:
            logger.exception("QMT 查询持仓异常: %s", e)
            return []
        finally:
            try:
                trader.stop()
            except Exception:
                pass


# 独立运行：连通性测试（不依赖 app）
# 用法：python -m app.services.data_source.adapter.qmt [xt_quant_path] [xt_quant_acct]
if __name__ == "__main__":
    import sys as _sys
    DEFAULT_TEST_PATH = r"C:\国金证券QMT交易端\userdata_mini"
    DEFAULT_TEST_ACCT = "39271919"
    if len(_sys.argv) > 1:
        path = _sys.argv[1].strip()
        acct = (_sys.argv[2].strip() if len(_sys.argv) > 2 else None) or DEFAULT_TEST_ACCT
        cfg = {"xt_quant_path": path, "xt_quant_acct": acct}
    else:
        cfg = {"xt_quant_path": DEFAULT_TEST_PATH, "xt_quant_acct": DEFAULT_TEST_ACCT}
    adapter = QMTAdapter(cfg)
    ok, msg = adapter.test_connection()
    print("连通性测试:", "通过" if ok else "失败", "-", msg)
    _sys.exit(0 if ok else 1)
