import api from './index'

export const sectorApi = {
  getList(params: Record<string, unknown> = {}) {
    return api.get('/sector/list', { params })
  },

  sync() {
    return api.post('/sector/sync')
  },

  getStatistics() {
    return api.get('/sector/statistics')
  },

  getDetail(sectorName: string) {
    return api.get(`/sector/${sectorName}`)
  }
}

export default sectorApi

