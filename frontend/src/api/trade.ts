import api from './index'

export const tradeApi = {
  getAccount(accountId: number | string) {
    return api.get(`/trade/account/${accountId}`)
  },

  createAccount(data: Record<string, unknown>) {
    return api.post('/trade/account', data)
  },

  syncAccount(accountId: number | string) {
    return api.post(`/trade/account/${accountId}/sync`)
  }
}

