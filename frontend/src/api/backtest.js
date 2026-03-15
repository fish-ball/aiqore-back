import api from './index'

/**
 * 回测 API：发起回测、回测任务列表与详情
 */
export const backtestApi = {
  /** 发起回测，创建 BackTestTask 并提交 Celery 执行 */
  run(body) {
    return api.post('/backtest/run', body)
  },

  /** 回测任务列表，支持 limit、offset、status、strategy_id（后端若支持则传 strategy） */
  list(params = {}) {
    return api.get('/backtest/tasks', { params })
  },

  /** 单条回测任务详情 */
  getOne(taskId) {
    return api.get(`/backtest/tasks/${taskId}`)
  },

  /** 删除回测任务 */
  delete(taskId) {
    return api.delete(`/backtest/tasks/${taskId}`)
  }
}
