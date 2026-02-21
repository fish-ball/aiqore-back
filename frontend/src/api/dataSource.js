import api from './index'

/**
 * 数据源连接 API（QMT/聚宽/tushare 等连接配置）
 */
export const dataSourceApi = {
  getList(params = {}) {
    return api.get('/data-source/list', { params })
  },

  getOne(id) {
    return api.get(`/data-source/connections/${id}`)
  },

  create(body) {
    return api.post('/data-source/connections', body)
  },

  update(id, body) {
    return api.put(`/data-source/connections/${id}`, body)
  },

  delete(id) {
    return api.delete(`/data-source/connections/${id}`)
  },

  /** 测试连接有效性 */
  test(id) {
    return api.post(`/data-source/connections/${id}/test`)
  },

  /** 接口调试（当前仅 miniQMT 支持） */
  debugSectors(id) {
    return api.get(`/data-source/connections/${id}/debug/sectors`)
  },
  debugStocksInSector(id, sector) {
    return api.post(`/data-source/connections/${id}/debug/stocks-in-sector`, { sector })
  },
  debugInstrumentDetail(id, symbol) {
    return api.post(`/data-source/connections/${id}/debug/instrument-detail`, { symbol })
  },
  debugMarketData(id, symbol, period = '1d', count = 100) {
    return api.post(`/data-source/connections/${id}/debug/market-data`, { symbol, period, count })
  },
  debugRealtimeQuote(id, symbols) {
    return api.post(`/data-source/connections/${id}/debug/realtime-quote`, { symbols })
  },
  debugStockList(id, payload = {}) {
    return api.post(`/data-source/connections/${id}/debug/stock-list`, payload)
  },
  debugPositions(id, account_id) {
    return api.post(`/data-source/connections/${id}/debug/positions`, { account_id })
  },
  debugAccountInfo(id, account_id) {
    return api.post(`/data-source/connections/${id}/debug/account-info`, { account_id })
  },
  debugSearchStocks(id, keyword) {
    return api.post(`/data-source/connections/${id}/debug/search-stocks`, { keyword })
  }
}
