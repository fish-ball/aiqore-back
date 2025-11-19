import api from './index'

export const tradeApi = {
  // 账户相关
  getAccounts() {
    return api.get('/trade/accounts')
  },
  
  getAccount(accountId) {
    return api.get(`/trade/account/${accountId}`)
  },
  
  createAccount(data) {
    return api.post('/trade/account', data)
  },
  
  syncAccount(accountId) {
    return api.post(`/trade/account/${accountId}/sync`)
  },
  
  // 持仓相关
  getPositions(accountId) {
    return api.get(`/trade/account/${accountId}/positions`)
  },
  
  syncPositions(accountId) {
    return api.post(`/trade/account/${accountId}/positions/sync`)
  },
  
  // 交易记录
  getTrades(accountId, params = {}) {
    return api.get(`/trade/account/${accountId}/trades`, { params })
  },
  
  recordTrade(accountId, data) {
    return api.post(`/trade/account/${accountId}/trade`, data)
  }
}

