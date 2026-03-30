import type { VueCoreConfig } from '@iottest/vue-core/src/config'
import routes from './routes'
import { ElMessage } from 'element-plus'
import type { RestResource } from '@iottest/vue-core/src/libs/api'

export default {
  name: 'AIQore 个人投资管理系统',
  routes,
  apiRoot: '/api/v1',
  // 统一在末尾追加 `/`，与后端路由风格保持一致，避免 307 跳转
  urlFormat: '{id}{/action}/',
  axiosOptions: {
    timeout: 60000, // 60秒超时
  },
  onRequestSuccess(resp) {
    const resourceObject = (resp.config as unknown as { resourceObject: RestResource })?.resourceObject
    if (resourceObject?.metadata.silent) return
    if (!resp.data?.msg) return
    if (resp.data?.msg && !resp.data?.silent) {
      if (resp.data.silent) {
        if (!resp.data.ok) console.error('!!!请求接口错误!!!', resp.data.msg)
      } else {
        if (resp.data.ok) ElMessage.success(resp.data.msg)
        else ElMessage.error(resp.data.msg)
      }
    }
  },
} as VueCoreConfig
