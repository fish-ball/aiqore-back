<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">
          <el-icon><IconTrendCharts /></el-icon>
          AIQore - 个人投资管理系统
        </h1>
        <div class="header-actions">
          <el-select
            :model-value="dataSourceStore.currentId"
            placeholder="当前数据源"
            clearable
            filterable
            style="width: 180px; margin-right: 12px"
            :loading="dataSourceStore.loading"
            @update:model-value="dataSourceStore.setCurrent"
          >
            <el-option
              v-for="item in dataSourceStore.list"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            >
              <span>{{ item.name }}</span>
              <span class="data-source-type-tag">{{ sourceTypeLabel(item.source_type) }}</span>
            </el-option>
          </el-select>
          <el-autocomplete
            v-model="searchKeyword"
            :fetch-suggestions="searchSecurities"
            :trigger-on-focus="false"
            placeholder="搜索证券代码、名称或拼音"
            style="width: 300px; margin-right: 12px"
            @select="handleSelectSecurity"
            clearable
          >
            <template #default="{ item }">
              <div class="search-item">
                <span class="symbol">{{ item.code }}</span>
                <span class="name">{{ item.name }}</span>
                <span class="market">{{ item.market }}</span>
              </div>
            </template>
          </el-autocomplete>
          <el-button type="primary" @click="refreshData">
            <el-icon><IconRefresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-header>
    
    <el-container class="app-body">
      <el-aside width="200px" class="app-sidebar">
        <el-scrollbar class="sidebar-scrollbar" height="100%">
          <el-menu
            :default-active="activeMenu"
            :default-openeds="['account-trade', 'instruments', 'basic-info']"
            router
            class="sidebar-menu"
          >
            <el-menu-item index="/dashboard">
              <el-icon><IconOdometer /></el-icon>
              <span>仪表盘</span>
            </el-menu-item>
            <el-sub-menu index="account-trade">
              <template #title>
                <el-icon><Money /></el-icon>
                <span>账户交易</span>
              </template>
              <el-menu-item index="/account">账户管理</el-menu-item>
              <el-menu-item index="/position">持仓管理</el-menu-item>
              <el-menu-item index="/trade">交易记录</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="instruments">
              <template #title>
                <el-icon><Goods /></el-icon>
                <span>合约标的</span>
              </template>
              <el-menu-item index="/instruments/stocks">股票</el-menu-item>
              <el-menu-item index="/instruments/etf-options">ETF期权</el-menu-item>
              <el-menu-item index="/instruments/futures">期货</el-menu-item>
              <el-menu-item index="/instruments/future-options">期货期权</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="basic-info">
              <template #title>
                <el-icon><FolderOpened /></el-icon>
                <span>基础信息</span>
              </template>
              <el-menu-item index="/data-sources">数据源连接</el-menu-item>
              <el-menu-item index="/exchanges">交易所</el-menu-item>
              <el-menu-item index="/sectors">板块</el-menu-item>
              <el-menu-item index="/tasks">任务管理</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/instruments_old">
              <el-icon><IconList /></el-icon>
              <span>标的列表</span>
            </el-menu-item>
            <el-menu-item index="/strategies">
              <el-icon><IconOperation /></el-icon>
              <span>策略管理</span>
            </el-menu-item>
            <el-menu-item index="/backtest-records">
              <el-icon><IconHistogram /></el-icon>
              <span>回测记录</span>
            </el-menu-item>
          </el-menu>
        </el-scrollbar>
      </el-aside>
      
      <el-main class="app-main" :class="{ 'app-main--full': isSecurityDetailPage }">
        <!-- 不使用 transition，避免子路由切换时中间区域卡在空白（out-in 与动态组件组合易出问题） -->
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Goods, Money, FolderOpened } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '../../stores/account'
import { useDataSourceStore } from '../../stores/dataSource'
import { api } from '@iottest/vue-core/src/libs/api'

const securitySearchResource = api('instrument/search')

const route = useRoute()
const router = useRouter()
const accountStore = useAccountStore()
const dataSourceStore = useDataSourceStore()

function sourceTypeLabel(sourceType) {
  const map = { qmt: 'QMT', joinquant: '聚宽', tushare: 'Tushare' }
  return map[sourceType] || sourceType || ''
}

onMounted(() => {
  dataSourceStore.fetchList()
})

const activeMenu = computed(() => route.path)
const isSecurityDetailPage = computed(() => route.name === 'admin-instrument-detail' && !!route.params.symbol)
const searchKeyword = ref('')

const refreshData = () => {
  accountStore.fetchAccounts()
  ElMessage.success('数据已刷新')
}

// 搜索证券
const searchSecurities = async (queryString, cb) => {
  if (!queryString || queryString.trim().length === 0) {
    cb([])
    return
  }
  
  try {
    const resp = await securitySearchResource.get({}, { keyword: queryString.trim(), limit: 10 })
    const response = resp.data
    if (response && Array.isArray(response)) {
      // 格式化数据供 autocomplete 使用
      const suggestions = response.map(item => ({
        value: `${item.code} ${item.name}`,
        code: item.code,
        name: item.name,
        market: item.market
      }))
      cb(suggestions)
    } else {
      cb([])
    }
  } catch (error) {
    console.error('搜索证券失败:', error)
    cb([])
  }
}

// 选择证券
const handleSelectSecurity = (item) => {
  if (item && item.code) {
    router.push({
      name: 'admin-instrument-detail',
      params: { symbol: item.code },
    })
    searchKeyword.value = ''
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 头部以下区域占满剩余高度，侧栏与主区在视口内分配，避免整页被侧栏撑高 */
.app-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 20px;
}

.app-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.app-sidebar {
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Element Plus 滚动条：菜单超出时在侧栏内纵向滚动 */
.sidebar-scrollbar {
  flex: 1;
  min-height: 0;
  height: 100%;
}

/* 仅纵向滚动，避免子菜单展开时出现横向滚动条 */
.sidebar-scrollbar :deep(.el-scrollbar__wrap) {
  overflow-x: hidden;
}

.sidebar-menu {
  border-right: none;
  min-height: min-content;
}

.app-main {
  padding: 20px;
  background-color: #f5f7fa;
  overflow-y: auto;
}

.app-main.app-main--full {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.app-main.app-main--full > * {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.search-item .symbol {
  font-weight: 600;
  color: #409eff;
  min-width: 100px;
}

.search-item .name {
  flex: 1;
  color: #303133;
}

.search-item .market {
  font-size: 12px;
  color: #909399;
  padding: 2px 6px;
  background-color: #f4f4f5;
  border-radius: 2px;
}

.data-source-type-tag {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>

