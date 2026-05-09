import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@iottest/vue-core/src/libs/api'

/** 未选数据源时 requireDataSourceId 抛出，便于 await 后自然中断后续逻辑 */
export class DataSourceRequiredError extends Error {
  readonly code = 'NO_DATA_SOURCE_ID' as const
  constructor() {
    super('NO_DATA_SOURCE_ID')
    this.name = 'DataSourceRequiredError'
  }
}

type DataSourceId = number

interface DataSource {
  id: DataSourceId
  source_type?: string
  [key: string]: unknown
}

const STORAGE_KEY = 'aiqore_current_data_source_id'

function loadCurrentIdFromStorage(): DataSourceId | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw != null && raw !== '') {
      const n = Number.parseInt(raw, 10)
      if (!Number.isNaN(n)) return n
    }
  } catch {
    // localStorage 可能在某些环境不可用
  }
  return null
}

export const useDataSourceStore = defineStore('dataSource', () => {
  const list = ref<DataSource[]>([])
  const loading = ref(false)
  const currentId = ref<DataSourceId | null>(loadCurrentIdFromStorage())

  const currentDataSource = computed<DataSource | null>(() => {
    const id = currentId.value
    if (id == null) return null
    return list.value.find((item) => item.id === id) || null
  })

  /** 当前有效的数据源连接 id（用于 API 的 data_source_id）；无效或未选返回 null */
  function currentDataSourceId(): DataSourceId | null {
    const id = currentId.value
    if (id == null || typeof id !== 'number' || !Number.isFinite(id) || id < 1) return null
    return id
  }

  const hasCurrentDataSource = computed(() => currentDataSourceId() != null)

  /**
   * 需要带 data_source_id 调用接口时使用：有 id 则返回；无 id 时默认提示并抛出 DataSourceRequiredError
   */
  async function requireDataSourceId(): Promise<DataSourceId> {
    const id = currentDataSourceId()
    if (id != null) return id
    ElMessage.warning('请先在顶栏选择数据源')
    throw new DataSourceRequiredError()
  }

  const dataSourceListResource = api('data-source/connections')

  const fetchList = async () => {
    loading.value = true
    try {
      const resp = await dataSourceListResource.get({}, { is_active: true, page: 1, page_size: 500 })
      const res = resp.data as { results?: DataSource[] }
      const items = Array.isArray(res?.results) ? res.results : []
      list.value = items as DataSource[]
      const id = currentId.value
      if (id != null && !list.value.some((item) => item.id === id)) {
        const first = list.value[0]
        currentId.value = first ? first.id : null
        persistCurrent()
      }
    } catch (error) {
      console.error('获取数据源列表失败:', error)
      list.value = []
    } finally {
      loading.value = false
    }
  }

  function setCurrent(id: DataSourceId | null) {
    currentId.value = id
    persistCurrent()
  }

  function persistCurrent() {
    try {
      if (currentId.value != null) {
        localStorage.setItem(STORAGE_KEY, String(currentId.value))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      // localStorage 可能在某些环境不可用
    }
  }

  return {
    list,
    loading,
    currentId,
    currentDataSource,
    hasCurrentDataSource,
    currentDataSourceId,
    requireDataSourceId,
    fetchList,
    setCurrent
  }
})

