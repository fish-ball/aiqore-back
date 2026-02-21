<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">
          <el-icon><TrendCharts /></el-icon>
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
                <span class="symbol">{{ item.symbol }}</span>
                <span class="name">{{ item.name }}</span>
                <span class="market">{{ item.market }}</span>
              </div>
            </template>
          </el-autocomplete>
          <el-button type="primary" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="200px" class="app-sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/accounts">
            <el-icon><Wallet /></el-icon>
            <span>账户管理</span>
          </el-menu-item>
          <el-menu-item index="/positions">
            <el-icon><Box /></el-icon>
            <span>持仓管理</span>
          </el-menu-item>
          <el-menu-item index="/trades">
            <el-icon><Document /></el-icon>
            <span>交易记录</span>
          </el-menu-item>
          <el-menu-item index="/securities">
            <el-icon><List /></el-icon>
            <span>证券列表</span>
          </el-menu-item>
          <el-menu-item index="/sectors">
            <el-icon><List /></el-icon>
            <span>板块管理</span>
          </el-menu-item>
          <el-menu-item index="/data-sources">
            <el-icon><Connection /></el-icon>
            <span>数据源连接</span>
          </el-menu-item>
          <el-menu-item index="/analysis">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据分析</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAccountStore } from './stores/account'
import { useDataSourceStore } from './stores/dataSource'
import { securityApi } from './api/security'

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
    const response = await securityApi.search(queryString.trim(), 10)
    if (response && Array.isArray(response)) {
      // 格式化数据供 autocomplete 使用
      const suggestions = response.map(item => ({
        value: `${item.symbol} ${item.name}`,
        symbol: item.symbol,
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
  if (item && item.symbol) {
    router.push(`/security/${item.symbol}`)
    searchKeyword.value = ''
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
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
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.app-main {
  padding: 20px;
  background-color: #f5f7fa;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
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

