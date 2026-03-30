// 证券与行情相关类型定义

export type MarketCode = 'SH' | 'SZ' | string

export interface Security {
  symbol: string
  name?: string
  market: MarketCode
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
  symbol: string
  name: string
  market: MarketCode
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

