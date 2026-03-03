# -*- coding: utf-8 -*-
"""
网格策略：以基准价为中线，按比例上下画格，价格向下穿越网格线买入、向上穿越卖出。
适合震荡市，单边行情需注意网格范围。
"""
import backtrader as bt


class GridStrategy(bt.Strategy):
    """
    网格策略：在基准价上下按 grid_step_pct 生成网格线，
    收盘价向下穿越某格时买入一份，向上穿越某格时卖出该格对应的一份。
    """

    params = (
        ("base_price", None),   # 基准价，None 表示用首根 K 线收盘价
        ("grid_step_pct", 0.02),  # 网格间距，如 0.02 表示 2%
        ("grid_num", 10),       # 基准价上下各多少格
        ("percents", 10),       # 每格占用资金的百分比
    )

    def __init__(self):
        self.levels = []        # 网格线价格列表（升序）
        self.level_pos = {}     # 每条线对应的持仓份数（线索引 -> 份数）
        self.base_price = None
        self._last_close = None
        self._grid_order_size = 0

    def start(self):
        self._last_close = None

    def next(self):
        if len(self.data) < 2:
            self._last_close = self.data.close[0]
            return

        # 首根 K 线确定基准价并生成网格
        if self.base_price is None:
            self.base_price = self.params.base_price
            if self.base_price is None or self.base_price <= 0:
                self.base_price = float(self.data.close[0])
            self._build_levels()
            self._last_close = self.data.close[0]
            return

        cur = float(self.data.close[0])
        last = self._last_close
        self._last_close = cur

        # 遍历网格线：向下穿越则买入，向上穿越则卖出
        one_size = self._one_grid_size()
        if one_size <= 0:
            return
        for i, level in enumerate(self.levels):
            if last > level >= cur:
                # 向下穿越：买入一格
                self._grid_order_size = one_size
                self.buy(size=one_size)
                self.level_pos[i] = self.level_pos.get(i, 0) + 1
            elif last < level <= cur:
                # 向上穿越：卖出一格（该格有持仓才卖）
                if self.level_pos.get(i, 0) > 0 and self.position:
                    sell_size = min(one_size, self.position.size)
                    self._grid_order_size = sell_size
                    self.sell(size=sell_size)
                    self.level_pos[i] = self.level_pos.get(i, 0) - 1

    def _build_levels(self):
        """根据基准价和间距生成网格线（升序）。"""
        base = self.base_price
        step = self.params.grid_step_pct
        n = self.params.grid_num
        self.levels = []
        for i in range(-n, 0):
            self.levels.append(base * (1 - step) ** (-i))
        self.levels.append(base)
        for i in range(1, n + 1):
            self.levels.append(base * (1 + step) ** i)
        self.levels.sort()
        self.level_pos = {i: 0 for i in range(len(self.levels))}

    def _one_grid_size(self):
        """每格买入的股数：按当前资金 * percents% / 当前价 计算。"""
        cash = self.broker.getcash()
        price = self.data.close[0]
        if price <= 0:
            return 0
        value = cash * (self.params.percents / 100.0)
        return max(0, int(value / price))


class GridOrderSizer(bt.Sizer):
    """网格策略用：使用策略在 buy/sell 前设置的 _grid_order_size，保证按格数量下单。"""

    def _getsizing(self, comminfo, cash, data, isbuy):
        size = getattr(self.strategy, "_grid_order_size", None)
        if size is not None and size > 0:
            return int(size)
        price = data.close[0] or 1
        return max(0, int(cash / price))
