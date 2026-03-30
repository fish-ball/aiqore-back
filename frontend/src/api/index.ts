import axios, { type AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

interface ApiEnvelope<T = unknown> {
  code: number
  data: T
  message?: string
}

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response: AxiosResponse<ApiEnvelope>) => {
    const { code, data, message } = response.data
    // 与业务约定一致：拦截器直接返回 data，类型上需与 Axios 默认签名区分
    if (code === 0) return data as never
    ElMessage.error(message || '请求失败')
    return Promise.reject(new Error(message || '请求失败'))
  },
  (error: AxiosError<unknown>) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as { detail?: string; message?: string } | undefined

      if (status === 409) {
        const message = data?.detail || data?.message || '任务正在运行中，请等待完成后再试'
        ElMessage.warning(message)
        return Promise.reject(new Error(message))
      }

      const message = data?.detail || data?.message || error.message || '请求失败'
      ElMessage.error(message)
      return Promise.reject(new Error(message))
    }

    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default api

