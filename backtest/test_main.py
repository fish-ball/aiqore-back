# -*- coding: utf-8 -*-
"""
backtrader 回测示例：从 data/stock/300760.SZ 读取 daily.parquet 日线数据，
可选从 ticks/ 目录读取分时数据（此处示例仅使用日线）。
策略见 backtest/strategy/：双均线 SmaCrossStrategy、网格 GridStrategy。
"""
from pathlib import Path
import sys

import pandas as pd
import backtrader as bt

# 保证以 python backtest/test_main.py 运行时也能解析 backtest 包
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backtest.strategy import SmaCrossStrategy, GridStrategy, GridOrderSizer


# 数据目录：项目根目录下 data/stock/300760.SZ
def get_data_root() -> Path:
    """回测脚本所在目录的上级为项目根。"""
    return Path(__file__).resolve().parent.parent


def load_daily_df(symbol: str = "300760.SZ") -> pd.DataFrame:
    """
    从 data/stock/{symbol}/daily.parquet 加载日线。
    列：time(UNIX毫秒), open, high, low, close, volume, ...
    转为 backtrader 需要的 DataFrame：datetime 索引，列 open/high/low/close/volume。
    """
    root = get_data_root()
    daily_path = root / "data" / "stock" / symbol / "daily.parquet"
    if not daily_path.is_file():
        raise FileNotFoundError(f"日线文件不存在: {daily_path}")
    df = pd.read_parquet(daily_path)
    # time 为 UNIX 毫秒 -> datetime 索引
    df["datetime"] = pd.to_datetime(df["time"], unit="ms")
    df = df.set_index("datetime")
    # 按时间排序
    df = df.sort_index()
    # backtrader PandasData 需要：open, high, low, close, volume
    feed_df = df[["open", "high", "low", "close", "volume"]].copy()
    feed_df = feed_df.astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )
    return feed_df


def run_backtest(
    symbol: str = "300760.SZ",
    strategy: str = "sma_cross",
    start_date: str = None,
    end_date: str = None,
    cash: float = 100000.0,
    commission: float = 0.001,
    **strategy_params,
):
    """
    运行回测：加载日线、添加策略、执行并打印结果。
    strategy: "sma_cross" 双均线 或 "grid" 网格。
    start_date/end_date 格式 YYYY-MM-DD，None 表示不裁剪。
    strategy_params 传给策略，如 fast_period/slow_period、grid_step_pct/grid_num 等。
    """
    df = load_daily_df(symbol)
    if start_date:
        df = df.loc[df.index >= start_date]
    if end_date:
        df = df.loc[df.index <= end_date]
    if df.empty:
        raise ValueError("裁剪后无数据，请检查 start_date/end_date 或数据文件")

    cerebro = bt.Cerebro()
    if strategy == "sma_cross":
        cerebro.addstrategy(
            SmaCrossStrategy,
            fast_period=strategy_params.get("fast_period", 5),
            slow_period=strategy_params.get("slow_period", 20),
        )
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    elif strategy == "grid":
        cerebro.addstrategy(
            GridStrategy,
            base_price=strategy_params.get("base_price"),
            grid_step_pct=strategy_params.get("grid_step_pct", 0.02),
            grid_num=strategy_params.get("grid_num", 10),
            percents=strategy_params.get("percents", 10),
        )
        cerebro.addsizer(GridOrderSizer)
    else:
        raise ValueError("strategy 仅支持 sma_cross / grid")

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data, name="daily")
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)

    print("回测前资金: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("回测后资金: %.2f" % cerebro.broker.getvalue())
    return cerebro


if __name__ == "__main__":
    # 双均线回测
    # run_backtest(
    #     symbol="300760.SZ",
    #     strategy="sma_cross",
    #     start_date=None,
    #     end_date=None,
    #     cash=100000.0,
    #     commission=0.001,
    #     fast_period=5,
    #     slow_period=20,
    # )
    # 网格回测（取消注释运行）
    run_backtest(
        symbol="300760.SZ",
        strategy="grid",
        cash=100000.0,
        commission=0.001,
        grid_step_pct=0.02,
        grid_num=10,
        percents=10,
    )
