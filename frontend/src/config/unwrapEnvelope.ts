/**
 * 从 vue-core Axios 响应中取出后端统一信封内的 data（要求 code === 0）。
 * 列表整形见 config/index.ts 的 hooks；非 ListView 请求可继续用本函数。
 */
export function unwrapEnvelope<T>(resp: { data: { code?: number; data?: T; message?: string } }): T {
  const body = resp.data
  if (body?.code !== 0) {
    throw new Error(body?.message || '请求失败')
  }
  return body.data as T
}
