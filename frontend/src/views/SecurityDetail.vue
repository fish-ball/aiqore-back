<template>
  <div class="security-detail">
    <div class="page-header">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>{{ securityInfo.name || symbol }}</h2>
      <div></div>
    </div>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 基本信息 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>基本信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="证券代码">{{ symbol }}</el-descriptions-item>
            <el-descriptions-item label="证券名称">{{ securityInfo.name || '--' }}</el-descriptions-item>
            <el-descriptions-item label="市场">
              <el-tag :type="securityInfo.market === 'SH' ? 'success' : 'warning'">
                {{ securityInfo.market === 'SH' ? '上海' : '深圳' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="证券类型">{{ securityInfo.security_type || '--' }}</el-descriptions-item>
            <el-descriptions-item label="所属行业">{{ securityInfo.industry || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 实时行情 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>实时行情</span>
              <el-button size="small" @click="refreshQuote">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <el-row :gutter="20" v-loading="quoteLoading">
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">最新价</div>
                <div class="quote-value" :style="{ color: getPriceColor(quote.last_price, quote.pre_close) }">
                  ¥{{ formatPrice(quote.last_price) }}
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">涨跌</div>
                <div class="quote-value" :style="{ color: quote.change >= 0 ? '#F56C6C' : '#67C23A' }">
                  {{ quote.change >= 0 ? '+' : '' }}{{ formatPrice(quote.change) }}
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">涨跌幅</div>
                <div class="quote-value" :style="{ color: quote.change_percent >= 0 ? '#F56C6C' : '#67C23A' }">
                  {{ quote.change_percent >= 0 ? '+' : '' }}{{ formatChangePercent(quote.change_percent) }}%
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">昨收</div>
                <div class="quote-value">¥{{ formatPrice(quote.pre_close) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">开盘</div>
                <div class="quote-value">¥{{ formatPrice(quote.open) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">最高</div>
                <div class="quote-value" style="color: #F56C6C">¥{{ formatPrice(quote.high) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">最低</div>
                <div class="quote-value" style="color: #67C23A">¥{{ formatPrice(quote.low) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">成交量</div>
                <div class="quote-value">{{ formatVolume(quote.volume) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="quote-item">
                <div class="quote-label">成交额</div>
                <div class="quote-value">{{ formatAmount(quote.amount) }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- K线图 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>K线图 - {{ symbol }}</span>
          <div>
            <el-select v-model="klinePeriod" style="width: 120px; margin-right: 10px" @change="fetchKline">
              <el-option label="1分钟" value="1m" />
              <el-option label="5分钟" value="5m" />
              <el-option label="15分钟" value="15m" />
              <el-option label="30分钟" value="30m" />
              <el-option label="1小时" value="1h" />
              <el-option label="日线" value="1d" />
              <el-option label="周线" value="1w" />
              <el-option label="月线" value="1M" />
            </el-select>
            <el-button type="primary" @click="fetchKline">刷新</el-button>
          </div>
        </div>
      </template>
      <div id="kline-chart" style="width: 100%; height: 500px" v-loading="klineLoading"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { securityApi } from '../api/security'
import { marketApi } from '../api/market'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const symbol = ref(route.params.symbol || '')
const securityInfo = ref({})
const quote = ref({
  last_price: 0,
  open: 0,
  high: 0,
  low: 0,
  pre_close: 0,
  volume: 0,
  amount: 0,
  change: 0,
  change_percent: 0
})
const quoteLoading = ref(false)
const klineLoading = ref(false)
const klinePeriod = ref('1d')
let klineChart = null

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

const getPriceColor = (lastPrice, preClose) => {
  if (lastPrice > preClose) return '#F56C6C'
  if (lastPrice < preClose) return '#67C23A'
  return '#909399'
}

const fetchSecurityInfo = async () => {
  try {
    const info = await securityApi.getDetail(symbol.value)
    securityInfo.value = info
  } catch (error) {
    console.error('获取证券信息失败:', error)
  }
}

const fetchQuote = async () => {
  quoteLoading.value = true
  try {
    const quotes = await marketApi.getQuote(symbol.value)
    if (Array.isArray(quotes) && quotes.length > 0) {
      quote.value = quotes[0]
    } else if (quotes && quotes.symbol) {
      quote.value = quotes
    }
  } catch (error) {
    console.error('获取行情失败:', error)
    ElMessage.error('获取行情失败')
  } finally {
    quoteLoading.value = false
  }
}

const refreshQuote = () => {
  fetchQuote()
  ElMessage.success('行情已刷新')
}

const fetchKline = async () => {
  if (!symbol.value) return
  
  klineLoading.value = true
  try {
    const data = await marketApi.getKline(symbol.value, klinePeriod.value, 100)
    
    await nextTick()
    
    const chartDom = document.getElementById('kline-chart')
    if (!chartDom) {
      klineLoading.value = false
      return
    }
    
    if (klineChart) {
      klineChart.dispose()
    }
    
    klineChart = echarts.init(chartDom)
    
    if (data && data.length > 0) {
      const timeData = data.map(item => {
        const time = item.time || item.date || ''
        if (time.includes(' ')) {
          return time.split(' ')[0]
        }
        return time
      })
      
      const priceData = data.map(item => parseFloat(item.close || 0))
      
      const option = {
        title: {
          text: `${symbol.value} - ${klinePeriod.value}`,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: timeData,
          axisLabel: { rotate: 45 }
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: {
            formatter: value => '¥' + value.toFixed(2)
          }
        },
        series: [{
          name: '收盘价',
          type: 'line',
          data: priceData,
          smooth: false,
          symbol: 'circle',
          symbolSize: 4,
          itemStyle: { color: '#409EFF' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
                { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
              ]
            }
          }
        }]
      }
      
      klineChart.setOption(option)
      
      window.addEventListener('resize', () => {
        if (klineChart) {
          klineChart.resize()
        }
      })
    } else {
      ElMessage.warning('暂无K线数据')
    }
  } catch (error) {
    console.error('获取K线失败:', error)
    ElMessage.error('获取K线失败')
  } finally {
    klineLoading.value = false
  }
}

const goBack = () => {
  router.back()
}

onMounted(async () => {
  await fetchSecurityInfo()
  await fetchQuote()
  await fetchKline()
})

onBeforeUnmount(() => {
  if (klineChart) {
    klineChart.dispose()
    klineChart = null
  }
})
</script>

<style scoped>
.security-detail {
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
  flex: 1;
  text-align: center;
}

.quote-item {
  padding: 15px;
  text-align: center;
}

.quote-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.quote-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
</style>

