import api from './index'

/**
 * 数据源连接 API（QMT/聚宽/tushare 等连接配置）
 */
export const dataSourceApi = {
  getList(params = {}) {
    return api.get('/data-source/list', { params })
  },

  getOne(id) {
    return api.get(`/data-source/connections/${id}`)
  },

  create(body) {
    return api.post('/data-source/connections', body)
  },

  update(id, body) {
    return api.put(`/data-source/connections/${id}`, body)
  },

  delete(id) {
    return api.delete(`/data-source/connections/${id}`)
  },

  /** 测试连接有效性 */
  test(id) {
    return api.post(`/data-source/connections/${id}/test`)
  }
}
