import api from './index'

/**
 * 策略管理 API（策略名称 / 策略类型 / 代码 script）
 */
export const strategyApi = {
  getList(params = {}) {
    return api.get('/strategy/list', { params })
  },

  getOne(id) {
    return api.get(`/strategy/strategies/${id}`)
  },

  create(body) {
    return api.post('/strategy/strategies', body)
  },

  update(id, body) {
    return api.put(`/strategy/strategies/${id}`, body)
  },

  delete(id) {
    return api.delete(`/strategy/strategies/${id}`)
  }
}
