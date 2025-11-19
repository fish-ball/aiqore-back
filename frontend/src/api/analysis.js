import api from './index'

export const analysisApi = {
  getAccountSummary(accountId) {
    return api.get(`/analysis/account/${accountId}/summary`)
  },
  
  getPositionAnalysis(accountId) {
    return api.get(`/analysis/account/${accountId}/positions`)
  },
  
  getTradeStatistics(accountId, startDate = null, endDate = null) {
    return api.get(`/analysis/account/${accountId}/trade-stats`, {
      params: {
        start_date: startDate,
        end_date: endDate
      }
    })
  },
  
  getProfitTrend(accountId, days = 30) {
    return api.get(`/analysis/account/${accountId}/profit-trend`, {
      params: { days }
    })
  }
}

