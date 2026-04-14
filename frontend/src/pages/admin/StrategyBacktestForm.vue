<template>
  <el-form label-width="100px">
    <el-form-item label="策略">
      <el-input :model-value="strategyId" disabled placeholder="当前策略" />
    </el-form-item>
    <el-form-item label="证券代码" required>
      <el-input v-model="form.symbol" placeholder="如 600519.SH" />
    </el-form-item>
    <el-form-item label="开始日期" required>
      <el-date-picker
        v-model="form.start_date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择开始日期"
        style="width: 100%"
      />
    </el-form-item>
    <el-form-item label="结束日期" required>
      <el-date-picker
        v-model="form.end_date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择结束日期"
        style="width: 100%"
      />
    </el-form-item>
    <el-form-item label="初始资金">
      <el-input-number v-model="form.initial_cash" :min="10000" :step="100000" style="width: 100%" />
    </el-form-item>
    <el-form-item label="手续费">
      <el-input-number v-model="form.commission" :min="0" :max="0.01" :step="0.0001" :precision="4" style="width: 100%" />
    </el-form-item>
    <el-form-item label="仓位比例(%)">
      <el-input-number v-model="form.position_pct" :min="1" :max="100" style="width: 100%" />
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@iottest/vue-core/src/libs/api'
import { unwrapEnvelope } from '../../config/unwrapEnvelope'

const backtestRunResource = api('backtest/run')

const props = defineProps({
  strategyId: { type: String, default: '' },
})

const form = ref({
  symbol: '',
  start_date: '',
  end_date: '',
  initial_cash: 1000000,
  commission: 0.0002,
  position_pct: 95,
})

watch(
  () => props.strategyId,
  (id) => {
    if (id) {
      form.value = {
        symbol: '',
        start_date: '',
        end_date: '',
        initial_cash: 1000000,
        commission: 0.0002,
        position_pct: 95,
      }
    }
  },
  { immediate: true },
)

async function submit() {
  if (!form.value.symbol?.trim()) {
    ElMessage.warning('请填写证券代码')
    throw new Error('validation')
  }
  if (!form.value.start_date) {
    ElMessage.warning('请选择开始日期')
    throw new Error('validation')
  }
  if (!form.value.end_date) {
    ElMessage.warning('请选择结束日期')
    throw new Error('validation')
  }
  const resp = await backtestRunResource.post({}, {
    strategy_id: props.strategyId,
    symbol: form.value.symbol.trim(),
    start_date: form.value.start_date,
    end_date: form.value.end_date,
    initial_cash: form.value.initial_cash,
    commission: form.value.commission,
    position_pct: form.value.position_pct,
  })
  const res = unwrapEnvelope(resp)
  const taskId = res?.backtest_task_id
  ElMessage.success(taskId ? '回测已提交，请到回测记录查看' : '提交成功')
}

defineExpose({ submit })
</script>
