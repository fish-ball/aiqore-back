"""miniqmt 标的类型推断工具。

函数式用法：
- `from aiqore_data.providers.miniqmt import get_instrument_type`

CLI 用法（直接运行本文件）：
- `python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 600519.SH`
- `python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 510300.SH`
- `python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol nr09.INE`
- `python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol sc2612C610.INE`

已执行样例（当前 QMT 环境）：
- 上证 A 股：`600519.SH` -> `{"stock": true}`
- 深证 A 股：`000001.SZ` -> `{"stock": true}`
- 基金：`161725.SZ` -> `{"fund": true}`
- ETF：`510300.SH` -> `{"etf": true}`
- 基金+ETF：`159741.SZ` -> `{"fund": true, "etf": true}`
- 期货：`PK612.ZF` -> `{}`
- 期权：`IO2605-P-5000.IF` -> `{}`
- 其他（指数/债券）：
  - `000300.SH` -> `{"index": true}`
  - `186511.SH` -> `{}`
"""

import argparse
from typing import Any



def get_instrument_type(symbol: str, *, xtdata: Any | None = None) -> str | None:
    """根据 symbol 在 miniQMT 板块中的归属推断标的类型。

    使用说明：
    - 输入 symbol 建议使用 `代码.市场` 格式，例如 `600519.SH`、`IF2406.CFFEX`、`nr09.INE`、`sc2612C610.INE`。
    - 当 symbol 不存在或无法识别时返回 `None`。
    - 当匹配结果出现多个 key 同时命中时抛出 `ValueError`。

    示例：
    ```python
    from aiqore_data.providers.miniqmt import get_instrument_type

    instrument_type = get_instrument_type("600519.SH")
    print(instrument_type)  # 例如: "stock"
    ```

    分类型样例：
    - 上证 A 股：`get_instrument_type("600519.SH")`
    - 深证 A 股：`get_instrument_type("000001.SZ")`
    - 基金：`get_instrument_type("161725.SZ")`
    - 期货：`get_instrument_type("PK612.ZF")`
    - 期权：`get_instrument_type("IO2605-P-5000.IF")`
    - 其他（指数/债券）：`get_instrument_type("000300.SH")`、`get_instrument_type("186511.SH")`
    """
    if xtdata is None:
        from xtquant import xtdata

        xtdata.enable_hello = False

    raw_type = xtdata.get_instrument_type(symbol)
    if raw_type is None:
        return None
    if isinstance(raw_type, str):
        return raw_type or None
    if not isinstance(raw_type, dict):
        raise ValueError(f"未知的标的类型返回格式: {type(raw_type)}")

    matched_keys = [key for key, enabled in raw_type.items() if enabled]
    if not matched_keys:
        return None
    if len(matched_keys) > 1:
        raise ValueError(f"symbol={symbol} 匹配到多个类型: {matched_keys}")
    return matched_keys[0]


def main() -> None:
    """CLI 入口：根据 symbol 推断 miniQMT 标的类型。"""
    parser = argparse.ArgumentParser(
        description="根据 symbol 推断 miniQMT 标的类型",
        epilog=(
            "调用示例:\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 600519.SH\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 000001.SZ\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 161725.SZ\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol PK612.ZF\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol IO2605-P-5000.IF\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 000300.SH\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol 186511.SH\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol nr09.INE\n"
            "  python -m aiqore_data.providers.miniqmt.get_instrument_type --symbol sc2612C610.INE"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="待推断的 symbol，示例：600519.SH",
    )
    args = parser.parse_args()

    try:
        instrument_type = get_instrument_type(args.symbol)
    except ValueError as exc:
        parser.error(str(exc))
        return

    if instrument_type is not None:
        print(instrument_type)


if __name__ == "__main__":
    main()
