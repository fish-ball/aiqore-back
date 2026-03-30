import api from './index'

export const dataSourceApi = {
  getList(params: Record<string, unknown> = {}) {
    return api.get('/data-source/list', { params })
  },

  getOne(id: number | string) {
    return api.get(`/data-source/connections/${id}`)
  },

  create(body: Record<string, unknown>) {
    return api.post('/data-source/connections', body)
  },

  update(id: number | string, body: Record<string, unknown>) {
    return api.put(`/data-source/connections/${id}`, body)
  },

  delete(id: number | string) {
    return api.delete(`/data-source/connections/${id}`)
  },

  test(id: number | string) {
    return api.post(`/data-source/connections/${id}/test`)
  },

  debugSectors(id: number | string) {
    return api.get(`/data-source/connections/${id}/debug/sectors`)
  },
  debugStocksInSector(id: number | string, sector: string) {
    return api.post(`/data-source/connections/${id}/debug/stocks-in-sector`, { sector })
  },
  debugInstrumentDetail(id: number | string, symbol: string) {
    return api.post(`/data-source/connections/${id}/debug/instrument-detail`, { symbol })
  },
  debugMarketData(id: number | string, symbol: string, period = '1d', count = 100) {
    return api.post(`/data-source/connections/${id}/debug/market-data`, { symbol, period, count })
  },
  debugRealtimeQuote(id: number | string, symbols: string) {
    return api.post(`/data-source/connections/${id}/debug/realtime-quote`, { symbols })
  },
  debugStockList(id: number | string, payload: Record<string, unknown> = {}) {
    return api.post(`/data-source/connections/${id}/debug/stock-list`, payload)
  },
  debugPositions(id: number | string, account_id: number | string) {
    return api.post(`/data-source/connections/${id}/debug/positions`, { account_id })
  },
  debugAccountInfo(id: number | string, account_id: number | string) {
    return api.post(`/data-source/connections/${id}/debug/account-info`, { account_id })
  },
  debugSearchStocks(id: number | string, keyword: string) {
    return api.post(`/data-source/connections/${id}/debug/search-stocks`, { keyword })
  }
}

