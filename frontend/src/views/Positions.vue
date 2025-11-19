<template>
  <div class="positions">
    <div class="page-header">
      <h2>持仓管理</h2>
      <div>
        <el-select v-model="selectedAccountId" placeholder="选择账户" style="width: 200px; margin-right: 10px">
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.name || account.account_id"
            :value="account.id"
          />
        </el-select>
        <el-button type="primary" @click="syncPositions" :disabled="!selectedAccountId">
          <el-icon><Refresh /></el-icon>
          同步持仓
        </el-button>
      </div>
    </div>

    <el-card style="margin-top: 20px">
      <el-table :data="positions" style="width: 100%" v-loading="loading">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column prop="symbol_name" label="名称" />
        <el-table-column prop="quantity" label="持仓数量" />
        <el-table-column prop="cost_price" label="成本价" :formatter="formatMoney" />
        <el-table-column prop="current_price" label="当前价" :formatter="formatMoney" />
        <el-table-column label="持仓市值" :formatter="formatMarketValue" />
        <el-table-column label="盈亏" :formatter="formatProfit" />
        <el-table-column label="盈亏率" :formatter="formatProfitRate" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAccountStore } from '../stores/account'
import { tradeApi } from '../api/trade'

const accountStore = useAccountStore()
const loading = ref(false)
const positions = ref([])
const selectedAccountId = ref(null)

const accounts = computed(() => accountStore.accounts)

const formatMoney = (row, column, cellValue) => {
  return `¥${parseFloat(cellValue || 0).toFixed(2)}`
}

const formatMarketValue = (row) => {
  const value = parseFloat(row.current_price || 0) * parseInt(row.quantity || 0)
  return `¥${value.toFixed(2)}`
}

const formatProfit = (row) => {
  const cost = parseFloat(row.cost_price || 0) * parseInt(row.quantity || 0)
  const current = parseFloat(row.current_price || 0) * parseInt(row.quantity || 0)
  const profit = current - cost
  const color = profit >= 0 ? '#67C23A' : '#F56C6C'
  return `<span style="color: ${color}">¥${profit.toFixed(2)}</span>`
}

const formatProfitRate = (row) => {
  const cost = parseFloat(row.cost_price || 0)
  const current = parseFloat(row.current_price || 0)
  if (cost === 0) return '--'
  const rate = ((current - cost) / cost * 100).toFixed(2)
  const color = rate >= 0 ? '#67C23A' : '#F56C6C'
  return `<span style="color: ${color}">${rate}%</span>`
}

const fetchPositions = async () => {
  if (!selectedAccountId.value) {
    positions.value = []
    return
  }
  
  loading.value = true
  try {
    positions.value = await tradeApi.getPositions(selectedAccountId.value)
  } catch (error) {
    console.error('获取持仓失败:', error)
    ElMessage.error('获取持仓失败')
  } finally {
    loading.value = false
  }
}

const syncPositions = async () => {
  if (!selectedAccountId.value) return
  
  loading.value = true
  try {
    await tradeApi.syncPositions(selectedAccountId.value)
    ElMessage.success('同步成功')
    await fetchPositions()
  } catch (error) {
    ElMessage.error('同步失败')
  } finally {
    loading.value = false
  }
}

watch(selectedAccountId, () => {
  fetchPositions()
})

onMounted(async () => {
  await accountStore.fetchAccounts()
  if (accounts.value.length > 0) {
    selectedAccountId.value = accounts.value[0].id
  }
})
</script>

<style scoped>
.positions {
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
</style>

