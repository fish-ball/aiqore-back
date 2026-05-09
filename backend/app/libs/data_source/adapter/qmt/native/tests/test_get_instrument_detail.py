# -*- coding: utf-8 -*-
"""get_instrument_detail 单元测试；依赖本机 xtquant/miniQMT。

以下 KEY 集合与重要字段取值，均在本机对 miniQMT 实测得到（xtquant 版本随环境可能变化，若失败需按新返回值更新常量）。
"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_instrument_detail import (
    get_instrument_detail,
)

# iscomplete=False 时当前环境固定返回 31 个字段（股票/指数/基金/期货/期权样本两两对比 key 集合一致）
DETAIL_KEYS_INCOMPLETE = frozenset(
    {
        "ContractOpenInterestQuota",
        "ContractTradeQuota",
        "CreateDate",
        "DownStopPrice",
        "ExchangeCode",
        "ExchangeID",
        "ExpireDate",
        "FloatVolume",
        "InstrumentID",
        "InstrumentName",
        "InstrumentStatus",
        "IsRecent",
        "IsTrading",
        "LastVolume",
        "LongMarginRatio",
        "MainContract",
        "OpenDate",
        "PreClose",
        "PriceTick",
        "ProductID",
        "ProductName",
        "ProductOpenInterestQuota",
        "ProductTradeQuota",
        "ProductType",
        "SettlementPrice",
        "ShortMarginRatio",
        "TotalVolume",
        "TradingDay",
        "UniCode",
        "UpStopPrice",
        "VolumeMultiple",
    }
)

# iscomplete=True 时当前环境固定返回 83 个字段
DETAIL_KEYS_COMPLETE = frozenset(
    {
        "AccumulatedInterest",
        "BondParValue",
        "Ccy",
        "ContractOpenInterestQuota",
        "ContractTradeQuota",
        "ContractType",
        "CreateDate",
        "DayCountFromIPO",
        "DeliveryMonth",
        "DeliveryYear",
        "DownStopPrice",
        "EndDelivDate",
        "ExchangeCode",
        "ExchangeID",
        "ExpireDate",
        "ExtendName",
        "FloatVolume",
        "FloatVolumn",
        "HSGTFlag",
        "InstrumentID",
        "InstrumentName",
        "InstrumentStatus",
        "IsContinuous",
        "IsRecent",
        "IsTrading",
        "LastVolume",
        "LongMarginRatio",
        "MainContract",
        "MarginUnit",
        "MaxFixedBuyOrderVol",
        "MaxFixedSellOrderVol",
        "MaxLimitOrderVolume",
        "MaxLimitSellOrderVolume",
        "MaxMarginSideAlgorithm",
        "MaxMarketOrderVolume",
        "MaxMarketSellOrderVolume",
        "MaxOrderPriceRange",
        "MinFixedBuyOrderVol",
        "MinFixedSellOrderVol",
        "MinLimitOrderVolume",
        "MinLimitSellOrderVolume",
        "MinMarketOrderVolume",
        "MinMarketSellOrderVolume",
        "MinOrderPriceRange",
        "NeeqExeType",
        "OpenDate",
        "OptExchFixedMargin",
        "OptExchMiniMargin",
        "OptExercisePrice",
        "OptLotSize",
        "OptUndlCode",
        "OptUndlHistoryRate",
        "OptUndlMarket",
        "OptUndlRiskFreeRate",
        "OptUnit",
        "OptionType",
        "PreClose",
        "PriceTick",
        "PriceTickType",
        "ProductID",
        "ProductName",
        "ProductOpenInterestQuota",
        "ProductTradeQuota",
        "QualifiedType",
        "RegisteredCapital",
        "RzrkCode",
        "SettlementPrice",
        "ShortMarginRatio",
        "TotalVolume",
        "TotalVolumn",
        "TradingDay",
        "UnderlyingCode",
        "UniCode",
        "UpStopPrice",
        "VolumeMultiple",
        "VoteRightRatio",
        "bDualClass",
        "bNotProfitable",
        "m_nMaxRepurchaseDaysLimit",
        "m_nMinRepurchaseDaysLimit",
        "secuAttri",
        "secuCategory",
        "tradingStatus",
    }
)


def _non_empty_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _require_detail(symbol: str, iscomplete: bool) -> dict:
    d = get_instrument_detail(symbol, iscomplete=iscomplete)
    if d is None:
        raise AssertionError(
            f"期望有详情，实际为 None: symbol={symbol!r} iscomplete={iscomplete}"
        )
    return d


class TestGetInstrumentDetail(unittest.TestCase):
    """按品种抽样：字段 key 集合与当前 miniQMT 一致；重要字段非空。"""

    def test_known_equity_symbol_dict_or_none(self) -> None:
        """验证常见 A 股代码返回 None 或 dict；为 dict 时含 InstrumentName。"""
        for sym in ("600000.SH", "000001.SZ"):
            with self.subTest(symbol=sym):
                d = get_instrument_detail(sym, iscomplete=False)
                self.assertTrue(d is None or isinstance(d, dict))
                if isinstance(d, dict):
                    self.assertIn("InstrumentName", d)

    def test_complete_flag_variants(self) -> None:
        """验证 iscomplete 为 False/True 时均能返回 None 或 dict（不抛异常）。"""
        for complete in (False, True):
            with self.subTest(iscomplete=complete):
                d = get_instrument_detail("600519.SH", iscomplete=complete)
                self.assertTrue(d is None or isinstance(d, dict))

    def test_invalid_like_symbol_safe(self) -> None:
        """验证明显无效代码返回 None 或 dict，不因格式异常崩溃。"""
        d = get_instrument_detail("__invalid__.SH", iscomplete=False)
        self.assertTrue(d is None or isinstance(d, dict))

    def test_stock_detail_keys_and_values(self) -> None:
        """股票：字段 key 不重不漏；名称、交易所、代码有值。

        数据实例（600519.SH，本机 miniQMT）：
        - iscomplete=False：InstrumentName=贵州茅台，ExchangeID=SH，InstrumentID=600519，
          ProductID/ProductName 常为空串，ExpireDate=99999999，共 31 键。
        - iscomplete=True：在上述基础上扩展至 83 键，OptionType=-1，OptExercisePrice=0。
        """
        sym = "600519.SH"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("InstrumentID")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))

    def test_index_detail_keys_and_values(self) -> None:
        """指数：字段 key 不重不漏；名称、交易所、代码有值。

        数据实例（000300.SH）：
        - iscomplete=False：InstrumentName=沪深300，ExchangeID=SH，InstrumentID=000300，共 31 键。
        - iscomplete=True：83 键，与股票样本的 complete 键集合相同。
        """
        sym = "000300.SH"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("InstrumentID")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))

    def test_fund_detail_keys_and_values(self) -> None:
        """基金：字段 key 不重不漏；名称、交易所、代码有值。

        数据实例（161725.SZ）：
        - iscomplete=False：InstrumentName=招商中证白酒指数分级等（LOF 名称以环境为准），
          ExchangeID=SZ，InstrumentID=161725，共 31 键。
        - iscomplete=True：83 键。
        """
        sym = "161725.SZ"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("InstrumentID")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))

    def test_future_detail_keys_and_values(self) -> None:
        """期货：字段 key 不重不漏；名称、品种代码、品种名称、交易所有值。

        数据实例（rb2605.SF）：
        - iscomplete=False：InstrumentName=螺纹钢2605，ProductID=rb，ProductName=螺纹钢，
          ExchangeID=SHFE，ExpireDate=20260515，共 31 键。
        - iscomplete=True：83 键，OptUndlCode 等期权字段存在但期货侧多为默认 0/空。
        """
        sym = "rb2605.SF"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("ProductID")))
            self.assertTrue(_non_empty_str(d.get("ProductName")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))
            self.assertTrue(_non_empty_str(d.get("InstrumentID")))

    def test_future_option_detail_keys_and_values(self) -> None:
        """期货期权（商品期权）：字段 key 不重不漏；品种与标的、行权价等在 complete 下可校验。

        数据实例（ag2612P11700.SF）：
        - iscomplete=False：ProductID=ag_o，ProductName=白银期权，InstrumentName 含 ag 与行权价，
          ExchangeID=SHFE，共 31 键。
        - iscomplete=True：83 键，OptUndlCode=ag2612（标的期货），OptionType 为有效期权类型（非 -1），
          OptExercisePrice>0。
        """
        sym = "ag2612P11700.SF"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("ProductID")))
            self.assertTrue(_non_empty_str(d.get("ProductName")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))
        self.assertNotEqual(hi.get("OptionType"), -1)
        self.assertTrue(_non_empty_str(hi.get("OptUndlCode")))
        self.assertIsInstance(hi.get("OptExercisePrice"), (int, float))
        self.assertGreater(float(hi.get("OptExercisePrice", 0)), 0.0)

    def test_etf_option_detail_keys_and_values(self) -> None:
        """ETF 期权（上交所 SHO）：字段 key 不重不漏；产品 ID/名称、complete 下挂钩 ETF 代码与行权价。

        数据实例（10011096.SHO）：
        - iscomplete=False：ProductID=科创50(588000)，ProductName=科创50购9月，
          ExchangeID=SHO，共 31 键。
        - iscomplete=True：83 键，OptUndlCode=588000，OptionType=1，OptExercisePrice=1.35。
        """
        sym = "10011096.SHO"
        lo = _require_detail(sym, False)
        hi = _require_detail(sym, True)
        self.assertEqual(frozenset(lo.keys()), DETAIL_KEYS_INCOMPLETE)
        self.assertEqual(frozenset(hi.keys()), DETAIL_KEYS_COMPLETE)
        for d in (lo, hi):
            self.assertTrue(_non_empty_str(d.get("InstrumentName")))
            self.assertTrue(_non_empty_str(d.get("ProductID")))
            self.assertTrue(_non_empty_str(d.get("ProductName")))
            self.assertTrue(_non_empty_str(d.get("ExchangeID")))
        self.assertNotEqual(hi.get("OptionType"), -1)
        self.assertTrue(_non_empty_str(hi.get("OptUndlCode")))
        self.assertIsInstance(hi.get("OptExercisePrice"), (int, float))
        self.assertGreater(float(hi.get("OptExercisePrice", 0)), 0.0)


if __name__ == "__main__":
    unittest.main()
