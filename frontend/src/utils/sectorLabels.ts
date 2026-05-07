/**
 * 与后端 `backend/app/libs/data_source/models/enums.py` 中
 * AssetClass / InstrumentType 的枚举 value 一一对应（展示用中文名取自枚举注释）。
 */

/** 资产大类 AssetClass.value */
export const ASSET_CLASS_LABELS: Record<string, string> = {
  EQUITY: '权益',
  DEBT: '债权',
  HYBRID: '混合',
  COMMODITY: '商品',
  CURRENCY: '货币',
  CRYPTO: '加密货币',
}

/** 标的类型 InstrumentType.value */
export const INSTRUMENT_TYPE_LABELS: Record<string, string> = {
  STOCK: '普通股',
  PREF_STOCK: '优先股',
  FUND: '基金',
  ETF: '交易所基金',
  INDEX: '指数',
  BOND: '纯债',
  CONV_BOND: '可转债',
  REPO: '回购',
  FUTURE: '期货',
  OPTION: '期权',
  PERP: '永续合约',
  WARRANT: '权证',
}

export function assetClassLabel(value: string | null | undefined): string {
  if (!value) return '--'
  return ASSET_CLASS_LABELS[value] || value
}

export function instrumentTypeLabel(value: string | null | undefined): string {
  if (!value) return '--'
  return INSTRUMENT_TYPE_LABELS[value] || value
}

/**
 * 证券页等板块分组用的粗分类（与 SecurityList 中 CATEGORY_ORDER 键一致）
 */
export function sectorGroupLabelFromInstrumentType(
  it: string | null | undefined,
): string {
  const u = (it || '').toUpperCase()
  if (['STOCK', 'PREF_STOCK'].includes(u)) return '股票'
  if (u === 'FUND') return '基金'
  if (u === 'ETF') return 'ETF'
  if (['BOND', 'CONV_BOND', 'REPO'].includes(u)) return '债券'
  if (u === 'INDEX') return '指数'
  if (['FUTURE', 'PERP'].includes(u)) return '期货'
  if (['OPTION', 'WARRANT'].includes(u)) return '期权'
  return '其他'
}
