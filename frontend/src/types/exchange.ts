/** 交易所（与 /api/exchange/list 单项一致，静态目录无数据库 id） */

export interface ExchangeRow {
  code: string
  name: string
  short_name?: string | null
  /** 证券代码点号后规范片段（不含点），大写 */
  suffix?: string | null
  country_region?: string | null
  sort_order?: number
  description?: string | null
  is_active?: number
}
