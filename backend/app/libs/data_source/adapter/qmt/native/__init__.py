# -*- coding: utf-8 -*-
"""QMT native 封装：对 xtquant 的薄封装，供适配器等通过 ``native.xxx`` 调用。"""

from .get_instrument_detail import get_instrument_detail
from .get_instrument_type import get_instrument_type

__all__ = ["get_instrument_detail", "get_instrument_type"]
