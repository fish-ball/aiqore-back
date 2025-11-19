import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    const { code, data, message } = response.data
    if (code === 0) {
      return data
    } else {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message || '请求失败'))
    }
  },
  error => {
    // 处理HTTP错误响应
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      
      // 409 Conflict - 任务冲突
      if (status === 409) {
        const message = data?.detail || data?.message || '任务正在运行中，请等待完成后再试'
        ElMessage.warning(message)
        return Promise.reject(new Error(message))
      }
      
      // 其他HTTP错误
      const message = data?.detail || data?.message || error.message || '请求失败'
      ElMessage.error(message)
      return Promise.reject(new Error(message))
    }
    
    // 网络错误或其他错误
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default api

