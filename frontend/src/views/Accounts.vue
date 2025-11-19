<template>
  <div class="accounts">
    <div class="page-header">
      <h2>账户管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建账户
      </el-button>
    </div>

    <el-card style="margin-top: 20px">
      <el-table :data="accounts" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="account_id" label="账户ID" />
        <el-table-column prop="name" label="账户名称" />
        <el-table-column prop="initial_capital" label="初始资金" :formatter="formatMoney" />
        <el-table-column prop="current_balance" label="当前余额" :formatter="formatMoney" />
        <el-table-column prop="available_balance" label="可用余额" :formatter="formatMoney" />
        <el-table-column prop="created_at" label="创建时间" :formatter="formatDate" />
        <el-table-column label="操作" width="250">
          <template #default="scope">
            <el-button size="small" @click="viewAccount(scope.row.id)">查看</el-button>
            <el-button size="small" type="success" @click="syncAccount(scope.row.id)">同步</el-button>
            <el-button size="small" type="info" @click="viewPositions(scope.row.id)">持仓</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建账户对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建账户" width="500px">
      <el-form :model="accountForm" label-width="100px">
        <el-form-item label="账户ID" required>
          <el-input v-model="accountForm.account_id" placeholder="请输入账户ID" />
        </el-form-item>
        <el-form-item label="账户名称">
          <el-input v-model="accountForm.name" placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="初始资金" required>
          <el-input-number v-model="accountForm.initial_capital" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountStore } from '../stores/account'
import { tradeApi } from '../api/trade'

const router = useRouter()
const accountStore = useAccountStore()
const loading = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)

const accounts = computed(() => accountStore.accounts)

const accountForm = ref({
  account_id: '',
  name: '',
  initial_capital: 0
})

const formatMoney = (row, column, cellValue) => {
  return `¥${parseFloat(cellValue || 0).toFixed(2)}`
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return '--'
  return new Date(cellValue).toLocaleString('zh-CN')
}

const viewAccount = (accountId) => {
  router.push(`/analysis?accountId=${accountId}`)
}

const viewPositions = (accountId) => {
  router.push(`/positions?accountId=${accountId}`)
}

const syncAccount = async (accountId) => {
  try {
    await tradeApi.syncAccount(accountId)
    ElMessage.success('同步成功')
    await accountStore.fetchAccounts()
  } catch (error) {
    ElMessage.error('同步失败')
  }
}

const handleCreate = async () => {
  if (!accountForm.value.account_id) {
    ElMessage.warning('请输入账户ID')
    return
  }
  
  creating.value = true
  try {
    await accountStore.createAccount(accountForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    accountForm.value = {
      account_id: '',
      name: '',
      initial_capital: 0
    }
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  loading.value = true
  await accountStore.fetchAccounts()
  loading.value = false
})
</script>

<style scoped>
.accounts {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}
</style>

