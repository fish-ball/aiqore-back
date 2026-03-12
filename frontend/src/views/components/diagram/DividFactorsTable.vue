<template>
  <div class="divid-panel">
    <div v-if="loading" class="divid-loading">加载中...</div>
    <template v-else>
      <div v-if="!rows.length" class="divid-empty">暂无除权除息数据</div>
      <div v-else class="divid-table-wrapper">
        <table class="divid-table">
          <thead>
            <tr>
              <th
                v-for="col in columns"
                :key="col.prop"
                :class="['divid-cell', { 'divid-date': isDateColumn(col.prop) }]"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in rows" :key="idx">
              <td
                v-for="col in columns"
                :key="col.prop"
                :class="['divid-cell', { 'divid-date': isDateColumn(col.prop) }]"
              >
                {{ formatCell(row, col.prop) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import moment from 'moment'
import { marketApi } from '../../../api/market'

const props = defineProps({
  // 证券代码，例如 000001.SZ
  symbol: {
    type: String,
    required: true
  }
})

const rows = ref([])
const loading = ref(false)

const columns = computed(() => {
  if (!Array.isArray(rows.value) || rows.value.length === 0) return []
  const first = rows.value[0] || {}
  const keyToLabel = {
    // 日期类字段：统一显示为“日期”
    time: '日期',
    date: '日期',
    m_timetag: '日期',
    // 除权除息字段映射（简略列名，含中文含义注释）
    // interest: 派息金额（每股股利，元）
    interest: '派',
    // stockBonus: 每股送股数量（股）
    stockBonus: '送',
    // stockGift: 每股转增股本（股）
    stockGift: '转',
    // allotNum: 每股配股数（股）
    allotNum: '配',
    // allotPrice: 配股价格（元）
    allotPrice: '配价',
    // gugai: 是否股改
    gugai: '股改',
    // dr: 除权系数（DR）
    dr: 'DR'
  }
  return Object.keys(first).map((k) => ({
    prop: k,
    label: keyToLabel[k] || k
  }))
})

async function fetchData() {
  const s = (props.symbol || '').trim()
  if (!s) {
    rows.value = []
    return
  }
  loading.value = true
  try {
    const res = await marketApi.getDividFactors(s)
    rows.value = Array.isArray(res) ? res : []
  } catch (error) {
    console.error('获取除权除息数据失败:', error)
    ElMessage.error('获取除权除息数据失败')
  } finally {
    loading.value = false
  }
}

function formatCell(row, prop) {
  const v = row[prop]
  if (v == null || v === '') return ''
  // 日期/时间字段统一转为 YYYY-MM-DD
  if (prop === 'time' || prop === 'date' || prop === 'm_timetag') {
    // 支持 UNIX 毫秒时间戳（例如 1462464000000），优先按数字判断
    const num = Number(v)
    if (!Number.isNaN(num) && num > 0) {
      return moment(num).format('YYYY-MM-DD')
    }
    let s = String(v).trim()
    if (/^\d{8}$/.test(s)) {
      return moment(s, 'YYYYMMDD').format('YYYY-MM-DD')
    }
    if (/^\d{14}$/.test(s)) {
      return moment(s, 'YYYYMMDDHHmmss').format('YYYY-MM-DD')
    }
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
      return s.slice(0, 10)
    }
    return s
  }
  // 数值字段统一四舍五入到分（两位小数）
  const num = Number(v)
  if (!Number.isNaN(num)) {
    return num.toFixed(2)
  }
  return v
}

function isDateColumn(prop) {
  return prop === 'time' || prop === 'date' || prop === 'm_timetag'
}

onMounted(() => {
  fetchData()
})

watch(
  () => props.symbol,
  () => {
    fetchData()
  }
)
</script>

<style scoped>
.divid-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: #e0e0e0;
  font-size: 12px;
}

.divid-loading,
.divid-empty {
  padding: 8px 4px;
  color: #808080;
}

.divid-table-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.divid-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: transparent;
}

.divid-table thead {
  background: #111111;
}

.divid-table th,
.divid-table td {
  padding: 4px 6px;
  border: 1px solid #262626;
  color: #b0b0b0;
  text-align: center;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.divid-table th {
  font-weight: 500;
  color: #e0e0e0;
}

.divid-table tbody tr:nth-child(2n) {
  background: #141414;
}

.divid-table tbody tr:hover {
  background: #1a1a1a;
}

.divid-cell.divid-date {
  width: 80px;
}
</style>

