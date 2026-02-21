<template>
  <div class="data-source-connections">
    <div class="page-header">
      <h2>数据源连接</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建连接
      </el-button>
    </div>

    <el-card style="margin-top: 20px">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="source_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ sourceTypeLabel(row.source_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="160">
          <template #default="{ row }">
            <el-tag v-if="row.is_quote_source" size="small" type="success" style="margin-right: 4px">行情源</el-tag>
            <el-tag v-if="row.is_trading_source" size="small" type="warning">交易源</el-tag>
            <span v-if="!row.is_quote_source && !row.is_trading_source">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="启用" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" width="120" show-overflow-tooltip />
        <el-table-column prop="updated_at" label="更新时间" width="165">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleTest(row)" :loading="testingId === row.id">测试</el-button>
            <el-button size="small" @click="goDebug(row)">调试</el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 第一步：选择数据源类型（仅新建时使用） -->
    <el-dialog v-model="typeSelectVisible" title="选择数据源类型" width="480px" destroy-on-close>
      <div class="type-select-cards">
        <div class="type-card" @click="chooseType('qmt')">
          <div class="type-card-title">miniQMT / QMT</div>
          <div class="type-card-desc">国金 QMT 或 miniQMT 本地行情与交易，需配置 xtquant 路径等。</div>
        </div>
        <div class="type-card" @click="chooseType('joinquant')">
          <div class="type-card-title">聚宽</div>
          <div class="type-card-desc">聚宽平台数据源，需配置 Token / API（后续开放）。</div>
        </div>
        <div class="type-card" @click="chooseType('tushare')">
          <div class="type-card-title">Tushare</div>
          <div class="type-card-desc">Tushare 数据源，需配置 Token（后续开放）。</div>
        </div>
      </div>
    </el-dialog>

    <!-- 第二步：按类型展示的独立表单弹窗 -->
    <!-- QMT 表单 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="formDialogTitle"
      width="520px"
      destroy-on-close
      v-if="form.source_type === 'qmt'"
    >
      <el-form ref="formRef" :model="form" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="xtquant 路径" required>
          <el-input v-model="form.xt_quant_path" placeholder="miniQMT 的 userdata_mini 目录，如 C:\国金证券QMT交易端\userdata_mini" />
        </el-form-item>
        <el-form-item label="资金账号" required>
          <el-input v-model="form.xt_quant_acct" placeholder="交易/账户同步时使用，与 miniQMT 客户端登录账号一致" />
        </el-form-item>
        <el-form-item label="设为行情源">
          <el-switch v-model="form.is_quote_source" />
        </el-form-item>
        <el-form-item label="设为交易驱动源">
          <el-switch v-model="form.is_trading_source" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 聚宽表单 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="formDialogTitle"
      width="520px"
      destroy-on-close
      v-if="form.source_type === 'joinquant'"
    >
      <el-form ref="formRef" :model="form" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="说明">
          <span class="form-hint">聚宽需配置 Token / API，后续开放；当前仅保存名称与类型。</span>
        </el-form-item>
        <el-form-item label="设为行情源">
          <el-switch v-model="form.is_quote_source" />
        </el-form-item>
        <el-form-item label="设为交易驱动源">
          <el-switch v-model="form.is_trading_source" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- Tushare 表单 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="formDialogTitle"
      width="520px"
      destroy-on-close
      v-if="form.source_type === 'tushare'"
    >
      <el-form ref="formRef" :model="form" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="说明">
          <span class="form-hint">Tushare 需配置 Token，后续开放；当前仅保存名称与类型。</span>
        </el-form-item>
        <el-form-item label="设为行情源">
          <el-switch v-model="form.is_quote_source" />
        </el-form-item>
        <el-form-item label="设为交易驱动源">
          <el-switch v-model="form.is_trading_source" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" rows="2" placeholder="可选" />
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { dataSourceApi } from '../api/dataSource'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const testingId = ref(null)
const typeSelectVisible = ref(false)
const formDialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const form = ref({
  name: '',
  source_type: 'qmt',
  is_active: true,
  is_quote_source: false,
  is_trading_source: false,
  host: '',
  port: 7709,
  user: '',
  password: '',
  xt_quant_path: '',
  xt_quant_acct: '',
  description: ''
})

const formDialogTitle = computed(() => {
  const t = form.value.source_type
  const typeName = { qmt: 'miniQMT/QMT', joinquant: '聚宽', tushare: 'Tushare' }[t] || t
  return isEdit.value ? `编辑${typeName}连接` : `新建${typeName}连接`
})

const sourceTypeLabel = (t) => {
  const m = { qmt: 'miniQMT/QMT', joinquant: '聚宽', tushare: 'Tushare' }
  return m[t] || t
}

const formatDate = (v) => {
  if (!v) return '--'
  return new Date(v).toLocaleString('zh-CN')
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await dataSourceApi.getList()
    list.value = (res && res.items) ? res.items : []
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

function getEmptyForm(type) {
  const base = {
    name: '',
    source_type: type,
    is_active: true,
    is_quote_source: false,
    is_trading_source: false,
    description: ''
  }
  if (type === 'qmt') {
    return { ...base, host: '', port: null, user: '', password: '', xt_quant_path: '', xt_quant_acct: '' }
  }
  return base
}

const chooseType = (type) => {
  form.value = getEmptyForm(type)
  typeSelectVisible.value = false
  formDialogVisible.value = true
}

const openCreate = () => {
  isEdit.value = false
  typeSelectVisible.value = true
}

const goDebug = (row) => {
  router.push({ path: '/data-sources/debug/' + row.id, query: { name: row.name, source_type: row.source_type } })
}

const handleTest = async (row) => {
  testingId.value = row.id
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
  } finally {
    testingId.value = null
  }
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = {
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
    description: row.description || ''
  }
  formDialogVisible.value = true
}

const submit = async () => {
  if (!form.value.name?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  if (form.value.source_type === 'qmt') {
    if (!form.value.xt_quant_path?.trim()) {
      ElMessage.warning('请填写 xtquant 路径')
      return
    }
    if (!form.value.xt_quant_acct?.trim()) {
      ElMessage.warning('请填写资金账号')
      return
    }
  }
  submitting.value = true
  try {
    const isQmt = form.value.source_type === 'qmt'
    const payload = {
      name: form.value.name.trim(),
      source_type: form.value.source_type,
      is_active: form.value.is_active,
      is_quote_source: form.value.is_quote_source,
      is_trading_source: form.value.is_trading_source,
      host: isQmt ? (form.value.host?.trim() || null) : null,
      port: isQmt ? (form.value.port ?? null) : null,
      user: isQmt ? (form.value.user?.trim() || null) : null,
      xt_quant_path: isQmt ? (form.value.xt_quant_path?.trim() || null) : null,
      xt_quant_acct: isQmt ? (form.value.xt_quant_acct?.trim() || null) : null,
      description: form.value.description?.trim() || null
    }
    if (isEdit.value) {
      await dataSourceApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await dataSourceApi.create(payload)
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
    await ElMessageBox.confirm(`确定删除连接「${row.name}」吗？`, '确认删除', {
      type: 'warning'
    })
    await dataSourceApi.delete(row.id)
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
.data-source-connections h2 {
  margin: 0;
}
.form-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.type-select-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.type-card {
  padding: 14px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.type-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-fill-color-light);
}
.type-card-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.type-card-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>
