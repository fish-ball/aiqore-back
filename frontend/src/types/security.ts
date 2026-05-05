// 证券与行情相关类型定义

export type MarketCode = 'SH' | 'SZ' | 'BJ' | string

/** 资产大类，与后端 instruments.asset_class 一致 */
export type AssetClassCode = 'EQUITY' | 'FIXED_INCOME' | 'COMMODITY'

/** 标的类型，与后端 instruments.instrument_type 一致 */
export type InstrumentTypeCode =
  | 'STOCK'
  | 'FUND'
  | 'INDEX'
  | 'FUTURE'
  | 'OPTION'
  | 'BOND'
  | 'ETF'

/** 交易所摘要（嵌套在证券接口中） */
export interface ExchangeBrief {
  code: string
  name: string
  short_name?: string | null
  /** 与交易所目录 suffix 一致 */
  suffix?: string | null
}

export interface Security {
  code: string
  name?: string
  market?: MarketCode
  exchange_code?: string
  exchange?: ExchangeBrief | null
  asset_class?: AssetClassCode
  instrument_type?: InstrumentTypeCode
}

export interface SecurityQuote {
  symbol?: string
  name?: string
  last_price?: number
  open?: number
  high?: number
  low?: number
  pre_close?: number
  volume?: number
  amount?: number
  change?: number
  change_percent?: number
  change_pct?: number
}

// 列表页展示的一行数据（证券基础信息 + 行情）
export interface SecurityTableRow {
  code: string
  name: string
  market: MarketCode
  exchange_code?: string
  exchange?: ExchangeBrief | null
  asset_class?: AssetClassCode
  instrument_type?: InstrumentTypeCode
  last_price: number
  open: number
  high: number
  low: number
  pre_close: number
  volume: number
  amount: number
  change: number
  change_percent: number
}
