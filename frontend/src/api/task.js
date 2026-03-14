import api from './index'

export const taskApi = {
  /** 获取当前注册的任务规格列表 */
  getSpecs() {
    return api.get('/tasks/specs')
  },

  /**
   * 通过通用接口发起任务
   * @param {string} taskName 逻辑任务名称（如 update_bulk_security_info）
   * @param {object} params 任务参数
   */
  run(taskName, params = {}) {
    return api.post('/tasks/run', {
      task_name: taskName,
      params
    })
  },

  /**
   * 获取任务列表
   * @param {object} params { limit, offset }
   */
  list(params = {}) {
    return api.get('/tasks', { params })
  },

  /** 查询单个任务状态 */
  get(taskId) {
    return api.get(`/tasks/${taskId}`)
  },

  /** 停止任务 */
  stop(taskId) {
    return api.post(`/tasks/${taskId}/stop`)
  },

  /** 删除任务记录（仅删除列表中的记录，不影响 Celery 后端） */
  delete(taskId) {
    return api.delete(`/tasks/${taskId}`)
  }
}

