<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="24">
        <h2>仪表盘</h2>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon :size="24"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>账户列表</span>
          </template>
          <el-table :data="accounts" style="width: 100%" v-loading="loading">
            <el-table-column prop="name" label="账户名称" />
            <el-table-column prop="account_id" label="账户ID" />
            <el-table-column prop="current_balance" label="当前余额" :formatter="formatMoney" />
            <el-table-column label="操作">
              <template #default="scope">
                <el-button size="small" @click="viewAccount(scope.row.id)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近交易</span>
          </template>
          <el-table :data="recentTrades" style="width: 100%" v-loading="tradesLoading">
            <el-table-column prop="symbol" label="代码" />
            <el-table-column prop="symbol_name" label="名称" />
            <el-table-column prop="direction" label="方向" />
            <el-table-column prop="price" label="价格" />
            <el-table-column prop="quantity" label="数量" />
            <el-table-column prop="trade_time" label="时间" :formatter="formatDate" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountStore } from '../stores/account'
import { tradeApi } from '../api/trade'
import { Wallet, Box, TrendCharts, Document } from '@element-plus/icons-vue'

const router = useRouter()
const accountStore = useAccountStore()
const loading = ref(false)
const tradesLoading = ref(false)
const recentTrades = ref([])

const accounts = computed(() => accountStore.accounts)

const stats = computed(() => [
  {
    title: '账户总数',
    value: accounts.value.length,
    icon: 'Wallet',
    color: '#409EFF'
  },
  {
    title: '总资产',
    value: accounts.value.reduce((sum, acc) => sum + parseFloat(acc.current_balance || 0), 0).toFixed(2),
    icon: 'TrendCharts',
    color: '#67C23A'
  },
  {
    title: '持仓数量',
    value: '--',
    icon: 'Box',
    color: '#E6A23C'
  },
  {
    title: '交易记录',
    value: '--',
    icon: 'Document',
    color: '#F56C6C'
  }
])

const formatMoney = (row, column, cellValue) => {
  return `¥${parseFloat(cellValue || 0).toFixed(2)}`
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return '--'
  return new Date(cellValue).toLocaleString('zh-CN')
}

const viewAccount = (accountId) => {
  router.push(`/accounts?id=${accountId}`)
}

const fetchRecentTrades = async () => {
  if (accounts.value.length === 0) return
  
  tradesLoading.value = true
  try {
    const accountId = accounts.value[0].id
    const data = await tradeApi.getTrades(accountId, { limit: 5 })
    recentTrades.value = data.items || []
  } catch (error) {
    console.error('获取交易记录失败:', error)
  } finally {
    tradesLoading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  await accountStore.fetchAccounts()
  loading.value = false
  await fetchRecentTrades()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-title {
  font-size: 14px;
  color: #909399;
}
</style>

