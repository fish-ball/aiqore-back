import api from './index'

export const marketApi = {
  getQuote(symbols) {
    return api.get('/market/quote', {
      params: { symbols }
    })
  },
  
  getKline(symbol, period = '1d', count = 100, startDate = null, endDate = null) {
    return api.get('/market/kline', {
      params: {
        symbol,
        period,
        count,
        start_date: startDate,
        end_date: endDate
      }
    })
  },

  getTicks(symbol, tradeDate, forceUpdate = false) {
    return api.get('/market/ticks', {
      params: {
        symbol,
        trade_date: tradeDate,
        force_update: forceUpdate
      }
    })
  },

  searchStocks(keyword) {
    return api.get('/market/search', {
      params: { keyword }
    })
  }
}

