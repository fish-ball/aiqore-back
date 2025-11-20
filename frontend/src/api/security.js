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
  
  update(market = null, sector = null) {
    const params = {}
    if (market) {
      params.market = market
    }
    if (sector) {
      params.sector = sector
    }
    return api.post('/security/update', null, { params })
  }
}

