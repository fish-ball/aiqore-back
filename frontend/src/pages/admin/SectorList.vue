<template>
  <ListView ref="listViewRef" v-bind="listViewOptions">
    <template #sector_name_link_cell="{ row }">
      <el-link type="primary" @click="viewSectorSecurities(row.alias)">
        {{ row.name }}
      </el-link>
    </template>
    <template #sector_asset_class_cell="{ row }">
      <el-tag type="info" size="small" effect="plain">{{ assetClassLabel(row.asset_class) }}</el-tag>
    </template>
    <template #sector_instrument_type_cell="{ row }">
      <el-tag
        :type="getGroupTagType(sectorGroupLabelFromInstrumentType(row.instrument_type))"
        size="small"
      >
        {{ sectorGroupLabelFromInstrumentType(row.instrument_type) }}
      </el-tag>
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
import { useDataSourceStore } from '../../stores/dataSource'
import {
  assetClassLabel,
  sectorGroupLabelFromInstrumentType,
  ASSET_CLASS_LABELS,
  INSTRUMENT_TYPE_LABELS,
} from '../../utils/sectorLabels'

const router = useRouter()
const dataSourceStore = useDataSourceStore()
const listViewRef = ref(null)
const sectorSyncResource = api('sector/sync')
const securityUpdateResource = api('instrument/update')

const formatDateValue = (value) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN')
}

const getGroupTagType = (category) => {
  const typeMap = {
    股票: 'success',
    基金: 'primary',
    ETF: 'primary',
    债券: 'warning',
    期货: 'danger',
    期权: 'info',
    指数: 'info',
    其他: '',
  }
  return typeMap[category] || ''
}

const assetClassFilterChoices = [
  { text: '全部', value: '' },
  ...Object.keys(ASSET_CLASS_LABELS).map((k) => ({
    text: `${k}（${ASSET_CLASS_LABELS[k]}）`,
    value: k,
  })),
]

const instrumentTypeFilterChoices = [
  { text: '全部', value: '' },
  ...Object.keys(INSTRUMENT_TYPE_LABELS).map((k) => ({
    text: `${k}（${INSTRUMENT_TYPE_LABELS[k]}）`,
    value: k,
  })),
]

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
  const sid = await dataSourceStore.requireDataSourceId()
  const uResp = await securityUpdateResource.post({}, { source_id: sid, sector: sectorAlias })
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
    await ElMessageBox.confirm('确定要从当前所选数据源同步板块列表吗？', '确认同步', {
      type: 'warning',
    })
  } catch (e) {
    if (e === 'cancel') return
    throw e
  }
  const sid = await dataSourceStore.requireDataSourceId()
  const resp = await sectorSyncResource.post({}, { source_id: sid })
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
      width: 160,
      slotName: 'sector_name_link',
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'source',
      label: '数据源',
      width: 140,
      elTableColumnProps: { sortable: true },
      filtering: {
        type: 'select',
        key: 'source',
        choices: [
          { text: '全部', value: '' },
          { text: 'qmt', value: 'qmt' },
          { text: 'joinquant', value: 'joinquant' },
          { text: 'tushare', value: 'tushare' },
        ],
      },
    },
    {
      key: 'asset_class',
      label: '资产大类',
      width: 140,
      slotName: 'sector_asset_class',
      elTableColumnProps: { sortable: true },
      filtering: {
        type: 'select',
        key: 'asset_class',
        choices: assetClassFilterChoices,
      },
    },
    {
      key: 'instrument_type',
      label: '标的类型',
      width: 140,
      slotName: 'sector_instrument_type',
      elTableColumnProps: { sortable: true },
      filtering: {
        type: 'select',
        key: 'instrument_type',
        choices: instrumentTypeFilterChoices,
      },
    },
    {
      key: 'parent_id',
      label: '父级',
      width: 88,
      filter: (value) => (value != null && value !== '' ? value : '--'),
      elTableColumnProps: { sortable: true },
    },
    {
      key: 'updated_at',
      label: '最后更新',
      minWidth: 170,
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
