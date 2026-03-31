<template>
  <ListView ref="listViewRef" v-bind="listViewOptions" />
</template>

<script setup>
import { reactive, ref } from 'vue'
import ListView from '@iottest/vue-core/src/libs/data-view/components/ListView.vue'
import { api } from '@iottest/vue-core/src/libs/api'
import { formatMoneyValue } from '../../utils/formatter'

const listViewRef = ref()
const accountResource = api('trade/account')
const accountNameMap = ref({})
let accountChoicesPromise = null

const formatDateValue = (value) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN')
}

const loadAccountChoices = async () => {
  if (accountChoicesPromise) return accountChoicesPromise
  accountChoicesPromise = (async () => {
    const resp = await accountResource.get({}, { page: 1, page_size: 200 })
    const rows = Array.isArray(resp?.data?.results) ? resp.data.results : []
    const mapped = {}
    rows.forEach((item) => {
      mapped[String(item.id)] = item.name || item.account_id || String(item.id)
    })
    accountNameMap.value = mapped
    return rows.map((item) => ({
      text: item.name || item.account_id,
      value: String(item.id),
    }))
  })()
  return accountChoicesPromise
}

const listViewOptions = reactive({
  title: '交易记录',
  model: 'trade/trade',
  options: {
    canCreate: true,
    canEdit: true,
    canDelete: true,
    inlineEdit: true,
    actionColumnWidth: 140,
  },
  fields: [
    {
      key: 'account_id',
      label: '账户',
      filter: async (value) => {
        if (!Object.keys(accountNameMap.value).length) {
          await loadAccountChoices()
        }
        return accountNameMap.value[String(value)] || String(value || '--')
      },
      filtering: {
        type: 'select',
        key: 'account_id',
        choices: () => loadAccountChoices(),
      },
    },
    { key: 'symbol', label: '代码' },
    { key: 'symbol_name', label: '名称' },
    { key: 'direction', label: '方向' },
    { key: 'price', label: '价格', filter: (value) => formatMoneyValue(value) },
    { key: 'quantity', label: '数量' },
    { key: 'amount', label: '金额', filter: (value) => formatMoneyValue(value) },
    { key: 'commission', label: '手续费', filter: (value) => formatMoneyValue(value) },
    { key: 'tax', label: '税费', filter: (value) => formatMoneyValue(value) },
    { key: 'trade_time', label: '交易时间', minWidth: 180, filter: (value) => formatDateValue(value) },
    { key: 'remark', label: '备注', minWidth: 160 },
  ],
  editViewOptions: {
    model: 'trade/trade',
    title: '记录交易',
    fields: [
      {
        key: 'account_id',
        label: '账户',
        type: 'select',
        required: true,
        choices: () => loadAccountChoices(),
      },
      {
        key: 'symbol',
        label: '证券代码',
        type: 'text',
        required: true,
        placeholder: '如：000001.SZ',
      },
      {
        key: 'symbol_name',
        label: '证券名称',
        type: 'text',
        placeholder: '请输入证券名称',
      },
      {
        key: 'direction',
        label: '交易方向',
        type: 'select',
        required: true,
        choices: [
          { text: '买入', value: '买入' },
          { text: '卖出', value: '卖出' },
        ],
        default: '买入',
      },
      { key: 'price', label: '价格', type: 'number', required: true, default: 0 },
      { key: 'quantity', label: '数量', type: 'number', required: true, default: 0 },
      {
        key: 'trade_time',
        label: '交易时间',
        type: 'text',
        required: true,
        default: () => new Date().toISOString(),
      },
      { key: 'commission', label: '手续费', type: 'number', default: 0 },
      { key: 'tax', label: '税费', type: 'number', default: 0 },
      { key: 'remark', label: '备注', type: 'text' },
    ],
  },
})
</script>

<style scoped></style>
