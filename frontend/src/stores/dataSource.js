import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataSourceApi } from '../api/dataSource'

const STORAGE_KEY = 'aiqore_current_data_source_id'

function loadCurrentIdFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw != null && raw !== '') {
      const n = parseInt(raw, 10)
      if (!Number.isNaN(n)) return n
    }
  } catch (_) {}
  return null
}

export const useDataSourceStore = defineStore('dataSource', () => {
  const list = ref([])
  const loading = ref(false)
  const currentId = ref(loadCurrentIdFromStorage())

  const currentDataSource = computed(() => {
    const id = currentId.value
    if (id == null) return null
    return list.value.find((item) => item.id === id) || null
  })

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await dataSourceApi.getList({ is_active: true })
      list.value = (res && res.items) ? res.items : []
      const id = currentId.value
      if (id != null && !list.value.some((item) => item.id === id)) {
        currentId.value = list.value.length ? list.value[0].id : null
        persistCurrent()
      }
    } catch (error) {
      console.error('获取数据源列表失败:', error)
      list.value = []
    } finally {
      loading.value = false
    }
  }

  function setCurrent(id) {
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
    } catch (_) {}
  }

  return {
    list,
    loading,
    currentId,
    currentDataSource,
    fetchList,
    setCurrent
  }
})
