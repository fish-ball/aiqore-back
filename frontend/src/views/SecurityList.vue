<template>
  <div class="security-list">
    <div class="page-header">
      <h2>证券列表</h2>
    </div>

    <!-- 筛选器区域 -->
    <el-card class="filter-card">
      <!-- 板块筛选（按分类分组，每个分类一行） -->
      <div class="filter-row" v-if="Object.keys(sectorsByCategory).length > 0">
        <div class="filter-label">板块：</div>
        <div class="filter-options">
          <el-button
            :type="activeSector === '' ? 'primary' : 'default'"
            :plain="activeSector !== ''"
            size="small"
            @click="handleSectorChange('')"
            class="filter-btn"
          >
            全部
          </el-button>
        </div>
      </div>
      <template v-for="(sectorsList, category) in sectorsByCategory" :key="category">
        <div class="filter-row">
          <div class="filter-label">{{ category || '其他' }}：</div>
          <div class="filter-options">
            <el-button
              v-for="sector in sectorsList"
              :key="sector.name"
              :type="activeSector === sector.name ? 'primary' : 'default'"
              :plain="activeSector !== sector.name"
              size="small"
              @click="handleSectorChange(sector.name)"
              class="filter-btn"
            >
              {{ sector.display_name || sector.name }}
              <span class="sector-count">({{ sector.security_count || 0 }})</span>
            </el-button>
          </div>
        </div>
      </template>

      <!-- 第二行：市场、搜索和操作按钮 -->
      <div class="filter-row filter-row-actions">
        <div class="filter-label">市场：</div>
        <div class="filter-options">
          <el-button
            :type="filterMarket === '' ? 'primary' : 'default'"
            :plain="filterMarket !== ''"
            size="small"
            @click="handleMarketChange('')"
            class="filter-btn"
          >
            全部
          </el-button>
          <el-button
            :type="filterMarket === 'SH' ? 'primary' : 'default'"
            :plain="filterMarket !== 'SH'"
            size="small"
            @click="handleMarketChange('SH')"
            class="filter-btn"
          >
            上海
          </el-button>
          <el-button
            :type="filterMarket === 'SZ' ? 'primary' : 'default'"
            :plain="filterMarket !== 'SZ'"
            size="small"
            @click="handleMarketChange('SZ')"
            class="filter-btn"
          >
            深圳
          </el-button>
        </div>
        <div class="filter-actions">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索代码或名称"
            class="search-input"
            @keyup.enter="handleSearch"
            clearable
          >
            <template #append>
              <el-button @click="handleSearch" size="small">搜索</el-button>
            </template>
          </el-input>
          <el-button 
            type="success" 
            size="small"
            @click="updateFromQMT" 
            :loading="updating" 
            :disabled="updating"
            v-if="!activeSector"
          >
            <el-icon><Download /></el-icon>
            {{ updating ? (updateProgress > 0 ? `更新中 ${updateProgress}%` : '更新中...') : '从QMT更新' }}
          </el-button>
          <el-button 
            type="success" 
            size="small"
            @click="updateSectorFromQMT" 
            :loading="updating" 
            :disabled="updating"
            v-if="activeSector"
          >
            <el-icon><Download /></el-icon>
            {{ updating ? '同步中...' : '同步该板块' }}
          </el-button>
          <el-button type="primary" size="small" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

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
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { securityApi } from '../api/security'
import { marketApi } from '../api/market'
import sectorApi from '../api/sector.js'

const router = useRouter()
const route = useRoute()

// 从路由参数获取板块
const activeSector = ref(route.query.sector || '')
const loading = ref(false)
const updating = ref(false)
const updateProgress = ref(0)
const tableData = ref([])
const filterMarket = ref('')
const searchKeyword = ref('')
const sectors = ref([])

// 按分类分组板块
const sectorsByCategory = computed(() => {
  const grouped = {}
  sectors.value.forEach(sector => {
    const category = sector.category || '其他'
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push(sector)
  })
  // 按分类排序
  const categoryOrder = { '股票': 1, '基金': 2, 'ETF': 2, '债券': 3, '指数': 4, '期货': 5, '期权': 6 }
  return Object.keys(grouped)
    .sort((a, b) => {
      const orderA = categoryOrder[a] || 99
      const orderB = categoryOrder[b] || 99
      return orderA - orderB
    })
    .reduce((acc, category) => {
      acc[category] = grouped[category].sort((a, b) => (b.security_count || 0) - (a.security_count || 0))
      return acc
    }, {})
})

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

// 获取板块列表
const fetchSectors = async () => {
  try {
    const response = await sectorApi.getList({ is_active: 1 })
    sectors.value = response.items || []
    // 按分类排序，主要板块在前
    sectors.value.sort((a, b) => {
      const categoryOrder = { '股票': 1, '基金': 2, 'ETF': 2, '债券': 3, '指数': 4, '期货': 5, '期权': 6 }
      const orderA = categoryOrder[a.category] || 99
      const orderB = categoryOrder[b.category] || 99
      if (orderA !== orderB) return orderA - orderB
      return (b.security_count || 0) - (a.security_count || 0)
    })
  } catch (error) {
    console.error('获取板块列表失败:', error)
  }
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
    
    // 如果选择了板块，添加板块参数
    if (activeSector.value) {
      params.sector = activeSector.value
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

const handleSectorChange = (sectorName) => {
  activeSector.value = sectorName
  pagination.value.page = 1
  if (searchKeyword.value) {
    searchKeyword.value = ''
  }
  fetchSecurities()
}

const handleMarketChange = (market) => {
  filterMarket.value = market
  pagination.value.page = 1
  if (searchKeyword.value) {
    searchKeyword.value = ''
  }
  fetchSecurities()
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
      ElMessage.success('任务已提交，正在后台处理...')
      // 任务在后台异步执行，稍后刷新列表
      setTimeout(async () => {
        await fetchSecurities()
        updating.value = false
        updateProgress.value = 0
      }, 3000)
    } else {
      updating.value = false
      updateProgress.value = 0
      ElMessage.error(result.message || '提交任务失败')
    }
  } catch (error) {
    updating.value = false
    updateProgress.value = 0
    console.error('更新失败:', error)
    // 错误消息已经在响应拦截器中显示，这里不需要重复显示
    // 但如果是任务冲突，已经显示为warning，这里可以不再显示
    if (!error.message || !error.message.includes('正在运行中')) {
      ElMessage.error('更新失败: ' + (error.message || '未知错误'))
    }
  }
}

const updateSectorFromQMT = async () => {
  if (!activeSector.value) return
  
  updating.value = true
  try {
    const result = await securityApi.update(filterMarket.value || null, activeSector.value)
    if (result.code === 0) {
      ElMessage.success('任务已提交，正在后台处理...')
      setTimeout(async () => {
        await fetchSecurities()
        await fetchSectors() // 刷新板块列表以更新证券数量
        updating.value = false
      }, 3000)
    } else {
      updating.value = false
      ElMessage.error(result.message || '提交任务失败')
    }
  } catch (error) {
    updating.value = false
    console.error('同步板块失败:', error)
    if (!error.message || !error.message.includes('正在运行中')) {
      ElMessage.error('同步失败: ' + (error.message || '未知错误'))
    }
  }
}

onMounted(() => {
  fetchSectors()
  fetchSecurities()
})
</script>

<style scoped>
.security-list {
  padding: 0;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filter-card {
  margin-bottom: 16px;
  padding: 12px 16px;
}

.filter-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-row-actions {
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #EBEEF5;
}

.filter-label {
  min-width: 60px;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  padding-top: 6px;
  flex-shrink: 0;
}

.filter-options {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.filter-btn {
  margin: 0;
  padding: 6px 12px;
  font-size: 12px;
  height: 28px;
  border-radius: 4px;
}

.filter-btn .sector-count {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.8;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.search-input {
  width: 240px;
}

.symbol-link {
  color: #409EFF;
  cursor: pointer;
  font-weight: 500;
}

.symbol-link:hover {
  text-decoration: underline;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
  }
  
  .filter-label {
    margin-bottom: 8px;
    padding-top: 0;
  }
  
  .filter-actions {
    margin-left: 0;
    margin-top: 12px;
    width: 100%;
    flex-wrap: wrap;
  }
  
  .search-input {
    width: 100%;
  }
}
</style>

