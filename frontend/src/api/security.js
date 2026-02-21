import api from './index'

export const securityApi = {
  getList(params = {}) {
    return api.get('/security/list', { params })
  },
  
  getDetail(symbol) {
    return api.get(`/security/${symbol}`)
  },
  
  search(keyword, limit = 50) {
    return api.get('/security/search', {
      params: { keyword, limit }
    })
  },
  
  update(market = null, sector = null, sourceType = 'qmt', sourceId = null) {
    const params = { source_type: sourceType }
    if (market) params.market = market
    if (sector) params.sector = sector
    if (sourceId != null) params.source_id = sourceId
    return api.post('/security/update', null, { params })
  },

  /** 从数据源更新单个证券（同步） */
  updateOne(symbol, sourceType = 'qmt', sourceId = null) {
    const params = { symbol, source_type: sourceType }
    if (sourceId != null) params.source_id = sourceId
    return api.post('/security/update-one', null, { params })
  }
}

