import api from './index'

export const tradeApi = {
  getAccounts() {
    return api.get('/trade/accounts')
  },

  getAccount(accountId: number | string) {
    return api.get(`/trade/account/${accountId}`)
  },

  createAccount(data: Record<string, unknown>) {
    return api.post('/trade/account', data)
  },

  syncAccount(accountId: number | string) {
    return api.post(`/trade/account/${accountId}/sync`)
  },

  getPositions(accountId: number | string) {
    return api.get(`/trade/account/${accountId}/positions`)
  },

  syncPositions(accountId: number | string) {
    return api.post(`/trade/account/${accountId}/positions/sync`)
  },

  getTrades(accountId: number | string, params: Record<string, unknown> = {}) {
    return api.get(`/trade/account/${accountId}/trades`, { params })
  },

  recordTrade(accountId: number | string, data: Record<string, unknown>) {
    return api.post(`/trade/account/${accountId}/trade`, data)
  }
}

