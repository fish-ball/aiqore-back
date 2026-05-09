"""miniqmt 交易日查询工具。

函数式用法：
- `from aiqore_data.providers.miniqmt import get_trading_dates`

CLI 用法（直接运行本文件）：
- `python -m aiqore_data.providers.miniqmt.get_trading_dates --market SH --start-time 20240101 --end-time 20240131`
- `python -m aiqore_data.providers.miniqmt.get_trading_dates --market SZ --start-time 20240101 --end-time 20240131 --count 10`
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from dateutil import parser as date_parser

from aiqore_data.providers.miniqmt.core import load_xtdata


def _normalize_cli_date(value: str) -> str:
    """将 CLI 输入日期智能转换为 YYYYMMDD。"""
    raw = value.strip()
    if not raw:
        raise ValueError("日期不能为空")

    # 纯数字: 仅支持 YYYYMMDD
    if raw.isdigit():
        if len(raw) == 8:
            return raw
        raise ValueError(f"不支持的纯数字日期格式: {value}，仅支持 YYYYMMDD")

    # 其他日期格式交给 dateutil 智能解析
    try:
        parsed = date_parser.parse(raw)
        return parsed.strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError(
            f"不支持的日期格式: {value}，支持 YYYYMMDD、YYYY-MM-DD、YYYY/MM/DD、YYYY.MM.DD"
        ) from exc


def get_trading_dates(
    market: str = "SH",
    start_time: str | None = None,
    end_time: str | None = None,
    count: int = -1,
    *,
    xtdata: Any | None = None,
) -> Any:
    """封装 miniQMT 的交易日查询接口。

    使用说明：
    - `market` 为交易市场代码，默认 `SH`。
    - `start_time`/`end_time` 可缺省；缺省时会以空字符串传入 xtdata。
    - `count=-1` 表示按时间范围返回全部可用交易日；设置正整数可限制返回数量。

    示例：
    ```python
    from aiqore_data.providers.miniqmt import get_trading_dates

    dates = get_trading_dates(start_time="20240101", end_time="20240131")
    print(dates)
    ```
    """
    runtime_xtdata = xtdata or load_xtdata()
    normalized_start = _normalize_cli_date(start_time) if start_time else ""
    normalized_end = _normalize_cli_date(end_time) if end_time else ""
    return runtime_xtdata.get_trading_dates(market, normalized_start, normalized_end, count)


def main() -> None:
    """CLI 入口：查询 miniQMT 交易日。"""
    parser = argparse.ArgumentParser(
        description="查询 miniQMT 交易日",
        epilog=(
            "调用示例:\n"
            "  python -m aiqore_data.providers.miniqmt.get_trading_dates --market SH --start-time 20240101 --end-time 20240131\n"
            "  python -m aiqore_data.providers.miniqmt.get_trading_dates --market SZ --start-time 20240101 --end-time 20240131 --count 10\n"
            "  python -m aiqore_data.providers.miniqmt.get_trading_dates --start-time 20240101\n"
            "  python -m aiqore_data.providers.miniqmt.get_trading_dates"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--market", default="SH", help="市场代码，默认 SH，例如 SH、SZ")
    parser.add_argument(
        "--start-time",
        default=None,
        help="开始日期，可缺省；支持 YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD",
    )
    parser.add_argument(
        "--end-time",
        default=None,
        help="结束日期，可缺省；支持 YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD",
    )
    parser.add_argument("--count", type=int, default=-1, help="返回数量限制，默认 -1 表示不限制")
    args = parser.parse_args()

    try:
        start_time = _normalize_cli_date(args.start_time) if args.start_time else ""
        end_time = _normalize_cli_date(args.end_time) if args.end_time else ""
    except ValueError as exc:
        parser.error(str(exc))
        return

    dates = get_trading_dates(
        market=args.market,
        start_time=start_time,
        end_time=end_time,
        count=args.count,
    )
    print(json.dumps(dates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
