<template>
  <ListView ref="listViewRef" v-bind="listViewOptions">
    <template #instrument_stock_exchange_cell="{ row }">
      <span>{{ formatExchange(row) }}</span>
    </template>
    <template #instrument_stock_active_cell="{ row }">
      <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
        {{ row.is_active ? '有效' : '无效' }}
      </el-tag>
    </template>
  </ListView>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ListView from '../../components/ListViewNoRouteSync.vue'
import type { SecurityTableRow } from '../../types/security'

const router = useRouter()
const listViewRef = ref(null)

/** 列表日期展示 */
const formatDateValue = (value: unknown) => {
  if (!value) return '—'
  return new Date(String(value)).toLocaleString('zh-CN')
}

/** 最新价 */
const formatPrice = (value: unknown) => {
  if (value === null || value === undefined) return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(3)
}

/** 交易所展示（嵌套 exchange 或 exchange_code） */
const formatExchange = (row: SecurityTableRow & { is_active?: boolean }) => {
  const ex = row.exchange
  if (ex && (ex.short_name || ex.name)) return String(ex.short_name || ex.name)
  if (row.exchange_code) return row.exchange_code
  return '—'
}

const listViewOptions = reactive({
  title: '股票',
  model: 'instrument/list',
  /** 固定筛选：仅股票类型 */
  filters: {
    instrument_type: 'STOCK',
  },
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 120,
  },
  elTableProps: {
    height: 600,
    defaultSort: { prop: 'code', order: 'ascending' },
  },
  fields: [
    {
      key: 'code',
      label: '代码',
      width: 120,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'name',
      label: '名称',
      minWidth: 160,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'market',
      label: '市场',
      width: 80,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'exchange',
      label: '交易所',
      width: 120,
      slotName: 'instrument_stock_exchange',
    },
    {
      key: 'asset_class',
      label: '资产大类',
      width: 110,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'instrument_type',
      label: '标的类型',
      width: 100,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'last_price',
      label: '最新价',
      width: 100,
      filter: (v: unknown) => formatPrice(v),
    },
    {
      key: 'abbreviation',
      label: '拼音缩写',
      width: 100,
      filter: (v: unknown) => v || '—',
    },
    {
      key: 'is_active',
      label: '状态',
      width: 90,
      slotName: 'instrument_stock_active',
    },
    {
      key: 'created_at',
      label: '创建时间',
      minWidth: 170,
      filter: (v: unknown) => formatDateValue(v),
    },
    {
      key: 'updated_at',
      label: '更新时间',
      minWidth: 170,
      filter: (v: unknown) => formatDateValue(v),
    },
  ],
  actions: [
    {
      label: '详情',
      buttonType: 'primary' as const,
      action: (item: unknown) => {
        const row = item as SecurityTableRow
        if (!row?.code) return
        router.push({
          name: 'admin-instrument-detail',
          params: { symbol: row.code },
        })
      },
    },
  ],
})
</script>

<style scoped></style>
