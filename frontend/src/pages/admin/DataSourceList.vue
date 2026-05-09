<template>
  <div class="data-source-list">
    <ListView ref="listViewRef" v-bind="listViewOptions">
      <template #ds_source_type_cell="{ row }">
        <el-tag size="small">{{ sourceTypeLabel(row.source_type) }}</el-tag>
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
import { ElMessage } from 'element-plus'
import ListView from '../../components/ListViewNoRouteSync.vue'
import EmbedForm from '@iottest/vue-core/src/libs/data-view/components/EmbedForm.vue'
import { openDialog } from '@iottest/vue-core/src/libs/dialogs'
import { api } from '@iottest/vue-core/src/libs/api'
import DataSourceTypePicker from './DataSourceTypePicker.vue'

const router = useRouter()
const listViewRef = ref(null)
const dataSourceConnResource = api('data-source/connections')

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

/** 列表展示 config：QMT 优先显示资金账号等业务字段 */
const formatConfigCell = (v) => {
  if (!v || typeof v !== 'object') return '--'
  if (v.xt_quant_acct) return `资金账号: ${v.xt_quant_acct}`
  const keys = Object.keys(v)
  if (keys.length === 0) return '--'
  const s = JSON.stringify(v)
  return s.length > 80 ? `${s.slice(0, 80)}…` : s
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
    description: '',
    hint: '',
  }
  if (type === 'qmt') {
    return { ...base, hint_qmt: '行情无需配置路径，请保持 miniQMT 客户端已启动。', xt_quant_acct: '' }
  }
  return { ...base, config_json: '{}' }
}

function buildFields(sourceType) {
  const nameField = {
    key: 'name',
    label: '名称',
    type: 'text',
    required: true,
    placeholder: '显示名称',
  }
  const switches = [{ key: 'is_active', label: '启用', type: 'switch' }]
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
        key: 'hint_qmt',
        label: '说明',
        type: 'label',
      },
      {
        key: 'xt_quant_acct',
        label: '资金账号（可选）',
        required: false,
        placeholder: '交易调试等使用，写入 config.xt_quant_acct；行情依赖本机已启动的 miniQMT',
      },
      ...switches,
      desc,
    ]
  }
  if (sourceType === 'joinquant' || sourceType === 'tushare') {
    return [
      nameField,
      {
        key: 'config_json',
        label: '配置 JSON',
        type: 'text',
        htmlType: 'textarea',
        placeholder: '{}',
        controlProps: { rows: 4 },
      },
      { key: 'hint', label: '说明', type: 'label' },
      ...switches,
      desc,
    ]
  }
  return [nameField, ...switches, desc]
}

function mapRowToForm(row) {
  const cfg = row.config && typeof row.config === 'object' ? row.config : {}
  return {
    id: row.id,
    name: row.name,
    source_type: row.source_type,
    is_active: row.is_active,
    hint_qmt: '行情无需配置路径，请保持 miniQMT 客户端已启动。',
    xt_quant_acct: cfg.xt_quant_acct || '',
    config_json: JSON.stringify(cfg && Object.keys(cfg).length ? cfg : {}, null, 2),
    description: row.description || '',
    hint:
      row.source_type === 'joinquant'
        ? '聚宽需配置 Token / API，后续开放；可先在 JSON 中预留字段。'
        : row.source_type === 'tushare'
          ? 'Tushare 需配置 Token，后续开放；可先在 JSON 中预留字段。'
          : '',
  }
}

function buildConfigPayload(validated) {
  const isQmt = validated.source_type === 'qmt'
  if (isQmt) {
    const c = {}
    const a = validated.xt_quant_acct?.trim()
    if (a) c.xt_quant_acct = a
    return c
  }
  try {
    const raw = (validated.config_json || '').trim() || '{}'
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
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
          const payload = {
            name: validated.name.trim(),
            source_type: validated.source_type,
            is_active: validated.is_active,
            config: buildConfigPayload(validated),
            description: validated.description?.trim() || null,
          }
          if (validated.id != null && validated.id !== '') {
            await dataSourceConnResource.put({ id: validated.id }, payload)
            ElMessage.success('更新成功')
          } else {
            await dataSourceConnResource.post({}, payload)
            ElMessage.success('创建成功')
          }
          dialog.close()
          resolve()
        } catch {
          // EmbedForm 校验失败已弹窗；接口错误由全局请求处理或本页 catch 提示
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
    item.hint = '聚宽需配置 Token / API，后续开放；可先在 JSON 中预留字段。'
  }
  if (type === 'tushare') {
    item.hint = 'Tushare 需配置 Token，后续开放；可先在 JSON 中预留字段。'
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
    const resp = await dataSourceConnResource.post({ id: row.id, action: 'test' }, {})
    const res = resp.data
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

const listViewOptions = reactive({
  title: '数据源连接',
  model: 'data-source/connections',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: true,
    inlineEdit: false,
    actionColumnWidth: 300,
  },
  elTableProps: {
    height: 560,
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
      key: 'config',
      label: '配置',
      minWidth: 200,
      elTableColumnProps: { showOverflowTooltip: true },
      filter: (v) => formatConfigCell(v),
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
  ],
})
</script>

<style scoped></style>
