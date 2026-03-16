# -*- coding: utf-8 -*-
"""
Backtrader 回测引擎实现：从策略脚本字符串解析 bt.Strategy 子类，配置 Cerebro，执行并产出绩效与图表。
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Type

import backtrader as bt
import pandas as pd

from app.services.backtest.engine_base import BacktestEngineBase


logger = logging.getLogger(__name__)


def _strip_main_block(script: str) -> str:
    """移除脚本中 if __name__ == '__main__': 及其下属块，避免执行示例代码。"""
    if not script or not script.strip():
        return script
    # 匹配 if __name__ == '__main__': 或 if __name__ == "__main__":
    pattern = r'''(?ms)^\s*if\s+__name__\s*==\s*['"]__main__['"]\s*:\s*\n(.*?)(?=\n(?:[^\s#]|\Z))'''
    # 移除该块：保留到 if 之前，以及块后内容（用简单策略：按行处理，遇到 if __name__ 则跳过直到缩进恢复）
    lines = script.split('\n')
    out = []
    skip_indent = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", stripped):
            skip_indent = len(line) - len(line.lstrip()) if line.strip() else 0
            continue
        if skip_indent is not None:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
            if line.strip() and current_indent <= skip_indent:
                skip_indent = None
                out.append(line)
            continue
        out.append(line)
    return '\n'.join(out)


def _find_first_strategy_class(ns: Dict[str, Any]) -> Type[bt.Strategy]:
    """在命名空间中查找第一个 bt.Strategy 的子类（非 bt.Strategy 自身）。"""
    for name, obj in ns.items():
        if (
            isinstance(obj, type)
            and issubclass(obj, bt.Strategy)
            and obj is not bt.Strategy
        ):
            return obj
    raise ValueError("脚本中未找到 bt.Strategy 的子类")


def _wrap_strategy(strategy_class: Type[bt.Strategy]) -> Type[bt.Strategy]:
    """包装策略类，自动记录 _trade_log 与 _nav_log，供绘图使用。"""
    class WrappedStrategy(strategy_class):
        def __init__(self):
            super().__init__()
            self._trade_log = []
            self._nav_log = []

        def notify_order(self, order):
            if order.status == order.Completed:
                self._trade_log.append({
                    "date": self.data.datetime.date(0),
                    "type": "BUY" if order.isbuy() else "SELL",
                    "price": round(order.executed.price, 2),
                    "size": abs(int(order.executed.size)),
                })
            if hasattr(super(), "notify_order"):
                super().notify_order(order)

        def next(self):
            self._nav_log.append({
                "date": self.data.datetime.date(0),
                "nav": self.broker.getvalue(),
            })
            super().next()

    WrappedStrategy.__name__ = strategy_class.__name__
    WrappedStrategy.__qualname__ = strategy_class.__qualname__
    WrappedStrategy.__module__ = strategy_class.__module__
    return WrappedStrategy


def _calc_metrics(cerebro: bt.Cerebro, strat: bt.Strategy, df: pd.DataFrame, initial_cash: float) -> Dict[str, Any]:
    """从 Backtrader 结果提取绩效指标（与课程 _calc_metrics 对齐）。"""
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash if initial_cash else 0

    trading_days = len(df)
    years = trading_days / 252 if trading_days else 0
    if years > 0 and total_return > -1:
        annual_return = (1 + total_return) ** (1 / years) - 1
    else:
        annual_return = total_return

    sharpe_ratio = 0.0
    try:
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", 0) or 0
    except Exception:
        pass

    max_drawdown = 0.0
    max_dd_len = 0
    try:
        dd = strat.analyzers.drawdown.get_analysis()
        max_drawdown = dd.get("max", {}).get("drawdown", 0) / 100
        max_dd_len = dd.get("max", {}).get("len", 0)
    except Exception:
        pass

    calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

    total_trades = 0
    won_trades = 0
    lost_trades = 0
    win_rate = 0.0
    avg_win = 0.0
    avg_loss = 0.0
    profit_loss_ratio = 0.0
    profit_factor = 0.0
    max_consecutive_losses = 0
    expected_value = 0.0
    try:
        ta = strat.analyzers.trades.get_analysis()
        total_trades = ta.get("total", {}).get("total", 0)
        won_trades = ta.get("won", {}).get("total", 0)
        lost_trades = ta.get("lost", {}).get("total", 0)
        win_rate = won_trades / total_trades if total_trades > 0 else 0
        avg_win = ta.get("won", {}).get("pnl", {}).get("average", 0) or 0
        avg_loss = ta.get("lost", {}).get("pnl", {}).get("average", 0) or 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        gross_profit = ta.get("won", {}).get("pnl", {}).get("total", 0) or 0
        gross_loss = ta.get("lost", {}).get("pnl", {}).get("total", 0) or 0
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
        streak = ta.get("streak", {}).get("lost", {})
        max_consecutive_losses = streak.get("longest", 0) if streak else 0
        expected_value = win_rate * avg_win + (1 - win_rate) * avg_loss if total_trades > 0 else 0
    except Exception:
        pass

    return {
        "final_value": round(final_value, 2),
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "max_dd_len": max_dd_len,
        "sharpe_ratio": round(sharpe_ratio, 4),
        "calmar_ratio": round(calmar_ratio, 4),
        "total_trades": total_trades,
        "won_trades": won_trades,
        "lost_trades": lost_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_loss_ratio": round(profit_loss_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "max_consecutive_losses": max_consecutive_losses,
        "expected_value": round(expected_value, 2),
        "years": round(years, 2),
        "trading_days": trading_days,
    }


def _plot_backtest(
    result: Dict[str, Any],
    df: pd.DataFrame,
    initial_cash: float,
    output_dir: str,
    symbol: str = "",
    title: str = "Backtest",
) -> List[str]:
    """绘制回测结果图到 output_dir，返回生成的文件路径列表。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    plot_files = []

    trades = result.get("trades", [])
    nav_data = result.get("nav", [])
    if not nav_data:
        return plot_files

    nav_df = pd.DataFrame(nav_data)
    nav_df["date"] = pd.to_datetime(nav_df["date"])
    nav_df.set_index("date", inplace=True)
    nav_df["nav_pct"] = nav_df["nav"] / initial_cash
    nav_df["peak"] = nav_df["nav"].cummax()
    nav_df["drawdown"] = (nav_df["nav"] - nav_df["peak"]) / nav_df["peak"] * 100

    close_start = float(df["close"].iloc[0])
    benchmark = df["close"] / close_start

    buy_dates = [t["date"] for t in trades if t["type"] == "BUY"]
    buy_prices = [t["price"] for t in trades if t["type"] == "BUY"]
    sell_dates = [t["date"] for t in trades if t["type"] == "SELL"]
    sell_prices = [t["price"] for t in trades if t["type"] == "SELL"]

    m = result
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={"height_ratios": [3, 2, 1]})

    ax1.plot(df.index, df["close"], "gray", linewidth=1, alpha=0.8, label="收盘价")
    if buy_dates:
        ax1.scatter(buy_dates, buy_prices, color="#e74c3c", marker="^", s=80, zorder=5, label=f"买入({len(buy_dates)}次)")
    if sell_dates:
        ax1.scatter(sell_dates, sell_prices, color="#2ecc71", marker="v", s=80, zorder=5, label=f"卖出({len(sell_dates)}次)")
    ax1.set_ylabel("价格")
    ax1.set_title(f"{title}  {symbol}", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.3)
    info_text = (
        f"Return:    {m['total_return']*100:+.2f}%\n"
        f"Annual:    {m['annual_return']*100:+.2f}%\n"
        f"MaxDD:     {m['max_drawdown']*100:.2f}%\n"
        f"Sharpe:    {m['sharpe_ratio']:.2f}\n"
        f"Calmar:    {m['calmar_ratio']:.2f}\n"
        f"WinRate:   {m['win_rate']*100:.1f}%\n"
        f"P/L Ratio: {m['profit_loss_ratio']:.2f}\n"
        f"ProfitF:   {m['profit_factor']:.2f}"
    )
    ax1.text(0.98, 0.97, info_text, transform=ax1.transAxes, fontsize=9, verticalalignment="top",
             horizontalalignment="right", bbox=dict(boxstyle="round,pad=0.5", facecolor="wheat", alpha=0.8), family="monospace")

    ax2.plot(nav_df.index, nav_df["nav_pct"], "#2980b9", linewidth=1.5, label="策略净值")
    ax2.plot(benchmark.index, benchmark, "gray", linewidth=1, alpha=0.6, label="买入持有")
    ax2.axhline(y=1.0, color="red", linestyle="--", alpha=0.3)
    ax2.set_ylabel("净值 (初始=1.0)")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)

    ax3.fill_between(nav_df.index, nav_df["drawdown"], 0, color="#e74c3c", alpha=0.4)
    ax3.plot(nav_df.index, nav_df["drawdown"], "#c0392b", linewidth=0.8)
    ax3.set_ylabel("回撤(%)")
    ax3.set_xlabel("日期")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    safe_name = title.replace(" ", "_").replace("/", "_") or "backtest"
    plot_file = os.path.join(output_dir, f"{safe_name}.png")
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")
    plt.close()
    plot_files.append(plot_file)
    return plot_files


class BacktraderEngine(BacktestEngineBase):
    """Backtrader 回测引擎实现"""

    def run(
        self,
        strategy_source: Any,
        data_df: Any,
        params: Dict[str, Any],
        output_dir: str,
    ) -> Dict[str, Any]:
        """
        strategy_source: 策略脚本字符串（将 exec 后查找 bt.Strategy 子类）
        data_df: pandas DataFrame，datetime 索引，open/high/low/close/volume
        params: initial_cash, commission, position_pct
        output_dir: 图表输出目录
        """
        initial_cash = float(params.get("initial_cash", 1000000))
        commission = float(params.get("commission", 0.0002))
        position_pct = int(params.get("position_pct", 95))
        symbol = params.get("symbol", "")

        if isinstance(strategy_source, str):
            script = _strip_main_block(strategy_source)
            ns = {"bt": bt}
            exec(script, ns)
            strategy_class = _find_first_strategy_class(ns)
        elif isinstance(strategy_source, type) and issubclass(strategy_source, bt.Strategy):
            strategy_class = strategy_source
        else:
            raise ValueError("strategy_source 须为策略脚本字符串或 bt.Strategy 子类")

        wrapped_class = _wrap_strategy(strategy_class)
        cerebro = bt.Cerebro()
        cerebro.addstrategy(wrapped_class)
        cerebro.adddata(bt.feeds.PandasData(dataname=data_df))
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=commission)
        cerebro.addsizer(bt.sizers.PercentSizer, percents=position_pct)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        results = cerebro.run()
        strat = results[0]
        metrics = _calc_metrics(cerebro, strat, data_df, initial_cash)
        trades = getattr(strat, "_trade_log", [])
        nav = getattr(strat, "_nav_log", [])

        # 使用 pandas DataFrame 持久化交易明细与净值曲线，方便后续查看
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            if trades:
                trades_df = pd.DataFrame(trades)
                trade_file_name = "trades.csv"
                trades_df.to_csv(os.path.join(output_dir, trade_file_name), index=False, encoding="utf-8-sig")
                metrics["trade_file"] = trade_file_name
            if nav:
                nav_df = pd.DataFrame(nav)
                nav_file_name = "nav.csv"
                nav_df.to_csv(os.path.join(output_dir, nav_file_name), index=False, encoding="utf-8-sig")
                metrics["nav_file"] = nav_file_name
        except Exception as e:
            # 生成明细文件失败不影响整体回测结果，但打日志方便排查
            logger.exception("保存回测明细文件失败 output_dir=%s: %s", output_dir, e)

        plot_files = []
        try:
            plot_result = dict(metrics)
            plot_result["trades"] = trades
            plot_result["nav"] = nav
            plot_files = _plot_backtest(
                plot_result,
                data_df,
                initial_cash,
                output_dir,
                symbol=symbol,
                title="Backtest",
            )
        except Exception as e:
            logger.exception("绘制回测图失败 output_dir=%s: %s", output_dir, e)
        metrics["plot_files"] = plot_files
        return metrics
