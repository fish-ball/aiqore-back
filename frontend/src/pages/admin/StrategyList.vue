<template>
  <div class="strategy-list">
    <ListView ref="listViewRef" v-bind="listViewOptions">
      <template #strategy_id_short_cell="{ row }">
        <el-tooltip :content="row.id" placement="top">
          <span>{{ row.id ? row.id.slice(0, 8) : '-' }}</span>
        </el-tooltip>
      </template>
      <template #strategy_type_tag_cell="{ row }">
        <el-tag size="small">{{ strategyTypeLabel(row.strategy_type) }}</el-tag>
      </template>
      <template #strategy_script_preview_cell="{ row }">
        <span>{{ scriptPreview(row.script) }}</span>
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
import { strategyApi } from '../../api/strategy'
import StrategyBacktestForm from './StrategyBacktestForm.vue'

const router = useRouter()
const listViewRef = ref(null)

const reloadTable = async () => {
  await listViewRef.value?.reload()
}

const strategyTypeLabel = (t) => {
  const m = { backtrader: 'Backtrader' }
  return m[t] || t
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

function scriptPreview(script) {
  if (!script) return '--'
  return script.length > 80 ? `${script.slice(0, 80)}...` : script
}

const loadStrategyList = async (page, pageSize) => {
  const res = await strategyApi.getList()
  const items = res?.items ? res.items : []
  const total = items.length
  const start = (page - 1) * pageSize
  return {
    results: items.slice(start, start + pageSize),
    count: total,
  }
}

function buildStrategyFields() {
  return [
    {
      key: 'name',
      label: '策略名称',
      type: 'text',
      required: true,
      htmlType: 'text',
      placeholder: '请输入策略名称',
      controlProps: { maxlength: 100, showWordLimit: true },
    },
    {
      key: 'strategy_type',
      label: '策略类型',
      type: 'select',
      required: true,
      choices: [{ text: 'Backtrader', value: 'backtrader' }],
    },
    {
      key: 'script',
      label: '代码 script',
      type: 'text',
      htmlType: 'textarea',
      placeholder: '策略代码（可选）',
      controlProps: { rows: 14 },
    },
  ]
}

function getEmptyForm() {
  return {
    name: '',
    strategy_type: 'backtrader',
    script: '',
  }
}

function mapRowToForm(row) {
  return {
    id: row.id,
    name: row.name,
    strategy_type: row.strategy_type,
    script: row.script || '',
  }
}

/** 使用 openDialog + EmbedForm，替代手写 el-dialog */
function openStrategyFormDialog(item, title) {
  return new Promise((resolve, reject) => {
    let formVNode
    const formOpts = reactive({
      item,
      fields: buildStrategyFields(),
      size: 'default',
      options: { formOptions: { labelWidth: '100px' } },
    })
    openDialog({
      title,
      width: 640,
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
            strategy_type: validated.strategy_type,
            script: validated.script?.trim() || null,
          }
          if (validated.id != null && validated.id !== '') {
            await strategyApi.update(validated.id, payload)
            ElMessage.success('更新成功')
          } else {
            await strategyApi.create(payload)
            ElMessage.success('创建成功')
          }
          dialog.close()
          resolve()
        } catch {
          /* EmbedForm 校验失败已弹窗；接口错误由 axios 拦截器提示 */
        }
      },
      onCancel(dialog) {
        dialog.close()
        reject(new Error('cancel'))
      },
    })
  })
}

const openCreate = () => {
  const item = reactive(getEmptyForm())
  void (async () => {
    try {
      await openStrategyFormDialog(item, '新建策略')
      await reloadTable()
    } catch (e) {
      if (e?.message !== 'cancel') throw e
    }
  })()
}

const openEdit = (row) => {
  const item = reactive(mapRowToForm(row))
  void (async () => {
    try {
      await openStrategyFormDialog(item, '编辑策略')
      await reloadTable()
    } catch (e) {
      if (e?.message !== 'cancel') throw e
    }
  })()
}

function goBacktestRecords() {
  router.push({ path: '/backtest-records' })
}

function openBacktestDialog(row) {
  let formVNode
  openDialog({
    title: '发起回测',
    width: 520,
    actions: [
      {
        label: '回测记录',
        position: 'left',
        async action(dialog) {
          router.push({ path: '/backtest-records', query: { strategy: row.id } })
          dialog.close()
        },
      },
    ],
    render: () => {
      formVNode = h(StrategyBacktestForm, { strategyId: row.id })
      return formVNode
    },
    async onOk(dialog) {
      try {
        await formVNode?.component?.exposed?.submit()
        dialog.close()
      } catch (e) {
        if (e?.message === 'validation') return
      }
    },
    onCancel(dialog) {
      dialog.close()
    },
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除策略「${row.name}」吗？`, '确认删除', {
      type: 'warning',
    })
    await strategyApi.delete(row.id)
    ElMessage.success('已删除')
    await reloadTable()
  } catch (e) {
    if (e !== 'cancel') {
      throw e
    }
  }
}

const listViewOptions = reactive({
  title: '策略管理',
  model: 'strategy',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 240,
  },
  elTableProps: {
    height: 520,
  },
  hooks: {
    actionLoadData: loadStrategyList,
  },
  listActions: [
    {
      label: '回测记录',
      action: async () => goBacktestRecords(),
    },
    {
      label: '新建策略',
      buttonType: 'primary',
      action: async () => openCreate(),
    },
  ],
  fields: [
    {
      key: 'id',
      label: 'ID',
      width: 100,
      slotName: 'strategy_id_short',
    },
    {
      key: 'name',
      label: '策略名称',
      minWidth: 160,
      elTableColumnProps: { showOverflowTooltip: true },
    },
    {
      key: 'strategy_type',
      label: '策略类型',
      width: 120,
      slotName: 'strategy_type_tag',
    },
    {
      key: 'script',
      label: '代码',
      minWidth: 200,
      slotName: 'strategy_script_preview',
      elTableColumnProps: { showOverflowTooltip: true },
    },
    {
      key: 'updated_at',
      label: '更新时间',
      width: 165,
      filter: (v) => formatDate(v),
    },
  ],
  actions: [
    {
      label: '回测',
      buttonType: 'primary',
      action: async (item) => openBacktestDialog(item),
    },
    {
      label: '编辑',
      action: async (item) => openEdit(item),
    },
    {
      label: '删除',
      buttonType: 'danger',
      action: async (item) => handleDelete(item),
    },
  ],
})
</script>

<style scoped>
.strategy-list {
  min-height: 0;
}
</style>
