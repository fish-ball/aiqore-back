<template>
  <div class="analysis">
    <div class="page-header">
      <h2>数据分析</h2>
      <div>
        <el-select v-model="selectedAccountId" placeholder="选择账户" style="width: 200px; margin-right: 10px">
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.name || account.account_id"
            :value="account.id"
          />
        </el-select>
        <el-button type="primary" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 账户汇总 -->
    <el-card v-if="summary" style="margin-top: 20px">
      <template #header>
        <span>账户汇总</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">总资产</div>
            <div class="summary-value">¥{{ formatMoney(summary.total_assets) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">持仓市值</div>
            <div class="summary-value">¥{{ formatMoney(summary.position_value) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">可用资金</div>
            <div class="summary-value">¥{{ formatMoney(summary.available_balance) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">总盈亏</div>
            <div class="summary-value" :style="{ color: summary.total_profit >= 0 ? '#67C23A' : '#F56C6C' }">
              {{ summary.total_profit >= 0 ? '+' : '' }}¥{{ formatMoney(summary.total_profit) }}
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 持仓分析 -->
    <el-card v-if="positionAnalysis.length > 0" style="margin-top: 20px">
      <template #header>
        <span>持仓分析</span>
      </template>
      <el-table :data="positionAnalysis" style="width: 100%">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column prop="symbol_name" label="名称" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="cost_price" label="成本价" :formatter="formatMoney" />
        <el-table-column prop="current_price" label="当前价" :formatter="formatMoney" />
        <el-table-column label="盈亏" :formatter="formatProfit" />
        <el-table-column label="盈亏率" :formatter="formatProfitRate" />
        <el-table-column label="持仓占比" :formatter="formatPositionRatio" />
      </el-table>
    </el-card>

    <!-- 交易统计 -->
    <el-card v-if="tradeStats" style="margin-top: 20px">
      <template #header>
        <span>交易统计</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">总交易次数</div>
            <div class="summary-value">{{ tradeStats.total_trades || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">买入次数</div>
            <div class="summary-value">{{ tradeStats.buy_count || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">卖出次数</div>
            <div class="summary-value">{{ tradeStats.sell_count || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">总交易金额</div>
            <div class="summary-value">¥{{ formatMoney(tradeStats.total_amount) }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 盈亏趋势 -->
    <el-card v-if="profitTrend.length > 0" style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>盈亏趋势</span>
          <el-select v-model="trendDays" style="width: 120px">
            <el-option label="7天" :value="7" />
            <el-option label="30天" :value="30" />
            <el-option label="90天" :value="90" />
            <el-option label="180天" :value="180" />
          </el-select>
        </div>
      </template>
      <div id="trend-chart" style="width: 100%; height: 400px" v-loading="loading"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAccountStore } from '../stores/account'
import { analysisApi } from '../api/analysis'
import * as echarts from 'echarts'

const accountStore = useAccountStore()
const loading = ref(false)
const summary = ref(null)
const positionAnalysis = ref([])
const tradeStats = ref(null)
const profitTrend = ref([])
const selectedAccountId = ref(null)
const trendDays = ref(30)
let trendChart = null

const accounts = computed(() => accountStore.accounts)

const formatMoney = (value) => {
  return parseFloat(value || 0).toFixed(2)
}

const formatProfit = (row) => {
  const profit = parseFloat(row.profit || 0)
  const color = profit >= 0 ? '#67C23A' : '#F56C6C'
  return `<span style="color: ${color}">¥${profit.toFixed(2)}</span>`
}

const formatProfitRate = (row) => {
  const rate = parseFloat(row.profit_rate || 0)
  const color = rate >= 0 ? '#67C23A' : '#F56C6C'
  return `<span style="color: ${color}">${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%</span>`
}

const formatPositionRatio = (row) => {
  const ratio = parseFloat(row.position_ratio || 0)
  return `${ratio.toFixed(2)}%`
}

const fetchSummary = async () => {
  if (!selectedAccountId.value) return
  
  try {
    summary.value = await analysisApi.getAccountSummary(selectedAccountId.value)
  } catch (error) {
    console.error('获取账户汇总失败:', error)
  }
}

const fetchPositionAnalysis = async () => {
  if (!selectedAccountId.value) return
  
  try {
    positionAnalysis.value = await analysisApi.getPositionAnalysis(selectedAccountId.value)
  } catch (error) {
    console.error('获取持仓分析失败:', error)
  }
}

const fetchTradeStats = async () => {
  if (!selectedAccountId.value) return
  
  try {
    tradeStats.value = await analysisApi.getTradeStatistics(selectedAccountId.value)
  } catch (error) {
    console.error('获取交易统计失败:', error)
  }
}

const fetchProfitTrend = async () => {
  if (!selectedAccountId.value) return
  
  loading.value = true
  try {
    profitTrend.value = await analysisApi.getProfitTrend(selectedAccountId.value, trendDays.value)
    
    if (!trendChart) {
      const chartDom = document.getElementById('trend-chart')
      if (chartDom) {
        trendChart = echarts.init(chartDom)
      }
    }
    
    if (trendChart && profitTrend.value.length > 0) {
      const option = {
        title: {
          text: '盈亏趋势',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: profitTrend.value.map(item => item.date)
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '盈亏',
            type: 'line',
            data: profitTrend.value.map(item => parseFloat(item.profit || 0)),
            smooth: true,
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
                  { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
                ]
              }
            },
            itemStyle: {
              color: '#409EFF'
            }
          }
        ]
      }
      trendChart.setOption(option)
    }
  } catch (error) {
    console.error('获取盈亏趋势失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await Promise.all([
    fetchSummary(),
    fetchPositionAnalysis(),
    fetchTradeStats(),
    fetchProfitTrend()
  ])
  ElMessage.success('数据已刷新')
}

watch(selectedAccountId, () => {
  refreshData()
})

watch(trendDays, () => {
  fetchProfitTrend()
})

onMounted(async () => {
  await accountStore.fetchAccounts()
  if (accounts.value.length > 0) {
    selectedAccountId.value = accounts.value[0].id
  }
})
</script>

<style scoped>
.analysis {
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

.summary-item {
  text-align: center;
  padding: 20px;
}

.summary-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.summary-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
</style>

