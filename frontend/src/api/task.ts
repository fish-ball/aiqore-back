import api from './index'

export const taskApi = {
  getSpecs() {
    return api.get('/tasks/specs')
  },

  run(taskName: string, params: Record<string, unknown> = {}) {
    return api.post('/tasks/run', {
      task_name: taskName,
      params
    })
  },

  list(params: Record<string, unknown> = {}) {
    return api.get('/tasks', { params })
  },

  get(taskId: string) {
    return api.get(`/tasks/${taskId}`)
  },

  waitForTask(taskId: string, options: { timeout?: number } = {}) {
    const { timeout = 600 } = options
    return api.get(`/tasks/${taskId}/wait`, {
      params: { timeout },
      timeout: (timeout + 30) * 1000
    })
  },

  stop(taskId: string) {
    return api.post(`/tasks/${taskId}/stop`)
  },

  delete(taskId: string) {
    return api.delete(`/tasks/${taskId}`)
  }
}

