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
      <!-- 左侧面板：行情（K线在上、技术指标在下，中间可拖拽） -->
      <div
        v-show="layoutMode !== 'right'"
        class="panel-left"
        :style="{ width: layoutMode === 'left' ? '100%' : leftPanelWidthPx }"
      >
        <div class="panel-left-inner">
          <el-tabs v-model="chartTab" class="chart-tabs">
            <el-tab-pane label="分时" name="intraday" lazy>
              <DayLineChart ref="dayLineRef" :symbol="symbol" />
            </el-tab-pane>
            <el-tab-pane label="日K" name="day" lazy>
              <KlineChart ref="klineDayRef" :symbol="symbol" period="1d" style="height: 100%;" />
            </el-tab-pane>
            <el-tab-pane label="周K" name="week" lazy>
              <KlineChart ref="klineWeekRef" :symbol="symbol" period="1w" style="height: 100%;" />
            </el-tab-pane>
            <el-tab-pane label="月K" name="month" lazy>
              <KlineChart ref="klineMonthRef" :symbol="symbol" period="1M" style="height: 100%;" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <!-- 可拖拽分割条（仅双侧时显示） -->
      <div
        v-show="layoutMode === 'both'"
        class="resizer"
        @mousedown="startResize"
      ></div>

      <!-- 右侧面板：F10 / 除权除息 -->
      <div
        v-show="layoutMode !== 'left'"
        class="panel-right"
        :style="{ width: layoutMode === 'right' ? '100%' : undefined, flex: layoutMode === 'both' ? 1 : undefined }"
      >
        <div class="f10-panel">
          <el-tabs v-model="rightTab" class="f10-tabs">
            <el-tab-pane label="F10" name="f10">
              <el-collapse v-model="f10ActiveNames">
                <el-collapse-item title="操盘必读" name="read">
                  <div class="f10-placeholder">操盘必读 - 待接口</div>
                </el-collapse-item>
                <el-collapse-item title="财务分析" name="finance">
                  <div class="f10-placeholder">财务分析 - 待接口</div>
                </el-collapse-item>
              </el-collapse>
            </el-tab-pane>
            <el-tab-pane label="除权除息" name="divid">
              <DividFactorsTable v-if="rightTab === 'divid'" :symbol="symbol" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { securityApi } from '../api/security'
import { marketApi } from '../api/market'
import { useDataSourceStore } from '../stores/dataSource'
import DividFactorsTable from './components/diagram/DividFactorsTable.vue'
import DayLineChart from './components/diagram/DayLineChart.vue'
import KlineChart from './components/diagram/KlineChart.vue'

const dataSourceStore = useDataSourceStore()

// localStorage 键名：证券详情页左右切分宽度、左侧上下切分底部高度
const STORAGE_LEFT_PANEL_WIDTH = 'security-detail-left-panel-width'
const STORAGE_LEFT_PANEL_BOTTOM_HEIGHT = 'security-detail-left-panel-bottom-height'
const DEFAULT_LEFT_PANEL_BOTTOM_HEIGHT = 280

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
// 左侧面板宽度（像素），双侧时有效；从 localStorage 恢复
function getInitialLeftPanelWidth() {
  try {
    const v = localStorage.getItem(STORAGE_LEFT_PANEL_WIDTH)
    if (v != null) {
      const n = parseInt(v, 10)
      if (Number.isFinite(n) && n >= 200) return n
    }
  } catch (_) {}
  return undefined
}
const leftPanelWidth = ref(getInitialLeftPanelWidth() ?? 0)
const leftPanelWidthPx = ref(
  leftPanelWidth.value ? `${leftPanelWidth.value}px` : '60%'
)
// 左侧上下切分：底部区域高度（px），从 localStorage 恢复，默认 280
function getInitialLeftPanelBottomHeight() {
  try {
    const v = localStorage.getItem(STORAGE_LEFT_PANEL_BOTTOM_HEIGHT)
    if (v != null) {
      const n = parseInt(v, 10)
      if (Number.isFinite(n) && n >= 80) return n
    }
  } catch (_) {}
  return DEFAULT_LEFT_PANEL_BOTTOM_HEIGHT
}
const leftPanelBottomHeight = ref(getInitialLeftPanelBottomHeight())
let resizing = false
let resizingVertical = false

// 分时 / 日K / 周K / 月K
const chartTab = ref('intraday')
const dayLineRef = ref(null)
const klineDayRef = ref(null)
const klineWeekRef = ref(null)
const klineMonthRef = ref(null)
const intradayChartRef = ref(null)
const intradayVolRef = ref(null)
const klineChartRef = ref(null)
const klineSubRef = ref(null)
const klineWeekChartRef = ref(null)
const klineWeekSubRef = ref(null)
const klineMonthChartRef = ref(null)
const klineMonthSubRef = ref(null)
const panelLeftRef = ref(null)
// K 线主图 hover 时的数据索引，null 表示显示最新一根
const klineHoverIndex = ref(null)

const klineIndicator = ref('volume')
const klineWeekIndicator = ref('volume')
const klineMonthIndicator = ref('volume')

const klineData = ref([])
const klineWeekData = ref([])
const klineMonthData = ref([])
const klineLoading = ref(false)
// 预计算缓存：按 tab 存 MA 与副图指标，点击图例时 O(1) 取值
const klineCache = ref({ day: null, week: null, month: null })

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
const rightTab = ref('f10')

// 当前 K 线主图展示的数据（点击时为该根，否则为最新一根）；含日期与全部 MA，优先用缓存 O(1)
const displayKlineOHLC = computed(() => {
  const tab = chartTab.value
  const data = tab === 'day' ? klineData.value : tab === 'week' ? klineWeekData.value : klineMonthData.value
  const cache = tab === 'day' ? klineCache.value?.day : tab === 'week' ? klineCache.value?.week : klineCache.value?.month
  if (!data || data.length === 0) {
    return { date: '', open: '--', close: '--', high: '--', low: '--', ma5: '--', ma10: '--', ma20: '--', ma30: '--', ma60: '--', ma120: '--', ma250: '--' }
  }
  const idx = klineHoverIndex.value != null ? Math.max(0, Math.min(klineHoverIndex.value, data.length - 1)) : data.length - 1
  const bar = data[idx]
  const t = bar.time ?? bar.timestamp ?? bar.date ?? ''
  const v = (arr, i) => (arr && arr[i] !== undefined ? (arr[i] === '-' ? '--' : arr[i]) : '--')
  const ma = cache?.ma
  return {
    date: formatKlineTimeForAxis(t),
    open: formatPrice(bar.open),
    close: formatPrice(bar.close),
    high: formatPrice(bar.high),
    low: formatPrice(bar.low),
    ma5: ma ? v(ma.ma5, idx) : v(calcMA(data, 5), idx),
    ma10: ma ? v(ma.ma10, idx) : v(calcMA(data, 10), idx),
    ma20: ma ? v(ma.ma20, idx) : v(calcMA(data, 20), idx),
    ma30: ma ? v(ma.ma30, idx) : v(calcMA(data, 30), idx),
    ma60: ma ? v(ma.ma60, idx) : v(calcMA(data, 60), idx),
    ma120: ma ? v(ma.ma120, idx) : v(calcMA(data, 120), idx),
    ma250: ma ? v(ma.ma250, idx) : v(calcMA(data, 250), idx)
  }
})

// 当前副图指标展示的数据（与主图同索引）；优先用缓存 O(1)
const displaySubIndicator = computed(() => {
  const tab = chartTab.value
  const ind = tab === 'day' ? klineIndicator.value : tab === 'week' ? klineWeekIndicator.value : klineMonthIndicator.value
  const data = tab === 'day' ? klineData.value : tab === 'week' ? klineWeekData.value : klineMonthData.value
  const sub = tab === 'day' ? klineCache.value?.day?.sub : tab === 'week' ? klineCache.value?.week?.sub : klineCache.value?.month?.sub
  if (!data || data.length === 0) return { date: '', text: '--' }
  const idx = klineHoverIndex.value != null ? Math.max(0, Math.min(klineHoverIndex.value, data.length - 1)) : data.length - 1
  const date = formatKlineTimeForAxis(data[idx].time ?? data[idx].timestamp ?? data[idx].date ?? '')
  if (ind === 'volume') {
    const vol = parseInt(data[idx].volume || 0, 10)
    return { date, text: `成交量 ${formatVolume(vol)}` }
  }
  if (ind === 'amount') {
    const amt = parseFloat(data[idx].amount || 0)
    return { date, text: `成交额 ${formatAmount(amt)}` }
  }
  if (ind === 'kdj') {
    const { k, d, j } = sub?.kdj ?? calcKDJ(data)
    return { date, text: `K: ${k[idx]}  D: ${d[idx]}  J: ${j[idx]}` }
  }
  if (ind === 'rsi') {
    const rsi = sub?.rsi ?? calcRSI(data)
    return { date, text: `RSI: ${rsi[idx]}` }
  }
  if (ind === 'macd') {
    const { dif, dea, macd } = sub?.macd ?? calcMACD(data)
    return { date, text: `DIF: ${dif[idx]}  DEA: ${dea[idx]}  MACD: ${macd[idx]}` }
  }
  return { date, text: '--' }
})

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

// 将 K 线时间字段（UNIX 秒/毫秒或日期字符串）转为横轴显示日期 YYYY-MM-DD
function formatKlineTimeForAxis(t) {
  if (t == null || t === '') return ''
  if (typeof t === 'string') {
    if (t.includes(' ')) return t.slice(0, 16)
    if (/^\d{4}-\d{2}-\d{2}/.test(t)) return t.slice(0, 10)
    const n = parseInt(t, 10)
    if (Number.isFinite(n)) t = n
  }
  if (typeof t === 'number') {
    const ms = t < 1e12 ? t * 1000 : t
    const d = new Date(ms)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return String(t).slice(0, 10)
}

// 上下图统一 grid：约 10px 留白避免文字被裁切，y 轴宽度固定（左侧多 20px 给标签）
const GRID_LEFT = 82
const GRID_RIGHT = 22
const GRID_BOTTOM = 14
const GRID_TOP = 14

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

// KDJ，O(n)：滑动窗口用单调队列（索引前移不 shift）求区间 min/max
function calcKDJ(data, n = 9, m1 = 3, m2 = 3) {
  const k = [], d = [], j = []
  let kNum = 50, dNum = 50
  const lowArr = data.map(x => parseFloat(x.low) || 0)
  const highArr = data.map(x => parseFloat(x.high) || 0)
  const qMin = []
  const qMax = []
  let minHead = 0
  let maxHead = 0
  for (let i = 0; i < data.length; i++) {
    const left = i - n + 1
    while (minHead < qMin.length && qMin[minHead] < left) minHead++
    while (maxHead < qMax.length && qMax[maxHead] < left) maxHead++
    while (qMin.length > minHead && lowArr[qMin[qMin.length - 1]] >= lowArr[i]) qMin.pop()
    qMin.push(i)
    while (qMax.length > maxHead && highArr[qMax[qMax.length - 1]] <= highArr[i]) qMax.pop()
    qMax.push(i)
    if (i < n - 1) {
      k.push('-')
      d.push('-')
      j.push('-')
      continue
    }
    const low = lowArr[qMin[minHead]]
    const high = highArr[qMax[maxHead]]
    const close = parseFloat(data[i].close) || 0
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

function buildKlineOption(rawData, maCache) {
  if (!rawData || rawData.length === 0) return null
  const times = rawData.map(item => {
    const t = item.time ?? item.timestamp ?? item.date ?? ''
    return formatKlineTimeForAxis(t)
  })
  const o = rawData.map(x => parseFloat(x.open || 0))
  const c = rawData.map(x => parseFloat(x.close || 0))
  const l = rawData.map(x => parseFloat(x.low || 0))
  const h = rawData.map(x => parseFloat(x.high || 0))
  const candleData = rawData.map((_, i) => [o[i], c[i], l[i], h[i]])

  const ma5 = maCache?.ma5 ?? calcMA(rawData, 5)
  const ma10 = maCache?.ma10 ?? calcMA(rawData, 10)
  const ma20 = maCache?.ma20 ?? calcMA(rawData, 20)
  const ma30 = maCache?.ma30 ?? calcMA(rawData, 30)
  const ma60 = maCache?.ma60 ?? calcMA(rawData, 60)
  const ma120 = maCache?.ma120 ?? calcMA(rawData, 120)
  const ma250 = maCache?.ma250 ?? calcMA(rawData, 250)

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
    tooltip: {
      show: true,
      trigger: 'axis',
      formatter: () => '',
      axisPointer: { type: 'cross', lineStyle: { color: '#ffeb3b', type: 'solid', width: 1 } }
    },
    grid: { left: GRID_LEFT, right: GRID_RIGHT, bottom: GRID_BOTTOM, top: GRID_TOP, containLabel: false },
    graphic: [
      { id: HOVER_CROSS_V_ID, type: 'line', invisible: true, shape: { x1: 0, y1: 0, x2: 0, y2: 0 }, lineStyle: { type: 'dashed', color: '#fff', width: 1 } },
      { id: HOVER_CROSS_H_ID, type: 'line', invisible: true, shape: { x1: 0, y1: 0, x2: 0, y2: 0 }, lineStyle: { type: 'dashed', color: '#fff', width: 1 } }
    ],
    xAxis: {
      type: 'category',
      data: times,
      boundaryGap: true,
      axisLabel: { show: false },
      axisLine: CHART_DARK.axisLine,
      splitLine: { show: false }
    },
    yAxis: { type: 'value', scale: true, min: 'dataMin', max: 'dataMax', axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine },
    series
  }
}

function buildSubOption(rawData, type, subCache) {
  if (!rawData || rawData.length === 0) return null
  const times = rawData.map(item => {
    const t = item.time ?? item.timestamp ?? item.date ?? ''
    return formatKlineTimeForAxis(t)
  })
  const grid = { left: GRID_LEFT, right: GRID_RIGHT, bottom: GRID_BOTTOM, top: GRID_TOP, containLabel: false }
  const xAxis = {
    type: 'category',
    data: times,
    boundaryGap: true,
    axisLabel: { show: false },
    axisLine: CHART_DARK.axisLine,
    splitLine: { show: false }
  }

  const xAxisMerged = xAxis
  const axisCommon = { axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine, axisLabel: CHART_DARK.axisLabel }
  if (type === 'volume') {
    const vol = subCache?.volume?.data ?? rawData.map(x => parseInt(x.volume || 0, 10))
    const colors = subCache?.volume?.colors ?? rawData.map((x, i) => (i > 0 && x.close >= rawData[i - 1].close ? '#ef5350' : '#26a69a'))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { show: true, trigger: 'axis', formatter: () => '', axisPointer: { type: 'cross' } },
      grid,
      xAxis: xAxisMerged,
      yAxis: { type: 'value', ...axisCommon, axisLabel: { formatter: v => formatVolume(v), ...CHART_DARK.axisLabel } },
      series: [{ name: '成交量', type: 'bar', data: vol, itemStyle: { color: (params) => colors[params.dataIndex] } }]
    }
  }
  if (type === 'amount') {
    const amount = subCache?.amount?.data ?? rawData.map(x => parseFloat(x.amount || 0))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { show: true, trigger: 'axis', formatter: () => '', axisPointer: { type: 'cross' } },
      grid,
      xAxis: xAxisMerged,
      yAxis: { type: 'value', ...axisCommon, axisLabel: { formatter: v => (v >= 1e8 ? (v / 1e8).toFixed(1) + '亿' : (v / 1e4).toFixed(0) + '万'), ...CHART_DARK.axisLabel } },
      series: [{ name: '成交额', type: 'bar', data: amount, itemStyle: { color: '#5c9eed' } }]
    }
  }
  if (type === 'kdj') {
    const { k, d, j } = subCache?.kdj ?? calcKDJ(rawData)
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { show: true, trigger: 'axis', formatter: () => '', axisPointer: { type: 'cross' } },
      grid,
      xAxis: xAxisMerged,
      yAxis: { type: 'value', min: 0, max: 100, ...axisCommon },
      series: [
        { name: 'K', type: 'line', data: k, smooth: false, symbol: 'none' },
        { name: 'D', type: 'line', data: d, smooth: false, symbol: 'none' },
        { name: 'J', type: 'line', data: j, smooth: false, symbol: 'none' }
      ]
    }
  }
  if (type === 'rsi') {
    const rsi = subCache?.rsi ?? calcRSI(rawData)
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { show: true, trigger: 'axis', formatter: () => '', axisPointer: { type: 'cross' } },
      grid,
      xAxis: xAxisMerged,
      yAxis: { type: 'value', min: 0, max: 100, ...axisCommon },
      series: [{ name: 'RSI', type: 'line', data: rsi, smooth: false, symbol: 'none' }]
    }
  }
  if (type === 'macd') {
    const { dif, dea, macd } = subCache?.macd ?? calcMACD(rawData)
    const barColors = macd.map((v, i) => (v !== '-' && parseFloat(v) >= 0 ? '#ef5350' : '#26a69a'))
    return {
      ...CHART_DARK,
      animation: false,
      tooltip: { show: true, trigger: 'axis', formatter: () => '', axisPointer: { type: 'cross' } },
      grid,
      xAxis: xAxisMerged,
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

function buildKlineCache(data) {
  if (!data || data.length === 0) return null
  const vol = data.map(x => parseInt(x.volume || 0, 10))
  const volColors = data.map((x, i) => (i > 0 && parseFloat(x.close) >= parseFloat(data[i - 1].close) ? '#ef5350' : '#26a69a'))
  const amount = data.map(x => parseFloat(x.amount || 0))
  return {
    ma: {
      ma5: calcMA(data, 5),
      ma10: calcMA(data, 10),
      ma20: calcMA(data, 20),
      ma30: calcMA(data, 30),
      ma60: calcMA(data, 60),
      ma120: calcMA(data, 120),
      ma250: calcMA(data, 250)
    },
    sub: {
      volume: { data: vol, colors: volColors },
      amount: { data: amount },
      kdj: calcKDJ(data),
// 仅主图显示十字线，副图不显示以减轻重绘
      rsi: calcRSI(data),
      macd: calcMACD(data)
    }
// 仅主图显示十字线，副图不显示以减轻重绘
// 主图十字线：hover 为白色虚线十字，点击锚定为黄色实线十字
  }
}

const HOVER_CROSS_V_ID = 'klineHoverCrossV'
const HOVER_CROSS_H_ID = 'klineHoverCrossH'

function updateHoverCross(mainChart, dataIndex, yPixel, visible) {
  if (!mainChart || !mainChart.setOption) return
  if (!visible || dataIndex == null) {
    mainChart.setOption({
      graphic: [
        { id: HOVER_CROSS_V_ID, invisible: true },
        { id: HOVER_CROSS_H_ID, invisible: true }
      ]
    })
    return
  }
  const point = mainChart.convertToPixel({ seriesIndex: 0 }, [dataIndex, 0])
  if (point == null || !Array.isArray(point)) return
  const x = point[0]
  const w = mainChart.getWidth()
  const h = mainChart.getHeight()
  const y = yPixel != null ? yPixel : point[1]
  mainChart.setOption({
    graphic: [
      { id: HOVER_CROSS_V_ID, shape: { x1: x, y1: 0, x2: x, y2: h }, invisible: false },
      { id: HOVER_CROSS_H_ID, shape: { x1: 0, y1: y, x2: w, y2: y }, invisible: false }
    ]
  })
}

function syncCrosshair(mainChart, subChart, dataIndex) {
  if (mainChart && mainChart.dispatchAction) {
    mainChart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex })
  }
  if (subChart && subChart.dispatchAction) {
    subChart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex })
  }
}

function hideCrosshair(mainChart, subChart) {
  if (mainChart && mainChart.setOption) {
    updateHoverCross(mainChart, null, null, false)
  }
  if (mainChart && mainChart.dispatchAction) {
    mainChart.dispatchAction({ type: 'hideTip' })
  }
  if (subChart && subChart.dispatchAction) {
    subChart.dispatchAction({ type: 'hideTip' })
  }
}

function bindKlineHover(mainChart, subChart, dataLen) {
  let lastDataIndex = -1
  let lastHoverIndex = -1
  function setSelected(dataIndex) {
    if (dataIndex < 0 || dataIndex >= dataLen) return
    if (dataIndex === lastDataIndex) return
    lastDataIndex = dataIndex
    klineHoverIndex.value = dataIndex
    updateHoverCross(mainChart, null, null, false)
    syncCrosshair(mainChart, subChart, dataIndex)
  }
  function clearSelected() {
    if (lastDataIndex === -1) return
    lastDataIndex = -1
    klineHoverIndex.value = null
    hideCrosshair(mainChart, subChart)
  }
  if (mainChart && mainChart.getZr) {
    const zr = mainChart.getZr()
    zr.off('click')
    zr.off('mousemove')
    zr.off('mouseout')
    zr.on('click', (e) => {
      const result = mainChart.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
      if (result != null && Array.isArray(result) && result.length >= 1) {
        setSelected(Math.round(result[0]))
      }
    })
    zr.on('mousemove', (e) => {
      if (lastDataIndex >= 0) return
      const result = mainChart.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
      if (result != null && Array.isArray(result) && result.length >= 1) {
        const idx = Math.round(result[0])
        if (idx >= 0 && idx < dataLen && idx !== lastHoverIndex) {
          lastHoverIndex = idx
          updateHoverCross(mainChart, idx, e.offsetY, true)
        }
      }
    })
    zr.on('mouseout', () => {
      lastHoverIndex = -1
      updateHoverCross(mainChart, null, null, false)
    })
  }
  if (subChart && subChart.getZr) {
    const zr = subChart.getZr()
    zr.off('click')
    zr.on('click', (e) => {
      const result = subChart.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
      if (result != null && Array.isArray(result) && result.length >= 1) {
        setSelected(Math.round(result[0]))
      }
    })
  }
}

function renderKline(chartDom, subDom, rawData, indicator, tabCache) {
  if (!chartDom || !rawData.length) return
  const mainChart = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom)
  const opt = buildKlineOption(rawData, tabCache?.ma)
  if (opt) mainChart.setOption(opt, true)
  let subChart = null
  if (subDom && rawData.length) {
    subChart = echarts.getInstanceByDom(subDom) || echarts.init(subDom)
    const subOpt = buildSubOption(rawData, indicator, tabCache?.sub)
    if (subOpt) subChart.setOption(subOpt, true)
  }
  bindKlineHover(mainChart, subChart, rawData.length)
}

function updateKlineIndicator() {
  if (klineSubRef.value && klineData.value.length) {
    const subChart = echarts.getInstanceByDom(klineSubRef.value) || echarts.init(klineSubRef.value)
    const opt = buildSubOption(klineData.value, klineIndicator.value, klineCache.value?.day?.sub ?? null)
    if (opt) subChart.setOption(opt, true)
  }
}

function updateKlineWeekIndicator() {
  if (klineWeekSubRef.value && klineWeekData.value.length) {
    const subChart = echarts.getInstanceByDom(klineWeekSubRef.value) || echarts.init(klineWeekSubRef.value)
    const opt = buildSubOption(klineWeekData.value, klineWeekIndicator.value, klineCache.value?.week?.sub ?? null)
    if (opt) subChart.setOption(opt, true)
  }
}

function updateKlineMonthIndicator() {
  if (klineMonthSubRef.value && klineMonthData.value.length) {
    const subChart = echarts.getInstanceByDom(klineMonthSubRef.value) || echarts.init(klineMonthSubRef.value)
    const opt = buildSubOption(klineMonthData.value, klineMonthIndicator.value, klineCache.value?.month?.sub ?? null)
    if (opt) subChart.setOption(opt, true)
  }
}

async function loadDayKline() {
  klineLoading.value = true
  try {
    const data = await fetchKlineForTab('1d', 250)
    klineData.value = data
    klineCache.value = { ...klineCache.value, day: buildKlineCache(data) }
    await nextTick()
    renderKline(klineChartRef.value, klineSubRef.value, data, klineIndicator.value, klineCache.value?.day ?? null)
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
    klineCache.value = { ...klineCache.value, week: buildKlineCache(data) }
    await nextTick()
    renderKline(klineWeekChartRef.value, klineWeekSubRef.value, data, klineWeekIndicator.value, klineCache.value?.week ?? null)
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
    klineCache.value = { ...klineCache.value, month: buildKlineCache(data) }
    await nextTick()
    renderKline(klineMonthChartRef.value, klineMonthSubRef.value, data, klineMonthIndicator.value, klineCache.value?.month ?? null)
    nextTick(() => resizeCharts())
  } finally {
    klineLoading.value = false
  }
}

// 分时：请求 ticks 接口原样数据，按整分钟聚合后渲染（价格取分钟最后 lastClose，成交量取分钟内 amount 累加）
async function loadIntraday() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const data = await marketApi.getTicks(symbol.value, today)
    const list = Array.isArray(data) ? data : []
    await nextTick()
    const priceDom = intradayChartRef.value
    const volDom = intradayVolRef.value
    if (!priceDom || !volDom) return
    if (list.length === 0) {
      if (!intradayChart) intradayChart = echarts.init(priceDom)
      intradayChart.setOption({
        ...CHART_DARK,
        title: { text: '分时 - 暂无数据', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
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
    // openInt: 12=集合竞价C, 13=连续交易T。按分钟聚合且区分 12/13；集合竞价无 lastPrice 时用 askPrice[0] 或 bidPrice[0]（买一/卖一）
    const OPENINT_CALL_AUCTION = 12
    const OPENINT_CONTINUOUS = 13
    const minuteMap = new Map()
    for (const item of list) {
      const t = item.time != null ? Number(item.time) : NaN
      if (Number.isNaN(t)) continue
      const openInt = item.openInt != null ? parseInt(item.openInt, 10) : 13
      if (openInt !== OPENINT_CALL_AUCTION && openInt !== OPENINT_CONTINUOUS) continue
      const minuteKey = Math.floor(t / 60000)
      const tickvol = parseInt(item.tickvol ?? 0, 10) || 0
      let price
      if (openInt === OPENINT_CALL_AUCTION) {
        const ask = Array.isArray(item.askPrice) ? item.askPrice[0] : null
        const bid = Array.isArray(item.bidPrice) ? item.bidPrice[0] : null
        price = parseFloat(ask ?? bid ?? item.lastPrice ?? item.close ?? 0)
      } else {
        price = parseFloat(item.lastPrice ?? item.close ?? 0)
      }
      if (!minuteMap.has(minuteKey)) {
        minuteMap.set(minuteKey, { 12: null, 13: null })
      }
      const row = minuteMap.get(minuteKey)
      if (!row[openInt]) row[openInt] = { time: t, price, tickvol }
      else {
        row[openInt].time = t
        row[openInt].price = price
        row[openInt].tickvol += tickvol
      }
    }
    const sorted = Array.from(minuteMap.entries()).sort((a, b) => a[0] - b[0])
    const times = sorted.map(([k]) => {
      const d = new Date(k * 60000)
      return d.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false })
    })
    const pricesCallAuction = sorted.map(([, v]) => (v[OPENINT_CALL_AUCTION] ? v[OPENINT_CALL_AUCTION].price : null))
    const pricesContinuous = sorted.map(([, v]) => (v[OPENINT_CONTINUOUS] ? v[OPENINT_CONTINUOUS].price : null))
    const volsCallAuction = sorted.map(([, v]) => (v[OPENINT_CALL_AUCTION] ? v[OPENINT_CALL_AUCTION].tickvol : 0))
    const volsContinuous = sorted.map(([, v]) => (v[OPENINT_CONTINUOUS] ? v[OPENINT_CONTINUOUS].tickvol : 0))
    const preClose = quote.value.pre_close ?? list[0]?.lastClose ?? list[0]?.close ?? 0
    const avgPrices = []
    let sum = 0
    let n = 0
    for (let i = 0; i < pricesContinuous.length; i++) {
      const p = pricesContinuous[i]
      if (p != null) { sum += p; n++ }
      avgPrices.push(n > 0 ? (sum / n).toFixed(2) : null)
    }
    if (!intradayChart) intradayChart = echarts.init(priceDom)
    intradayChart.setOption({
      ...CHART_DARK,
      animation: false,
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: { type: 'category', data: times, boundaryGap: false, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: { show: false } },
      yAxis: { type: 'value', scale: true, axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine },
      series: [
        { name: '集合竞价', type: 'line', data: pricesCallAuction, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#9e9e9e' } },
        { name: '连续交易', type: 'line', data: pricesContinuous, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#5c9eed' } },
        { name: '均价', type: 'line', data: avgPrices, smooth: false, symbol: 'none', connectNulls: true, lineStyle: { width: 1, color: '#ffc107' } }
      ]
    }, true)
    if (!intradayVolChart) intradayVolChart = echarts.init(volDom)
    intradayVolChart.setOption({
      ...CHART_DARK,
      animation: false,
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: { type: 'category', data: times, boundaryGap: true, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel },
      yAxis: { type: 'value', axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: CHART_DARK.splitLine },
      series: [
        { name: '集合竞价量', type: 'bar', stack: 'vol', data: volsCallAuction, itemStyle: { color: '#9e9e9e' } },
        { name: '连续交易量', type: 'bar', stack: 'vol', data: volsContinuous, itemStyle: { color: '#5c9eed' } }
      ]
    }, true)
  } catch (e) {
    console.error('分时加载失败:', e)
  }
}

watch(chartTab, () => {
  klineHoverIndex.value = null
})

// 拖拽调整左侧宽度（结束时写入 localStorage）
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
    try {
      localStorage.setItem(STORAGE_LEFT_PANEL_WIDTH, String(leftPanelWidth.value))
    } catch (_) {}
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

// 拖拽调整左侧上下切分（技术指标区高度，结束时写入 localStorage；拖拽过程中实时 resize 图表）
function startResizeVertical(e) {
  resizingVertical = true
  const startY = e.clientY
  const startH = leftPanelBottomHeight.value
  function move(ev) {
    if (!resizingVertical) return
    const dy = startY - ev.clientY
    const h = Math.max(80, Math.min(600, startH + dy))
    leftPanelBottomHeight.value = h
    nextTick(resizeChartsThrottled)
  }
  function up() {
    resizingVertical = false
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
    try {
      localStorage.setItem(STORAGE_LEFT_PANEL_BOTTOM_HEIGHT, String(leftPanelBottomHeight.value))
    } catch (_) {}
    nextTick(resizeChartsThrottled)
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

async function refreshCharts() {
  if (chartTab.value === 'intraday' && dayLineRef.value?.refresh) {
    await dayLineRef.value.refresh()
  } else if (chartTab.value === 'day' && klineDayRef.value?.refresh) {
    await klineDayRef.value.refresh()
  } else if (chartTab.value === 'week' && klineWeekRef.value?.refresh) {
    await klineWeekRef.value.refresh()
  } else if (chartTab.value === 'month' && klineMonthRef.value?.refresh) {
    await klineMonthRef.value.refresh()
  }
  await fetchQuote()
}

let resizeObserver = null
const RESIZE_THROTTLE_MS = 120
let resizeThrottleTimer = null
function resizeChartsThrottled() {
  if (resizeThrottleTimer != null) return
  resizeThrottleTimer = setTimeout(() => {
    resizeThrottleTimer = null
    resizeCharts()
  }, RESIZE_THROTTLE_MS)
}
onMounted(async () => {
  window.addEventListener('resize', resizeChartsThrottled)
  if (panelLeftRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      nextTick(resizeChartsThrottled)
    })
    resizeObserver.observe(panelLeftRef.value)
  }
  await fetchSecurityInfo()
  await fetchQuote()
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
  if (resizeThrottleTimer != null) clearTimeout(resizeThrottleTimer)
  window.removeEventListener('resize', resizeChartsThrottled)
  if (resizeObserver && panelLeftRef.value) {
    resizeObserver.unobserve(panelLeftRef.value)
    resizeObserver = null
  }
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

.panel-left-inner {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* K 线/分时 主图与副图之间的可拖拽分割条 */
.resizer-kline {
  height: 6px;
  flex-shrink: 0;
  background: #262626;
  cursor: row-resize;
}

.resizer-kline:hover {
  background: #404040;
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
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.intraday-wrap {
  display: flex;
  flex: 1;
  min-height: 0;
}

.intraday-charts {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-half.chart-price {
  flex: 1;
  min-height: 0;
}

.chart-half.chart-volume {
  flex-shrink: 0;
  min-height: 80px;
  overflow: hidden;
}

.chart-dom {
  width: 100%;
  height: 100%;
  min-height: 0;
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
  flex: 1;
  min-height: 0;
  padding: 0;
}

.kline-data-panel {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 4px 8px;
  font-size: 12px;
  color: #e0e0e0;
  background: #0d0d0d;
  border-bottom: 1px solid #262626;
}

.kline-data-panel-sub {
  border-bottom: none;
  border-top: 1px solid #262626;
}

.kline-data-row1,
.kline-data-row2 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  width: 100%;
}

.kline-data-row2 {
  margin-top: 2px;
}

.kline-data-item {
  color: #e0e0e0;
}

.kline-main-area {
  flex: 1;
  min-height: 0;
}

.kline-chart-dom {
  flex: 1;
  min-height: 0;
}

.kline-indicator {
  flex-shrink: 0;
  padding: 2px 8px;
}

.kline-sub-dom {
  flex-shrink: 0;
  min-height: 80px;
  overflow: hidden;
}

.security-detail :deep(.kline-indicator .el-radio-button__inner) {
  font-size: 12px;
  padding: 4px 8px;
}

.f10-panel {
  padding: 8px;
}

.f10-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.f10-tabs :deep(.el-tabs__header) {
  margin: 0 0 4px 0;
}

.f10-tabs :deep(.el-tabs__nav-wrap::after),
.f10-tabs :deep(.el-tabs__nav-wrap) {
  background: #0d0d0d;
  border-bottom: 1px solid #333;
}

.f10-tabs :deep(.el-tabs__item) {
  color: #b0b0b0;
  font-size: 12px;
}

.f10-tabs :deep(.el-tabs__item.is-active) {
  color: #e0e0e0;
}

.f10-tabs :deep(.el-tabs__active-bar),
.f10-tabs :deep(.el-tabs__ink-bar) {
  background: #5c9eed;
}

.f10-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  padding: 0;
}

.divid-panel {
  height: 100%;
}

.security-detail :deep(.el-table) {
  background: transparent;
  color: #e0e0e0;
}

.security-detail :deep(.el-table__inner-wrapper),
.security-detail :deep(.el-table__header-wrapper),
.security-detail :deep(.el-table__body-wrapper),
.security-detail :deep(.el-table th),
.security-detail :deep(.el-table td) {
  background: transparent !important;
  border-color: #262626;
  color: #b0b0b0;
}

.security-detail :deep(.el-table__row:hover > td) {
  background: #1a1a1a !important;
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
