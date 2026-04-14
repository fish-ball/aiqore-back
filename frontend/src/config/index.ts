import type { VueCoreConfig } from '@iottest/vue-core/src/config'
import {
  defaultVueCoreConfigHooks,
  type ListViewLoadDataContext,
  type ListViewNormalizeDataContext,
} from '@iottest/vue-core/src/config/hooks'
import type { ListViewData } from '@iottest/vue-core/src/libs/data-view/types/view'
import type { ListViewQuery } from '@iottest/vue-core/src/libs/data-view/types/fields'
import routes from './routes'
import { ElMessage } from 'element-plus'
import { api } from '@iottest/vue-core/src/libs/api'
import type { RestResource } from '@iottest/vue-core/src/libs/api'

/** 从 Axios 响应体中解析统一信封（不抛错，供 load 内联使用） */
function envelopeInner(body: unknown): { items?: unknown[]; total?: number } | null {
  if (body == null || typeof body !== 'object') return null
  const b = body as { code?: number; data?: { items?: unknown[]; total?: number }; message?: string }
  if (b.code !== 0 || b.data == null || typeof b.data !== 'object') return null
  const inner = b.data
  return {
    items: Array.isArray(inner.items) ? inner.items : undefined,
    total: typeof inner.total === 'number' ? inner.total : undefined,
  }
}

export default {
  name: 'AIQore 个人投资管理系统',
  routes,
  apiRoot: '/api',
  // 统一在末尾追加 `/`，与后端路由风格保持一致，避免 307 跳转
  urlFormat: '{id}{/action}',
  axiosOptions: {
    timeout: 60000, // 60秒超时
  },
  hooks: {
    ...defaultVueCoreConfigHooks,
    /**
     * 各列表 model 与后端对齐；一次性全量返回的列表在服务端按页切片。
     * 默认：resource.get({}, { page, page_size, ...query })。
     */
    async listViewLoadData(page: number, pageSize: number, query: ListViewQuery, context: ListViewLoadDataContext) {
      const model = context.listViewOptions.model

      // 列表走 GET /api/strategy/list；model 用 strategy/strategies 以便与删除等资源路径一致
      if (model === 'strategy/strategies') {
        const resp = await api('strategy/list').get({}, { ...query })
        const inner = envelopeInner(resp.data) ?? { items: [], total: 0 }
        const items = inner.items ?? []
        const total = inner.total ?? items.length
        const start = (page - 1) * pageSize
        return {
          results: items.slice(start, start + pageSize),
          count: total,
        }
      }

      if (model === 'tasks') {
        const resp = await context.resource.get(
          {},
          {
            limit: pageSize,
            offset: (page - 1) * pageSize,
            ...query,
          },
        )
        return resp.data
      }

      if (model === 'backtest/tasks') {
        const params: Record<string, unknown> = {
          limit: pageSize,
          offset: (page - 1) * pageSize,
        }
        if (query?.strategy) params.strategy = query.strategy
        if (query?.status) params.status = query.status
        const resp = await context.resource.get({}, params)
        return resp.data
      }

      // 列表走 GET /api/data-source/list；model 用 data-source/connections 与删除等资源一致
      if (model === 'data-source/connections') {
        const params: Record<string, unknown> = {}
        if (query.source_type) params.source_type = query.source_type
        if (query.is_active === 'true') params.is_active = true
        else if (query.is_active === 'false') params.is_active = false
        const resp = await api('data-source/list').get({}, params)
        const inner = envelopeInner(resp.data) ?? { items: [], total: 0 }
        const items = inner.items ?? []
        const total = inner.total ?? items.length
        const start = (page - 1) * pageSize
        return {
          results: items.slice(start, start + pageSize),
          count: total,
        }
      }

      if (model === 'sector/list') {
        const params: Record<string, unknown> = {}
        if (query.category) params.category = query.category
        if (query.market && query.market !== '__cross__') {
          params.market = query.market
        }
        const resp = await context.resource.get({}, params)
        const inner = envelopeInner(resp.data) ?? { items: [], total: 0 }
        let items = Array.isArray(inner.items) ? [...inner.items] : []
        if (query.market === '__cross__') {
          items = items.filter((r) => !(r as { market?: unknown })?.market)
        }
        const total = items.length
        const start = (page - 1) * pageSize
        return {
          results: items.slice(start, start + pageSize),
          count: total,
        }
      }

      return defaultVueCoreConfigHooks.listViewLoadData(page, pageSize, query, context)
    },
    /**
     * 将后端统一信封 { code, data: { items, total } } 转为 ListView 所需的 { results, count }。
     * 已是 ListView 形态时直接返回。
     */
    listViewNormalizeData(
      data: unknown,
      context?: ListViewNormalizeDataContext,
    ): ListViewData<unknown> | Promise<ListViewData<unknown>> {
      if (data != null && typeof data === 'object' && 'results' in data && 'count' in data) {
        return data as ListViewData<unknown>
      }
      const body = data as {
        code?: number
        data?: { items?: unknown[]; total?: number; results?: unknown[]; count?: number }
        message?: string
      }
      if (body?.code === 0 && body.data != null && typeof body.data === 'object') {
        const inner = body.data
        if (Array.isArray(inner.items)) {
          return {
            results: inner.items,
            count: typeof inner.total === 'number' ? inner.total : inner.items.length,
          }
        }
        if (Array.isArray(inner.results) && typeof inner.count === 'number') {
          return { results: inner.results, count: inner.count }
        }
      }
      return defaultVueCoreConfigHooks.listViewNormalizeData(data, context)
    },
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
