<template>
  <div v-if="spec" class="task-run-form">
    <p class="task-title">
      {{ spec.title || spec.name }}
      <span class="task-name">（{{ spec.name }}）</span>
    </p>
    <p v-if="spec.description" class="task-desc">{{ spec.description }}</p>

    <el-alert
      v-if="spec.params && spec.params.length"
      title="参数说明"
      type="info"
      :closable="false"
      class="param-alert"
    >
      <ul class="param-list">
        <li v-for="p in spec.params" :key="p.name">
          <strong>{{ p.name }}</strong>
          <span v-if="p.required" class="required-flag">（必填）</span>
          <span v-else class="optional-flag">（可选）</span>
          <span v-if="p.description">：{{ p.description }}</span>
          <span v-if="p.default !== null && p.default !== undefined">，默认值：{{ String(p.default) }}</span>
        </li>
      </ul>
    </el-alert>

    <el-form v-if="spec.params && spec.params.length" label-width="120px">
      <el-form-item v-for="p in spec.params" :key="p.name" :label="`${p.name}${p.required ? ' *' : ''}`">
        <el-input
          v-if="!p.type || p.type === 'string'"
          v-model="runForm[p.name]"
          :placeholder="p.description || `请输入 ${p.name}`"
          clearable
        />
        <el-input-number
          v-else-if="p.type === 'integer' || p.type === 'number'"
          v-model="runForm[p.name]"
          :placeholder="p.description || `请输入 ${p.name}`"
          :controls="false"
          style="width: 100%"
        />
        <el-switch
          v-else-if="p.type === 'boolean'"
          v-model="runForm[p.name]"
          active-text="是"
          inactive-text="否"
        />
        <el-input
          v-else-if="p.type === 'array[string]'"
          v-model="runFormArrayText[p.name]"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 8 }"
          :placeholder="p.description ? `${p.description}；多个值用逗号或换行分隔` : '多个值用逗号或换行分隔'"
        />
        <el-input
          v-else
          v-model="runForm[p.name]"
          :placeholder="p.description || `请输入 ${p.name}`"
          clearable
        />
      </el-form-item>
    </el-form>

    <el-alert v-else title="此任务无需参数，直接点击下方「提交」即可。" type="success" :closable="false" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '../../api/task'

const props = defineProps({
  spec: { type: Object, default: null },
})

const runForm = ref({})
const runFormArrayText = ref({})
const submitting = ref(false)

function initRunForm(spec) {
  const obj = {}
  const arrText = {}
  if (spec && Array.isArray(spec.params)) {
    for (const p of spec.params) {
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

watch(
  () => props.spec,
  (s) => {
    if (s) initRunForm(s)
  },
  { immediate: true },
)

/** 供 openDialog 页脚「确定」调用 */
async function submit() {
  if (!props.spec) return
  const spec = props.spec
  const params = {}

  if (spec && Array.isArray(spec.params)) {
    for (const p of spec.params) {
      const name = p.name
      const type = p.type || 'string'

      if (type === 'array[string]') {
        const text = (runFormArrayText.value && runFormArrayText.value[name]) || ''
        if (!text.trim()) {
          if (p.required) {
            ElMessage.error(`参数 ${name} 为必填`)
            throw new Error('validation')
          }
          continue
        }
        const parts = text
          .split(/[\n\r,]+/)
          .map((s) => s.trim())
          .filter((s) => s.length > 0)
        if (!parts.length) {
          if (p.required) {
            ElMessage.error(`参数 ${name} 为必填`)
            throw new Error('validation')
          }
          continue
        }
        params[name] = parts
        continue
      }

      const value = runForm.value ? runForm.value[name] : undefined

      if (p.required) {
        if (type === 'boolean') {
          /* 允许 false */
        } else if (value === '' || value === null || value === undefined) {
          ElMessage.error(`参数 ${name} 为必填`)
          throw new Error('validation')
        }
      }

      if (value === '' || value === null || value === undefined) {
        continue
      }

      if (type === 'integer' || type === 'number') {
        const num = Number(value)
        if (Number.isNaN(num)) {
          ElMessage.error(`参数 ${name} 必须是数字`)
          throw new Error('validation')
        }
        params[name] = type === 'integer' ? parseInt(num, 10) : num
      } else if (type === 'boolean') {
        params[name] = !!value
      } else {
        params[name] = value
      }
    }
  }

  submitting.value = true
  try {
    const data = await taskApi.run(spec.name, params)
    ElMessage.success(`任务已提交，ID: ${data.task_id}`)
  } finally {
    submitting.value = false
  }
}

defineExpose({ submit, submitting })
</script>

<style scoped>
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
</style>
