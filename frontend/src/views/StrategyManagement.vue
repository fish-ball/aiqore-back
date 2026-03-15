<template>
  <div class="strategy-management">
    <div class="page-header">
      <h2>策略管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建策略
      </el-button>
    </div>

    <el-card style="margin-top: 20px">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="策略名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="strategy_type" label="策略类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ strategyTypeLabel(row.strategy_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="script" label="代码" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.script ? (row.script.length > 80 ? row.script.slice(0, 80) + '...' : row.script) : '--' }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="165">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="formDialogVisible"
      :title="formDialogTitle"
      width="640px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="策略名称" required>
          <el-input v-model="form.name" placeholder="请输入策略名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="策略类型" required>
          <el-select v-model="form.strategy_type" placeholder="请选择" style="width: 100%">
            <el-option label="Backtrader" value="backtrader" />
          </el-select>
        </el-form-item>
        <el-form-item label="代码 script">
          <el-input v-model="form.script" type="textarea" :rows="14" placeholder="策略代码（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { strategyApi } from '../api/strategy'

const loading = ref(false)
const list = ref([])
const formDialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const form = ref({
  name: '',
  strategy_type: 'backtrader',
  script: ''
})

const formDialogTitle = computed(() => (isEdit.value ? '编辑策略' : '新建策略'))

const strategyTypeLabel = (t) => {
  const m = { backtrader: 'Backtrader' }
  return m[t] || t
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await strategyApi.getList()
    list.value = (res && res.items) ? res.items : []
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

const getEmptyForm = () => ({
  name: '',
  strategy_type: 'backtrader',
  script: ''
})

const openCreate = () => {
  isEdit.value = false
  form.value = getEmptyForm()
  formDialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = {
    id: row.id,
    name: row.name,
    strategy_type: row.strategy_type,
    script: row.script || ''
  }
  formDialogVisible.value = true
}

const submit = async () => {
  if (!form.value.name?.trim()) {
    ElMessage.warning('请填写策略名称')
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      strategy_type: form.value.strategy_type,
      script: form.value.script?.trim() || null
    }
    if (isEdit.value) {
      await strategyApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await strategyApi.create(payload)
      ElMessage.success('创建成功')
    }
    formDialogVisible.value = false
    await fetchList()
  } catch (e) {
    // error already shown by interceptor
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除策略「${row.name}」吗？`, '确认删除', {
      type: 'warning'
    })
    await strategyApi.delete(row.id)
    ElMessage.success('已删除')
    await fetchList()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.strategy-management h2 {
  margin: 0;
}
</style>
