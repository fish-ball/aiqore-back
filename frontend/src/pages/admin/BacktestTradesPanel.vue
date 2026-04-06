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
import { backtestApi } from '../../api/backtest'

const props = defineProps({
  taskId: { type: String, required: true },
})

const loading = ref(true)
const trades = ref([])

onMounted(async () => {
  try {
    const res = await backtestApi.getTrades(props.taskId)
    if (Array.isArray(res)) {
      trades.value = res
    } else if (res && Array.isArray(res.data)) {
      trades.value = res.data
    } else {
      trades.value = []
    }
  } catch (e) {
    trades.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取交易明细失败')
  } finally {
    loading.value = false
  }
})
</script>
