<template>
  <div class="trades">
    <div class="page-header">
      <h2>交易记录</h2>
      <div>
        <el-select v-model="selectedAccountId" placeholder="选择账户" style="width: 200px; margin-right: 10px">
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.name || account.account_id"
            :value="account.id"
          />
        </el-select>
        <el-button type="primary" @click="showRecordDialog = true" :disabled="!selectedAccountId">
          <el-icon><Plus /></el-icon>
          记录交易
        </el-button>
      </div>
    </div>

    <el-card style="margin-top: 20px">
      <el-table :data="trades" style="width: 100%" v-loading="loading">
        <el-table-column prop="symbol" label="代码" />
        <el-table-column prop="symbol_name" label="名称" />
        <el-table-column prop="direction" label="方向">
          <template #default="scope">
            <el-tag :type="scope.row.direction === '买入' ? 'success' : 'danger'">
              {{ scope.row.direction }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" :formatter="formatMoney" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="amount" label="金额" :formatter="formatMoney" />
        <el-table-column prop="commission" label="手续费" :formatter="formatMoney" />
        <el-table-column prop="tax" label="税费" :formatter="formatMoney" />
        <el-table-column prop="trade_time" label="交易时间" :formatter="formatDate" />
        <el-table-column prop="remark" label="备注" />
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchTrades"
        @current-change="fetchTrades"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 记录交易对话框 -->
    <el-dialog v-model="showRecordDialog" title="记录交易" width="600px">
      <el-form :model="tradeForm" label-width="100px">
        <el-form-item label="证券代码" required>
          <el-input v-model="tradeForm.symbol" placeholder="如：000001.SZ" />
        </el-form-item>
        <el-form-item label="证券名称">
          <el-input v-model="tradeForm.symbol_name" placeholder="请输入证券名称" />
        </el-form-item>
        <el-form-item label="交易方向" required>
          <el-radio-group v-model="tradeForm.direction">
            <el-radio label="买入">买入</el-radio>
            <el-radio label="卖出">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="价格" required>
          <el-input-number v-model="tradeForm.price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="tradeForm.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="交易时间" required>
          <el-date-picker
            v-model="tradeForm.trade_time"
            type="datetime"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="手续费">
          <el-input-number v-model="tradeForm.commission" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="税费">
          <el-input-number v-model="tradeForm.tax" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="tradeForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRecordDialog = false">取消</el-button>
        <el-button type="primary" @click="handleRecord" :loading="recording">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAccountStore } from '../stores/account'
import { tradeApi } from '../api/trade'

const accountStore = useAccountStore()
const loading = ref(false)
const recording = ref(false)
const trades = ref([])
const selectedAccountId = ref(null)
const showRecordDialog = ref(false)

const accounts = computed(() => accountStore.accounts)

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const tradeForm = ref({
  symbol: '',
  symbol_name: '',
  direction: '买入',
  price: 0,
  quantity: 0,
  trade_time: new Date().toISOString().slice(0, 19),
  commission: 0,
  tax: 0,
  remark: ''
})

const formatMoney = (row, column, cellValue) => {
  return `¥${parseFloat(cellValue || 0).toFixed(2)}`
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return '--'
  return new Date(cellValue).toLocaleString('zh-CN')
}

const fetchTrades = async () => {
  if (!selectedAccountId.value) {
    trades.value = []
    return
  }
  
  loading.value = true
  try {
    const data = await tradeApi.getTrades(selectedAccountId.value, {
      limit: pagination.value.pageSize,
      offset: (pagination.value.page - 1) * pagination.value.pageSize
    })
    trades.value = data.items || []
    pagination.value.total = data.total || 0
  } catch (error) {
    console.error('获取交易记录失败:', error)
    ElMessage.error('获取交易记录失败')
  } finally {
    loading.value = false
  }
}

const handleRecord = async () => {
  if (!tradeForm.value.symbol || !tradeForm.value.price || !tradeForm.value.quantity) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  recording.value = true
  try {
    await tradeApi.recordTrade(selectedAccountId.value, tradeForm.value)
    ElMessage.success('记录成功')
    showRecordDialog.value = false
    tradeForm.value = {
      symbol: '',
      symbol_name: '',
      direction: '买入',
      price: 0,
      quantity: 0,
      trade_time: new Date().toISOString().slice(0, 19),
      commission: 0,
      tax: 0,
      remark: ''
    }
    await fetchTrades()
  } catch (error) {
    ElMessage.error('记录失败')
  } finally {
    recording.value = false
  }
}

watch(selectedAccountId, () => {
  pagination.value.page = 1
  fetchTrades()
})

onMounted(async () => {
  await accountStore.fetchAccounts()
  if (accounts.value.length > 0) {
    selectedAccountId.value = accounts.value[0].id
  }
})
</script>

<style scoped>
.trades {
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

