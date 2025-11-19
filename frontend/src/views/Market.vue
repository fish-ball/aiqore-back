<template>
  <div class="market">
    <div class="page-header">
      <h2>行情查询</h2>
    </div>

    <el-card style="margin-top: 20px">
      <el-form :inline="true" class="search-form">
        <el-form-item label="搜索股票">
          <el-input
            v-model="searchKeyword"
            placeholder="输入股票代码或名称"
            style="width: 300px"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="证券代码">
          <el-input
            v-model="quoteSymbol"
            placeholder="如：000001.SZ,600000.SH"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchQuote">查询行情</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 搜索结果 -->
    <el-card v-if="searchResults.length > 0" style="margin-top: 20px">
      <template #header>
        <span>搜索结果</span>
      </template>
      <el-table :data="searchResults" style="width: 100%">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column label="名称">
          <template #default="scope">
            {{ scope.row.name || scope.row.symbol || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="scope">
            <el-button size="small" @click="selectSymbol(scope.row.symbol)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 行情数据 -->
    <el-card v-if="quotes.length > 0" style="margin-top: 20px">
      <template #header>
        <span>实时行情</span>
      </template>
      <el-table :data="quotes" style="width: 100%" v-loading="quoteLoading">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column label="名称">
          <template #default="scope">
            {{ scope.row.name || scope.row.symbol || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="最新价">
          <template #default="scope">
            ¥{{ formatPrice(scope.row.last_price) }}
          </template>
        </el-table-column>
        <el-table-column label="涨跌">
          <template #default="scope">
            <span :style="{ color: (scope.row.change || 0) >= 0 ? '#F56C6C' : '#67C23A' }">
              {{ (scope.row.change || 0) >= 0 ? '+' : '' }}{{ formatPrice(scope.row.change || 0) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅">
          <template #default="scope">
            <span :style="{ color: (scope.row.change_percent || scope.row.change_pct || 0) >= 0 ? '#F56C6C' : '#67C23A' }">
              {{ (scope.row.change_percent || scope.row.change_pct || 0) >= 0 ? '+' : '' }}{{ ((scope.row.change_percent || scope.row.change_pct || 0)).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成交量">
          <template #default="scope">
            {{ formatVolume(scope.row.volume) }}
          </template>
        </el-table-column>
        <el-table-column label="成交额">
          <template #default="scope">
            {{ formatAmount(scope.row.amount) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- K线图 -->
    <el-card v-if="selectedSymbol" style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>K线图 - {{ selectedSymbol }}</span>
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
      <div id="kline-chart" style="width: 100%; height: 400px" v-loading="klineLoading"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { marketApi } from '../api/market'
import * as echarts from 'echarts'

const searchKeyword = ref('')
const quoteSymbol = ref('')
const searchResults = ref([])
const quotes = ref([])
const quoteLoading = ref(false)
const klineLoading = ref(false)
const selectedSymbol = ref('')
const klinePeriod = ref('1d')
let klineChart = null

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  try {
    searchResults.value = await marketApi.searchStocks(searchKeyword.value)
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败')
  }
}

const selectSymbol = (symbol) => {
  quoteSymbol.value = symbol
  selectedSymbol.value = symbol
  fetchQuote()
  fetchKline()
}

const fetchQuote = async () => {
  if (!quoteSymbol.value.trim()) {
    ElMessage.warning('请输入证券代码')
    return
  }
  
  quoteLoading.value = true
  try {
    quotes.value = await marketApi.getQuote(quoteSymbol.value)
    if (quotes.value.length > 0 && !selectedSymbol.value) {
      selectedSymbol.value = quotes.value[0].symbol
      fetchKline()
    }
  } catch (error) {
    console.error('获取行情失败:', error)
    ElMessage.error('获取行情失败')
  } finally {
    quoteLoading.value = false
  }
}

const fetchKline = async () => {
  if (!selectedSymbol.value) return
  
  klineLoading.value = true
  try {
    const data = await marketApi.getKline(selectedSymbol.value, klinePeriod.value, 100)
    
    // 等待DOM更新
    await nextTick()
    
    const chartDom = document.getElementById('kline-chart')
    if (!chartDom) {
      console.error('图表容器不存在')
      klineLoading.value = false
      return
    }
    
    // 如果图表已存在，先销毁
    if (klineChart) {
      klineChart.dispose()
    }
    
    // 初始化图表
    klineChart = echarts.init(chartDom)
    
    if (data && data.length > 0) {
      // 处理时间数据
      const timeData = data.map(item => {
        const time = item.time || item.date || ''
        // 如果是完整时间戳，只取日期部分
        if (time.includes(' ')) {
          return time.split(' ')[0]
        }
        return time
      })
      
      // 处理价格数据
      const priceData = data.map(item => parseFloat(item.close || 0))
      
      const option = {
        title: {
          text: `${selectedSymbol.value} - ${klinePeriod.value}`,
          left: 'center',
          textStyle: {
            fontSize: 16
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: function(params) {
            const param = params[0]
            return `${param.name}<br/>${param.seriesName}: ¥${param.value.toFixed(2)}`
          }
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
          axisLabel: {
            rotate: 45,
            formatter: function(value) {
              return value
            }
          }
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: {
            formatter: function(value) {
              return '¥' + value.toFixed(2)
            }
          }
        },
        series: [
          {
            name: '收盘价',
            type: 'line',
            data: priceData,
            smooth: false,
            symbol: 'circle',
            symbolSize: 4,
            itemStyle: {
              color: '#409EFF'
            },
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
            }
          }
        ]
      }
      
      klineChart.setOption(option)
      
      // 响应式调整
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
    ElMessage.error('获取K线失败: ' + (error.message || '未知错误'))
  } finally {
    klineLoading.value = false
  }
}

const formatPrice = (value) => {
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

onMounted(() => {
  // 初始化
})

onBeforeUnmount(() => {
  // 清理图表
  if (klineChart) {
    klineChart.dispose()
    klineChart = null
  }
})
</script>

<style scoped>
.market {
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

.search-form {
  margin-bottom: 0;
}
</style>

