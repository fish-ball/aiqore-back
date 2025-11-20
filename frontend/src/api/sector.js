import api from './index.js'

export default {
  // 获取板块列表
  getList(params = {}) {
    return api.get('/sector/list', { params })
  },
  
  // 同步板块
  sync() {
    return api.post('/sector/sync')
  },
  
  // 获取板块统计
  getStatistics() {
    return api.get('/sector/statistics')
  },
  
  // 获取板块详情
  getDetail(sectorName) {
    return api.get(`/sector/${sectorName}`)
  }
}

