"""
miniQMT 交易端：通过 xtquant.xttrader 查询账户资产与持仓。
config 需含 xt_quant_path（userdata_mini 根目录）；xt_quant_acct 可选。与行情 xtdata 不同，XtQuantTrader 依赖该路径。
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import SecuritiesTrader

logger = logging.getLogger(__name__)

_xttrader_cls = None
_stock_account_cls = None


def _ensure_xttrader_types() -> tuple[Any, Any]:
    """确保 xttrader 相关类型已加载并缓存，避免重复导入。"""
    global _xttrader_cls, _stock_account_cls
    if _xttrader_cls is not None and _stock_account_cls is not None:
        return _xttrader_cls, _stock_account_cls
    from xtquant.xttrader import XtQuantTrader
    from xtquant.xttype import StockAccount

    _xttrader_cls = XtQuantTrader
    _stock_account_cls = StockAccount
    return _xttrader_cls, _stock_account_cls


class QMTTrader(SecuritiesTrader):
    """QMT/miniQMT 交易端实现。"""

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}
        raw_path = self._config.get("xt_quant_path")
        self._xt_quant_path = str(raw_path).strip() if raw_path else None
        self._xt_quant_acct = self._config.get("xt_quant_acct") or None
        self._xttrader = None
        self._xttrader_connected = False
        self._xttrader_session_id: Optional[int] = None

    def _get_xttrader(self, session_id: Optional[int] = None):
        """
        复用 xttrader 连接，避免每次查询都重复构造与启动。
        session_id 仅在首次构造 xttrader 时生效；未传时默认使用当前时间戳。
        """
        base = Path(self._xt_quant_path) if self._xt_quant_path else None
        if not base or not base.is_dir():
            raise RuntimeError("QMT 交易路径未配置或不可用（config.xt_quant_path 或默认 XT_QUANT_PATH）")

        try:
            XtQuantTrader, _ = _ensure_xttrader_types()
        except ImportError as e:
            raise RuntimeError(f"xtquant.xttrader 不可用: {e}") from e

        if self._xttrader is None:
            resolved_session_id = int(time.time()) if session_id is None else int(session_id)
            self._xttrader_session_id = resolved_session_id
            self._xttrader = XtQuantTrader(str(base.resolve()), resolved_session_id)
            self._xttrader.start()
            self._xttrader_connected = False

        if not self._xttrader_connected:
            if self._xttrader.connect() != 0:
                self._xttrader = None
                self._xttrader_connected = False
                raise RuntimeError("xttrader 连接失败")
            self._xttrader_connected = True
        return self._xttrader

    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """通过 xttrader 查询指定资金账号的资产信息。"""
        try:
            _, StockAccount = _ensure_xttrader_types()
            trader = self._get_xttrader()
            account = StockAccount(account_id, "STOCK")
            asset = trader.query_stock_asset(account)
            if not asset:
                return None

            cash = float(getattr(asset, "cash", 0))
            frozen_cash = float(getattr(asset, "frozen_cash", 0))
            market_value = float(getattr(asset, "market_value", 0))
            total_asset = float(getattr(asset, "total_asset", 0))
            return {
                "account_id": account_id,
                "balance": total_asset,
                "available": cash,
                "frozen": frozen_cash,
                "market_value": market_value,
                "total_asset": total_asset,
            }
        except RuntimeError as e:
            logger.warning("QMT 查询账户资产失败: %s", e)
            return None
        except Exception as e:
            logger.exception("QMT 查询账户资产异常: %s", e)
            return None

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """通过 xttrader 查询指定资金账号的股票持仓。"""
        try:
            _, StockAccount = _ensure_xttrader_types()
            trader = self._get_xttrader()
            account = StockAccount(account_id, "STOCK")
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
        except RuntimeError as e:
            logger.warning("QMT 查询持仓失败: %s", e)
            return []
        except Exception as e:
            logger.exception("QMT 查询持仓异常: %s", e)
            return []
