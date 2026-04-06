<template>
  <ListView ref="listViewRef" v-bind="listViewOptions" />
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ListView from '../../components/ListViewNoRouteSync.vue'
import { api } from '@iottest/vue-core/src/libs/api'
import { formatMoneyValue } from '../../utils/formatter'

const router = useRouter()
const listViewRef = ref()

const accountResource = api('trade/account')

const formatDateValue = (value) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN')
}

const viewPositions = (accountId) => {
  router.push({
    name: 'admin-position-list',
    query: { account_id: String(accountId) },
  })
}

const syncAccount = async (accountId) => {
  try {
    await accountResource.post({ id: accountId, action: 'sync' }, {})
    ElMessage.success('同步成功')
    await listViewRef.value?.reload()
  } catch {
    ElMessage.error('同步失败')
  }
}

const listViewOptions = reactive({
  title: '账户管理',
  model: 'trade/account',
  options: {
    canCreate: true,
    canEdit: true,
    canDelete: true,
    inlineEdit: true,
    actionColumnWidth: 260
  },
  fields: [
    { key: 'id', label: 'ID', width: 80 },
    { key: 'account_id', label: '账户ID' },
    { key: 'name', label: '账户名称' },
    {
      key: 'initial_capital',
      label: '初始资金',
      filter: (value) => formatMoneyValue(value)
    },
    {
      key: 'current_balance',
      label: '当前余额',
      filter: (value) => formatMoneyValue(value)
    },
    {
      key: 'available_balance',
      label: '可用余额',
      filter: (value) => formatMoneyValue(value)
    },
    {
      key: 'created_at',
      label: '创建时间',
      minWidth: 180,
      filter: (value) => formatDateValue(value)
    }
  ],
  actions: [
    {
      label: '同步',
      buttonType: 'primary',
      action: async (item) => syncAccount(item?.id)
    },
    {
      label: '持仓',
      buttonType: 'info',
      action: (item) => viewPositions(item?.id)
    }
  ],
  editViewOptions: {
    model: 'trade/account',
    title: '新建账户',
    fields: [
      {
        key: 'account_id',
        label: '账户ID',
        type: 'text',
        required: true,
        placeholder: '请输入账户ID'
      },
      {
        key: 'name',
        label: '账户名称',
        type: 'text',
        placeholder: '请输入账户名称'
      },
      {
        key: 'initial_capital',
        label: '初始资金',
        type: 'number',
        required: true,
        default: 0
      }
    ]
  }
})
</script>

<style scoped></style>
