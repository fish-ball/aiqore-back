<template>
  <div class="security-list">
    <div class="page-header">
      <h2>证券列表</h2>
      <div>
        <el-select v-model="filterMarket" placeholder="选择市场" style="width: 120px; margin-right: 10px" @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="上海" value="SH" />
          <el-option label="深圳" value="SZ" />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索代码或名称"
          style="width: 200px; margin-right: 10px"
          @keyup.enter="handleSearch"
          clearable
        >
          <template #append>
            <el-button @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
        <el-button type="success" @click="updateFromQMT" :loading="updating" :disabled="updating">
          <el-icon><Download /></el-icon>
          {{ updating ? (updateProgress > 0 ? `更新中 ${updateProgress}%` : '更新中...') : '从QMT更新' }}
        </el-button>
        <el-button type="primary" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-card style="margin-top: 20px">
      <el-table
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
        @row-dblclick="handleRowDoubleClick"
        :default-sort="{ prop: 'last_price', order: 'descending' }"
        stripe
        height="600"
      >
        <el-table-column prop="symbol" label="代码" width="120" sortable="custom" fixed="left">
          <template #default="scope">
            <span class="symbol-link">{{ scope.row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="150" sortable="custom" fixed="left">
          <template #default="scope">
            {{ scope.row.name || scope.row.symbol || '--' }}
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="80" sortable="custom">
          <template #default="scope">
            <el-tag :type="scope.row.market === 'SH' ? 'success' : 'warning'" size="small">
              {{ scope.row.market === 'SH' ? '上海' : '深圳' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最新价" width="100" sortable="custom" :sort-method="sortByPrice">
          <template #default="scope">
            <span :style="{ color: getPriceColor(scope.row) }">
              ¥{{ formatPrice(scope.row.last_price) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌" width="100" sortable="custom" :sort-method="sortByChange">
          <template #default="scope">
            <span :style="{ color: scope.row.change >= 0 ? '#F56C6C' : '#67C23A' }">
              {{ scope.row.change >= 0 ? '+' : '' }}{{ formatPrice(scope.row.change) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="100" sortable="custom" :sort-method="sortByChangePercent">
          <template #default="scope">
            <span :style="{ color: scope.row.change_percent >= 0 ? '#F56C6C' : '#67C23A' }">
              {{ scope.row.change_percent >= 0 ? '+' : '' }}{{ formatChangePercent(scope.row.change_percent) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="开盘" width="100" sortable="custom" :sort-method="sortByPrice">
          <template #default="scope">
            ¥{{ formatPrice(scope.row.open) }}
          </template>
        </el-table-column>
        <el-table-column label="最高" width="100" sortable="custom" :sort-method="sortByPrice">
          <template #default="scope">
            <span style="color: #F56C6C">¥{{ formatPrice(scope.row.high) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最低" width="100" sortable="custom" :sort-method="sortByPrice">
          <template #default="scope">
            <span style="color: #67C23A">¥{{ formatPrice(scope.row.low) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="昨收" width="100" sortable="custom" :sort-method="sortByPrice">
          <template #default="scope">
            ¥{{ formatPrice(scope.row.pre_close) }}
          </template>
        </el-table-column>
        <el-table-column label="成交量" width="120" sortable="custom" :sort-method="sortByVolume">
          <template #default="scope">
            {{ formatVolume(scope.row.volume) }}
          </template>
        </el-table-column>
        <el-table-column label="成交额" width="120" sortable="custom" :sort-method="sortByAmount">
          <template #default="scope">
            {{ formatAmount(scope.row.amount) }}
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[50, 100, 200, 500]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { securityApi } from '../api/security'
import { marketApi } from '../api/market'

const router = useRouter()
const loading = ref(false)
const updating = ref(false)
const updateProgress = ref(0)
const tableData = ref([])
const filterMarket = ref('')
const searchKeyword = ref('')

const pagination = ref({
  page: 1,
  pageSize: 100,
  total: 0
})

const formatPrice = (value) => {
  return parseFloat(value || 0).toFixed(2)
}

const formatChangePercent = (value) => {
  return parseFloat(value || 0).toFixed(2)
}

const formatVolume = (value) => {
  const num = parseFloat(value || 0)
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(2)}亿`
  } else if (num >= 10000) {
    return `${(num / 10000).toFixed(2)}万`
  }
  return num.toFixed(0)
}

const formatAmount = (value) => {
  const num = parseFloat(value || 0)
  if (num >= 100000000) {
    return `¥${(num / 100000000).toFixed(2)}亿`
  } else if (num >= 10000) {
    return `¥${(num / 10000).toFixed(2)}万`
  }
  return `¥${num.toFixed(2)}`
}

const getPriceColor = (row) => {
  if (row.change > 0) return '#F56C6C'
  if (row.change < 0) return '#67C23A'
  return '#909399'
}

// 排序方法
const sortByPrice = (a, b) => {
  return (a.last_price || 0) - (b.last_price || 0)
}

const sortByChange = (a, b) => {
  return (a.change || 0) - (b.change || 0)
}

const sortByChangePercent = (a, b) => {
  return (a.change_percent || 0) - (b.change_percent || 0)
}

const sortByVolume = (a, b) => {
  return (a.volume || 0) - (b.volume || 0)
}

const sortByAmount = (a, b) => {
  return (a.amount || 0) - (b.amount || 0)
}

const fetchSecurities = async () => {
  loading.value = true
  try {
    const params = {
      limit: pagination.value.pageSize,
      offset: (pagination.value.page - 1) * pagination.value.pageSize
    }
    
    if (filterMarket.value) {
      params.market = filterMarket.value
    }
    
    const response = await securityApi.getList(params)
    const securities = response.items || []
    
    // 获取所有证券代码
    const symbols = securities.map(s => s.symbol)
    
    // 分批获取实时行情（每批50个，避免URL过长）
    const quotesMap = {}
    if (symbols.length > 0) {
      const batchSize = 50
      for (let i = 0; i < symbols.length; i += batchSize) {
        const batch = symbols.slice(i, i + batchSize)
        const symbolsStr = batch.join(',')
        try {
          const quotes = await marketApi.getQuote(symbolsStr)
          if (Array.isArray(quotes)) {
            quotes.forEach(quote => {
              quotesMap[quote.symbol] = quote
            })
          }
        } catch (error) {
          console.warn(`获取批次 ${i / batchSize + 1} 行情失败:`, error)
        }
      }
    }
    
    // 合并数据
    tableData.value = securities.map(security => {
      const quote = quotesMap[security.symbol] || {}
      return {
        symbol: security.symbol,
        name: security.name || quote.name || '',
        market: security.market,
        last_price: quote.last_price || 0,
        open: quote.open || 0,
        high: quote.high || 0,
        low: quote.low || 0,
        pre_close: quote.pre_close || 0,
        volume: quote.volume || 0,
        amount: quote.amount || 0,
        change: quote.change || 0,
        change_percent: quote.change_percent || quote.change_pct || 0
      }
    })
    
    pagination.value.total = response.total || 0
  } catch (error) {
    console.error('获取证券列表失败:', error)
    ElMessage.error('获取证券列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    fetchSecurities()
    return
  }
  
  loading.value = true
  try {
    const securities = await securityApi.search(searchKeyword.value, 200)
    
    if (securities.length > 0) {
      const symbols = securities.map(s => s.symbol)
      
      // 分批获取行情
      const quotesMap = {}
      const batchSize = 50
      for (let i = 0; i < symbols.length; i += batchSize) {
        const batch = symbols.slice(i, i + batchSize)
        const symbolsStr = batch.join(',')
        try {
          const quotes = await marketApi.getQuote(symbolsStr)
          if (Array.isArray(quotes)) {
            quotes.forEach(quote => {
              quotesMap[quote.symbol] = quote
            })
          }
        } catch (error) {
          console.warn(`获取批次 ${i / batchSize + 1} 行情失败:`, error)
        }
      }
      
      tableData.value = securities.map(security => {
        const quote = quotesMap[security.symbol] || {}
        return {
          symbol: security.symbol,
          name: security.name || quote.name || '',
          market: security.market,
          last_price: quote.last_price || 0,
          open: quote.open || 0,
          high: quote.high || 0,
          low: quote.low || 0,
          pre_close: quote.pre_close || 0,
          volume: quote.volume || 0,
          amount: quote.amount || 0,
          change: quote.change || 0,
          change_percent: quote.change_percent || quote.change_pct || 0
        }
      })
      
      pagination.value.total = securities.length
      pagination.value.page = 1
    } else {
      tableData.value = []
      pagination.value.total = 0
    }
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.value.page = 1
  if (searchKeyword.value) {
    searchKeyword.value = ''
  }
  fetchSecurities()
}

const handlePageChange = () => {
  if (searchKeyword.value) {
    handleSearch()
  } else {
    fetchSecurities()
  }
}

const handleRowDoubleClick = (row) => {
  router.push(`/security/${row.symbol}`)
}

const refreshData = () => {
  if (searchKeyword.value) {
    handleSearch()
  } else {
    fetchSecurities()
  }
  ElMessage.success('数据已刷新')
}

const updateFromQMT = async () => {
  updating.value = true
  updateProgress.value = 0
  try {
    const result = await securityApi.update(filterMarket.value || null)
    if (result.code === 0) {
      const taskId = result.data.task_id
      ElMessage.info('任务已提交，正在后台处理...')
      
      // 轮询任务状态
      const checkTaskStatus = async () => {
        try {
          const { taskApi } = await import('../api/task')
          const statusResult = await taskApi.getStatus(taskId)
          
          if (statusResult.code === 0) {
            const taskData = statusResult.data
            
            // 更新进度
            if (taskData.progress !== undefined) {
              updateProgress.value = taskData.progress
            }
            
            if (taskData.state === 'SUCCESS') {
              updating.value = false
              updateProgress.value = 100
              const result = taskData.result || {}
              ElMessage.success(
                `更新完成！总计: ${result.total || 0}, 新增: ${result.created || 0}, 更新: ${result.updated || 0}${result.errors ? `, 错误: ${result.errors}` : ''}`
              )
              // 更新后刷新列表
              await fetchSecurities()
            } else if (taskData.state === 'FAILURE') {
              updating.value = false
              updateProgress.value = 0
              ElMessage.error('更新失败: ' + (taskData.error || '未知错误'))
            } else if (taskData.state === 'PROGRESS') {
              // 继续轮询
              setTimeout(checkTaskStatus, 2000)
            } else {
              // PENDING或其他状态，继续轮询
              setTimeout(checkTaskStatus, 1000)
            }
          }
        } catch (error) {
          console.error('查询任务状态失败:', error)
          setTimeout(checkTaskStatus, 2000)
        }
      }
      
      // 开始轮询
      setTimeout(checkTaskStatus, 1000)
    } else {
      updating.value = false
      updateProgress.value = 0
      ElMessage.error(result.message || '提交任务失败')
    }
  } catch (error) {
    updating.value = false
    updateProgress.value = 0
    console.error('更新失败:', error)
    ElMessage.error('更新失败: ' + (error.message || '未知错误'))
  }
}

onMounted(() => {
  fetchSecurities()
})
</script>

<style scoped>
.security-list {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.symbol-link {
  color: #409EFF;
  cursor: pointer;
  font-weight: 500;
}

.symbol-link:hover {
  text-decoration: underline;
}
</style>

