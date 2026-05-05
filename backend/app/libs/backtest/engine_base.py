# -*- coding: utf-8 -*-
"""
回测引擎抽象基类：统一 run(strategy_source, data_df, params) 接口，便于扩展多种回测引擎。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

# 策略来源可为策略类或脚本字符串，由具体引擎解析
# data_df: pandas DataFrame，datetime 索引，列 open/high/low/close/volume
# params: initial_cash, commission, position_pct 等
# 返回: 统一 result 结构，便于写入 BackTestTask.result 与前端展示


class BacktestEngineBase(ABC):
    """回测引擎抽象基类"""

    @abstractmethod
    def run(
        self,
        strategy_source: Any,
        data_df: Any,
        params: Dict[str, Any],
        output_dir: str,
    ) -> Dict[str, Any]:
        """
        执行回测。

        参数:
            strategy_source: 策略类或脚本字符串，由具体引擎解析
            data_df: 日 K DataFrame，datetime 索引，列 open/high/low/close/volume
            params: 含 initial_cash、commission、position_pct 等
            output_dir: 图表等资产输出目录（约定 backend/data/backtest/{task_uuid}/）

        返回:
            dict: 含 final_value、total_return、annual_return、max_drawdown、sharpe_ratio、
            total_trades、win_rate 等绩效，以及 plot_files 列表（产出文件路径）
        """
        pass
