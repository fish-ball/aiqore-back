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

    <!-- 右侧：五档盘口，数据来自 ticks 最后一条的 askPrice/askVol/bidPrice/bidVol -->
    <div class="intraday-side">
      <div class="side-block">
        <table class="five-level-table">
          <tbody>
            <tr v-for="row in fiveLevelRows.slice(0, 5)" :key="row.label">
              <td class="cell label">{{ row.label }}</td>
              <td class="cell price" :class="priceColorClass(row.price)">{{ row.price }}</td>
              <td class="cell vol">{{ row.vol }}</td>
            </tr>
            <tr class="five-level-ratio-row">
              <td colspan="3">
                <div class="five-level-ratio-bar">
                  <div class="five-level-ratio-buy" :style="{ width: (fiveLevelBuyRatio * 100) + '%' }"></div>
                  <div class="five-level-ratio-sell" :style="{ width: (fiveLevelSellRatio * 100) + '%' }"></div>
                </div>
              </td>
            </tr>
            <tr v-for="row in fiveLevelRows.slice(5, 10)" :key="row.label">
              <td class="cell label">{{ row.label }}</td>
              <td class="cell price" :class="priceColorClass(row.price)">{{ row.price }}</td>
              <td class="cell vol">{{ row.vol }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { marketApi } from '../../../api/market'

const props = defineProps({
  // 证券代码，例如 000001.SZ
  symbol: {
    type: String,
    required: true
  },
  // 证券详情（含 metadata.ticks.end_date），必填，由外部在加载成功后传入
  securityDetail: {
    type: Object,
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
// 盘前(集合竞价)区域在 x 轴上的结束索引，用于主图/副图 markArea
const subChartCallAuctionEndIndex = ref(-1)
// 主图是否有右侧涨跌幅轴，副图 grid.right 与之对齐
const subChartHasRightAxis = ref(false)
// 副图每根柱子颜色：按当前分钟与上一分钟最后价比较，涨红跌绿平价白
const subChartBarColors = ref([])

let intradayChart = null
let intradayVolChart = null

// 五档盘口：卖5~卖1、买1~买5，由 loadIntraday 中取 ticks 最后一条的 askPrice/askVol/bidPrice/bidVol 填充
const FIVE_LEVEL_LABELS = ['卖5', '卖4', '卖3', '卖2', '卖1', '买1', '买2', '买3', '买4', '买5']
function defaultFiveLevelRows() {
  return FIVE_LEVEL_LABELS.map(label => ({ label, price: '--', vol: '--' }))
}
const fiveLevelRows = ref(defaultFiveLevelRows())
// 昨收价，用于五档价格颜色：平价白、溢价红、折价绿
const fiveLevelLastClose = ref(null)
// 五档买盘/卖盘总量比例（0~1），用于买1与卖1之间的比例条
const fiveLevelBuyRatio = ref(0.5)
const fiveLevelSellRatio = ref(0.5)

function priceColorClass(priceStr) {
  if (priceStr === '--' || fiveLevelLastClose.value == null || !Number.isFinite(fiveLevelLastClose.value)) return 'price-equal'
  const p = parseFloat(priceStr)
  if (!Number.isFinite(p)) return 'price-equal'
  if (p > fiveLevelLastClose.value) return 'price-up'
  if (p < fiveLevelLastClose.value) return 'price-down'
  return 'price-equal'
}

function formatFiveLevelVol(v) {
  if (v == null || !Number.isFinite(Number(v))) return '--'
  const n = Number(v)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '\u4ebf'
  if (n >= 1e4) return (n / 1e4).toFixed(2) + '\u4e07'
  return String(Math.round(n))
}

function buildFiveLevelFromLastTick(last) {
  const askPrice = Array.isArray(last.askPrice) ? last.askPrice : []
  const askVol = Array.isArray(last.askVol) ? last.askVol : []
  const bidPrice = Array.isArray(last.bidPrice) ? last.bidPrice : []
  const bidVol = Array.isArray(last.bidVol) ? last.bidVol : []
  const rows = []
  for (let i = 4; i >= 0; i--) {
    const p = askPrice[i] != null && Number.isFinite(Number(askPrice[i])) ? Number(askPrice[i]).toFixed(2) : '--'
    const v = formatFiveLevelVol(askVol[i])
    rows.push({ label: FIVE_LEVEL_LABELS[4 - i], price: p, vol: v })
  }
  for (let i = 0; i <= 4; i++) {
    const p = bidPrice[i] != null && Number.isFinite(Number(bidPrice[i])) ? Number(bidPrice[i]).toFixed(2) : '--'
    const v = formatFiveLevelVol(bidVol[i])
    rows.push({ label: FIVE_LEVEL_LABELS[5 + i], price: p, vol: v })
  }
  return rows
}

function sumVol(arr) {
  if (!Array.isArray(arr)) return 0
  let s = 0
  for (let i = 0; i < arr.length; i++) {
    const v = Number(arr[i])
    if (Number.isFinite(v)) s += v
  }
  return s
}

// 行情页黑底白字图表主题（与现有行情软件风格一致）
const CHART_DARK = {
  backgroundColor: '#0d0d0d',
  textStyle: { color: '#e0e0e0' },
  axisLine: { lineStyle: { color: '#404040' } },
  splitLine: { lineStyle: { color: '#262626' } },
  axisLabel: { color: '#b0b0b0' }
}

// 主图与副图：Y 轴固定 60px，横轴与绘图区对齐；副图底部留 10px 留白；有右侧涨跌幅轴时主图/副图统一用 8% 右边距以对齐
const CHART_GRID = { left: 60, right: '5%', bottom: '14%', top: '8%', containLabel: false }
const CHART_GRID_WITH_RIGHT_AXIS = { left: 60, right: '8%', bottom: '14%', top: '8%', containLabel: false }
const CHART_GRID_VOL = { left: 60, right: '5%', bottom: 40, top: '8%', containLabel: false }

// 盘前区域背景：浅灰 20% 半透明
const MARK_AREA_PRE_MARKET = {
  silent: true,
  itemStyle: { color: 'rgba(128,128,128,0.2)' }
}

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
  const rawData = ind === 'amount' ? amounts : volumes
  const barData = subChartBarColors.value.length === rawData.length
    ? rawData.map((val, i) => ({ value: val, itemStyle: { color: subChartBarColors.value[i] || '#e0e0e0' } }))
    : rawData.map(val => ({ value: val, itemStyle: { color: '#e0e0e0' } }))
  const name = ind === 'amount' ? '成交额' : '成交量'
  const endIdx = subChartCallAuctionEndIndex.value
  const hasRight = subChartHasRightAxis.value
  const volPreMarketMarkArea = endIdx >= 0
    ? { ...MARK_AREA_PRE_MARKET, data: [[{ xAxis: 0 }, { xAxis: endIdx }]] }
    : {}
  const volGrid = { ...CHART_GRID_VOL, right: hasRight ? '8%' : '5%' }
  intradayVolChart.setOption({
    ...CHART_DARK,
    animation: false,
    grid: volGrid,
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
      { name, type: 'bar', data: barData, markArea: volPreMarketMarkArea }
    ]
  }, true)
}

// 分时：使用 props.securityDetail.metadata.ticks.end_date 作为交易日
async function loadIntraday() {
  const s = (props.symbol || '').trim()
  if (!s) return
  try {
    const tradeDate = props.securityDetail?.metadata?.ticks?.end_date || new Date().toISOString().slice(0, 10)
    const data = await marketApi.getTicks(s, tradeDate, false)
    const list = Array.isArray(data) ? data : []
    await nextTick()
    const priceDom = intradayChartRef.value
    const volDom = intradayVolRef.value
    if (!priceDom || !volDom) return
    if (list.length === 0) {
      fiveLevelRows.value = defaultFiveLevelRows()
      fiveLevelLastClose.value = null
      fiveLevelBuyRatio.value = 0.5
      fiveLevelSellRatio.value = 0.5
      subChartTimes.value = []
      subChartVolumes.value = []
      subChartAmounts.value = []
      subChartBarColors.value = []
      subChartCallAuctionEndIndex.value = -1
      subChartHasRightAxis.value = false
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
    const lastTick = list[list.length - 1]
    fiveLevelRows.value = buildFiveLevelFromLastTick(lastTick)
    const lastCloseNum = list[0]?.lastClose != null ? parseFloat(list[0].lastClose) : null
    fiveLevelLastClose.value = Number.isFinite(lastCloseNum) ? lastCloseNum : null
    const bidTotal = sumVol(lastTick.bidVol)
    const askTotal = sumVol(lastTick.askVol)
    const total = bidTotal + askTotal
    fiveLevelBuyRatio.value = total > 0 ? bidTotal / total : 0.5
    fiveLevelSellRatio.value = total > 0 ? askTotal / total : 0.5
    const sorted = Array.from(minuteMap.entries()).sort((a, b) => a[0] - b[0])
    const times = sorted.map(([k]) => {
      const d = new Date(k * 60000)
      return d.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false })
    })
    const pricesCallAuction = sorted.map(([, v]) => (v[OPENINT_CALL_AUCTION] ? v[OPENINT_CALL_AUCTION].price : null))
    const pricesContinuous = sorted.map(([, v]) => (v[OPENINT_CONTINUOUS] ? v[OPENINT_CONTINUOUS].price : null))
    const lastClose = list[0]?.lastClose != null ? parseFloat(list[0].lastClose) : null
    const allPrices = [...pricesCallAuction, ...pricesContinuous].filter(p => p != null && Number.isFinite(p))
    const priceMin = allPrices.length ? Math.min(...allPrices) : null
    const priceMax = allPrices.length ? Math.max(...allPrices) : null
    const hasRightAxis = lastClose != null && lastClose > 0 && priceMin != null && priceMax != null
    // lastClose 居中、上下幅度对称：取相对 lastClose 的最大偏离作为半幅
    const maxDev = hasRightAxis ? Math.max(priceMax - lastClose, lastClose - priceMin) : 0
    const axisMin = hasRightAxis ? lastClose - maxDev : null
    const axisMax = hasRightAxis ? lastClose + maxDev : null
    const pctMin = hasRightAxis ? -maxDev / lastClose * 100 : null
    const pctMax = hasRightAxis ? maxDev / lastClose * 100 : null
    let callAuctionEndIndex = -1
    for (let i = 0; i < pricesCallAuction.length; i++) {
      if (pricesCallAuction[i] != null) callAuctionEndIndex = i
    }
    subChartCallAuctionEndIndex.value = callAuctionEndIndex
    subChartHasRightAxis.value = hasRightAxis
    const cumVols = sorted.map(([, v]) => v.volume || 0)
    const cumAmts = sorted.map(([, v]) => v.amount || 0)
    const volumesPerMinute = cumVols.map((cum, i) => Math.max(0, cum - (i > 0 ? cumVols[i - 1] : 0)))
    const amountsPerMinute = cumAmts.map((cum, i) => Math.max(0, cum - (i > 0 ? cumAmts[i - 1] : 0)))
    subChartTimes.value = times
    subChartVolumes.value = volumesPerMinute
    subChartAmounts.value = amountsPerMinute
    const barColors = []
    const BAR_COLOR_UP = '#F56C6C'
    const BAR_COLOR_DOWN = '#67C23A'
    const BAR_COLOR_EQUAL = '#e0e0e0'
    for (let i = 0; i < times.length; i++) {
      const curr = pricesContinuous[i] != null ? pricesContinuous[i] : pricesCallAuction[i]
      const prev = i > 0 ? (pricesContinuous[i - 1] != null ? pricesContinuous[i - 1] : pricesCallAuction[i - 1]) : null
      if (prev == null || curr == null || !Number.isFinite(curr)) {
        barColors.push(BAR_COLOR_EQUAL)
      } else if (curr > prev) {
        barColors.push(BAR_COLOR_UP)
      } else if (curr < prev) {
        barColors.push(BAR_COLOR_DOWN)
      } else {
        barColors.push(BAR_COLOR_EQUAL)
      }
    }
    subChartBarColors.value = barColors
    const avgPrices = []
    let sum = 0
    let n = 0
    for (let i = 0; i < pricesContinuous.length; i++) {
      const p = pricesContinuous[i]
      if (p != null) { sum += p; n++ }
      avgPrices.push(n > 0 ? (sum / n).toFixed(2) : null)
    }
    const preMarketMarkArea = callAuctionEndIndex >= 0
      ? { ...MARK_AREA_PRE_MARKET, data: [[{ xAxis: 0 }, { xAxis: callAuctionEndIndex }]] }
      : {}
    const baselineMarkLine = lastClose != null && Number.isFinite(lastClose)
      ? { silent: true, symbol: ['none', 'none'], lineStyle: { type: 'dashed', color: '#fff' }, data: [{ yAxis: lastClose }] }
      : {}
    const mainGrid = hasRightAxis ? CHART_GRID_WITH_RIGHT_AXIS : CHART_GRID
    // 有右侧涨跌幅轴时：Y 轴 lastClose 居中、上下幅度对称（axisMin/Max）；并关闭左侧 splitLine
    const mainYAxisLeft = hasRightAxis
      ? { type: 'value', min: axisMin, max: axisMax, scale: true, axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: { show: false } }
      : { type: 'value', scale: true, axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel }, axisLine: CHART_DARK.axisLine, splitLine: CHART_DARK.splitLine }
    // 右侧仅作涨跌幅坐标轴，与主价格系列同尺度（pctMin/pctMax 由 priceMin/priceMax 与 lastClose 算出，0% 即 lastClose）
    const mainYAxisRight = hasRightAxis
      ? { type: 'value', position: 'right', min: pctMin, max: pctMax, scale: true, axisLine: CHART_DARK.axisLine, axisLabel: { formatter: v => (v >= 0 ? '+' : '') + v.toFixed(2) + '%', ...CHART_DARK.axisLabel }, splitLine: { show: false } }
      : null
    if (!intradayChart) intradayChart = echarts.init(priceDom)
    intradayChart.setOption({
      ...CHART_DARK,
      animation: false,
      grid: mainGrid,
      xAxis: { type: 'category', data: times, boundaryGap: false, axisLine: CHART_DARK.axisLine, axisLabel: CHART_DARK.axisLabel, splitLine: { show: false } },
      yAxis: mainYAxisRight != null ? [mainYAxisLeft, mainYAxisRight] : mainYAxisLeft,
      series: [
        { name: '集合竞价', type: 'line', data: pricesCallAuction, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#9e9e9e' }, markArea: preMarketMarkArea, yAxisIndex: 0 },
        { name: '连续交易', type: 'line', data: pricesContinuous, smooth: false, symbol: 'none', connectNulls: false, lineStyle: { width: 2, color: '#e0e0e0' }, markLine: baselineMarkLine, yAxisIndex: 0 },
        { name: '均价', type: 'line', data: avgPrices, smooth: false, symbol: 'none', connectNulls: true, lineStyle: { width: 1, color: '#ffc107' }, yAxisIndex: 0 }
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

.five-level-table .cell.price.price-up {
  color: #F56C6C;
}
.five-level-table .cell.price.price-down {
  color: #67C23A;
}
.five-level-table .cell.price.price-equal {
  color: #e0e0e0;
}

.five-level-ratio-row td {
  padding: 2px 4px;
  vertical-align: middle;
  border-bottom: 1px solid #262626;
}

.five-level-ratio-bar {
  height: 4px;
  display: flex;
  width: 100%;
  border-radius: 2px;
  overflow: hidden;
  background: #262626;
}

.five-level-ratio-buy {
  background: #F56C6C;
  min-width: 0;
}

.five-level-ratio-sell {
  background: #67C23A;
  min-width: 0;
}
</style>
