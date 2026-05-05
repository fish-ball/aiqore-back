<template>
  <div class="security-list">
    <div class="page-header">
      <h2>证券列表</h2>
    </div>

    <!-- 筛选条：左侧快捷选项 + 右侧搜索与操作，底部可展开详细板块 -->
    <el-card class="filter-card">
      <div class="filter-bar">
        <div class="filter-bar-row">
          <div class="filter-bar-left">
            <el-button
              class="quick-filter-btn"
              size="small"
              disabled
              plain
            >
              自选
            </el-button>
            <el-button
              :type="isQuickFilterActive('all') ? 'primary' : 'default'"
              :plain="!isQuickFilterActive('all')"
              size="small"
              class="quick-filter-btn"
              @click="handleQuickFilter('all')"
            >
              A股
            </el-button>
            <el-button
              :type="isQuickFilterActive('SH') ? 'primary' : 'default'"
              :plain="!isQuickFilterActive('SH')"
              size="small"
              class="quick-filter-btn"
              @click="handleQuickFilter('SH')"
            >
              上证
            </el-button>
            <el-button
              :type="isQuickFilterActive('SZ') ? 'primary' : 'default'"
              :plain="!isQuickFilterActive('SZ')"
              size="small"
              class="quick-filter-btn"
              @click="handleQuickFilter('SZ')"
            >
              深证
            </el-button>
            <el-button
              :type="isQuickFilterActive('创业板') ? 'primary' : 'default'"
              :plain="!isQuickFilterActive('创业板')"
              size="small"
              class="quick-filter-btn"
              @click="handleQuickFilter('创业板')"
            >
              创业板
            </el-button>
            <el-button
              :type="isQuickFilterActive('科创板') ? 'primary' : 'default'"
              :plain="!isQuickFilterActive('科创板')"
              size="small"
              class="quick-filter-btn"
              @click="handleQuickFilter('科创板')"
            >
              科创板
            </el-button>
          </div>
          <div class="filter-bar-right">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索代码或名称"
              class="search-input"
              size="small"
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
              @click="openUpdateDialog"
              :loading="updating"
              :disabled="updating || !dataSourceStore.currentId"
              v-if="!activeSector"
            >
              <el-icon><IconDownload /></el-icon>
              {{ updating ? '提交中...' : '从数据源更新' }}
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="updateSectorFromDataSource"
              :loading="updating"
              :disabled="updating || !dataSourceStore.currentId"
              v-if="activeSector"
            >
              <el-icon><IconDownload /></el-icon>
              {{ updating ? '同步中...' : '同步该板块' }}
            </el-button>
            <el-button type="primary" size="small" @click="refreshData">
              <el-icon><IconRefresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
        <span class="filter-bar-toggle" @click="filterPanelExpanded = !filterPanelExpanded">
          {{ filterPanelExpanded ? '折叠' : '展开' }}
          <el-icon class="filter-bar-toggle-icon"><IconArrowDown /></el-icon>
        </span>
      </div>
      <div class="filter-panel-body" v-show="filterPanelExpanded">
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
                :key="sector.alias"
                :type="activeSector === sector.alias ? 'primary' : 'default'"
                :plain="activeSector !== sector.alias"
                size="small"
                @click="handleSectorChange(sector.alias)"
                class="filter-btn"
              >
                {{ sector.name }}
                <span class="sector-count">({{ sector.security_count || 0 }})</span>
              </el-button>
            </div>
          </div>
        </template>
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
            <el-button
              :type="filterMarket === 'BJ' ? 'primary' : 'default'"
              :plain="filterMarket !== 'BJ'"
              size="small"
              @click="handleMarketChange('BJ')"
              class="filter-btn"
            >
              北京
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 整体从数据源更新：弹窗输入参数后下发 Celery 任务 -->
    <el-dialog
      v-model="updateDialogVisible"
      title="从数据源更新证券列表"
      width="420px"
      @close="resetUpdateForm"
    >
      <el-form :model="updateForm" label-width="80px">
        <el-form-item label="市场">
          <el-select v-model="updateForm.market" placeholder="不限制则更新全部" clearable style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="上海" value="SH" />
            <el-option label="深圳" value="SZ" />
          </el-select>
        </el-form-item>
        <el-form-item label="板块">
          <el-input v-model="updateForm.sector" placeholder="可选，指定则只同步该板块" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="submitUpdateTask">提交后台更新</el-button>
      </template>
    </el-dialog>

    <el-card class="table-card">
      <el-table
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
        @row-dblclick="handleRowDoubleClick"
        :default-sort="{ prop: 'last_price', order: 'descending' }"
        stripe
        height="600"
      >
        <el-table-column prop="code" label="代码" width="120" sortable="custom" fixed="left">
          <template #default="scope">
            <span class="symbol-link">{{ scope.row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="150" sortable="custom" fixed="left">
          <template #default="scope">
            {{ scope.row.name || scope.row.code || '--' }}
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="80" sortable="custom">
          <template #default="scope">
            <el-tag
              :type="scope.row.market === 'SH' ? 'success' : scope.row.market === 'BJ' ? 'info' : 'warning'"
              size="small"
            >
              {{
                scope.row.market === 'SH'
                  ? '上海'
                  : scope.row.market === 'BJ'
                    ? '北京'
                    : scope.row.market === 'SZ'
                      ? '深圳'
                      : scope.row.market || '—'
              }}
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
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              link
              size="small"
              :loading="updatingSymbol === scope.row.code"
              :disabled="!dataSourceStore.currentId"
              @click="updateOneSecurity(scope.row)"
            >
              更新
            </el-button>
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
        class="pagination-bar"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@iottest/vue-core/src/libs/api'
import { useDataSourceStore } from '../../stores/dataSource'
import type { Pagination } from '../../types/common'
import type { Sector, SectorCategoryGrouped } from '../../types/sector'
import type { Security, SecurityQuote, SecurityTableRow } from '../../types/security'

const securityListResource = api('instrument/list')
const securitySearchResource = api('instrument/search')
const securityBySymbolResource = api('instrument')
const securityUpdateResource = api('instrument/update')
const securityUpdateOneResource = api('instrument/update-one')
const marketQuoteResource = api('market/quote')
const sectorListResource = api('sector/list')

/** 板块分类排序权重（与其它处逻辑保持一致） */
const CATEGORY_ORDER: Record<string, number> = {
  股票: 1,
  基金: 2,
  ETF: 2,
  债券: 3,
  指数: 4,
  期货: 5,
  期权: 6
}

const router = useRouter()
const route = useRoute()
const dataSourceStore = useDataSourceStore()

// 从路由参数获取板块
/** 与路由 query.market 对齐（SH/SZ/BJ），用于交易所页跳转筛选 */
function normalizeMarketQuery(raw: unknown): string {
  const m = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
  return ['SH', 'SZ', 'BJ'].includes(m) ? m : ''
}

/** 路由 query.exchange_code，来自交易所页跳转（规范代码如 SSE） */
function normalizeExchangeCodeQuery(raw: unknown): string | undefined {
  if (raw == null || raw === '') return undefined
  const s = String(raw).trim().toUpperCase()
  return /^[A-Z][A-Z0-9]{1,31}$/.test(s) ? s : undefined
}

const activeSector = ref<string>((route.query.sector as string) || '')
const loading = ref(false)
const updating = ref(false)
const tableData = ref<SecurityTableRow[]>([])
const filterMarket = ref<string>(normalizeMarketQuery(route.query.market))
const filterExchangeCode = ref<string | undefined>(normalizeExchangeCodeQuery(route.query.exchange_code))
const searchKeyword = ref<string>('')
const sectors = ref<Sector[]>([])
const filterPanelExpanded = ref(false)
const updatingSymbol = ref<string | null>(null)
const updateDialogVisible = ref(false)
const updateForm = ref<{ market: string; sector: string }>({ market: '', sector: '' })

// 按分类分组板块
const sectorsByCategory = computed<SectorCategoryGrouped>(() => {
  const grouped: SectorCategoryGrouped = {}
  sectors.value.forEach((sector) => {
    const category = sector.category || '其他'
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push(sector)
  })
  return Object.keys(grouped)
    .sort((a, b) => {
      const orderA = CATEGORY_ORDER[a] ?? 99
      const orderB = CATEGORY_ORDER[b] ?? 99
      return orderA - orderB
    })
    .reduce((acc: SectorCategoryGrouped, category) => {
      const list = grouped[category]!
      acc[category] = list.sort((a, b) => (b.security_count || 0) - (a.security_count || 0))
      return acc
    }, {} as SectorCategoryGrouped)
})

const pagination = ref<Pagination>({
  page: 1,
  pageSize: 100,
  total: 0
})

const formatPrice = (value: number | string | null | undefined) => {
  return Number(value ?? 0).toFixed(2)
}

const formatChangePercent = (value: number | string | null | undefined) => {
  return Number(value ?? 0).toFixed(2)
}

const formatVolume = (value: number | string | null | undefined) => {
  const num = Number(value ?? 0)
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(2)}亿`
  } else if (num >= 10000) {
    return `${(num / 10000).toFixed(2)}万`
  }
  return num.toFixed(0)
}

const formatAmount = (value: number | string | null | undefined) => {
  const num = Number(value ?? 0)
  if (num >= 100000000) {
    return `¥${(num / 100000000).toFixed(2)}亿`
  } else if (num >= 10000) {
    return `¥${(num / 10000).toFixed(2)}万`
  }
  return `¥${num.toFixed(2)}`
}

const getPriceColor = (row: Pick<SecurityTableRow, 'change'>) => {
  if (row.change > 0) return '#F56C6C'
  if (row.change < 0) return '#67C23A'
  return '#909399'
}

// 排序方法
const sortByPrice = (a: SecurityTableRow, b: SecurityTableRow) => {
  return (a.last_price || 0) - (b.last_price || 0)
}

const sortByChange = (a: SecurityTableRow, b: SecurityTableRow) => {
  return (a.change || 0) - (b.change || 0)
}

const sortByChangePercent = (a: SecurityTableRow, b: SecurityTableRow) => {
  return (a.change_percent || 0) - (b.change_percent || 0)
}

const sortByVolume = (a: SecurityTableRow, b: SecurityTableRow) => {
  return (a.volume || 0) - (b.volume || 0)
}

const sortByAmount = (a: SecurityTableRow, b: SecurityTableRow) => {
  return (a.amount || 0) - (b.amount || 0)
}

// 获取板块列表
const fetchSectors = async () => {
  try {
    const resp = await sectorListResource.get({}, { is_active: 1, page: 1, page_size: 500 })
    const response = resp.data as { results?: Sector[] }
    const items = response?.results || []
    sectors.value = items as Sector[]
    // 按分类排序，主要板块在前
    sectors.value.sort((a, b) => {
      const orderA = CATEGORY_ORDER[a.category ?? ''] ?? 99
      const orderB = CATEGORY_ORDER[b.category ?? ''] ?? 99
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
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    }
    
    if (filterMarket.value) {
      params.market = filterMarket.value
    }

    if (filterExchangeCode.value != null) {
      params.exchange_code = filterExchangeCode.value
    }

    // 如果选择了板块，添加板块参数
    if (activeSector.value) {
      params.sector = activeSector.value
    }
    
    const listResp = await securityListResource.get({}, params)
    const response = listResp.data as { results?: Security[]; count?: number }
    const securities = response.results || []
    
    // 获取所有证券代码
    const codes = securities.map((s) => s.code)

    // 分批获取实时行情（每批50个，避免URL过长）
    const quotesMap: Record<string, SecurityQuote> = {}
    if (codes.length > 0) {
      const batchSize = 50
      for (let i = 0; i < codes.length; i += batchSize) {
        const batch = codes.slice(i, i + batchSize)
        const symbolsStr = batch.join(',')
        try {
          const qResp = await marketQuoteResource.get({}, { symbols: symbolsStr })
          const quotes = qResp.data as SecurityQuote[] | undefined
          if (Array.isArray(quotes)) {
            quotes.forEach((quote) => {
              if (quote.symbol) quotesMap[quote.symbol] = quote
            })
          }
        } catch (error) {
          console.warn(`获取批次 ${i / batchSize + 1} 行情失败:`, error)
        }
      }
    }
    
    // 合并数据
    tableData.value = securities.map((security) => {
      const quote: SecurityQuote = quotesMap[security.code] || {}
      return {
        code: security.code,
        name: security.name || quote.name || '',
        market: (security.market || '') as SecurityTableRow['market'],
        exchange_code: security.exchange_code,
        exchange: security.exchange,
        asset_class: security.asset_class,
        instrument_type: security.instrument_type,
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
    
    pagination.value.total = response.count ?? 0
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
    const sResp = await securitySearchResource.get({}, { keyword: searchKeyword.value, limit: 200 })
    const securities = sResp.data as Security[]
    
    if (securities.length > 0) {
      const codes = securities.map((s) => s.code)

      // 分批获取行情
      const quotesMap: Record<string, SecurityQuote> = {}
      const batchSize = 50
      for (let i = 0; i < codes.length; i += batchSize) {
        const batch = codes.slice(i, i + batchSize)
        const symbolsStr = batch.join(',')
        try {
          const qResp = await marketQuoteResource.get({}, { symbols: symbolsStr })
          const quotes = qResp.data as SecurityQuote[] | undefined
          if (Array.isArray(quotes)) {
            quotes.forEach((quote) => {
              if (quote.symbol) quotesMap[quote.symbol] = quote
            })
          }
        } catch (error) {
          console.warn(`获取批次 ${i / batchSize + 1} 行情失败:`, error)
        }
      }
      
      tableData.value = securities.map<SecurityTableRow>((security) => {
        const quote: SecurityQuote = quotesMap[security.code] || {}
        return {
          code: security.code,
          name: security.name || quote.name || '',
          market: (security.market || '') as SecurityTableRow['market'],
          exchange_code: security.exchange_code,
          exchange: security.exchange,
          asset_class: security.asset_class,
          instrument_type: security.instrument_type,
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

// 根据显示名或名称查找板块的 name（用于快捷筛选与下方板块选项等价）
const getSectorNameByLabel = (label: string) => {
  let s = sectors.value.find((item) => item.name === label || item.alias === label)
  if (!s) {
    s = sectors.value.find((item) => {
      const dn = item.name || item.alias || ''
      return dn.includes(label)
    })
  }
  return s ? s.alias : null
}

// 当前是否处于某快捷筛选项（与下方板块筛选项一致：A股=沪深A股，上证=上证A股，深证=深证A股）
const isQuickFilterActive = (type: string) => {
  const labelMap: Record<string, string> = { all: '沪深A股', SH: '上证A股', SZ: '深证A股' }
  const label = labelMap[type]
  if (label) {
    const sectorName = getSectorNameByLabel(label)
    return sectorName ? activeSector.value === sectorName : false
  }
  if (type === '创业板' || type === '科创板') {
    const sectorName = getSectorNameByLabel(type)
    return sectorName ? activeSector.value === sectorName : false
  }
  return false
}

// 快捷筛选：自选留白；A股=沪深A股，上证=上证A股，深证=深证A股，其余=对应板块
const handleQuickFilter = (type: string) => {
  if (type === '自选') return
  const labelMap: Record<string, string> = { all: '沪深A股', SH: '上证A股', SZ: '深证A股' }
  const label = labelMap[type] || (type === '创业板' || type === '科创板' ? type : null)
  if (label) {
    const sectorName = getSectorNameByLabel(label)
    if (sectorName) {
      activeSector.value = sectorName
      filterMarket.value = ''
      filterExchangeCode.value = undefined
      pagination.value.page = 1
      if (searchKeyword.value) searchKeyword.value = ''
      fetchSecurities()
    }
  }
}

const handleSectorChange = (sectorName: string) => {
  activeSector.value = sectorName
  filterExchangeCode.value = undefined
  pagination.value.page = 1
  if (searchKeyword.value) {
    searchKeyword.value = ''
  }
  fetchSecurities()
}

const handleMarketChange = (market: string) => {
  filterMarket.value = market
  filterExchangeCode.value = undefined
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

const handleRowDoubleClick = (row: SecurityTableRow) => {
  router.push({
    name: 'admin-instrument-detail',
    params: { symbol: row.code },
  })
}

const refreshData = () => {
  if (searchKeyword.value) {
    handleSearch()
  } else {
    fetchSecurities()
  }
  ElMessage.success('数据已刷新')
}

const sourceType = () => dataSourceStore.currentDataSource?.source_type || 'qmt'
const sourceId = () => dataSourceStore.currentId

function resetUpdateForm() {
  updateForm.value = { market: '', sector: '' }
}

function openUpdateDialog() {
  if (!dataSourceStore.currentId) {
    ElMessage.warning('请先在顶栏选择当前数据源')
    return
  }
  updateForm.value = { market: filterMarket.value || '', sector: '' }
  updateDialogVisible.value = true
}

const submitUpdateTask = async () => {
  updating.value = true
  try {
    const body: Record<string, unknown> = { source_type: sourceType() }
    if (updateForm.value.market) body.market = updateForm.value.market
    if (updateForm.value.sector) body.sector = updateForm.value.sector
    const sid = sourceId()
    if (sid != null) body.source_id = Number(sid)
    const uResp = await securityUpdateResource.post({}, body)
    const result = uResp.data as { task_id?: string }
    if (result && result.task_id) {
      updateDialogVisible.value = false
      ElMessage.success('任务已提交，正在后台处理')
    }
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : '未知错误'
    if (!msg.includes('正在运行中')) {
      ElMessage.error('提交失败: ' + msg)
    }
  } finally {
    updating.value = false
  }
}

const updateSectorFromDataSource = async () => {
  if (!activeSector.value) return
  if (!dataSourceStore.currentId) {
    ElMessage.warning('请先在顶栏选择当前数据源')
    return
  }
  updating.value = true
  try {
    const body: Record<string, unknown> = { source_type: sourceType(), sector: activeSector.value }
    if (filterMarket.value) body.market = filterMarket.value
    const sid = sourceId()
    if (sid != null) body.source_id = Number(sid)
    const uResp = await securityUpdateResource.post({}, body)
    const result = uResp.data as { task_id?: string }
    if (result && result.task_id) {
      ElMessage.success('任务已提交，正在后台处理')
      setTimeout(() => {
        fetchSecurities()
        fetchSectors()
      }, 2000)
    }
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : '未知错误'
    if (!msg.includes('正在运行中')) {
      ElMessage.error('同步失败: ' + msg)
    }
  } finally {
    updating.value = false
  }
}

const updateOneSecurity = async (row: SecurityTableRow) => {
  if (!dataSourceStore.currentId) {
    ElMessage.warning('请先在顶栏选择当前数据源')
    return
  }
  updatingSymbol.value = row.code
  try {
    const oneBody: Record<string, unknown> = { code: row.code, source_type: sourceType() }
    const sidOne = sourceId()
    if (sidOne != null) oneBody.source_id = Number(sidOne)
    await securityUpdateOneResource.post({}, oneBody)
    ElMessage.success('已更新 ' + (row.name || row.code))
    const idx = tableData.value.findIndex((r) => r.code === row.code)
    if (idx >= 0) {
      const dResp = await securityBySymbolResource.get({ id: row.code }, {})
      const detail = dResp.data as { name?: string; market?: string } | null
      if (detail) {
        const prev = tableData.value[idx]!
        const next: SecurityTableRow = {
          ...prev,
          name: detail.name ?? prev.name,
          market: (detail.market ?? prev.market) as SecurityTableRow['market']
        }
        tableData.value[idx] = next
      }
    }
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : '未知错误'
    ElMessage.error('更新失败: ' + msg)
  } finally {
    updatingSymbol.value = null
  }
}

watch(
  () => [route.query.market, route.query.sector, route.query.exchange_code] as const,
  ([m, s, ex]) => {
    filterMarket.value = normalizeMarketQuery(m)
    activeSector.value = typeof s === 'string' ? s : ''
    filterExchangeCode.value = normalizeExchangeCodeQuery(ex)
    pagination.value.page = 1
    if (searchKeyword.value) searchKeyword.value = ''
    fetchSecurities()
  },
)

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
  margin-bottom: 8px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.filter-card {
  margin-bottom: 8px;
  overflow: hidden;
}

.filter-card :deep(.el-card__body) {
  padding: 6px 8px;
}

.filter-bar {
  position: relative;
  padding: 4px 8px;
  background: #fff;
}

.filter-bar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-bar-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.filter-bar-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-right: 52px;
}

.filter-bar-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: #409EFF;
  cursor: pointer;
  user-select: none;
}

.filter-bar-toggle:hover {
  color: #66b1ff;
}

.filter-bar-toggle-icon {
  font-size: 12px;
}

.filter-bar-toggle-icon {
  font-size: 12px;
}

.quick-filter-btn {
  margin: 0;
  padding: 4px 10px;
  font-size: 12px;
  height: 26px;
  border-radius: 4px;
}

.filter-panel-body {
  padding: 6px 8px;
  border-top: 1px solid #EBEEF5;
}

.filter-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-row-actions {
  align-items: center;
  padding-top: 4px;
  border-top: 1px solid #EBEEF5;
}

.filter-label {
  min-width: 52px;
  font-size: 12px;
  color: #606266;
  font-weight: 500;
  padding-top: 4px;
  flex-shrink: 0;
}

.filter-options {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.filter-btn {
  margin: 0;
  padding: 4px 10px;
  font-size: 12px;
  height: 26px;
  border-radius: 4px;
}

.filter-btn .sector-count {
  margin-left: 2px;
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
  width: 200px;
}

.symbol-link {
  color: #409EFF;
  cursor: pointer;
  font-weight: 500;
}

.symbol-link:hover {
  text-decoration: underline;
}

.table-card {
  margin-top: 8px;
}

.pagination-bar {
  margin-top: 12px;
  justify-content: flex-end;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .filter-bar-row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar-right {
    width: 100%;
    flex-wrap: wrap;
  }

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

