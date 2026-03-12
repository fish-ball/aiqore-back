<template>
  <div ref="wrapRef" class="kline-wrap">
    <div class="kline-data-panel kline-data-panel-top">
      <div class="kline-data-row1">
        <span class="kline-data-item">日期 {{ displayOHLC.date }}</span>
        <span class="kline-data-item">开盘 {{ displayOHLC.open }}</span>
        <span class="kline-data-item">收盘 {{ displayOHLC.close }}</span>
        <span class="kline-data-item">最高 {{ displayOHLC.high }}</span>
        <span class="kline-data-item">最低 {{ displayOHLC.low }}</span>
      </div>
      <div class="kline-data-row2">
        <span class="kline-data-item">MA5 {{ displayOHLC.ma5 }}</span>
        <span class="kline-data-item">MA10 {{ displayOHLC.ma10 }}</span>
        <span class="kline-data-item">MA20 {{ displayOHLC.ma20 }}</span>
        <span class="kline-data-item">MA30 {{ displayOHLC.ma30 }}</span>
        <span class="kline-data-item">MA60 {{ displayOHLC.ma60 }}</span>
        <span class="kline-data-item">MA120 {{ displayOHLC.ma120 }}</span>
        <span class="kline-data-item">MA250 {{ displayOHLC.ma250 }}</span>
      </div>
    </div>
    <div class="kline-main-area">
      <div ref="mainRef" class="chart-dom kline-chart-dom"></div>
    </div>
    <div class="resizer-kline" @mousedown="startResizeVertical"></div>
    <div class="kline-indicator">
      <el-radio-group v-model="indicator" size="small" @change="updateIndicator">
        <el-radio-button value="volume">成交量</el-radio-button>
        <el-radio-button value="amount">成交额</el-radio-button>
        <el-radio-button value="kdj">KDJ</el-radio-button>
        <el-radio-button value="rsi">RSI</el-radio-button>
        <el-radio-button value="macd">MACD</el-radio-button>
      </el-radio-group>
    </div>
    <div class="kline-data-panel kline-data-panel-sub">
      <span class="kline-data-item">日期 {{ displaySub.date }}</span>
      <span class="kline-data-item">{{ displaySub.text }}</span>
    </div>
    <div ref="subRef" class="chart-dom kline-sub-dom" :style="{ height: leftPanelBottomHeight + 'px' }"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { marketApi } from '../../../api/market'

const props = defineProps({
  // 证券代码，例如 000001.SZ
  symbol: {
    type: String,
    required: true
  },
  // K 线周期：1d / 1w / 1M
  period: {
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

const mainRef = ref(null)
const subRef = ref(null)
const wrapRef = ref(null)

const data = ref([])
const cache = ref(null)
const indicator = ref('volume')
const hoverIndex = ref(null)
const loading = ref(false)

// 行情页黑底白字图表主题（与现有行情软件风格一致）
const CHART_DARK = {
  backgroundColor: '#0d0d0d',
  textStyle: { color: '#e0e0e0' },
  axisLine: { lineStyle: { color: '#404040' } },
  splitLine: { lineStyle: { color: '#262626' } },
  axisLabel: { color: '#b0b0b0' }
}

// 上下图统一 grid：约 10px 留白避免文字被裁切，y 轴宽度固定（左侧多 20px 给标签）
const GRID_LEFT = 82
const GRID_RIGHT = 22
const GRID_BOTTOM = 14
const GRID_TOP = 14

const HOVER_CROSS_V_ID = 'klineHoverCrossV'
const HOVER_CROSS_H_ID = 'klineHoverCrossH'

// 当前 K 线主图展示的数据（点击时为该根，否则为最新一根）；含日期与全部 MA，优先用缓存 O(1)
const displayOHLC = computed(() => {
  const arr = data.value
  const c = cache.value
  if (!arr || arr.length === 0) {
    return {
      date: '',
      open: '--',
      close: '--',
      high: '--',
      low: '--',
      ma5: '--',
      ma10: '--',
      ma20: '--',
      ma30: '--',
      ma60: '--',
      ma120: '--',
      ma250: '--'
    }
  }
  const idx = hoverIndex.value != null ? Math.max(0, Math.min(hoverIndex.value, arr.length - 1)) : arr.length - 1
  const bar = arr[idx]
  const t = bar.time ?? bar.timestamp ?? bar.date ?? ''
  const v = (arr2, i) => (arr2 && arr2[i] !== undefined ? (arr2[i] === '-' ? '--' : arr2[i]) : '--')
  const ma = c?.ma
  return {
    date: formatKlineTimeForAxis(t),
    open: formatPrice(bar.open),
    close: formatPrice(bar.close),
    high: formatPrice(bar.high),
    low: formatPrice(bar.low),
    ma5: ma ? v(ma.ma5, idx) : v(calcMA(arr, 5), idx),
    ma10: ma ? v(ma.ma10, idx) : v(calcMA(arr, 10), idx),
    ma20: ma ? v(ma.ma20, idx) : v(calcMA(arr, 20), idx),
    ma30: ma ? v(ma.ma30, idx) : v(calcMA(arr, 30), idx),
    ma60: ma ? v(ma.ma60, idx) : v(calcMA(arr, 60), idx),
    ma120: ma ? v(ma.ma120, idx) : v(calcMA(arr, 120), idx),
    ma250: ma ? v(ma.ma250, idx) : v(calcMA(arr, 250), idx)
  }
})

// 当前副图指标展示的数据（与主图同索引）；优先用缓存 O(1)
const displaySub = computed(() => {
  const ind = indicator.value
  const arr = data.value
  const sub = cache.value?.sub
  if (!arr || arr.length === 0) return { date: '', text: '--' }
  const idx = hoverIndex.value != null ? Math.max(0, Math.min(hoverIndex.value, arr.length - 1)) : arr.length - 1
  const date = formatKlineTimeForAxis(arr[idx].time ?? arr[idx].timestamp ?? arr[idx].date ?? '')
  if (ind === 'volume') {
    const vol = parseInt(arr[idx].volume || 0, 10)
    return { date, text: `成交量 ${formatVolume(vol)}` }
  }
  if (ind === 'amount') {
    const amt = parseFloat(arr[idx].amount || 0)
    return { date, text: `成交额 ${formatAmount(amt)}` }
  }
  if (ind === 'kdj') {
    const { k, d, j } = sub?.kdj ?? calcKDJ(arr)
    return { date, text: `K: ${k[idx]}  D: ${d[idx]}  J: ${j[idx]}` }
  }
  if (ind === 'rsi') {
    const rsi = sub?.rsi ?? calcRSI(arr)
    return { date, text: `RSI: ${rsi[idx]}` }
  }
  if (ind === 'macd') {
    const { dif, dea, macd } = sub?.macd ?? calcMACD(arr)
    return { date, text: `DIF: ${dif[idx]}  DEA: ${dea[idx]}  MACD: ${macd[idx]}` }
  }
  return { date, text: '--' }
})

function formatPrice(value) {
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

// 计算均线
function calcMA(arr, period) {
  const result = []
  for (let i = 0; i < arr.length; i++) {
    if (i < period - 1) {
      result.push('-')
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) sum += arr[i - j].close
      result.push((sum / period).toFixed(2))
    }
  }
  return result
}

// KDJ，O(n)：滑动窗口用单调队列（索引前移不 shift）求区间 min/max
function calcKDJ(arr, n = 9, m1 = 3, m2 = 3) {
  const k = []
  const d = []
  const j = []
  let kNum = 50
  let dNum = 50
  const lowArr = arr.map(x => parseFloat(x.low) || 0)
  const highArr = arr.map(x => parseFloat(x.high) || 0)
  const qMin = []
  const qMax = []
  let minHead = 0
  let maxHead = 0
  for (let i = 0; i < arr.length; i++) {
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
    const close = parseFloat(arr[i].close) || 0
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
function calcRSI(arr, n = 14) {
  const rsi = []
  for (let i = 0; i < arr.length; i++) {
    if (i < n) {
      rsi.push('-')
      continue
    }
    let up = 0
    let down = 0
    for (let j = i - n + 1; j <= i; j++) {
      const ch = arr[j].close - arr[j - 1].close
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
function calcMACD(arr, short = 12, long = 26, mid = 9) {
  const dif = []
  const dea = []
  const macd = []
  let eS = 0
  let eL = 0
  let eD = 0
  for (let i = 0; i < arr.length; i++) {
    const c = arr[i].close
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
    yAxis: {
      type: 'value',
      scale: true,
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: { formatter: v => v.toFixed(2), ...CHART_DARK.axisLabel },
      axisLine: CHART_DARK.axisLine,
      splitLine: CHART_DARK.splitLine
    },
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
      series: [{ name: '成交量', type: 'bar', data: vol, itemStyle: { color: params => colors[params.dataIndex] } }]
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
      yAxis: {
        type: 'value',
        ...axisCommon,
        axisLabel: {
          formatter: v => (v >= 1e8 ? (v / 1e8).toFixed(1) + '亿' : (v / 1e4).toFixed(0) + '万'),
          ...CHART_DARK.axisLabel
        }
      },
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
    const barColors = macd.map(v => (v !== '-' && parseFloat(v) >= 0 ? '#ef5350' : '#26a69a'))
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
        { name: 'MACD', type: 'bar', data: macd, itemStyle: { color: params => barColors[params.dataIndex] } }
      ]
    }
  }
  return null
}

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
    hoverIndex.value = dataIndex
    updateHoverCross(mainChart, null, null, false)
    syncCrosshair(mainChart, subChart, dataIndex)
  }
  function clearSelected() {
    if (lastDataIndex === -1) return
    lastDataIndex = -1
    hoverIndex.value = null
    hideCrosshair(mainChart, subChart)
  }
  if (mainChart && mainChart.getZr) {
    const zr = mainChart.getZr()
    zr.off('click')
    zr.off('mousemove')
    zr.off('mouseout')
    zr.on('click', e => {
      const result = mainChart.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
      if (result != null && Array.isArray(result) && result.length >= 1) {
        setSelected(Math.round(result[0]))
      }
    })
    zr.on('mousemove', e => {
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
      clearSelected()
    })
  }
  if (subChart && subChart.getZr) {
    const zr = subChart.getZr()
    zr.off('click')
    zr.on('click', e => {
      const result = subChart.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
      if (result != null && Array.isArray(result) && result.length >= 1) {
        setSelected(Math.round(result[0]))
      }
    })
  }
}

function buildKlineCache(arr) {
  if (!arr || arr.length === 0) return null
  const vol = arr.map(x => parseInt(x.volume || 0, 10))
  const volColors = arr.map((x, i) => (i > 0 && parseFloat(x.close) >= parseFloat(arr[i - 1].close) ? '#ef5350' : '#26a69a'))
  const amount = arr.map(x => parseFloat(x.amount || 0))
  return {
    ma: {
      ma5: calcMA(arr, 5),
      ma10: calcMA(arr, 10),
      ma20: calcMA(arr, 20),
      ma30: calcMA(arr, 30),
      ma60: calcMA(arr, 60),
      ma120: calcMA(arr, 120),
      ma250: calcMA(arr, 250)
    },
    sub: {
      volume: { data: vol, colors: volColors },
      amount: { data: amount },
      kdj: calcKDJ(arr),
      rsi: calcRSI(arr),
      macd: calcMACD(arr)
    }
  }
}

function renderKline(chartDom, subDom, rawData, ind, tabCache) {
  if (!chartDom || !rawData.length) return
  const mainChart = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom)
  const opt = buildKlineOption(rawData, tabCache?.ma)
  if (opt) mainChart.setOption(opt, true)
  let subChart = null
  if (subDom && rawData.length) {
    subChart = echarts.getInstanceByDom(subDom) || echarts.init(subDom)
    const subOpt = buildSubOption(rawData, ind, tabCache?.sub)
    if (subOpt) subChart.setOption(subOpt, true)
  }
  bindKlineHover(mainChart, subChart, rawData.length)
}

function updateIndicator() {
  if (subRef.value && data.value.length) {
    const subChart = echarts.getInstanceByDom(subRef.value) || echarts.init(subRef.value)
    const opt = buildSubOption(data.value, indicator.value, cache.value?.sub ?? null)
    if (opt) subChart.setOption(opt, true)
  }
}

async function fetchKline(count = 250) {
  const s = (props.symbol || '').trim()
  if (!s) return []
  try {
    const res = await marketApi.getKline(s, props.period, count)
    return Array.isArray(res) ? res : []
  } catch (e) {
    console.error('获取K线失败:', e)
    return []
  }
}

async function loadKline() {
  loading.value = true
  try {
    const arr = await fetchKline(250)
    data.value = arr
    cache.value = buildKlineCache(arr)
    hoverIndex.value = null
    await nextTick()
    if (!arr || arr.length === 0) {
      // 没有数据时也初始化一个简单的占位图，避免页面空白
      if (mainRef.value) {
        const mainChart = echarts.getInstanceByDom(mainRef.value) || echarts.init(mainRef.value)
        mainChart.setOption({
          ...CHART_DARK,
          title: { text: '暂无K线数据', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
          xAxis: { type: 'category', data: [] },
          yAxis: { type: 'value' },
          series: []
        }, true)
      }
      if (subRef.value) {
        const subChart = echarts.getInstanceByDom(subRef.value) || echarts.init(subRef.value)
        subChart.setOption({
          ...CHART_DARK,
          title: { text: '', left: 'center', textStyle: { color: CHART_DARK.textStyle.color } },
          xAxis: { type: 'category', data: [] },
          yAxis: { type: 'value' },
          series: []
        }, true)
      }
      nextTick(() => resizeCharts())
      return
    }
    renderKline(mainRef.value, subRef.value, arr, indicator.value, cache.value ?? null)
    nextTick(() => resizeCharts())
  } finally {
    loading.value = false
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
function resizeChartsThrottled() {
  if (resizeThrottleTimer != null) return
  resizeThrottleTimer = setTimeout(() => {
    resizeThrottleTimer = null
    resizeCharts()
  }, RESIZE_THROTTLE_MS)
}

function resizeCharts() {
  if (mainRef.value) {
    const ch = echarts.getInstanceByDom(mainRef.value)
    if (ch) ch.resize()
  }
  if (subRef.value) {
    const ch = echarts.getInstanceByDom(subRef.value)
    if (ch) ch.resize()
  }
}

async function refresh() {
  await loadKline()
}

let resizeObserver = null
onMounted(async () => {
  window.addEventListener('resize', resizeChartsThrottled)
  if (wrapRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      nextTick(resizeChartsThrottled)
    })
    resizeObserver.observe(wrapRef.value)
  }
  await refresh()
})

onBeforeUnmount(() => {
  if (resizeThrottleTimer != null) clearTimeout(resizeThrottleTimer)
  window.removeEventListener('resize', resizeChartsThrottled)
  if (resizeObserver && wrapRef.value) {
    resizeObserver.unobserve(wrapRef.value)
    resizeObserver = null
  }
  if (mainRef.value) {
    const ch = echarts.getInstanceByDom(mainRef.value)
    if (ch) ch.dispose()
  }
  if (subRef.value) {
    const ch = echarts.getInstanceByDom(subRef.value)
    if (ch) ch.dispose()
  }
})

defineExpose({
  refresh
})
</script>

<style scoped>
/* 使用父级定义的样式类名，这里只做兜底，避免组件单独使用时布局异常 */
.kline-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  padding: 0;
  overflow: hidden;
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

/* 主图区域：占据剩余空间，最小高度保证可见 */
.kline-main-area {
  flex: 1;
  min-height: 120px;
  display: flex;
  overflow: hidden;
}

.kline-chart-dom {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
}

/* 主图与副图之间的可拖拽分割条 */
.resizer-kline {
  height: 6px;
  flex-shrink: 0;
  background: #262626;
  cursor: row-resize;
}

.resizer-kline:hover {
  background: #404040;
}

.kline-indicator {
  flex-shrink: 0;
  padding: 2px 8px;
}

/* 副图区域：固定高度，可拖拽分割条调整 */
.kline-sub-dom {
  flex-shrink: 0;
  min-height: 80px;
  overflow: hidden;
  width: 100%;
}
</style>

