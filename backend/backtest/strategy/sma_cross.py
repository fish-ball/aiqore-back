# -*- coding: utf-8 -*-
"""
双均线交叉策略：短均线上穿长均线买入，下穿卖出。
"""
import backtrader as bt


class SmaCrossStrategy(bt.Strategy):
    """简单双均线交叉策略：短均线上穿长均线买入，下穿卖出。"""

    params = (
        ("fast_period", 5),
        ("slow_period", 20),
    )

    def __init__(self):
        self.fast_ma = bt.indicators.SMA(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SMA(
            self.data.close, period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.close()
