# -*- coding: utf-8 -*-
"""
原生 xtquant / xtdata 调用薄封装层（函数式 API）。

设计意图：
- 对外参数、返回值逐步对齐「标准 adapter / models」约定；
- 对内仅负责调用迅投 Python 接口（xtdata 等），不混入业务编排；
- 上层 QMTAdapter 等通过本包组合能力，便于单测 mock 与替换实现。

K 线类 ``get_market_data_ex`` 的统一结构见 ``app.services.data_source.models.KlineBatchBySymbol``，
由 ``app.services.data_source.adapter.qmt.market_data_ex_adapt`` 完成适配。

子模块：maintain（本地数据下载维护）、market（get_market_data_ex 行情获取）。
单元测试见 tests/test_maintain.py、tests/test_market.py（部分为真实 xtdata；无环境时 skip）。
"""

from __future__ import annotations

from app.services.data_source.adapter.qmt.native.maintain import download_history_data
from app.services.data_source.adapter.qmt.native.market import get_market_data_ex

__all__ = ["download_history_data", "get_market_data_ex"]
