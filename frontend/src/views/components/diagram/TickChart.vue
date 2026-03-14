<template>
  <div class="intraday-wrap">
    <!-- 左侧：主图 + 副图，上下 SplitPanel -->
    <div class="intraday-charts">
      <div class="chart-half chart-price">
        <div ref="intradayChartRef" class="chart-dom"></div>
      </div>
      <div class="resizer-kline" @mousedown="startResizeVertical"></div>
      <div class="chart-half chart-volume" :style="{ height: leftPanelBottomHeight + 'px' }">
        <div class="tick-sub-toolbar">
          <el-radio-group v-model="subChartIndicator" size="small" @change="applyVolChartOption">
            <el-radio-button value="volume">成交量</el-radio-button>
            <el-radio-button value="amount">成交额</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="intradayVolRef" class="chart-dom"></div>
      </div>
    </div>

    <!-- 右侧：五档盘口，固定宽度，原生 table -->
    <div class="intraday-side">
      <div class="side-block">
        <table class="five-level-table">
          <tbody>
            <tr v-for="row in fiveLevelPlaceholder" :key="row.label">
              <td class="cell label">{{ row.label }}</td>
              <td class="cell price">{{ row.price }}</td>
              <td class="cell vol">{{ row.vol }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="side-block">
        <div class="trade-placeholder">最新成交 - 待接口</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { marketApi } from '../../../api/market'
import { securityApi } from '../../../api/security'

const props = defineProps({
  // 证券代码，例如 000001.SZ
  symbol: {
    type: String,
    required: true
  }
})

// 左侧上下切分：底部区域高度（px），从 localStorage 恢复，默认 280
const DEFAULT_LEFT_PANEL_BOTTOM_HEIGHT = 280
const STORAGE_LEFT_PANEL_BOTTOM_HEIGHT = 'security-detail-left-panel-bottom-height'

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
let resizingVertical = false

const intradayChartRef = ref(null)
const intradayVolRef = ref(null)

// 副图：成交量/成交额切换（与 K 线图一致）
const subChartIndicator = ref('volume')
// 预处理后的分钟数据，供副图与切换使用
const subChartTimes = ref([])
const subChartVolumes = ref([])
const subChartAmounts = ref([])

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

// 行情页黑底白字图表主题（与现有行情软件风格一致）
const CHART_DARK = {
  backgroundColor: '#0d0d0d',
  textStyle: { color: '#e0e0e0' },
  axisLine: { lineStyle: { color: '#404040' } },
  splitLine: { lineStyle: { color: '#262626' } },
  axisLabel: { color: '#b0b0b0' }
}

// 主图与副图：Y 轴固定 60px，横轴与绘图区对齐；副图底部留 10px 留白
const CHART_GRID = { left: 60, right: '5%', bottom: '14%', top: '8%', containLabel: false }
const CHART_GRID_VOL = { left: 60, right: '5%', bottom: 40, top: '8%', containLabel: false }

// 成交量/成交额：tooltip 等用，万/亿两位小数
function formatVolumeAmount(value) {
  if (value == null || !Number.isFinite(value)) return '-'
  const v = Number(value)
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '\u4ebf'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '\u4e07'
  return String(Math.round(v))
}

// 副图 Y 轴刻度：万/亿时数字部分最多 4 字符，如 9999万、999万、99.9万、9.99万
function formatVolumeAxisLabel(value) {
  if (value == null || !Number.isFinite(value)) return '-'
  const v = Number(value)
  const suffixW = '\u4e07'
  const suffixY = '\u4ebf'
  if (v >= 1e8) {
    const x = v / 1e8
    if (x >= 1000) return Math.round(x) + suffixY
    if (x >= 100) return Math.round(x) + suffixY
    if (x >= 10) return (Math.round(x * 10) / 10).toFixed(1) + suffixY
    return (Math.round(x * 100) / 100).toFixed(2) + suffixY
  }
  if (v >= 1e4) {
    const x = v / 1e4
    if (x >= 1000) return Math.round(x) + suffixW
    if (x >= 100) return Math.round(x) + suffixW
    if (x >= 10) return (Math.round(x * 10) / 10).toFixed(1) + suffixW
    return (Math.round(x * 100) / 100).toFixed(2) + suffixW
  }
  return String(Math.round(v))
}

function applyVolChartOption() {
  if (!intradayVolChart) return
  const times = subChartTimes.value
  const volumes = subChartVolumes.value
  const amounts = subChartAmounts.value
  const ind = subChartIndicator.value
  const data = ind === 'amount' ? amounts : volumes
  const name = ind === 'amount' ? '成交额' : '成交量'
  intradayVolChart.setOption({
    ...CHART_DARK,
    animation: false,
    grid: CHART_GRID_VOL,
    xAxis: { type: 'category', data: times, boundaryGap: true, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel },
    yAxis: {
      type: 'value',
      axisLine: CHART_DARK.axisLine,
      axisLabel: { formatter: formatVolumeAxisLabel, ...CHART_DARK.axisLabel },
      splitLine: CHART_DARK.splitLine
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        if (!params || !params[0]) return ''
        const i = params[0].dataIndex
        const vol = volumes[i]
        const amt = amounts[i]
        const timeStr = times[i] || ''
        return `${timeStr}<br/>成交量: ${formatVolumeAmount(vol)}<br/>成交额: ${formatVolumeAmount(amt)}`
      }
    },
    series: [
      { name, type: 'bar', data, itemStyle: { color: '#5c9eed' } }
    ]
  }, true)
}

// 分时：先拉取证券详情取 metadata.ticks.end_date 作为交易日，再请求 ticks 接口
async function loadIntraday() {
  const s = (props.symbol || '').trim()
  if (!s) return
  try {
    let tradeDate = new Date().toISOString().slice(0, 10)
    try {
      const detail = await securityApi.getDetail(s)
      if (detail?.metadata?.ticks?.end_date) {
        tradeDate = detail.metadata.ticks.end_date
      }
    } catch (_) {
      // 详情失败时仍用当天
    }
    const data = await marketApi.getTicks(s, tradeDate, false)
    const list = Array.isArray(data) ? data : []
    await nextTick()
    const priceDom = intradayChartRef.value
    const volDom = intradayVolRef.value
    if (!priceDom || !volDom) return
    if (list.length === 0) {
      subChartTimes.value = []
      subChartVolumes.value = []
      subChartAmounts.value = []
      if (!intradayChart) intradayChart = echarts.init(priceDom)
      intradayChart.setOption({
        ...CHART_DARK,
        grid: CHART_GRID,
        title: { text: '分时 - 暂无数据', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
        xAxis: { type: 'category', data: [], axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: [] }]
      }, true)
      if (!intradayVolChart) intradayVolChart = echarts.init(volDom)
      intradayVolChart.setOption({
        ...CHART_DARK,
        grid: CHART_GRID_VOL,
        title: { text: '分时量 - 待数据', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value', axisLabel: { formatter: formatVolumeAxisLabel, ...CHART_DARK.axisLabel } },
        series: [{ type: 'bar', data: [] }]
      }, true)
      return
    }
    const OPENINT_CALL_AUCTION = 12
    const OPENINT_CONTINUOUS = 13
    const minuteMap = new Map()
    for (const item of list) {
      const t = item.time != null ? Number(item.time) : NaN
      if (Number.isNaN(t)) continue
      const minuteKey = Math.floor(t / 60000)
      const cumVol = Number(item.volume) || 0
      const cumAmt = Number(item.amount) || 0
      if (!minuteMap.has(minuteKey)) {
        minuteMap.set(minuteKey, { lastTime: -1, volume: 0, amount: 0, 12: null, 13: null })
      }
      const row = minuteMap.get(minuteKey)
      if (t >= row.lastTime) {
        row.lastTime = t
        row.volume = cumVol
        row.amount = cumAmt
      }
      const openInt = item.openInt != null ? parseInt(item.openInt, 10) : 13
      if (openInt !== OPENINT_CALL_AUCTION && openInt !== OPENINT_CONTINUOUS) continue
      const tickvol = parseInt(item.tickvol ?? 0, 10) || 0
      let price
      if (openInt === OPENINT_CALL_AUCTION) {
        const ask = Array.isArray(item.askPrice) ? item.askPrice[0] : null
        const bid = Array.isArray(item.bidPrice) ? item.bidPrice[0] : null
        price = parseFloat(ask ?? bid ?? item.lastPrice ?? item.close ?? 0)
      } else {
        price = parseFloat(item.lastPrice ?? item.close ?? 0)
      }
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
    const cumVols = sorted.map(([, v]) => v.volume || 0)
    const cumAmts = sorted.map(([, v]) => v.amount || 0)
    const volumesPerMinute = cumVols.map((cum, i) => Math.max(0, cum - (i > 0 ? cumVols[i - 1] : 0)))
    const amountsPerMinute = cumAmts.map((cum, i) => Math.max(0, cum - (i > 0 ? cumAmts[i - 1] : 0)))
    subChartTimes.value = times
    subChartVolumes.value = volumesPerMinute
    subChartAmounts.value = amountsPerMinute
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
      grid: CHART_GRID,
      xAxis: { type: 'category', data: times, boundaryGap: false, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: { show: false } },
      yAxis: { type: 'value', scale: true, axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine },
      series: [
        { name: '集合竞价', type: 'line', data: pricesCallAuction, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#9e9e9e' } },
        { name: '连续交易', type: 'line', data: pricesContinuous, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#5c9eed' } },
        { name: '均价', type: 'line', data: avgPrices, smooth: false, symbol: 'none', connectNulls: true, lineStyle: { width: 1, color: '#ffc107' } }
      ]
    }, true)
    if (!intradayVolChart) intradayVolChart = echarts.init(volDom)
    applyVolChartOption()
  } catch (e) {
    console.error('分时加载失败:', e)
    ElMessage.error('分时加载失败')
  }
}

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

const RESIZE_THROTTLE_MS = 120
let resizeThrottleTimer = null
let resizeObserver = null

function resizeChartsThrottled() {
  if (resizeThrottleTimer != null) return
  resizeThrottleTimer = setTimeout(() => {
    resizeThrottleTimer = null
    resizeCharts()
  }, RESIZE_THROTTLE_MS)
}

function resizeCharts() {
  const priceEl = intradayChartRef.value
  const volEl = intradayVolRef.value
  if (intradayChart && priceEl) {
    const w = priceEl.offsetWidth
    const h = priceEl.offsetHeight
    if (w > 0 && h > 0) intradayChart.resize({ width: w, height: h })
  }
  if (intradayVolChart && volEl) {
    const w = volEl.offsetWidth
    const h = volEl.offsetHeight
    if (w > 0 && h > 0) intradayVolChart.resize({ width: w, height: h })
  }
}

async function refresh() {
  await loadIntraday()
}

onMounted(async () => {
  window.addEventListener('resize', resizeChartsThrottled)
  await refresh()
  const priceEl = intradayChartRef.value
  const volEl = intradayVolRef.value
  if (priceEl || volEl) {
    resizeObserver = new ResizeObserver(resizeChartsThrottled)
    if (priceEl) resizeObserver.observe(priceEl)
    if (volEl) resizeObserver.observe(volEl)
  }
  nextTick(resizeChartsThrottled)
})

onBeforeUnmount(() => {
  if (resizeThrottleTimer != null) clearTimeout(resizeThrottleTimer)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  window.removeEventListener('resize', resizeChartsThrottled)
  if (intradayChart) { intradayChart.dispose(); intradayChart = null }
  if (intradayVolChart) { intradayVolChart.dispose(); intradayVolChart = null }
})

defineExpose({
  refresh
})
</script>

<style scoped>
/* 使用父级定义的样式类名，这里只做兜底，避免组件单独使用时布局异常 */
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
  min-height: 0;
}

.chart-half.chart-price {
  flex: 1;
  min-height: 0;
}

.chart-half.chart-volume {
  flex-shrink: 0;
  min-height: 80px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tick-sub-toolbar {
  flex-shrink: 0;
  padding: 2px 8px 4px;
  background: #0d0d0d;
  border-bottom: 1px solid #262626;
}

.tick-sub-toolbar :deep(.el-radio-group) {
  display: flex;
}

.tick-sub-toolbar :deep(.el-radio-button__inner) {
  padding: 4px 10px;
  font-size: 12px;
  color: #b0b0b0;
  background: transparent;
  border-color: #404040;
}

.tick-sub-toolbar :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  color: #e0e0e0;
  background: #262626;
  border-color: #5c9eed;
}

.chart-half.chart-volume .chart-dom {
  flex: 1;
  min-height: 0;
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
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
}

.five-level-table .cell {
  padding: 2px 4px;
  border-bottom: 1px solid #262626;
  color: #b0b0b0;
  text-align: right;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.five-level-table .cell.label {
  text-align: left;
  width: 44px;
  color: #e0e0e0;
}

.five-level-table .cell.price {
  width: 60px;
}

.five-level-table .cell.vol {
  width: 60px;
}

.trade-placeholder {
  font-size: 12px;
  color: #808080;
  padding: 4px 0;
}
</style>
