<template>
  <div class="data-source-connection-list">
    <ListView ref="listViewRef" v-bind="listViewOptions">
      <template #ds_source_type_cell="{ row }">
        <el-tag size="small">{{ sourceTypeLabel(row.source_type) }}</el-tag>
      </template>
      <template #ds_roles_cell="{ row }">
        <el-tag v-if="row.is_quote_source" size="small" type="success" style="margin-right: 4px">行情源</el-tag>
        <el-tag v-if="row.is_trading_source" size="small" type="warning">交易源</el-tag>
        <span v-if="!row.is_quote_source && !row.is_trading_source">-</span>
      </template>
      <template #ds_active_cell="{ row }">
        <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag>
      </template>
    </ListView>
  </div>
</template>

<script setup>
import { h, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ListView from '../../components/ListViewNoRouteSync.vue'
import EmbedForm from '@iottest/vue-core/src/libs/data-view/components/EmbedForm.vue'
import { openDialog } from '@iottest/vue-core/src/libs/dialogs'
import { dataSourceApi } from '../../api/dataSource'
import DataSourceTypePicker from './DataSourceTypePicker.vue'

const router = useRouter()
const listViewRef = ref(null)

const reloadTable = async () => {
  await listViewRef.value?.reload()
}

const sourceTypeLabel = (t) => {
  const m = { qmt: 'miniQMT/QMT', joinquant: '聚宽', tushare: 'Tushare' }
  return m[t] || t
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

const loadDataSourceList = async (page, pageSize, query) => {
  const params = {}
  if (query.source_type) params.source_type = query.source_type
  if (query.is_active === 'true') params.is_active = true
  else if (query.is_active === 'false') params.is_active = false
  const res = await dataSourceApi.getList(params)
  const items = res?.items ? res.items : []
  const total = items.length
  const start = (page - 1) * pageSize
  return {
    results: items.slice(start, start + pageSize),
    count: total,
  }
}

function formTitle(sourceType, edit) {
  const typeName = { qmt: 'miniQMT/QMT', joinquant: '聚宽', tushare: 'Tushare' }[sourceType] || sourceType
  return edit ? `编辑${typeName}连接` : `新建${typeName}连接`
}

function getEmptyForm(type) {
  const base = {
    name: '',
    source_type: type,
    is_active: true,
    is_quote_source: false,
    is_trading_source: false,
    description: '',
    hint: '',
  }
  if (type === 'qmt') {
    return { ...base, host: '', port: null, user: '', password: '', xt_quant_path: '', xt_quant_acct: '' }
  }
  return base
}

function buildFields(sourceType) {
  const nameField = {
    key: 'name',
    label: '名称',
    type: 'text',
    required: true,
    htmlType: 'text',
    placeholder: '显示名称',
  }
  const switches = [
    { key: 'is_quote_source', label: '设为行情源', type: 'switch' },
    { key: 'is_trading_source', label: '设为交易驱动源', type: 'switch' },
    { key: 'is_active', label: '启用', type: 'switch' },
  ]
  const desc = {
    key: 'description',
    label: '备注',
    type: 'text',
    htmlType: 'textarea',
    placeholder: '可选',
    controlProps: { rows: 2 },
  }
  if (sourceType === 'qmt') {
    return [
      nameField,
      {
        key: 'xt_quant_path',
        label: 'xtquant 路径',
        type: 'text',
        required: true,
        htmlType: 'text',
        placeholder: 'miniQMT 的 userdata_mini 目录，如 C:\\国金证券QMT交易端\\userdata_mini',
      },
      {
        key: 'xt_quant_acct',
        label: '资金账号',
        type: 'text',
        required: true,
        htmlType: 'text',
        placeholder: '交易/账户同步时使用，与 miniQMT 客户端登录账号一致',
      },
      ...switches,
      desc,
    ]
  }
  if (sourceType === 'joinquant' || sourceType === 'tushare') {
    return [
      nameField,
      { key: 'hint', label: '说明', type: 'label' },
      ...switches,
      desc,
    ]
  }
  return [nameField, ...switches, desc]
}

function mapRowToForm(row) {
  return {
    id: row.id,
    name: row.name,
    source_type: row.source_type,
    is_active: row.is_active,
    is_quote_source: row.is_quote_source,
    is_trading_source: row.is_trading_source,
    host: row.host || '',
    port: row.port ?? null,
    user: row.user || '',
    password: '',
    xt_quant_path: row.xt_quant_path || '',
    xt_quant_acct: row.xt_quant_acct || '',
    description: row.description || '',
    hint:
      row.source_type === 'joinquant'
        ? '聚宽需配置 Token / API，后续开放；当前仅保存名称与类型。'
        : row.source_type === 'tushare'
          ? 'Tushare 需配置 Token，后续开放；当前仅保存名称与类型。'
          : '',
  }
}

/** 使用 vue-core 的 openDialog + EmbedForm，替代手写 el-dialog */
function openDataSourceFormDialog(item, fields, title) {
  return new Promise((resolve, reject) => {
    let formVNode
    const formOpts = reactive({
      item,
      fields,
      size: 'default',
      options: { formOptions: { labelWidth: '120px' } },
    })
    openDialog({
      title,
      width: 520,
      render: () => {
        formVNode = h(EmbedForm, formOpts)
        return formVNode
      },
      async onOk(dialog) {
        try {
          const inst = formVNode?.component
          const validated = await inst?.exposed?.validate()
          if (!validated) return
          const isQmt = validated.source_type === 'qmt'
          const payload = {
            name: validated.name.trim(),
            source_type: validated.source_type,
            is_active: validated.is_active,
            is_quote_source: validated.is_quote_source,
            is_trading_source: validated.is_trading_source,
            host: isQmt ? (validated.host?.trim() || null) : null,
            port: isQmt ? (validated.port ?? null) : null,
            user: isQmt ? (validated.user?.trim() || null) : null,
            xt_quant_path: isQmt ? (validated.xt_quant_path?.trim() || null) : null,
            xt_quant_acct: isQmt ? (validated.xt_quant_acct?.trim() || null) : null,
            description: validated.description?.trim() || null,
          }
          if (validated.id != null && validated.id !== '') {
            await dataSourceApi.update(validated.id, payload)
            ElMessage.success('更新成功')
          } else {
            await dataSourceApi.create(payload)
            ElMessage.success('创建成功')
          }
          dialog.close()
          resolve()
        } catch {
          // EmbedForm 校验失败已弹窗；接口错误由 axios 拦截器提示
        }
      },
      onCancel(dialog) {
        dialog.close()
        reject(new Error('cancel'))
      },
    })
  })
}

async function runCreateForm(type) {
  const item = reactive(getEmptyForm(type))
  if (type === 'joinquant') {
    item.hint = '聚宽需配置 Token / API，后续开放；当前仅保存名称与类型。'
  }
  if (type === 'tushare') {
    item.hint = 'Tushare 需配置 Token，后续开放；当前仅保存名称与类型。'
  }
  try {
    await openDataSourceFormDialog(item, buildFields(type), formTitle(type, false))
    await reloadTable()
  } catch (e) {
    if (e?.message !== 'cancel') throw e
  }
}

const openCreate = () => {
  const holder = { dlg: null }
  holder.dlg = openDialog({
    title: '选择数据源类型',
    width: 480,
    showFooter: false,
    render: () =>
      h(DataSourceTypePicker, {
        onPick: (type) => {
          holder.dlg?.close()
          void runCreateForm(type)
        },
      }),
  })
}

const goDebug = (row) => {
  router.push({ path: '/data-sources/debug/' + row.id, query: { name: row.name, source_type: row.source_type } })
}

const handleTest = async (row) => {
  try {
    const res = await dataSourceApi.test(row.id)
    const ok = res?.ok ?? false
    const msg = res?.message ?? (ok ? '连接成功' : '连接失败')
    if (ok) {
      ElMessage.success(msg)
    } else {
      ElMessage.warning(msg)
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '测试失败')
  }
}

const openEdit = (row) => {
  const item = reactive(mapRowToForm(row))
  void (async () => {
    try {
      await openDataSourceFormDialog(item, buildFields(item.source_type), formTitle(item.source_type, true))
      await reloadTable()
    } catch (e) {
      if (e?.message !== 'cancel') throw e
    }
  })()
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除连接「${row.name}」吗？`, '确认删除', {
      type: 'warning',
    })
    await dataSourceApi.delete(row.id)
    ElMessage.success('已删除')
    await reloadTable()
  } catch (e) {
    if (e !== 'cancel') {
      throw e
    }
  }
}

const listViewOptions = reactive({
  title: '数据源连接',
  model: 'data-source',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 300,
  },
  elTableProps: {
    height: 560,
  },
  hooks: {
    actionLoadData: loadDataSourceList,
  },
  fields: [
    { key: 'id', label: 'ID', width: 70 },
    { key: 'name', label: '名称', minWidth: 120 },
    {
      key: 'source_type',
      label: '类型',
      width: 160,
      slotName: 'ds_source_type',
      filtering: {
        type: 'select',
        key: 'source_type',
        choices: [
          { text: '全部', value: '' },
          { text: 'miniQMT/QMT', value: 'qmt' },
          { text: '聚宽', value: 'joinquant' },
          { text: 'Tushare', value: 'tushare' },
        ],
      },
    },
    {
      key: 'is_quote_source',
      label: '角色',
      width: 160,
      slotName: 'ds_roles',
    },
    {
      key: 'is_active',
      label: '启用',
      width: 80,
      slotName: 'ds_active',
      filtering: {
        type: 'select',
        key: 'is_active',
        choices: [
          { text: '全部', value: '' },
          { text: '是', value: 'true' },
          { text: '否', value: 'false' },
        ],
      },
    },
    {
      key: 'host',
      label: '主机',
      width: 120,
      elTableColumnProps: { showOverflowTooltip: true },
    },
    {
      key: 'updated_at',
      label: '更新时间',
      width: 165,
      filter: (v) => formatDate(v),
    },
  ],
  listActions: [
    {
      label: '新建连接',
      buttonType: 'primary',
      action: openCreate,
    },
  ],
  actions: [
    {
      label: '测试',
      action: async (item) => handleTest(item),
    },
    {
      label: '调试',
      action: (item) => goDebug(item),
    },
    {
      label: '编辑',
      action: (item) => openEdit(item),
    },
    {
      label: '删除',
      buttonType: 'danger',
      action: async (item) => handleDelete(item),
    },
  ],
})
</script>

<style scoped></style>
