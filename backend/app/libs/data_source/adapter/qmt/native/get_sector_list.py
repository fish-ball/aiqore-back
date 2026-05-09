"""miniqmt 板块列表查询工具。

函数式用法：
- `from aiqore_data.providers.miniqmt import get_sector_list`

CLI 用法（直接运行本文件）：
- `python -m aiqore_data.providers.miniqmt.get_sector_list`
"""

import argparse
from typing import Any


def get_sector_list(*, xtdata: Any | None = None) -> list[str]:
    """查询 miniQMT 可用板块列表。"""
    if not xtdata:
        from xtquant import xtdata

        xtdata.enable_hello = False
    sectors = xtdata.get_sector_list()
    if sectors is None:
        return []
    if not isinstance(sectors, list):
        raise ValueError(f"板块列表返回格式异常: {type(sectors)}")
    return [str(item) for item in sectors]


def main() -> None:
    """CLI 入口：查询 miniQMT 板块列表。"""
    parser = argparse.ArgumentParser(
        description="查询 miniQMT 板块列表",
        epilog=("调用示例:\n  python -m aiqore_data.providers.miniqmt.get_sector_list"),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    args = parser.parse_args()

    try:
        sectors = get_sector_list(**vars(args))
    except ValueError as exc:
        parser.error(str(exc))
        return

    for sector in sectors:
        print(sector)


if __name__ == "__main__":
    main()
