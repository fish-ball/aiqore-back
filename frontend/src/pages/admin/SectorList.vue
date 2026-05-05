<template>
  <ListView ref="listViewRef" v-bind="listViewOptions">
    <template #sector_name_link_cell="{ row }">
      <el-link type="primary" @click="viewSectorSecurities(row.alias)">
        {{ row.name }}
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
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import ListView from '../../components/ListViewNoRouteSync.vue'
import { api } from '@iottest/vue-core/src/libs/api'

const router = useRouter()
const listViewRef = ref(null)
const sectorSyncResource = api('sector/sync')
const securityUpdateResource = api('instrument/update')

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

const viewSectorSecurities = (sectorAlias) => {
  router.push({
    name: 'admin-instruments-old',
    query: { sector: sectorAlias },
  })
}

const syncSectorSecurities = async (sectorAlias) => {
  try {
    await ElMessageBox.confirm(`确定要同步板块 "${sectorAlias}" 的证券吗？`, '确认同步', {
      type: 'warning',
    })
  } catch (e) {
    if (e === 'cancel') return
    throw e
  }
  const uResp = await securityUpdateResource.post({}, { source_type: 'qmt', sector: sectorAlias })
  const result = uResp.data
  if (result && result.task_id) {
    ElMessage.success('同步任务已提交，请查看任务列表')
  } else {
    ElMessage.error('提交同步任务失败')
  }
}

const editSectorRemark = async (item) => {
  const alias = item?.alias
  if (!alias) return
  try {
    const { value } = await ElMessageBox.prompt('请输入该板块的备注信息', '编辑备注', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: item.remark || '',
      inputType: 'textarea',
      customClass: 'sector-remark-prompt',
    })
    const trimmed = typeof value === 'string' ? value.trim() : ''
    await axios.patch(`/api/sector/${encodeURIComponent(alias)}`, {
      remark: trimmed.length ? trimmed : null,
    })
    ElMessage.success('备注已保存')
    await listViewRef.value?.reload()
  } catch (e) {
    if (e === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
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
    actionColumnWidth: 300,
  },
  elTableProps: {
    height: 600,
  },
  fields: [
    {
      key: 'alias',
      label: '别名',
      width: 160,
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'name',
      label: '显示名称',
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
    {
      key: 'remark',
      label: '备注',
      minWidth: 160,
      filter: (value) => (value && String(value).trim() ? String(value) : '--'),
      elTableColumnProps: { sortable: false, showOverflowTooltip: true },
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
      label: '编辑备注',
      buttonType: 'default',
      action: async (item) => editSectorRemark(item),
    },
    {
      label: '同步证券',
      buttonType: 'primary',
      action: async (item) => syncSectorSecurities(item?.alias),
    },
    {
      label: '查看证券',
      buttonType: 'info',
      action: (item) => viewSectorSecurities(item?.alias),
    },
  ],
})
</script>

<style scoped></style>
