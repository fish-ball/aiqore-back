import api from './index'

export const marketApi = {
  getQuote(symbols: string) {
    return api.get('/market/quote', {
      params: { symbols }
    })
  },

  getKline(
    symbol: string,
    period = '1d',
    count = 100,
    startDate: string | null = null,
    endDate: string | null = null,
    adjustType: string | null = null
  ) {
    return api.get('/market/kline', {
      params: {
        symbol,
        period,
        count,
        start_date: startDate,
        end_date: endDate,
        adjust_type: adjustType
      }
    })
  },

  getTicks(symbol: string, tradeDate: string, forceUpdate = false) {
    return api.get('/market/ticks', {
      params: {
        symbol,
        trade_date: tradeDate,
        force_update: forceUpdate
      }
    })
  },

  getDividFactors(symbol: string) {
    return api.get('/market/divid-factors', {
      params: { symbol }
    })
  },

  searchStocks(keyword: string) {
    return api.get('/market/search', {
      params: { keyword }
    })
  }
}

