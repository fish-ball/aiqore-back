<template>
  <ListView v-bind="listViewOptions">
    <template #sector_name_link_cell="{ row }">
      <el-link type="primary" @click="viewSectorSecurities(row.name)">
        {{ row.display_name || row.name }}
      </el-link>
    </template>
    <template #sector_category_cell="{ row }">
      <el-tag :type="getCategoryTagType(row.category)" size="small">
        {{ row.category || '其他' }}
      </el-tag>
    </template>
    <template #sector_market_cell="{ row }">
      <el-tag
        v-if="row.market"
        :type="row.market === 'SH' ? 'success' : 'warning'"
        size="small"
      >
        {{ row.market === 'SH' ? '上海' : row.market === 'SZ' ? '深圳' : row.market }}
      </el-tag>
      <span v-else style="color: #909399">跨市场</span>
    </template>
  </ListView>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ListView from '../../components/ListViewNoRouteSync.vue'
import { api } from '@iottest/vue-core/src/libs/api'

const router = useRouter()
const sectorSyncResource = api('sector/sync')
const securityUpdateResource = api('security/update')

const formatDateValue = (value) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN')
}

// ElTag 的 type 仅允许 primary/success/info/warning/danger，禁止传空字符串
const getCategoryTagType = (category) => {
  const typeMap = {
    股票: 'success',
    基金: 'primary',
    债券: 'warning',
    期货: 'danger',
    期权: 'info',
    指数: 'info',
  }
  return typeMap[category]
}

const viewSectorSecurities = (sectorName) => {
  router.push({
    name: 'admin-securities',
    query: { sector: sectorName },
  })
}

const syncSectorSecurities = async (sectorName) => {
  try {
    await ElMessageBox.confirm(`确定要同步板块 "${sectorName}" 的证券吗？`, '确认同步', {
      type: 'warning',
    })
  } catch (e) {
    if (e === 'cancel') return
    throw e
  }
  const uResp = await securityUpdateResource.post({}, { source_type: 'qmt', sector: sectorName })
  const result = uResp.data
  if (result && result.task_id) {
    ElMessage.success('同步任务已提交，请查看任务列表')
  } else {
    ElMessage.error('提交同步任务失败')
  }
}

const syncAllSectors = async (ctx) => {
  try {
    await ElMessageBox.confirm('确定要从QMT同步板块列表吗？', '确认同步', {
      type: 'warning',
    })
  } catch (e) {
    if (e === 'cancel') return
    throw e
  }
  const resp = await sectorSyncResource.post({}, {})
  const response = resp.data || {}
  ElMessage.success(
    `同步完成: 新增 ${response.created || 0} 个，更新 ${response.updated || 0} 个`,
  )
  await ctx?.$table?.reload()
}

const listViewOptions = reactive({
  title: '板块',
  model: 'sector/list',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 220,
  },
  elTableProps: {
    height: 600,
  },
  fields: [
    {
      key: 'name',
      label: '板块名称',
      width: 200,
      slotName: 'sector_name_link',
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'category',
      label: '分类',
      width: 100,
      slotName: 'sector_category',
      elTableColumnProps: { sortable: true },
      filtering: {
        type: 'select',
        key: 'category',
        choices: [
          { text: '全部', value: '' },
          { text: '股票', value: '股票' },
          { text: '基金', value: '基金' },
          { text: '债券', value: '债券' },
          { text: '期货', value: '期货' },
          { text: '期权', value: '期权' },
          { text: '指数', value: '指数' },
        ],
      },
    },
    {
      key: 'market',
      label: '市场',
      width: 100,
      slotName: 'sector_market',
      elTableColumnProps: { sortable: true },
      filtering: {
        type: 'select',
        key: 'market',
        choices: [
          { text: '全部', value: '' },
          { text: '上海', value: 'SH' },
          { text: '深圳', value: 'SZ' },
          { text: '跨市场', value: '__cross__' },
        ],
      },
    },
    {
      key: 'security_count',
      label: '证券数量',
      width: 120,
      filter: (value) => value ?? 0,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'last_sync_at',
      label: '最后同步',
      minWidth: 180,
      filter: (value) => formatDateValue(value),
      elTableColumnProps: { sortable: true },
    },
  ],
  listActions: [
    {
      label: '同步板块',
      buttonType: 'primary',
      action: syncAllSectors,
    },
  ],
  actions: [
    {
      label: '同步证券',
      buttonType: 'primary',
      action: async (item) => syncSectorSecurities(item?.name),
    },
    {
      label: '查看证券',
      buttonType: 'info',
      action: (item) => viewSectorSecurities(item?.name),
    },
  ],
})
</script>

<style scoped></style>
