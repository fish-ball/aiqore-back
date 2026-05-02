# -*- coding: utf-8 -*-
"""
行情获取类原生调用：xtdata.get_market_data_ex。

对应迅投知识库「行情函数 - 获取行情数据」中 ContextInfo.get_market_data_ex 的语义；
Python 独立模块中通过注入的 `xtdata` 调用，参数名与 XtQuant.XtData 文档一致（field_list、stock_list 等）。

参见：https://dict.thinktrader.net/innerApi/data_function.html （获取行情数据）
"""
from __future__ import annotations

from typing import Any, List, Optional, Sequence


def get_market_data_ex(
    xtdata: Any,
    *,
    field_list: Optional[Sequence[str]] = None,
    stock_list: Optional[Sequence[str]] = None,
    period: str = "1d",
    start_time: str = "",
    end_time: str = "",
    count: int = -1,
    dividend_type: str = "none",
    fill_data: bool = True,
) -> Any:
    """
    调用 xtdata.get_market_data_ex，拉取本地/实时行情（K 线、分笔、Level2 等，取决于 period）。

    - field_list：字段列表，空序列表示全部字段（与文档「传空则为全部字段」一致）。
    - stock_list：合约代码列表，如 600000.SH。
    - period：tick、1m、5m、15m、30m、1h、1d、1w、1mon、l2quote 等。
    - start_time / end_time：%Y%m%d 或 %Y%m%d%H%M%S，可为空串。
    - count：条数；-1 表示由起止时间决定（见官方说明）。
    - dividend_type：K 线复权方式；tick 等周期无效。
    - fill_data：是否填充缺失 K 线。

    说明：内置策略文档中 ContextInfo.get_market_data_ex 另有 subscribe 参数；独立运行时的
    XtQuant.XtData 接口不含该参数，故本封装与 xtdata 保持一致。

    若当前对象无 get_market_data_ex，返回 None（不抛异常）。

    K 线周期返回值请经 ``app.services.data_source.adapter.qmt.market_data_ex_adapt``
    转为 ``app.services.data_source.models.KlineBatchBySymbol``。
    """
    if not hasattr(xtdata, "get_market_data_ex"):
        return None
    fl: List[str] = list(field_list) if field_list is not None else []
    sl: List[str] = list(stock_list) if stock_list is not None else []
    return xtdata.get_market_data_ex(
        field_list=fl,
        stock_list=sl,
        period=period,
        start_time=start_time or "",
        end_time=end_time or "",
        count=count,
        dividend_type=dividend_type,
        fill_data=fill_data,
    )
