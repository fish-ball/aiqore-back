<template>
  <div class="task-manager">
    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="selectedTaskName"
            placeholder="选择要执行的任务"
            filterable
            clearable
            style="width: 280px"
          >
            <el-option
              v-for="spec in taskSpecs"
              :key="spec.name"
              :label="`${spec.title || spec.name} (${spec.name})`"
              :value="spec.name"
            />
          </el-select>
          <el-button
            type="primary"
            :disabled="!selectedTaskName"
            @click="openRunDialog"
          >
            发起任务
          </el-button>
          <el-button @click="fetchTaskList" :loading="loadingTasks">
            刷新列表
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table
        :data="taskList"
        border
        size="small"
        :height="tableHeight"
      >
        <el-table-column prop="task_id" label="任务ID" min-width="220" />
        <el-table-column prop="task_name" label="任务名称" min-width="180">
          <template #default="{ row }">
            <span>{{ getTaskTitle(row.task_name) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="state" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="stateTagType(row.state)">
              {{ row.state || 'UNKNOWN' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170">
          <template #default="{ row }">
            <span>{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="170">
          <template #default="{ row }">
            <span>{{ formatDateTime(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="进度/信息" min-width="220">
          <template #default="{ row }">
            <span>{{ row.meta?.status || row.meta?.message || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="showDetail(row)"
            >
              详情
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="!canStop(row)"
              @click="stopTask(row)"
            >
              停止
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              @click="deleteTask(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          background
          layout="prev, pager, next, jumper"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 发起任务对话框：根据任务规格动态渲染参数表单 -->
    <el-dialog
      v-model="runDialogVisible"
      title="发起任务"
      width="600px"
    >
      <div v-if="currentTaskSpec">
        <p class="task-title">
          {{ currentTaskSpec.title || currentTaskSpec.name }}
          <span class="task-name">（{{ currentTaskSpec.name }}）</span>
        </p>
        <p class="task-desc" v-if="currentTaskSpec.description">
          {{ currentTaskSpec.description }}
        </p>

        <el-alert
          v-if="currentTaskSpec.params && currentTaskSpec.params.length"
          title="参数说明"
          type="info"
          :closable="false"
          class="param-alert"
        >
          <ul class="param-list">
            <li v-for="p in currentTaskSpec.params" :key="p.name">
              <strong>{{ p.name }}</strong>
              <span v-if="p.required" class="required-flag">（必填）</span>
              <span v-else class="optional-flag">（可选）</span>
              <span v-if="p.description">：{{ p.description }}</span>
              <span v-if="p.default !== null && p.default !== undefined">
                ，默认值：{{ String(p.default) }}
              </span>
            </li>
          </ul>
        </el-alert>

        <el-form label-width="120px" v-if="currentTaskSpec.params && currentTaskSpec.params.length">
          <el-form-item
            v-for="p in currentTaskSpec.params"
            :key="p.name"
            :label="`${p.name}${p.required ? ' *' : ''}`"
          >
            <!-- 字符串类型 -->
            <el-input
              v-if="!p.type || p.type === 'string'"
              v-model="runForm[p.name]"
              :placeholder="p.description || `请输入 ${p.name}`"
              clearable
            />

            <!-- 整数 / 数值类型 -->
            <el-input-number
              v-else-if="p.type === 'integer' || p.type === 'number'"
              v-model="runForm[p.name]"
              :placeholder="p.description || `请输入 ${p.name}`"
              :controls="false"
              style="width: 100%"
            />

            <!-- 布尔类型 -->
            <el-switch
              v-else-if="p.type === 'boolean'"
              v-model="runForm[p.name]"
              active-text="是"
              inactive-text="否"
            />

            <!-- 字符串数组 -->
            <el-input
              v-else-if="p.type === 'array[string]'"
              v-model="runFormArrayText[p.name]"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              :placeholder="p.description ? `${p.description}；多个值用逗号或换行分隔` : '多个值用逗号或换行分隔'"
            />

            <!-- 兜底：按字符串处理 -->
            <el-input
              v-else
              v-model="runForm[p.name]"
              :placeholder="p.description || `请输入 ${p.name}`"
              clearable
            />
          </el-form-item>
        </el-form>

        <el-alert
          v-else
          title="此任务无需参数，直接点击下方“提交”即可。"
          type="success"
          :closable="false"
        />
      </div>
      <template #footer>
        <el-button @click="runDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="runningTask" @click="submitRun">
          提 交
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="700px"
    >
      <el-descriptions
        v-if="currentTaskDetail"
        :column="1"
        border
        size="small"
      >
        <el-descriptions-item label="任务ID">
          {{ currentTaskDetail.task_id }}
        </el-descriptions-item>
        <el-descriptions-item label="任务名称">
          {{ getTaskTitle(currentTaskDetail.task_name) }}
          <span v-if="currentTaskDetail.task_name" class="task-name">
            （{{ currentTaskDetail.task_name }}）
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="stateTagType(currentTaskDetail.state)">
            {{ currentTaskDetail.state || 'UNKNOWN' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(currentTaskDetail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDateTime(currentTaskDetail.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="参数">
          <pre class="json-block">{{ prettyJson(currentTaskDetail.params) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="元数据 / 进度">
          <pre class="json-block">{{ prettyJson(currentTaskDetail.meta) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '../api/task'

const taskSpecs = ref([])
const selectedTaskName = ref('')

const taskList = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadingTasks = ref(false)

const runDialogVisible = ref(false)
const currentTaskSpec = ref(null)
// 表单参数对象：key 为参数名
const runForm = ref({})
// 数组类型参数使用的纯文本输入（逗号 / 换行分隔）
const runFormArrayText = ref({})
const runningTask = ref(false)

const detailDialogVisible = ref(false)
const currentTaskDetail = ref(null)

const tableHeight = computed(() => 520)

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
  } catch (e) {
    return value
  }
}

function prettyJson(obj) {
  if (!obj) return '-'
  try {
    return JSON.stringify(obj, null, 2)
  } catch (e) {
    return String(obj)
  }
}

function canStop(row) {
  if (!row || !row.state) return false
  return ['PENDING', 'PROGRESS', 'STARTED'].includes(row.state)
}

async function fetchSpecs() {
  try {
    const data = await taskApi.getSpecs()
    taskSpecs.value = Array.isArray(data) ? data : []
  } catch (e) {
    // 已在全局拦截器中提示
  }
}

async function fetchTaskList() {
  loadingTasks.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value
    }
    const data = await taskApi.list(params)
    taskList.value = data?.items || []
    total.value = data?.total || 0
  } catch (e) {
    // 已在全局拦截器中提示
  } finally {
    loadingTasks.value = false
  }
}

function handlePageChange(p) {
  page.value = p
  fetchTaskList()
}

function initRunForm(spec) {
  const obj = {}
  const arrText = {}

  if (spec && Array.isArray(spec.params)) {
    for (const p of spec.params) {
      // 字符串数组单独处理
      if (p.type === 'array[string]') {
        const def = p.default
        if (Array.isArray(def) && def.length) {
          arrText[p.name] = def.join('\n')
        } else if (typeof def === 'string') {
          arrText[p.name] = def
        } else {
          arrText[p.name] = ''
        }
        continue
      }

      if (p.default !== null && p.default !== undefined) {
        obj[p.name] = p.default
      } else if (p.type === 'boolean') {
        obj[p.name] = false
      } else if (p.type === 'integer' || p.type === 'number') {
        obj[p.name] = null
      } else {
        obj[p.name] = ''
      }
    }
  }

  runForm.value = obj
  runFormArrayText.value = arrText
}

function openRunDialog() {
  if (!selectedTaskName.value) return
  const spec = taskSpecMap.value[selectedTaskName.value] || null
  currentTaskSpec.value = spec
  initRunForm(spec)
  runDialogVisible.value = true
}

async function submitRun() {
  if (!currentTaskSpec.value) return

  const spec = currentTaskSpec.value
  const params = {}

  if (spec && Array.isArray(spec.params)) {
    for (const p of spec.params) {
      const name = p.name
      const type = p.type || 'string'

      // 处理数组类型
      if (type === 'array[string]') {
        const text = (runFormArrayText.value && runFormArrayText.value[name]) || ''
        if (!text.trim()) {
          if (p.required) {
            ElMessage.error(`参数 ${name} 为必填`)
            return
          }
          continue
        }
        const parts = text
          .split(/[\n\r,]+/)
          .map(s => s.trim())
          .filter(s => s.length > 0)
        if (!parts.length) {
          if (p.required) {
            ElMessage.error(`参数 ${name} 为必填`)
            return
          }
          continue
        }
        params[name] = parts
        continue
      }

      const value = runForm.value ? runForm.value[name] : undefined

      // 必填校验
      if (p.required) {
        if (type === 'boolean') {
          // 布尔类型允许 false
        } else if (value === '' || value === null || value === undefined) {
          ElMessage.error(`参数 ${name} 为必填`)
          return
        }
      }

      if (value === '' || value === null || value === undefined) {
        // 非必填且未填写则跳过
        continue
      }

      if (type === 'integer' || type === 'number') {
        const num = Number(value)
        if (Number.isNaN(num)) {
          ElMessage.error(`参数 ${name} 必须是数字`)
          return
        }
        params[name] = type === 'integer' ? parseInt(num, 10) : num
      } else if (type === 'boolean') {
        params[name] = !!value
      } else {
        params[name] = value
      }
    }
  }

  runningTask.value = true
  try {
    const data = await taskApi.run(currentTaskSpec.value.name, params)
    ElMessage.success(`任务已提交，ID: ${data.task_id}`)
    runDialogVisible.value = false
    // 刷新一次列表
    fetchTaskList()
  } catch (e) {
    // 已在全局拦截器中提示
  } finally {
    runningTask.value = false
  }
}

async function showDetail(row) {
  if (!row || !row.task_id) return
  try {
    const data = await taskApi.get(row.task_id)
    currentTaskDetail.value = data
    detailDialogVisible.value = true
  } catch (e) {
    // 已在全局拦截器中提示
  }
}

async function stopTask(row) {
  if (!row || !row.task_id || !canStop(row)) return

  try {
    await ElMessageBox.confirm(
      '确定要停止该任务吗？\n这会向 Celery worker 发送终止信号，具体效果取决于任务实现。',
      '停止任务确认',
      {
        type: 'warning',
        confirmButtonText: '停止',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  try {
    await taskApi.stop(row.task_id)
    ElMessage.success('已请求停止任务')
    fetchTaskList()
  } catch (e) {
    // 已在全局拦截器中提示
  }
}

async function deleteTask(row) {
  if (!row || !row.task_id) return

  try {
    await ElMessageBox.confirm(
      '确定要从任务列表中删除该任务记录吗？仅删除本地记录，不影响 Celery 后端。',
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  try {
    await taskApi.delete(row.task_id)
    ElMessage.success('已删除')
    fetchTaskList()
  } catch (e) {
    // 已在全局拦截器中提示
  }
}

onMounted(() => {
  fetchSpecs()
  fetchTaskList()
})
</script>

<style scoped>
.task-manager {
  padding: 16px;
}

.toolbar-card {
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-card {
  margin-bottom: 16px;
}

.pagination-wrapper {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.task-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.task-name {
  font-size: 13px;
  color: #909399;
}

.task-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 10px;
}

.param-alert {
  margin-bottom: 16px;
}

.param-list {
  padding-left: 18px;
  margin: 0;
}

.param-list li {
  font-size: 13px;
  line-height: 1.6;
}

.required-flag {
  color: #f56c6c;
}

.optional-flag {
  color: #909399;
}

.json-block {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
}
</style>

