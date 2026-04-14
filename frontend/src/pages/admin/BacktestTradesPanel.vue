<template>
  <el-table :data="trades" v-loading="loading" height="400">
    <el-table-column prop="date" label="日期" width="140" />
    <el-table-column prop="type" label="方向" width="80" />
    <el-table-column prop="price" label="价格" width="120" />
    <el-table-column prop="size" label="数量" width="120" />
  </el-table>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@iottest/vue-core/src/libs/api'
import { unwrapEnvelope } from '../../config/unwrapEnvelope'

const backtestTasksResource = api('backtest/tasks')

const props = defineProps({
  taskId: { type: String, required: true },
})

const loading = ref(true)
const trades = ref([])

onMounted(async () => {
  try {
    const resp = await backtestTasksResource.get({ id: props.taskId, action: 'trades' }, {})
    const res = unwrapEnvelope(resp)
    trades.value = Array.isArray(res) ? res : []
  } catch (e) {
    trades.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取交易明细失败')
  } finally {
    loading.value = false
  }
})
</script>
