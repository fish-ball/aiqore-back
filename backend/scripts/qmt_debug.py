# -*- coding: utf-8 -*-
"""
通过 get_market_data(period='tick') 获取分笔数据的调试脚本。
运行：在 backend 目录执行 uv run python scripts/qmt_debug.py [标的] [日期]
示例：uv run python scripts/qmt_debug.py 000001.SZ 20260224
需配置 XT_QUANT_PATH 环境变量或 app 中数据源连接。
"""
import sys
from pathlib import Path
from datetime import datetime

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def get_xtdata_path():
    """从环境或 app 配置获取 QMT 路径。"""
    import os
    try:
        from app.config import settings
        path = getattr(settings, "XT_QUANT_PATH", None)
    except Exception:
        path = None
    return path or os.environ.get("XT_QUANT_PATH", "")


def get_xtdata(xt_quant_path: str):
    """加载 xtdata 模块，与 adapter 逻辑一致。"""
    path = (xt_quant_path or "").strip()
    if not path or not Path(path).is_dir():
        return None
    base = Path(path)
    if base.is_dir():
        datadir = base / "datadir"
        if datadir.is_dir() and str(datadir) not in sys.path:
            sys.path.insert(0, str(datadir))
    try:
        from xtquant import xtdata
        return xtdata
    except ImportError:
        return None


def main():
    symbol = (sys.argv[1] if len(sys.argv) > 1 else "000001.SZ").strip()
    trade_date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y%m%d")
    trade_date = trade_date.replace("-", "")[:8]
    if len(trade_date) != 8:
        print("日期格式应为 YYYYMMDD 或 YYYY-MM-DD")
        return 1

    xt_quant_path = get_xtdata_path()
    if not xt_quant_path or not Path(xt_quant_path).is_dir():
        print("未配置 XT_QUANT_PATH 或路径不存在，请设置环境变量或 app 配置")
        return 1

    xtdata = get_xtdata(xt_quant_path)
    if xtdata is None:
        print("无法加载 xtquant，请确认 miniQMT 已安装且 XT_QUANT_PATH 指向其根目录")
        return 1

    st = f"{trade_date[:4]}{trade_date[4:6]}{trade_date[6:8]}000000"
    et = f"{trade_date[:4]}{trade_date[4:6]}{trade_date[6:8]}235959"
    print(f"标的: {symbol}, 日期: {trade_date}, 时间范围: {st} ~ {et}")
    print("正在下载分笔历史...")

    if hasattr(xtdata, "download_history_data"):
        try:
            xtdata.download_history_data(symbol, period="tick", start_time=st, end_time=et)
            print("download_history_data(tick) 调用完成")
        except Exception as e:
            print("download_history_data 异常（继续尝试获取）:", e)

    print("调用 get_market_data(period='tick')...")
    try:
        data = xtdata.get_market_data_ex(
            # field_list=['time', 'stime', 'lastPrice', 'open', 'high', 'low', 'volume', 'lastClose', 
            # 'amount', 'volume', 'stockStatus', 'openInterest', 'transactionNum',
            # 'lastSettlementPrice', 'settlementPrice', 'askPrice', 'askVol', 'bidPrice', 'bidVol'],
            stock_list=[symbol],
            period="tick",
            dividend_type='none', # 不复权
            fill_data=False, # 不填充数据
            start_time=st,
            end_time=et,
            # count=-1, # 不传count时，仅返回历史行情
        )
        print('!!!!fuck')
        print(type(data))
        print(data[symbol])
        print(data[symbol].dtypes)
        for i, row in data[symbol].head(1).iterrows():
            print(f'----- row[{i}] -----')
            print(row)
    except Exception as e:
        print("get_market_data 异常:", e)
        return 1

    if not data:
        print("返回为空")
        return 0

    print("返回类型:", type(data).__name__)
    if isinstance(data, dict):
        print("键:", list(data.keys())[:20])
    if symbol not in data:
        print(f"未包含 {symbol}，可用键: {list(data.keys())}")
        return 0

    arr = data[symbol]
    print(f"data[{symbol!r}] 类型: {type(arr).__name__}")
    if arr is None:
        print("值为 None")
        return 0

    try:
        import numpy as np
        if isinstance(arr, np.ndarray):
            print("shape:", arr.shape, "dtype:", arr.dtype)
            if hasattr(arr.dtype, "names") and arr.dtype.names:
                print("字段:", list(arr.dtype.names))
                n = min(5, len(arr))
                print(f"前 {n} 条:")
                for i in range(n):
                    row = {name: arr[name][i] for name in arr.dtype.names}
                    print(f"  [{i}] {row}")
            elif len(arr) > 0:
                print("前 3 条:", arr[:3])
    except ImportError:
        pass
    if isinstance(arr, (list, tuple)):
        print("长度:", len(arr))
        print("前 3 条:", arr[:3])

    return 0


if __name__ == "__main__":
    sys.exit(main())
