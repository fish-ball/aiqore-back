import api from './index'

export const backtestApi = {
  run(body: Record<string, unknown>) {
    return api.post('/backtest/run', body)
  },

  list(params: Record<string, unknown> = {}) {
    return api.get('/backtest/tasks', { params })
  },

  getOne(taskId: string) {
    return api.get(`/backtest/tasks/${taskId}`)
  },

  getTrades(taskId: string) {
    return api.get(`/backtest/tasks/${taskId}/trades`)
  },

  delete(taskId: string) {
    return api.delete(`/backtest/tasks/${taskId}`)
  }
}

