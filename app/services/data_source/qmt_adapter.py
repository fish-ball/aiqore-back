"""
QMT/miniQMT 数据源适配器：直接调用 xtquant API，不依赖 QMTService。
连接仅使用 xt_quant_path、xt_quant_acct；host/port 为预留。
"""
from typing import List, Dict, Any, Optional
import os
import sys
import time
import logging
from datetime import datetime

from app.services.data_source.base import SecuritiesDataSourceAdapter
from app.config import settings

logger = logging.getLogger(__name__)

# 进程内首次使用的 path 会加入 sys.path，后续共用同一 xtdata
_xtdata = None
_xtdata_path_loaded: Optional[str] = None


def _ensure_xtdata(xt_quant_path: Optional[str]) -> Any:
    """确保 xtdata 已加载；使用 config 的 xt_quant_path 加入 sys.path 后导入。"""
    global _xtdata, _xtdata_path_loaded
    path = (xt_quant_path or settings.XT_QUANT_PATH).strip() if xt_quant_path else settings.XT_QUANT_PATH
    if _xtdata is not None:
        return _xtdata
    if path and os.path.isdir(path):
        datadir = os.path.join(path, "datadir")
        if os.path.isdir(datadir) and (datadir not in sys.path):
            sys.path.insert(0, datadir)
            _xtdata_path_loaded = datadir
    try:
        from xtquant import xtdata as _xt
        _xtdata = _xt
        return _xtdata
    except ImportError as e:
        logger.warning(f"xtquant 未安装或不可用: {e}")
        return None


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
        self._xt_quant_path = self._config.get("xt_quant_path") or settings.XT_QUANT_PATH
        self._xt_quant_acct = self._config.get("xt_quant_acct") or settings.XT_QUANT_ACCT

    def _get_xtdata(self):
        xtdata = _ensure_xtdata(self._xt_quant_path)
        if xtdata is None:
            raise RuntimeError("xtquant 未安装或不可用，请确保已安装 miniQMT 并配置 xt_quant_path")
        return xtdata

    def test_connection(self) -> tuple[bool, str]:
        if not self._xt_quant_path or not os.path.isdir(self._xt_quant_path):
            return False, "xtquant 路径不存在或不可用"
        acct = (self._xt_quant_acct or "").strip()
        if acct:
            acct_dir = os.path.join(self._xt_quant_path, acct)
            if not os.path.isdir(acct_dir):
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
            logger.error(f"获取板块 '{sector}' 证券列表失败: {e}")
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

    def get_market_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        xtdata = self._get_xtdata()
        try:
            data = xtdata.get_market_data(
                stock_list=[symbol], period=period, count=count,
                start_time=start_time, end_time=end_time,
            )
            if not data or symbol not in data:
                return []
            result = []
            df = data[symbol]
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    time_val = row.get("time", "")
                    result.append({
                        "time": time_val,
                        "date": str(time_val)[:10] if hasattr(time_val, "__str__") else "",
                        "open": float(row.get("open", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "close": float(row.get("close", 0)),
                        "volume": int(row.get("volume", 0)),
                        "amount": float(row.get("amount", 0)),
                    })
            return result
        except Exception as e:
            logger.error(f"获取行情数据失败 {symbol}: {e}")
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
            logger.error(f"获取实时行情失败: {e}")
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
        if not self._xt_quant_path or not os.path.isdir(self._xt_quant_path):
            logger.warning("QMT 路径未配置或不可用，无法查询持仓")
            return []
        try:
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount
        except ImportError as e:
            logger.warning(f"xtquant.xttrader 不可用: {e}")
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


# 可运行连通性测试（在项目根目录执行：uv run python -m app.services.data_source.qmt_adapter）
if __name__ == "__main__":
    import sys
    DEFAULT_TEST_PATH = r"C:\国金证券QMT交易端\userdata_mini"
    DEFAULT_TEST_ACCT = "39271919"
    if len(sys.argv) > 1:
        path = sys.argv[1].strip()
        acct = (sys.argv[2].strip() if len(sys.argv) > 2 else None) or DEFAULT_TEST_ACCT
        cfg = {"xt_quant_path": path, "xt_quant_acct": acct}
    else:
        cfg = {"xt_quant_path": DEFAULT_TEST_PATH, "xt_quant_acct": DEFAULT_TEST_ACCT}
    adapter = QMTAdapter(cfg)
    ok, msg = adapter.test_connection()
    print("连通性测试:", "通过" if ok else "失败", "-", msg)
    sys.exit(0 if ok else 1)
