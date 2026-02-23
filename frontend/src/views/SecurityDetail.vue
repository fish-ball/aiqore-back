<template>
  <div class="security-detail">
    <!-- 顶栏：左侧名称+代码，右侧布局切换+返回 -->
    <header class="detail-header">
      <div class="header-left">
        <span class="security-name">{{ securityInfo.name || symbol || '--' }}</span>
        <span class="security-symbol">{{ symbol }}</span>
      </div>
      <div class="header-right">
        <el-radio-group v-model="layoutMode" size="small" class="layout-switch">
          <el-radio-button value="left">左栏</el-radio-button>
          <el-radio-button value="both">双侧</el-radio-button>
          <el-radio-button value="right">右栏</el-radio-button>
        </el-radio-group>
        <el-button size="small" :loading="updateDataLoading" @click="triggerUpdateData">
          更新数据
        </el-button>
        <el-button size="small" @click="refreshCharts">
          刷新
        </el-button>
        <el-button size="small" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
      </div>
    </header>

    <!-- 主区域：可拖拽左右分栏 -->
    <div class="main-area">
      <!-- 左侧面板：行情 -->
      <div
        v-show="layoutMode !== 'right'"
        class="panel-left"
        :style="{ width: layoutMode === 'left' ? '100%' : leftPanelWidthPx }"
      >
        <el-tabs v-model="chartTab" class="chart-tabs">
          <el-tab-pane label="分时" name="intraday">
            <div class="intraday-wrap">
              <div class="intraday-charts">
                <div class="chart-half chart-price">
                  <div ref="intradayChartRef" class="chart-dom"></div>
                  <!-- 待接口：分时或当日 1m 数据 -->
                </div>
                <div class="chart-half chart-volume">
                  <div ref="intradayVolRef" class="chart-dom"></div>
                  <!-- 第一步仅支持分时量；无则占位 -->
                </div>
              </div>
              <div class="intraday-side">
                <!-- 待接口：五档盘口（可考虑从 get_full_tick 扩展） -->
                <div class="side-block">
                  <el-table :data="fiveLevelPlaceholder" size="small" class="five-level-table" :show-header="false">
                    <el-table-column prop="label" width="56" />
                    <el-table-column prop="price" />
                    <el-table-column prop="vol" />
                  </el-table>
                </div>
                <!-- 待接口：最新成交 -->
                <div class="side-block">
                  <div class="trade-placeholder">最新成交 - 待接口</div>
                </div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="日K" name="day">
            <div class="kline-wrap">
              <div ref="klineChartRef" class="chart-dom kline-chart-dom"></div>
              <div class="kline-indicator">
                <el-radio-group v-model="klineIndicator" size="small" @change="updateKlineIndicator">
                  <el-radio-button value="volume">成交量</el-radio-button>
                  <el-radio-button value="amount">成交额</el-radio-button>
                  <el-radio-button value="kdj">KDJ</el-radio-button>
                  <el-radio-button value="rsi">RSI</el-radio-button>
                  <el-radio-button value="macd">MACD</el-radio-button>
                </el-radio-group>
              </div>
              <div ref="klineSubRef" class="chart-dom kline-sub-dom"></div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="周K" name="week">
            <div class="kline-wrap">
              <div ref="klineWeekChartRef" class="chart-dom kline-chart-dom"></div>
              <div class="kline-indicator">
                <el-radio-group v-model="klineWeekIndicator" size="small" @change="updateKlineWeekIndicator">
                  <el-radio-button value="volume">成交量</el-radio-button>
                  <el-radio-button value="amount">成交额</el-radio-button>
                  <el-radio-button value="kdj">KDJ</el-radio-button>
                  <el-radio-button value="rsi">RSI</el-radio-button>
                  <el-radio-button value="macd">MACD</el-radio-button>
                </el-radio-group>
              </div>
              <div ref="klineWeekSubRef" class="chart-dom kline-sub-dom"></div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="月K" name="month">
            <div class="kline-wrap">
              <div ref="klineMonthChartRef" class="chart-dom kline-chart-dom"></div>
              <div class="kline-indicator">
                <el-radio-group v-model="klineMonthIndicator" size="small" @change="updateKlineMonthIndicator">
                  <el-radio-button value="volume">成交量</el-radio-button>
                  <el-radio-button value="amount">成交额</el-radio-button>
                  <el-radio-button value="kdj">KDJ</el-radio-button>
                  <el-radio-button value="rsi">RSI</el-radio-button>
                  <el-radio-button value="macd">MACD</el-radio-button>
                </el-radio-group>
              </div>
              <div ref="klineMonthSubRef" class="chart-dom kline-sub-dom"></div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 可拖拽分割条（仅双侧时显示） -->
      <div
        v-show="layoutMode === 'both'"
        class="resizer"
        @mousedown="startResize"
      ></div>

      <!-- 右侧面板：F10 -->
      <div
        v-show="layoutMode !== 'left'"
        class="panel-right"
        :style="{ width: layoutMode === 'right' ? '100%' : undefined, flex: layoutMode === 'both' ? 1 : undefined }"
      >
        <div class="f10-panel">
          <el-collapse v-model="f10ActiveNames">
            <el-collapse-item title="操盘必读" name="read">
              <div class="f10-placeholder">操盘必读 - 待接口</div>
            </el-collapse-item>
            <el-collapse-item title="财务分析" name="finance">
              <div class="f10-placeholder">财务分析 - 待接口</div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { securityApi } from '../api/security'
import { marketApi } from '../api/market'
import { useDataSourceStore } from '../stores/dataSource'
import * as echarts from 'echarts'

const dataSourceStore = useDataSourceStore()

// 行情页黑底白字图表主题（与现有行情软件风格一致）
const CHART_DARK = {
  backgroundColor: '#0d0d0d',
  textStyle: { color: '#e0e0e0' },
  axisLine: { lineStyle: { color: '#404040' } },
  splitLine: { lineStyle: { color: '#262626' } },
  axisLabel: { color: '#b0b0b0' }
}

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
const updateDataLoading = ref(false)

// 布局：left=仅左栏 both=双侧 right=仅右栏
const layoutMode = ref('both')
// 左侧面板宽度（像素），双侧时有效
const leftPanelWidth = ref(0)
const leftPanelWidthPx = ref('60%')
let resizing = false

// 分时 / 日K / 周K / 月K
const chartTab = ref('intraday')
const intradayChartRef = ref(null)
const intradayVolRef = ref(null)
const klineChartRef = ref(null)
const klineSubRef = ref(null)
const klineWeekChartRef = ref(null)
const klineWeekSubRef = ref(null)
const klineMonthChartRef = ref(null)
const klineMonthSubRef = ref(null)

const klineIndicator = ref('volume')
const klineWeekIndicator = ref('volume')
const klineMonthIndicator = ref('volume')

const klineData = ref([])
const klineWeekData = ref([])
const klineMonthData = ref([])
const klineLoading = ref(false)

let intradayChart = null
let intradayVolChart = null

// 五档、最新成交占位（待接口）
const fiveLevelPlaceholder = ref([
  { label: '卖5', price: '--', vol: '--' },
  { label: '卖4', price: '--', vol: '--' },
  { label: '卖3', price: '--', vol: '--' },
  { label: '卖2', price: '--', vol: '--' },
  { label: '卖1', price: '--', vol: '--' },
  { label: '买1', price: '--', vol: '--' },
  { label: '买2', price: '--', vol: '--' },
  { label: '买3', price: '--', vol: '--' },
  { label: '买4', price: '--', vol: '--' },
  { label: '买5', price: '--', vol: '--' }
])

const f10ActiveNames = ref(['read', 'finance'])

function formatPrice(value) {
  return parseFloat(value || 0).toFixed(2)
}

function formatChangePercent(value) {
  return parseFloat(value || 0).toFixed(2)
}

function formatVolume(value) {
  const num = parseFloat(value || 0)
  if (num >= 100000000) return `${(num / 100000000).toFixed(2)}亿`
  if (num >= 10000) return `${(num / 10000).toFixed(2)}万`
  return num.toFixed(0)
}

function formatAmount(value) {
  const num = parseFloat(value || 0)
  if (num >= 100000000) return `¥${(num / 100000000).toFixed(2)}亿`
  if (num >= 10000) return `¥${(num / 10000).toFixed(2)}万`
  return `¥${num.toFixed(2)}`
}

function getPriceColor(lastPrice, preClose) {
  if (lastPrice > preClose) return '#F56C6C'
  if (lastPrice < preClose) return '#67C23A'
  return '#909399'
}

async function fetchSecurityInfo() {
  try {
    const info = await securityApi.getDetail(symbol.value)
    securityInfo.value = info
  } catch (error) {
    console.error('获取证券信息失败:', error)
  }
}

async function fetchQuote() {
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

// 计算均线
function calcMA(data, period) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push('-')
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) sum += data[i - j].close
      result.push((sum / period).toFixed(2))
    }
  }
  return result
}

// KDJ
function calcKDJ(data, n = 9, m1 = 3, m2 = 3) {
  const k = [], d = [], j = []
  let kNum = 50, dNum = 50
  for (let i = 0; i < data.length; i++) {
    if (i < n - 1) {
      k.push('-')
      d.push('-')
      j.push('-')
      continue
    }
    const low = Math.min(...data.slice(i - n + 1, i + 1).map(x => x.low))
    const high = Math.max(...data.slice(i - n + 1, i + 1).map(x => x.high))
    const close = data[i].close
    const rsv = high === low ? 0 : ((close - low) / (high - low)) * 100
    kNum = i === n - 1 ? 50 : (2 / 3) * kNum + (1 / 3) * rsv
    dNum = i === n - 1 ? 50 : (2 / 3) * dNum + (1 / 3) * kNum
    const jVal = 3 * kNum - 2 * dNum
    k.push(kNum.toFixed(2))
    d.push(dNum.toFixed(2))
    j.push(jVal.toFixed(2))
  }
  return { k, d, j }
}

// RSI
function calcRSI(data, n = 14) {
  const rsi = []
  for (let i = 0; i < data.length; i++) {
    if (i < n) {
      rsi.push('-')
      continue
    }
    let up = 0, down = 0
    for (let j = i - n + 1; j <= i; j++) {
      const ch = data[j].close - data[j - 1].close
      if (ch > 0) up += ch
      else down -= ch
    }
    const avgUp = up / n
    const avgDown = down / n
    if (avgDown === 0) rsi.push(100)
    else rsi.push((100 - 100 / (1 + avgUp / avgDown)).toFixed(2))
  }
  return rsi
}

// MACD：DIF=EMA(close,12)-EMA(close,26)，DEA=EMA(DIF,9)，MACD=(DIF-DEA)*2
function calcMACD(data, short = 12, long = 26, mid = 9) {
  const dif = [], dea = [], macd = []
  let eS = 0, eL = 0, eD = 0
  for (let i = 0; i < data.length; i++) {
    const c = data[i].close
    if (i === 0) {
      eS = c
      eL = c
    } else {
      eS = (2 * c + (short - 1) * eS) / (short + 1)
      eL = (2 * c + (long - 1) * eL) / (long + 1)
    }
    const d = eS - eL
    dif.push(d.toFixed(2))
    if (i === 0) {
      eD = d
      dea.push('-')
      macd.push('-')
    } else if (i < mid) {
      eD = (2 * d + (mid - 1) * eD) / (mid + 1)
      dea.push('-')
      macd.push('-')
    } else {
      eD = (2 * d + (mid - 1) * eD) / (mid + 1)
      dea.push(eD.toFixed(2))
      macd.push((2 * (d - eD)).toFixed(2))
    }
  }
  return { dif, dea, macd }
}

function buildKlineOption(rawData) {
  if (!rawData || rawData.length === 0) return null
  const times = rawData.map(item => {
    const t = item.time || item.timestamp || item.date || ''
    return (typeof t === 'string' && t.includes(' ')) ? t.slice(0, 16) : String(t).slice(0, 10)
  })
  const o = rawData.map(x => parseFloat(x.open || 0))
  const c = rawData.map(x => parseFloat(x.close || 0))
  const l = rawData.map(x => parseFloat(x.low || 0))
  const h = rawData.map(x => parseFloat(x.high || 0))
  const candleData = rawData.map((_, i) => [o[i], c[i], l[i], h[i]])

  const ma5 = calcMA(rawData, 5)
  const ma10 = calcMA(rawData, 10)
  const ma20 = calcMA(rawData, 20)
  const ma30 = calcMA(rawData, 30)
  const ma60 = calcMA(rawData, 60)
  const ma120 = calcMA(rawData, 120)
  const ma250 = calcMA(rawData, 250)

  const series = [
    { name: 'K线', type: 'candlestick', data: candleData, itemStyle: { color: '#ef5350', borderColor: '#ef5350', color0: '#26a69a', borderColor0: '#26a69a' } },
    { name: 'MA5', type: 'line', data: ma5, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#e0e0e0' } },
    { name: 'MA10', type: 'line', data: ma10, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#b0b0b0' } },
    { name: 'MA20', type: 'line', data: ma20, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#808080' } },
    { name: 'MA30', type: 'line', data: ma30, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#606060' } },
    { name: 'MA60', type: 'line', data: ma60, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#5c9eed' } },
    { name: 'MA120', type: 'line', data: ma120, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#ffc107' } },
    { name: 'MA250', type: 'line', data: ma250, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#ff9800' } }
  ]

  return {
    ...CHART_DARK,
    animation: false,
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: { type: 'category', data: times, boundaryGap: true, axisLabel: { rotate: 45, ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, axisLabel: { formatter: v => '¥' + v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine },
    series
  }
}

function buildSubOption(rawData, type) {
  if (!rawData || rawData.length === 0) return null
  const times = rawData.map(item => {
    const t = item.time || item.timestamp || item.date || ''
    return (typeof t === 'string' && t.includes(' ')) ? t.slice(0, 16) : String(t).slice(0, 10)
  })
  const grid = { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true }
  const xAxis = { type: 'category', data: times, boundaryGap: true, axisLabel: { rotate: 45 } }

  const axisCommon = { axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine, axisLabel: CHART_DARK.axisLabel }
  if (type === 'volume') {
    const vol = rawData.map(x => parseInt(x.volume || 0, 10))
    const colors = rawData.map((x, i) => (i > 0 && x.close >= rawData[i - 1].close ? '#ef5350' : '#26a69a'))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { trigger: 'axis' },
      grid,
      xAxis: { ...xAxis, ...axisCommon },
      yAxis: { type: 'value', ...axisCommon, axisLabel: { formatter: v => formatVolume(v), ...CHART_DARK.axisLabel } },
      series: [{ name: '成交量', type: 'bar', data: vol, itemStyle: { color: (params) => colors[params.dataIndex] } }]
    }
  }
  if (type === 'amount') {
    const amount = rawData.map(x => parseFloat(x.amount || 0))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid,
      xAxis: { ...xAxis, ...axisCommon },
      yAxis: { type: 'value', ...axisCommon, axisLabel: { formatter: v => (v >= 1e8 ? (v / 1e8).toFixed(1) + '亿' : (v / 1e4).toFixed(0) + '万'), ...CHART_DARK.axisLabel } },
      series: [{ name: '成交额', type: 'bar', data: amount, itemStyle: { color: '#5c9eed' } }]
    }
  }
  if (type === 'kdj') {
    const { k, d, j } = calcKDJ(rawData)
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { trigger: 'axis' },
      grid,
      xAxis: { ...xAxis, ...axisCommon },
      yAxis: { type: 'value', min: 0, max: 100, ...axisCommon },
      series: [
        { name: 'K', type: 'line', data: k, smooth: false, symbol: 'none' },
        { name: 'D', type: 'line', data: d, smooth: false, symbol: 'none' },
        { name: 'J', type: 'line', data: j, smooth: false, symbol: 'none' }
      ]
    }
  }
  if (type === 'rsi') {
    const rsi = calcRSI(rawData)
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { trigger: 'axis' },
      grid,
      xAxis: { ...xAxis, ...axisCommon },
      yAxis: { type: 'value', min: 0, max: 100, ...axisCommon },
      series: [{ name: 'RSI', type: 'line', data: rsi, smooth: false, symbol: 'none' }]
    }
  }
  if (type === 'macd') {
    const { dif, dea, macd } = calcMACD(rawData)
    const barColors = macd.map((v, i) => (v !== '-' && parseFloat(v) >= 0 ? '#ef5350' : '#26a69a'))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { trigger: 'axis' },
      grid,
      xAxis: { ...xAxis, ...axisCommon },
      yAxis: { type: 'value', ...axisCommon },
      series: [
        { name: 'DIF', type: 'line', data: dif, smooth: false, symbol: 'none' },
        { name: 'DEA', type: 'line', data: dea, smooth: false, symbol: 'none' },
        { name: 'MACD', type: 'bar', data: macd, itemStyle: { color: (params) => barColors[params.dataIndex] } }
      ]
    }
  }
  return null
}

async function fetchKlineForTab(period, count = 250) {
  if (!symbol.value) return []
  try {
    // 不传 start_date/end_date，后端返回全部 K 线，由前端控制显示范围
    const res = await marketApi.getKline(symbol.value, period, count)
    return Array.isArray(res) ? res : []
  } catch (e) {
    console.error('获取K线失败:', e)
    return []
  }
}

function renderKline(chartDom, subDom, rawData, indicator) {
  if (!chartDom || !rawData.length) return
  const mainChart = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom)
  const opt = buildKlineOption(rawData)
  if (opt) mainChart.setOption(opt, true)
  if (subDom && rawData.length) {
    const subChart = echarts.getInstanceByDom(subDom) || echarts.init(subDom)
    const subOpt = buildSubOption(rawData, indicator)
    if (subOpt) subChart.setOption(subOpt, true)
  }
}

function updateKlineIndicator() {
  if (klineSubRef.value && klineData.value.length) {
    const subChart = echarts.getInstanceByDom(klineSubRef.value) || echarts.init(klineSubRef.value)
    const opt = buildSubOption(klineData.value, klineIndicator.value)
    if (opt) subChart.setOption(opt, true)
  }
}

function updateKlineWeekIndicator() {
  if (klineWeekSubRef.value && klineWeekData.value.length) {
    const subChart = echarts.getInstanceByDom(klineWeekSubRef.value) || echarts.init(klineWeekSubRef.value)
    const opt = buildSubOption(klineWeekData.value, klineWeekIndicator.value)
    if (opt) subChart.setOption(opt, true)
  }
}

function updateKlineMonthIndicator() {
  if (klineMonthSubRef.value && klineMonthData.value.length) {
    const subChart = echarts.getInstanceByDom(klineMonthSubRef.value) || echarts.init(klineMonthSubRef.value)
    const opt = buildSubOption(klineMonthData.value, klineMonthIndicator.value)
    if (opt) subChart.setOption(opt, true)
  }
}

async function loadDayKline() {
  klineLoading.value = true
  try {
    const data = await fetchKlineForTab('1d', 250)
    klineData.value = data
    await nextTick()
    renderKline(klineChartRef.value, klineSubRef.value, data, klineIndicator.value)
    nextTick(() => resizeCharts())
  } finally {
    klineLoading.value = false
  }
}

async function loadWeekKline() {
  klineLoading.value = true
  try {
    const data = await fetchKlineForTab('1w', 250)
    klineWeekData.value = data
    await nextTick()
    renderKline(klineWeekChartRef.value, klineWeekSubRef.value, data, klineWeekIndicator.value)
    nextTick(() => resizeCharts())
  } finally {
    klineLoading.value = false
  }
}

async function loadMonthKline() {
  klineLoading.value = true
  try {
    const data = await fetchKlineForTab('1M', 250)
    klineMonthData.value = data
    await nextTick()
    renderKline(klineMonthChartRef.value, klineMonthSubRef.value, data, klineMonthIndicator.value)
    nextTick(() => resizeCharts())
  } finally {
    klineLoading.value = false
  }
}

// 分时：用当日 1m 近似，无则占位
async function loadIntraday() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const data = await marketApi.getKline(symbol.value, '1m', 240, today, today)
    const list = Array.isArray(data) ? data : []
    await nextTick()
    const priceDom = intradayChartRef.value
    const volDom = intradayVolRef.value
    if (!priceDom || !volDom) return
    if (list.length === 0) {
      if (!intradayChart) intradayChart = echarts.init(priceDom)
      intradayChart.setOption({
        ...CHART_DARK,
        title: { text: '分时 - 暂无数据（待接口：分时或当日 1m）', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
        xAxis: { type: 'category', data: [], axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: [] }]
      }, true)
      if (!intradayVolChart) intradayVolChart = echarts.init(volDom)
      intradayVolChart.setOption({
        ...CHART_DARK,
        title: { text: '分时量 - 待数据', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: [] }]
      }, true)
      return
    }
    const times = list.map(item => (item.time || item.date || '').slice(11, 16))
    const prices = list.map(item => parseFloat(item.close || 0))
    const preClose = quote.value.pre_close || list[0]?.close || 0
    const avgPrices = []
    let sum = 0
    for (let i = 0; i < prices.length; i++) {
      sum += prices[i]
      avgPrices.push((sum / (i + 1)).toFixed(2))
    }
    const vols = list.map(item => parseInt(item.volume || 0, 10))
    if (!intradayChart) intradayChart = echarts.init(priceDom)
    intradayChart.setOption({
      ...CHART_DARK,
      animation: false,
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: { type: 'category', data: times, boundaryGap: false, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: { show: false } },
      yAxis: { type: 'value', scale: true, axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine },
      series: [
        { name: '价格', type: 'line', data: prices, smooth: false, symbol: 'none', lineStyle: { width: 2, color: '#5c9eed' } },
        { name: '均价', type: 'line', data: avgPrices, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#ffc107' } }
      ]
    }, true)
    if (!intradayVolChart) intradayVolChart = echarts.init(volDom)
    intradayVolChart.setOption({
      ...CHART_DARK,
      animation: false,
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: { type: 'category', data: times, boundaryGap: true, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel },
      yAxis: { type: 'value', axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: CHART_DARK.splitLine },
      series: [{ name: '量', type: 'bar', data: vols, itemStyle: { color: '#5c9eed' } }]
    }, true)
  } catch (e) {
    console.error('分时加载失败:', e)
  }
}

watch(chartTab, (name) => {
  if (name === 'day') loadDayKline()
  else if (name === 'week') loadWeekKline()
  else if (name === 'month') loadMonthKline()
  else if (name === 'intraday') loadIntraday()
})

// 拖拽调整左侧宽度
function startResize(e) {
  resizing = true
  const startX = e.clientX
  const startW = leftPanelWidth.value || (document.querySelector('.panel-left')?.offsetWidth || 600)
  leftPanelWidth.value = startW
  function move(ev) {
    if (!resizing) return
    const dx = ev.clientX - startX
    const w = Math.max(200, Math.min(window.innerWidth - 200, startW + dx))
    leftPanelWidth.value = w
    leftPanelWidthPx.value = w + 'px'
  }
  function up() {
    resizing = false
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

function goBack() {
  router.back()
}

async function triggerUpdateData() {
  if (!symbol.value) return
  const sourceType = dataSourceStore.currentDataSource?.source_type || 'qmt'
  const sourceId = dataSourceStore.currentId ?? null
  if (dataSourceStore.list?.length > 0 && !dataSourceStore.currentId) {
    ElMessage.warning('请先在顶栏选择数据源')
    return
  }
  updateDataLoading.value = true
  try {
    const res = await securityApi.updateData(symbol.value, sourceType, sourceId)
    if (res?.hint) {
      ElMessage.warning(res.hint)
    } else if (res && (res.daily != null || res.weekly != null || res.monthly != null || res.ticks_dates != null)) {
      ElMessage.success('数据已更新')
      await refreshCharts()
    }
  } catch (e) {
    ElMessage.error(e?.message || '更新数据失败')
  } finally {
    updateDataLoading.value = false
  }
}

function refreshCharts() {
  if (chartTab.value === 'intraday') loadIntraday()
  else if (chartTab.value === 'day') loadDayKline()
  else if (chartTab.value === 'week') loadWeekKline()
  else if (chartTab.value === 'month') loadMonthKline()
  fetchQuote()
}

onMounted(async () => {
  window.addEventListener('resize', resizeCharts)
  await fetchSecurityInfo()
  await fetchQuote()
  if (chartTab.value === 'intraday') loadIntraday()
  else if (chartTab.value === 'day') loadDayKline()
  else if (chartTab.value === 'week') loadWeekKline()
  else if (chartTab.value === 'month') loadMonthKline()
})

function resizeCharts() {
  if (intradayChart) intradayChart.resize()
  if (intradayVolChart) intradayVolChart.resize()
  ;[klineChartRef, klineSubRef, klineWeekChartRef, klineWeekSubRef, klineMonthChartRef, klineMonthSubRef].forEach(refEl => {
    if (refEl?.value) {
      const ch = echarts.getInstanceByDom(refEl.value)
      if (ch) ch.resize()
    }
  })
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  if (intradayChart) { intradayChart.dispose(); intradayChart = null }
  if (intradayVolChart) { intradayVolChart.dispose(); intradayVolChart = null }
  ;[klineChartRef, klineSubRef, klineWeekChartRef, klineWeekSubRef, klineMonthChartRef, klineMonthSubRef].forEach(refEl => {
    if (refEl?.value) {
      const ch = echarts.getInstanceByDom(refEl.value)
      if (ch) ch.dispose()
    }
  })
})
</script>

<style scoped>
.security-detail {
  padding: 0;
  margin: 0;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0d0d0d;
  color: #e0e0e0;
}

.detail-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  border-bottom: 1px solid #333;
  background: #0d0d0d;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.security-name {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.security-symbol {
  font-size: 12px;
  color: #b0b0b0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.layout-switch {
  margin-right: 4px;
}

.security-detail :deep(.el-radio-button__inner) {
  background: #1a1a1a;
  border-color: #333;
  color: #b0b0b0;
}

.security-detail :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #2a2a2a;
  border-color: #555;
  color: #e0e0e0;
}

.security-detail :deep(.el-button) {
  background: #1a1a1a;
  border-color: #333;
  color: #e0e0e0;
}

.security-detail :deep(.el-button:hover) {
  background: #2a2a2a;
  border-color: #555;
  color: #e0e0e0;
}

.main-area {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

.panel-left {
  flex-shrink: 0;
  min-width: 200px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
  padding: 0;
  background: #0d0d0d;
}

.panel-left[style*="100%"] {
  border-right: none;
}

.resizer {
  width: 6px;
  flex-shrink: 0;
  background: #262626;
  cursor: col-resize;
}

.resizer:hover {
  background: #404040;
}

.panel-right {
  min-width: 200px;
  overflow: auto;
  background: #0d0d0d;
  padding: 0;
}

.chart-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0;
}

.chart-tabs :deep(.el-tabs__header) {
  margin: 0 0 4px 0;
  padding: 0 8px;
}

.chart-tabs :deep(.el-tabs__nav-wrap::after),
.chart-tabs :deep(.el-tabs__nav-wrap) {
  background: #0d0d0d;
  border-bottom: 1px solid #333;
}

.chart-tabs :deep(.el-tabs__item) {
  color: #b0b0b0;
  font-size: 12px;
}

.chart-tabs :deep(.el-tabs__item.is-active) {
  color: #e0e0e0;
}

.chart-tabs :deep(.el-tabs__ink-bar) {
  background: #5c9eed;
}

.chart-tabs :deep(.el-tabs__active-bar) {
  background: #5c9eed;
}

.chart-tabs :deep(.el-tabs__nav) {
  border: none;
}

.chart-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.chart-tabs :deep(.el-tab-pane) {
  height: 100%;
  padding: 0;
}

.intraday-wrap {
  display: flex;
  height: 100%;
  min-height: 400px;
}

.intraday-charts {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-half {
  flex: 1;
  min-height: 180px;
}

.chart-dom {
  width: 100%;
  height: 100%;
  min-height: 160px;
}

.intraday-side {
  width: 200px;
  flex-shrink: 0;
  padding: 4px;
  border-left: 1px solid #333;
  overflow-y: auto;
  background: #0d0d0d;
}

.side-block {
  margin-bottom: 8px;
}

.side-block:last-child {
  margin-bottom: 0;
}

.five-level-table {
  font-size: 12px;
}

.security-detail :deep(.five-level-table.el-table) {
  background: transparent;
  color: #e0e0e0;
}

.security-detail :deep(.five-level-table .el-table__header-wrapper),
.security-detail :deep(.five-level-table .el-table__body-wrapper),
.security-detail :deep(.five-level-table th),
.security-detail :deep(.five-level-table td) {
  background: transparent !important;
  border-color: #262626;
  color: #b0b0b0;
}

.security-detail :deep(.five-level-table .el-table__row:hover > td) {
  background: #1a1a1a !important;
}

.trade-placeholder {
  font-size: 12px;
  color: #808080;
  padding: 4px 0;
}

.kline-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
  padding: 0;
}

.kline-chart-dom {
  flex: 1;
  min-height: 200px;
}

.kline-indicator {
  flex-shrink: 0;
  padding: 2px 8px;
}

.security-detail :deep(.kline-indicator .el-radio-button__inner) {
  font-size: 12px;
  padding: 4px 8px;
}

.f10-panel {
  padding: 8px;
}

.security-detail :deep(.f10-panel .el-collapse) {
  border: none;
}

.security-detail :deep(.f10-panel .el-collapse-item__header) {
  background: #1a1a1a;
  border-color: #333;
  color: #e0e0e0;
  font-size: 13px;
  padding: 6px 8px;
}

.security-detail :deep(.f10-panel .el-collapse-item__wrap) {
  background: #0d0d0d;
  border-color: #333;
}

.security-detail :deep(.f10-panel .el-collapse-item__content) {
  padding: 6px 8px;
}

.f10-placeholder {
  font-size: 12px;
  color: #808080;
  padding: 4px 0;
}
</style>
