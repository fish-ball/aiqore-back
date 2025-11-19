import api from './index'

export const taskApi = {
  getStatus(taskId) {
    return api.get(`/task/${taskId}`)
  },
  getList() {
    return api.get('/task/list')
  }
}

