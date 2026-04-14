<template>
  <div class="backtest-record-list">
    <ListView ref="listViewRef" v-bind="listViewOptions">
      <template #bt_task_id_cell="{ row }">
        <el-tooltip :content="row.id" placement="top">
          <span>{{ row.id ? row.id.slice(0, 8) : '-' }}</span>
        </el-tooltip>
      </template>
      <template #bt_strategy_cell="{ row }">
        <span>
          {{
            row.strategy_id
              ? row.strategy_id.slice(0, 8) + (row.strategy_name ? ` ${row.strategy_name}` : '')
              : '-'
          }}
        </span>
      </template>
      <template #bt_status_cell="{ row }">
        <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
      </template>
      <template #bt_result_summary_cell="{ row }">
        <span v-if="row.result && row.status === 'success'">
          收益 {{ formatPct(row.result.total_return) }}，回撤 {{ formatPct(row.result.max_drawdown) }}
        </span>
        <span v-else-if="row.result && row.result.error">{{ row.result.error }}</span>
        <span v-else>-</span>
      </template>
    </ListView>
  </div>
</template>

<script setup>
import { h, reactive, ref, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { openDialog } from '@iottest/vue-core/src/libs/dialogs'
import ListView from '../../components/ListViewNoRouteSync.vue'
import BacktestDetailPanel from './BacktestDetailPanel.vue'
import BacktestTradesPanel from './BacktestTradesPanel.vue'

const route = useRoute()
const listViewRef = ref(null)

const statusLabel = (s) => {
  const m = { pending: '待执行', running: '运行中', success: '成功', failure: '失败' }
  return m[s] || s || '-'
}

const statusTagType = (s) => {
  const m = { pending: 'info', running: 'warning', success: 'success', failure: 'danger' }
  return m[s] || 'info'
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

function formatPct(v) {
  if (v == null) return '-'
  return `${(v * 100).toFixed(2)}%`
}

function showDetail(row) {
  openDialog({
    title: '回测任务详情',
    width: 720,
    showFooter: false,
    render: () =>
      h(BacktestDetailPanel, {
        row,
        onOpenTrades: () => openTradesDialog(row),
      }),
  })
}

function openTradesDialog(row) {
  openDialog({
    title: '交易明细',
    width: 800,
    showFooter: false,
    render: () => h(BacktestTradesPanel, { taskId: row.id }),
  })
}

/** 与路由 query.strategy 同步到列表筛选 */
function syncRouteStrategyToTable() {
  const sid = route.query.strategy
  if (sid != null && sid !== '') {
    listViewRef.value?.doQuery({ strategy: String(sid) })
  } else {
    listViewRef.value?.doQuery({ strategy: undefined })
  }
}

onMounted(async () => {
  await nextTick()
  await nextTick()
  syncRouteStrategyToTable()
})

watch(
  () => route.query.strategy,
  async () => {
    await nextTick()
    syncRouteStrategyToTable()
  },
)

const listViewOptions = reactive({
  title: '回测记录',
  model: 'backtest/tasks',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: true,
    inlineEdit: false,
    actionColumnWidth: 140,
  },
  elTableProps: {
    height: 480,
  },
  fields: [
    {
      key: 'id',
      label: '任务 ID',
      width: 100,
      slotName: 'bt_task_id',
    },
    {
      key: 'strategy_id',
      label: '策略',
      minWidth: 180,
      slotName: 'bt_strategy',
      elTableColumnProps: { showOverflowTooltip: true },
      filtering: {
        type: 'keyword',
        key: 'strategy',
      },
    },
    {
      key: 'security_symbol',
      label: '证券代码',
      width: 110,
    },
    {
      key: 'security_name',
      label: '证券名称',
      minWidth: 100,
      elTableColumnProps: { showOverflowTooltip: true },
    },
    {
      key: 'start_date',
      label: '开始日期',
      width: 110,
    },
    {
      key: 'end_date',
      label: '结束日期',
      width: 110,
    },
    {
      key: 'status',
      label: '状态',
      width: 90,
      slotName: 'bt_status',
      filtering: {
        type: 'select',
        key: 'status',
        choices: [
          { text: '全部', value: '' },
          { text: '待执行', value: 'pending' },
          { text: '运行中', value: 'running' },
          { text: '成功', value: 'success' },
          { text: '失败', value: 'failure' },
        ],
      },
    },
    {
      key: 'result',
      label: '结果摘要',
      minWidth: 180,
      slotName: 'bt_result_summary',
      elTableColumnProps: { showOverflowTooltip: true },
    },
    {
      key: 'created_at',
      label: '创建时间',
      width: 165,
      filter: (v) => formatDate(v),
    },
  ],
  actions: [
    {
      label: '详情',
      buttonType: 'primary',
      action: async (item) => showDetail(item),
    },
  ],
})
</script>

<style scoped>
.backtest-record-list {
  min-height: 0;
}
</style>
