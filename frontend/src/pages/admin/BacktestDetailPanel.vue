<template>
  <el-descriptions v-if="row" :column="1" border size="small">
    <el-descriptions-item label="任务 ID">{{ row.id }}</el-descriptions-item>
    <el-descriptions-item label="策略">
      {{
        row.strategy_id
          ? row.strategy_id.slice(0, 8) + (row.strategy_name ? ` ${row.strategy_name}` : '')
          : '-'
      }}
    </el-descriptions-item>
    <el-descriptions-item label="证券">{{ row.security_symbol }} {{ row.security_name }}</el-descriptions-item>
    <el-descriptions-item label="区间">{{ row.start_date }} ~ {{ row.end_date }}</el-descriptions-item>
    <el-descriptions-item label="状态">
      <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
    </el-descriptions-item>
    <el-descriptions-item label="图表">
      <template v-if="chartUrl">
        <el-image :src="chartUrl" :preview-src-list="[chartUrl]" fit="contain" class="backtest-chart" />
      </template>
      <template v-else>
        <span>-</span>
      </template>
    </el-descriptions-item>
    <el-descriptions-item label="交易明细">
      <template v-if="hasTrades">
        <el-button type="primary" link @click="emit('openTrades')">查看交易明细</el-button>
      </template>
      <template v-else>
        <span>-</span>
      </template>
    </el-descriptions-item>
    <el-descriptions-item label="结果">
      <pre class="result-json">{{ prettyResult(row.result) }}</pre>
    </el-descriptions-item>
  </el-descriptions>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  row: { type: Object, default: null },
})

const emit = defineEmits(['openTrades'])

const statusLabel = (s) => {
  const m = { pending: '待执行', running: '运行中', success: '成功', failure: '失败' }
  return m[s] || s || '-'
}

const statusTagType = (s) => {
  const m = { pending: 'info', running: 'warning', success: 'success', failure: 'danger' }
  return m[s] || 'info'
}

const prettyResult = (r) => {
  if (r == null) return '-'
  try {
    return JSON.stringify(r, null, 2)
  } catch {
    return String(r)
  }
}

const chartUrl = computed(() => {
  const row = props.row
  if (!row || !row.result || !Array.isArray(row.result.plot_files) || row.result.plot_files.length === 0) {
    return ''
  }
  const fullPath = row.result.plot_files[0] || ''
  const parts = fullPath.split(/[/\\]/)
  const filename = parts[parts.length - 1] || ''
  if (!filename) return ''
  return `/api/backtest/output/${row.id}/${filename}`
})

const hasTrades = computed(() => {
  const row = props.row
  if (!row || !row.result) return false
  if (Array.isArray(row.result.trades) && row.result.trades.length > 0) return true
  if (row.result.trade_file) return true
  return false
})
</script>

<style scoped>
.result-json {
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.backtest-chart {
  max-width: 100%;
  max-height: 360px;
  display: block;
}
</style>
