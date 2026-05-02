<template>
  <ListView v-bind="listViewOptions">
    <template #exchange_suffix_cell="{ row }">
      <el-tag v-if="row.suffix" type="success" size="small">{{ row.suffix }}</el-tag>
      <span v-else style="color: #909399">—</span>
    </template>
    <template #exchange_active_cell="{ row }">
      <el-tag :type="row.is_active === 1 ? 'success' : 'info'" size="small">
        {{ row.is_active === 1 ? '有效' : '无效' }}
      </el-tag>
    </template>
  </ListView>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ListView from '../../components/ListViewNoRouteSync.vue'
import type { ExchangeRow } from '../../types/exchange'

const router = useRouter()

const SPOT_MARKET_SUFFIXES = new Set(['SH', 'SZ', 'BJ'])

const viewSecuritiesByMarket = (item: ExchangeRow) => {
  const q: Record<string, string> = {}
  if (item?.code) q.exchange_code = item.code
  const suf = item?.suffix?.trim().toUpperCase()
  if (suf && SPOT_MARKET_SUFFIXES.has(suf)) q.market = suf
  if (Object.keys(q).length === 0) {
    ElMessage.info('无法跳转证券列表（缺少交易所代码）')
    return
  }
  router.push({
    name: 'admin-securities',
    query: q,
  })
}

const listViewOptions = reactive({
  title: '交易所',
  model: 'exchange/list',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 160,
  },
  elTableProps: {
    height: 600,
    defaultSort: { prop: 'sort_order', order: 'ascending' },
  },
  fields: [
    {
      key: 'code',
      label: '代码',
      width: 100,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'short_name',
      label: '简称',
      width: 100,
      filter: (v: unknown) => v || '—',
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'name',
      label: '全称',
      minWidth: 220,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'suffix',
      label: '证券后缀',
      width: 110,
      slotName: 'exchange_suffix',
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'country_region',
      label: '地区',
      width: 80,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'sort_order',
      label: '排序',
      width: 90,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'is_active',
      label: '状态',
      width: 90,
      slotName: 'exchange_active',
    },
  ],
  actions: [
    {
      label: '查看证券',
      buttonType: 'primary',
      action: (item: unknown) => viewSecuritiesByMarket(item as ExchangeRow),
    },
  ],
})
</script>

<style scoped></style>
