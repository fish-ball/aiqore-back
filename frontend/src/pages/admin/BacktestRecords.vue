<template>
  <div class="backtest-records">
    <div class="page-header">
      <h2>回测记录</h2>
    </div>

    <el-card style="margin-top: 20px">
      <el-form inline class="filter-bar">
        <el-form-item label="策略">
          <el-input
            v-model="filterStrategyId"
            placeholder="策略 ID 筛选"
            clearable
            style="width: 220px"
            @clear="applyFilter"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterStatus" placeholder="全部" clearable style="width: 120px" @change="applyFilter">
            <el-option label="待执行" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failure" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchList">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column label="任务 ID" width="100">
          <template #default="{ row }">
            <el-tooltip :content="row.id" placement="top">
              <span>{{ row.id ? row.id.slice(0, 8) : '-' }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="策略" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.strategy_id ? row.strategy_id.slice(0, 8) + (row.strategy_name ? ' ' + row.strategy_name : '') : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="security_symbol" label="证券代码" width="110" />
        <el-table-column prop="security_name" label="证券名称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="start_date" label="开始日期" width="110" />
        <el-table-column prop="end_date" label="结束日期" width="110" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果摘要" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.result && row.status === 'success'">
              收益 {{ (row.result.total_return != null ? (row.result.total_return * 100).toFixed(2) : '-') }}%，
              回撤 {{ (row.result.max_drawdown != null ? (row.result.max_drawdown * 100).toFixed(2) : '-') }}%
            </span>
            <span v-else-if="row.result && row.result.error">{{ row.result.error }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="165">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="回测任务详情" width="720px">
      <el-descriptions v-if="currentRow" :column="1" border size="small">
        <el-descriptions-item label="任务 ID">{{ currentRow.id }}</el-descriptions-item>
        <el-descriptions-item label="策略">{{ currentRow.strategy_id ? currentRow.strategy_id.slice(0, 8) + (currentRow.strategy_name ? ' ' + currentRow.strategy_name : '') : '-' }}</el-descriptions-item>
        <el-descriptions-item label="证券">{{ currentRow.security_symbol }} {{ currentRow.security_name }}</el-descriptions-item>
        <el-descriptions-item label="区间">{{ currentRow.start_date }} ~ {{ currentRow.end_date }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(currentRow.status)" size="small">{{ statusLabel(currentRow.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="图表">
          <template v-if="chartUrl">
            <el-image
              :src="chartUrl"
              :preview-src-list="[chartUrl]"
              fit="contain"
              class="backtest-chart"
            />
          </template>
          <template v-else>
            <span>-</span>
          </template>
        </el-descriptions-item>
        <el-descriptions-item label="交易明细">
          <template v-if="hasTrades">
            <el-button type="primary" link @click="openTrades">查看交易明细</el-button>
          </template>
          <template v-else>
            <span>-</span>
          </template>
        </el-descriptions-item>
        <el-descriptions-item label="结果">
          <pre class="result-json">{{ prettyResult(currentRow.result) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="tradesVisible" title="交易明细" width="800px">
      <el-table :data="trades" v-loading="tradesLoading" height="400">
        <el-table-column prop="date" label="日期" width="140" />
        <el-table-column prop="type" label="方向" width="80" />
        <el-table-column prop="price" label="价格" width="120" />
        <el-table-column prop="size" label="数量" width="120" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { backtestApi } from '../../api/backtest'

const route = useRoute()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStrategyId = ref('')
const filterStatus = ref('')
const detailVisible = ref(false)
const currentRow = ref(null)
const tradesVisible = ref(false)
const tradesLoading = ref(false)
const trades = ref([])

const statusLabel = (s) => {
  const m = { pending: '待执行', running: '运行中', success: '成功', failure: '失败' }
  return m[s] || s || '-'
}

const statusTagType = (s) => {
  const m = { pending: 'info', running: 'warning', success: 'success', failure: 'danger' }
  return m[s] || 'info'
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

const prettyResult = (r) => {
  if (r == null) return '-'
  try {
    return JSON.stringify(r, null, 2)
  } catch (e) {
    return String(r)
  }
}

const chartUrl = computed(() => {
  const row = currentRow.value
  if (!row || !row.result || !Array.isArray(row.result.plot_files) || row.result.plot_files.length === 0) {
    return ''
  }
  const fullPath = row.result.plot_files[0] || ''
  const parts = fullPath.split(/[/\\]/)
  const filename = parts[parts.length - 1] || ''
  if (!filename) return ''
  return `/api/backtest/output/${row.id}/${filename}`
})

const hasTrades = computed(() => {
  const row = currentRow.value
  if (!row || !row.result) return false
  if (Array.isArray(row.result.trades) && row.result.trades.length > 0) return true
  if (row.result.trade_file) return true
  return false
})

const buildParams = () => {
  const params = { limit: pageSize.value, offset: (page.value - 1) * pageSize.value }
  if (filterStrategyId.value) params.strategy = filterStrategyId.value
  if (filterStatus.value) params.status = filterStatus.value
  return params
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await backtestApi.list(buildParams())
    list.value = (res && res.items) ? res.items : []
    total.value = res?.total ?? 0
  } catch (e) {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const applyFilter = () => {
  page.value = 1
  fetchList()
}

const resetFilter = () => {
  filterStrategyId.value = ''
  filterStatus.value = ''
  page.value = 1
  fetchList()
}

const handlePageChange = (p) => {
  page.value = p
  fetchList()
}

const showDetail = (row) => {
  currentRow.value = row
  detailVisible.value = true
}

const openTrades = async () => {
  const row = currentRow.value
  if (!row) return
  tradesVisible.value = true
  tradesLoading.value = true
  try {
    const res = await backtestApi.getTrades(row.id)
    if (res && Array.isArray(res)) {
      trades.value = res
    } else if (res && Array.isArray(res.data)) {
      trades.value = res.data
    } else {
      trades.value = []
    }
  } catch (e) {
    trades.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取交易明细失败')
  } finally {
    tradesLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该回测记录吗？删除后不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await backtestApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

// 同步 route.query.strategy 到筛选框并请求
watch(
  () => route.query.strategy,
  (sid) => {
    if (sid != null && sid !== '') {
      filterStrategyId.value = sid
      page.value = 1
      fetchList()
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (route.query.strategy == null || route.query.strategy === '') {
    fetchList()
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.backtest-records h2 {
  margin: 0;
}
.filter-bar {
  margin-bottom: 16px;
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.result-json {
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.backtest-chart {
  max-width: 100%;
  max-height: 360px;
  display: block;
}
</style>
