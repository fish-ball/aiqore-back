"""miniqmt 标的详情查询工具。

函数式用法：
- `from aiqore_data.providers.miniqmt import get_instrument_detail`

CLI 用法（直接运行本文件）：
- `python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 600519.SH`
- `python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 000001.SZ`
- `python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 600519.SH --complete`
- `python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol nr09.INE`
- `python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol sc2612C610.INE --complete`

`--complete` 实测样例（symbol=600519.SH，节选）：
```json
{
  "ExchangeID": "SH",            // 交易所代码
  "InstrumentID": "600519",      // 证券代码主体（无后缀）
  "InstrumentName": "贵州茅台",    // 证券名称
  "OpenDate": "20010827",        // 上市日期 YYYYMMDD
  "ExpireDate": "99999999",      // 到期日（股票通常为 99999999）
  "TradingDay": "20260423",      // 当前交易日 YYYYMMDD
  "PreClose": 1409.5,            // 前收盘价
  "UpStopPrice": 1550.45,        // 涨停价
  "DownStopPrice": 1268.55,      // 跌停价
  "PriceTick": 0.01,             // 最小价格变动单位
  "VolumeMultiple": 1,           // 成交量倍率/合约乘数
  "IsTrading": false,            // 是否处于可交易状态
  "secuCategory": 69210112,      // QMT 证券分类编码
  "secuAttri": 14                // QMT 证券属性编码
}
```

`--complete` 其他字段（同次实测，按功能分组）：
- 通用扩展字段：
```json
{
  "ProductID": "",                    // 产品代码
  "ProductName": "",                  // 产品名称
  "UnderlyingCode": "",               // 标的代码（衍生品常用）
  "ExtendName": "贵州茅台",            // 扩展名称
  "ExchangeCode": "600519",           // 交易所内代码
  "RzrkCode": "",                     // 融资融券相关代码
  "UniCode": "600519",                // 统一代码
  "CreateDate": "0",                  // 创建日期（未设置时常为 0）
  "SettlementPrice": 1409.5,          // 结算价
  "FloatVolumn": 1252270215.0,        // 流通股本（旧拼写字段）
  "TotalVolumn": 1252270215.0,        // 总股本（旧拼写字段）
  "FloatVolume": 1252270215.0,        // 流通股本（新拼写字段）
  "TotalVolume": 1252270215.0,        // 总股本（新拼写字段）
  "AccumulatedInterest": 0.0,         // 应计利息（债券常用）
  "BondParValue": 0.0,                // 债券面值
  "Ccy": "",                          // 币种
  "RegisteredCapital": 0,             // 注册资本
  "VoteRightRatio": 0.0               // 表决权比例
}
```

- 交易限制与状态字段：
```json
{
  "LongMarginRatio": 0.0,             // 多头保证金比例
  "ShortMarginRatio": 0.0,            // 空头保证金比例
  "MainContract": 0,                  // 是否主力合约
  "MaxMarketOrderVolume": 1000000,    // 市价单最大买量
  "MinMarketOrderVolume": 1,          // 市价单最小买量
  "MaxLimitOrderVolume": 1000000,     // 限价单最大买量
  "MinLimitOrderVolume": 0,           // 限价单最小买量
  "MaxMarketSellOrderVolume": 0,      // 市价单最大卖量
  "MinMarketSellOrderVolume": 0,      // 市价单最小卖量
  "MaxLimitSellOrderVolume": 0,       // 限价单最大卖量
  "MinLimitSellOrderVolume": 0,       // 限价单最小卖量
  "MaxFixedBuyOrderVol": 0,           // 固定价买单最大量
  "MinFixedBuyOrderVol": 0,           // 固定价买单最小量
  "MaxFixedSellOrderVol": 0,          // 固定价卖单最大量
  "MinFixedSellOrderVol": 0,          // 固定价卖单最小量
  "MaxMarginSideAlgorithm": 0,        // 保证金算法类型
  "InstrumentStatus": 0,              // 标的状态编码
  "tradingStatus": "",                // 交易状态文本
  "IsRecent": false,                  // 是否近月/近期合约
  "IsContinuous": false,              // 是否连续合约
  "HSGTFlag": 0,                      // 沪深港通标记
  "QualifiedType": 0,                 // 投资者适当性类型
  "PriceTickType": 0,                 // 最小变动价位类型
  "MaxOrderPriceRange": 0.0,          // 报价上限偏移
  "MinOrderPriceRange": 0.0           // 报价下限偏移
}
```

- 衍生品字段：
```json
{
  "OptUnit": 0.0,                     // 期权合约单位
  "MarginUnit": 0.0,                  // 保证金单位
  "OptUndlCode": "",                  // 期权标的代码
  "OptUndlMarket": "",                // 期权标的市场
  "OptLotSize": 0,                    // 期权一手数量
  "OptExercisePrice": 0.0,            // 期权行权价
  "OptExchFixedMargin": 0.0,          // 期权交易所固定保证金
  "OptExchMiniMargin": 0.0,           // 期权交易所最小保证金
  "OptUndlRiskFreeRate": 0.0,         // 期权标的无风险利率
  "OptUndlHistoryRate": 0.0,          // 期权标的历史波动率
  "OptionType": -1,                   // 期权类型编码（非期权常为 -1）
  "EndDelivDate": "0",                // 最后交割日
  "DeliveryYear": 0,                  // 交割年份
  "DeliveryMonth": 0,                 // 交割月份
  "ContractType": 0,                  // 合约类型
  "NeeqExeType": 0                    // 北交/股转执行类型
}
```

- 配额与其他标记字段：
```json
{
  "ProductTradeQuota": 0,             // 产品交易额度
  "ContractTradeQuota": 0,            // 合约交易额度
  "ProductOpenInterestQuota": 0,      // 产品持仓额度
  "ContractOpenInterestQuota": 0,     // 合约持仓额度
  "DayCountFromIPO": 0,               // 上市后天数
  "LastVolume": 0,                    // 昨持仓/昨成交相关字段
  "bNotProfitable": false,            // 是否未盈利企业标记
  "bDualClass": false,                // 是否同股不同权标记
  "m_nMinRepurchaseDaysLimit": 0,     // 回购最短天数限制
  "m_nMaxRepurchaseDaysLimit": 0      // 回购最长天数限制
}
```
"""

import argparse
import json
from typing import Any


def get_instrument_detail(
    symbol: str,
    iscomplete: bool = False,
    *,
    xtdata: Any | None = None,
) -> dict[str, Any] | None:
    """查询 miniQMT 标的详情。

    使用说明：
    - 输入 symbol 建议使用 `代码.市场` 格式，例如 `600519.SH`、`nr09.INE`、`sc2612C610.INE`。
    - `iscomplete` 默认 `False`，用于控制是否返回完整字段。
    - 当标的不存在或未返回详情时返回 `None`。
    """
    if xtdata is None:
        from xtquant import xtdata

        xtdata.enable_hello = False
    detail = xtdata.get_instrument_detail(symbol, iscomplete=iscomplete)
    if not detail:
        return None
    if not isinstance(detail, dict):
        raise ValueError(f"标的详情返回格式异常: {type(detail)}")
    return detail


def main() -> None:
    """CLI 入口：查询 miniQMT 标的详情。"""
    parser = argparse.ArgumentParser(
        description="查询 miniQMT 标的详情",
        epilog=(
            "调用示例:\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 600519.SH\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 000001.SZ\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol 600519.SH --complete\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol nr09.INE\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_detail --symbol sc2612C610.INE --complete"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--symbol", required=True, help="待查询的 symbol，示例：600519.SH")
    parser.add_argument(
        "--complete",
        dest="iscomplete",
        action="store_true",
        default=False,
        help="启用完整字段返回（默认关闭）",
    )
    args = parser.parse_args()

    try:
        detail = get_instrument_detail(args.symbol, iscomplete=args.iscomplete)
    except ValueError as exc:
        parser.error(str(exc))
        return

    if detail is not None:
        print(json.dumps(detail, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
