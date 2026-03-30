import api from './index'

export const analysisApi = {
  getAccountSummary(accountId: number | string) {
    return api.get(`/analysis/account/${accountId}/summary`)
  },

  getPositionAnalysis(accountId: number | string) {
    return api.get(`/analysis/account/${accountId}/positions`)
  },

  getTradeStatistics(accountId: number | string, startDate: string | null = null, endDate: string | null = null) {
    return api.get(`/analysis/account/${accountId}/trade-stats`, {
      params: {
        start_date: startDate,
        end_date: endDate
      }
    })
  },

  getProfitTrend(accountId: number | string, days = 30) {
    return api.get(`/analysis/account/${accountId}/profit-trend`, {
      params: { days }
    })
  }
}

