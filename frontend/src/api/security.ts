import api from './index'

export const securityApi = {
  getList(params: Record<string, unknown> = {}) {
    return api.get('/security/list', { params })
  },

  getDetail(symbol: string) {
    return api.get(`/security/${symbol}`)
  },

  search(keyword: string, limit = 50) {
    return api.get('/security/search', {
      params: { keyword, limit }
    })
  },

  update(market: string | null = null, sector: string | null = null, sourceType = 'qmt', sourceId: number | string | null = null) {
    const body: Record<string, unknown> = { source_type: sourceType }
    if (market) body.market = market
    if (sector) body.sector = sector
    if (sourceId != null && sourceId !== '') body.source_id = Number(sourceId)
    return api.post('/security/update', body)
  },

  /** 从数据源更新单个证券（同步） */
  updateOne(symbol: string, sourceType = 'qmt', sourceId: number | string | null = null) {
    const body: Record<string, unknown> = { symbol, source_type: sourceType }
    if (sourceId != null && sourceId !== '') body.source_id = Number(sourceId)
    return api.post('/security/update-one', body)
  },

  /** 拉取并补全单个证券的本地缓存数据：全量日/周/月 K 线及分时，按 meta 补全。需指定数据源 */
  updateData(symbol: string, sourceType = 'qmt', sourceId: number | string | null = null) {
    const body: Record<string, unknown> = { symbol, source_type: sourceType }
    if (sourceId != null && sourceId !== '') body.source_id = Number(sourceId)
    return api.post('/security/update-data', body)
  }
}

