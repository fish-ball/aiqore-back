<template>
  <el-descriptions v-if="detail" :column="1" border size="small">
    <el-descriptions-item label="任务 ID">{{ detail.task_id }}</el-descriptions-item>
    <el-descriptions-item label="任务名称">
      {{ taskTitle }}
      <span v-if="detail.task_name" class="task-name">（{{ detail.task_name }}）</span>
    </el-descriptions-item>
    <el-descriptions-item label="状态">
      <el-tag :type="stateTagType(detail.state)">{{ detail.state || 'UNKNOWN' }}</el-tag>
    </el-descriptions-item>
    <el-descriptions-item label="创建时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
    <el-descriptions-item label="更新时间">{{ formatDateTime(detail.updated_at) }}</el-descriptions-item>
    <el-descriptions-item label="参数">
      <pre class="json-block">{{ prettyJson(detail.params) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item label="元数据 / 进度">
      <pre class="json-block">{{ prettyJson(detail.meta) }}</pre>
    </el-descriptions-item>
  </el-descriptions>
</template>

<script setup>
defineProps({
  detail: { type: Object, default: null },
  taskTitle: { type: String, default: '' },
})

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

function prettyJson(obj) {
  if (!obj) return '-'
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}
</script>

<style scoped>
.task-name {
  font-size: 13px;
  color: #909399;
}
.json-block {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
}
</style>
