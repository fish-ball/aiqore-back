"""miniqmt 板块成分查询工具。

函数式用法：
- `from aiqore_data.providers.miniqmt import get_stock_list_in_sector`

CLI 用法（直接运行本文件）：
- `python -m aiqore_data.providers.miniqmt.get_stock_list_in_sector --sector 沪深A股`
"""

import argparse
from typing import Any

from aiqore_data.providers.miniqmt.core import load_xtdata


def get_stock_list_in_sector(sector: str, *, xtdata: Any | None = None) -> list[str]:
    """查询指定板块下的证券代码列表。"""
    runtime_xtdata = xtdata or load_xtdata()
    symbols = runtime_xtdata.get_stock_list_in_sector(sector)
    if symbols is None:
        return []
    if not isinstance(symbols, list):
        raise ValueError(f"板块成分返回格式异常: {type(symbols)}")
    return [str(item) for item in symbols]


def main() -> None:
    """CLI 入口：查询指定板块下的证券代码列表。"""
    parser = argparse.ArgumentParser(
        description="查询 miniQMT 指定板块下的证券代码列表",
        epilog=(
            "调用示例:\n"
            "  python -m aiqore_data.providers.miniqmt.get_stock_list_in_sector --sector 沪深A股"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--sector", required=True, help="板块名称，例如 沪深A股")
    args = parser.parse_args()

    try:
        symbols = get_stock_list_in_sector(args.sector)
    except ValueError as exc:
        parser.error(str(exc))
        return

    for symbol in symbols:
        print(symbol)


if __name__ == "__main__":
    main()
