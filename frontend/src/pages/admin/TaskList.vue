<template>
  <div class="task-list">
    <ListView ref="listViewRef" v-bind="listViewOptions">
      <template #toolbar-actions>
        <el-select
          v-model="selectedTaskName"
          placeholder="选择要执行的任务"
          filterable
          clearable
          style="width: 240px"
        >
          <el-option
            v-for="spec in taskSpecs"
            :key="spec.name"
            :label="`${spec.title || spec.name} (${spec.name})`"
            :value="spec.name"
          />
        </el-select>
        <el-button type="primary" :disabled="!selectedTaskName" @click="openRunDialog">发起任务</el-button>
      </template>
      <template #task_name_cell="{ row }">
        <span>{{ getTaskTitle(row.task_name) }}</span>
      </template>
      <template #task_state_cell="{ row }">
        <el-tag :type="stateTagType(row.state)">{{ row.state || 'UNKNOWN' }}</el-tag>
      </template>
      <template #task_created_cell="{ row }">
        {{ formatDateTime(row.created_at) }}
      </template>
      <template #task_updated_cell="{ row }">
        {{ formatDateTime(row.updated_at) }}
      </template>
      <template #task_meta_cell="{ row }">
        <span>{{ row.meta?.status || row.meta?.message || '-' }}</span>
      </template>
    </ListView>
  </div>
</template>

<script setup>
import { h, reactive, ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { openDialog } from '@iottest/vue-core/src/libs/dialogs'
import ListView from '../../components/ListViewNoRouteSync.vue'
import { taskApi } from '../../api/task'
import TaskRunForm from './TaskRunForm.vue'
import TaskDetailPanel from './TaskDetailPanel.vue'

const listViewRef = ref(null)
const taskSpecs = ref([])
const selectedTaskName = ref('')

const taskSpecMap = computed(() => {
  const map = {}
  for (const spec of taskSpecs.value) {
    map[spec.name] = spec
  }
  return map
})

function getTaskTitle(name) {
  if (!name) return '-'
  const spec = taskSpecMap.value[name]
  return spec?.title || name
}

function stateTagType(state) {
  switch (state) {
    case 'PENDING':
      return 'info'
    case 'PROGRESS':
    case 'STARTED':
      return 'warning'
    case 'SUCCESS':
      return 'success'
    case 'FAILURE':
    case 'REVOKED':
      return 'danger'
    default:
      return ''
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return value
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd} ${hh}:${mi}:${ss}`
  } catch {
    return value
  }
}

const reloadTable = async () => {
  await listViewRef.value?.reload()
}

async function fetchSpecs() {
  try {
    const data = await taskApi.getSpecs()
    taskSpecs.value = Array.isArray(data) ? data : []
  } catch {
    /* 拦截器已提示 */
  }
}

const loadTaskList = async (page, pageSize) => {
  const data = await taskApi.list({
    limit: pageSize,
    offset: (page - 1) * pageSize,
  })
  return {
    results: data?.items || [],
    count: data?.total || 0,
  }
}

function openRunDialog() {
  if (!selectedTaskName.value) return
  const spec = taskSpecMap.value[selectedTaskName.value]
  if (!spec) return
  let formVNode
  const holder = { dlg: null }
  holder.dlg = openDialog({
    title: '发起任务',
    width: 600,
    render: () => {
      formVNode = h(TaskRunForm, { spec })
      return formVNode
    },
    async onOk(dialog) {
      try {
        await formVNode?.component?.exposed?.submit()
        dialog.close()
        await reloadTable()
      } catch (e) {
        if (e?.message === 'validation') return
      }
    },
    onCancel(dialog) {
      dialog.close()
    },
  })
}

async function showDetail(row) {
  if (!row?.task_id) return
  try {
    const data = await taskApi.get(row.task_id)
    openDialog({
      title: '任务详情',
      width: 700,
      showFooter: false,
      render: () =>
        h(TaskDetailPanel, {
          detail: data,
          taskTitle: getTaskTitle(data?.task_name),
        }),
    })
  } catch {
    /* 拦截器 */
  }
}

async function stopTask(row) {
  if (!row?.task_id || !canStop(row)) return
  try {
    await ElMessageBox.confirm(
      '确定要停止该任务吗？\n这会向 Celery worker 发送终止信号，具体效果取决于任务实现。',
      '停止任务确认',
      { type: 'warning', confirmButtonText: '停止', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await taskApi.stop(row.task_id)
    ElMessage.success('已请求停止任务')
    await reloadTable()
  } catch {
    /* 拦截器 */
  }
}

async function deleteTask(row) {
  if (!row?.task_id) return
  try {
    await ElMessageBox.confirm('确定要从任务列表中删除该任务记录吗？仅删除本地记录，不影响 Celery 后端。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await taskApi.delete(row.task_id)
    ElMessage.success('已删除')
    await reloadTable()
  } catch {
    /* 拦截器 */
  }
}

function canStop(row) {
  if (!row?.state) return false
  return ['PENDING', 'PROGRESS', 'STARTED'].includes(row.state)
}

const listViewOptions = reactive({
  title: '任务管理',
  model: 'task',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    inlineEdit: false,
    actionColumnWidth: 220,
  },
  elTableProps: {
    height: 520,
  },
  hooks: {
    actionLoadData: loadTaskList,
  },
  fields: [
    { key: 'task_id', label: '任务ID', minWidth: 220 },
    {
      key: 'task_name',
      label: '任务名称',
      minWidth: 180,
      slotName: 'task_name',
    },
    {
      key: 'state',
      label: '状态',
      width: 110,
      slotName: 'task_state',
    },
    {
      key: 'created_at',
      label: '创建时间',
      minWidth: 170,
      slotName: 'task_created',
    },
    {
      key: 'updated_at',
      label: '更新时间',
      minWidth: 170,
      slotName: 'task_updated',
    },
    {
      key: 'meta',
      label: '进度/信息',
      minWidth: 220,
      slotName: 'task_meta',
    },
  ],
  actions: [
    {
      label: '详情',
      buttonType: 'primary',
      action: async (item) => showDetail(item),
    },
    {
      label: '停止',
      buttonType: 'danger',
      disabled: (item) => !canStop(item),
      action: async (item) => stopTask(item),
    },
    {
      label: '删除',
      buttonType: 'danger',
      action: async (item) => deleteTask(item),
    },
  ],
})

onMounted(() => {
  fetchSpecs()
})
</script>

<style scoped>
.task-list {
  min-height: 0;
}
</style>
