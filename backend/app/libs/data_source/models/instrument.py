# -*- coding: utf-8 -*-
"""证券列表、搜索及数据源侧标的详情（与 ORM Instrument 字段语义对齐）。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.libs.data_source.models.enums import OptionContractKind


class InstrumentBrief(BaseModel):
    """证券列表/搜索结果中的简要条目。"""

    symbol: str
    market: str = ""
    sector: str = ""
    name: str = ""


class DataSourceInstrument(BaseModel):
    """
    数据源侧标的详情基类（迅投 get_instrument_detail 等映射而来）。
    规范交易所代码由业务层再解析；此处仅保留数据源侧字段（如含交易所后缀的 code）。
    """

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    code: str = Field("", description="标的代码，如 600000.SH（含迅投后缀）")
    name: str = Field("", description="证券名称")
    instrument_type: str = Field("", description="标的类型")
    asset_class: str = Field("", description="资产大类枚举 value：EQUITY、COMMODITY 等")
    open_date: Optional[date] = Field(None, description="上市日或合约开始日")
    expire_date: Optional[date] = Field(None, description="到期日或退市日")
    trading_date: Optional[date] = Field(None, description="最新交易日")
    pre_close: Optional[float] = Field(None, description="昨收盘价")
    last_volume: Optional[int] = Field(None, description="昨成交量")
    settlement_price: Optional[float] = Field(None, description="结算价")
    up_stop_price: Optional[float] = Field(None, description="涨停价")
    down_stop_price: Optional[float] = Field(None, description="跌停价")
    price_tick: Optional[float] = Field(None, description="最小变动价位")
    multiplier: Optional[float] = Field(None, description="合约乘数")
    is_active: Optional[bool] = Field(None, description="是否可交易")
    last_price: Optional[float] = Field(None, description="最新价格")


class DataSourceInstrumentStock(DataSourceInstrument):
    """股票。"""

    float_share: Optional[float] = Field(None, description="流通股本")
    total_share: Optional[float] = Field(None, description="总股本")


class DataSourceInstrumentFuture(DataSourceInstrument):
    """期货。"""

    product_code: str = Field("", description="品种代码")
    product_name: str = Field("", description="品种名称")
    long_margin_ratio: Optional[float] = Field(None, description="多头保证金比例")
    short_margin_ratio: Optional[float] = Field(None, description="空头保证金比例")
    is_continuous: Optional[bool] = Field(None, description="是否连续合约")
    delivery_year: Optional[int] = Field(None, description="交割年份")
    delivery_month: Optional[int] = Field(None, description="交割月份")
    max_limit_order_volume: Optional[int] = Field(None, description="限价单最大买量")
    min_limit_order_volume: Optional[int] = Field(None, description="限价单最小买量")
    max_market_order_volume: Optional[int] = Field(None, description="市价单最大买量")
    min_market_order_volume: Optional[int] = Field(None, description="市价单最小买量")
    product_open_quota: Optional[int] = Field(None, description="产品持仓上限")
    contract_open_quota: Optional[int] = Field(None, description="合约持仓上限")


class DataSourceInstrumentFund(DataSourceInstrument):
    """基金（LOF 等）。"""


class DataSourceInstrumentETF(DataSourceInstrument):
    """ETF。"""


class DataSourceInstrumentIndex(DataSourceInstrument):
    """指数。"""


class DataSourceInstrumentOption(DataSourceInstrument):
    """期权。"""

    option_type: Optional[OptionContractKind] = Field(
        None, description="认购/认沽 OptionType 0/1"
    )
    product_code: str = Field("", description="品种代码 ProductID")
    product_name: str = Field("", description="品种名称 ProductName")
    underlying_code: str = Field("", description="标的代码 OptUndlCode + OptUndlMarket")
    max_limit_order_volume: Optional[int] = Field(
        None, description="限价单最大买量 MaxLimitOrderVolume"
    )
    min_limit_order_volume: Optional[int] = Field(
        None, description="限价单最小买量 MinLimitOrderVolume"
    )
    max_market_order_volume: Optional[int] = Field(
        None, description="市价单最大买量 MaxMarketOrderVolume"
    )
    min_market_order_volume: Optional[int] = Field(
        None, description="市价单最小买量 MinMarketOrderVolume"
    )
    exercise_price: Optional[float] = Field(None, description="行权价 OptExercisePrice")
    end_delivery_date: Optional[date] = Field(
        None, description="行权/交割终止日 EndDelivDate"
    )
    product_open_quota: Optional[int] = Field(
        None, description="产品持仓额度 ProductOpenInterestQuota"
    )
    contract_open_quota: Optional[int] = Field(
        None, description="合约持仓额度 ContractOpenInterestQuota"
    )
