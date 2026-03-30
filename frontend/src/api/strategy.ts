import api from './index'

export const strategyApi = {
  getList(params: Record<string, unknown> = {}) {
    return api.get('/strategy/list', { params })
  },

  getOne(id: number | string) {
    return api.get(`/strategy/strategies/${id}`)
  },

  create(body: Record<string, unknown>) {
    return api.post('/strategy/strategies', body)
  },

  update(id: number | string, body: Record<string, unknown>) {
    return api.put(`/strategy/strategies/${id}`, body)
  },

  delete(id: number | string) {
    return api.delete(`/strategy/strategies/${id}`)
  }
}

