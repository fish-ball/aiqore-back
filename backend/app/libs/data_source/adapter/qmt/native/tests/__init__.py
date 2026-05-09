# -*- coding: utf-8 -*-
"""
native 子包内单元测试（与实现同目录树）。

按模块拆分：test_normalize_cli_date、test_get_sector_list、test_get_stock_list_in_sector、
test_get_trading_dates、test_get_instrument_detail、test_get_instrument_type。

在 backend 目录下执行 discovery，例如：
python -m unittest discover -s app/libs/data_source/adapter/qmt/native/tests -p "test_*.py" -v
"""
