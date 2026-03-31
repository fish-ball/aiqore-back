<template>
  <ListView ref="listViewRef" v-bind="listViewOptions" />
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ListView from '@iottest/vue-core/src/libs/data-view/components/ListView.vue'
import { api } from '@iottest/vue-core/src/libs/api'
import { formatMoneyValue, formatPercentValue } from '../../utils/formatter'

const listViewRef = ref()

const accountResource = api('trade/account')

const loadAccountChoices = async () => {
  const resp = await accountResource.get({}, { page: 1, page_size: 200 })
  const rows = Array.isArray(resp?.data?.results) ? resp.data.results : []
  return rows.map((item) => ({
    text: item.name || item.account_id,
    value: String(item.id),
  }))
}

const syncPositions = async (accountId) => {
  if (!accountId) {
    ElMessage.warning('请先选择账户')
    return
  }
  try {
    await accountResource.post({ id: accountId, action: 'positions/sync' }, {})
    ElMessage.success('同步成功')
    await listViewRef.value?.reload()
  } catch {
    ElMessage.error('同步失败')
  }
}

const listViewOptions = reactive({
  title: '持仓管理',
  model: 'trade/position',
  options: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    actionColumnWidth: 120,
  },
  fields: [
    {
      key: 'account_id',
      label: '账户',
      filtering: {
        type: 'select',
        key: 'account_id',
        choices: () => loadAccountChoices(),
      },
    },
    { key: 'symbol', label: '代码' },
    { key: 'symbol_name', label: '名称' },
    { key: 'quantity', label: '持仓数量' },
    { key: 'cost_price', label: '成本价', filter: (value) => formatMoneyValue(value) },
    { key: 'current_price', label: '当前价', filter: (value) => formatMoneyValue(value) },
    { key: 'market_value', label: '持仓市值', filter: (value) => formatMoneyValue(value) },
    { key: 'profit_loss', label: '盈亏', filter: (value) => formatMoneyValue(value) },
    { key: 'profit_loss_ratio', label: '盈亏率', filter: (value) => formatPercentValue(value) },
  ],
  listActions: [
    {
      label: '同步持仓',
      buttonType: 'primary',
      action: async ({ $table }) => {
        const accountId = $table?.listViewQuery?.account_id
        await syncPositions(accountId)
      },
    },
  ],
})
</script>

<style scoped></style>
