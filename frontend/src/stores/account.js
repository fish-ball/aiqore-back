import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tradeApi } from '../api/trade'

export const useAccountStore = defineStore('account', () => {
  const accounts = ref([])
  const currentAccount = ref(null)
  const loading = ref(false)

  const fetchAccounts = async () => {
    loading.value = true
    try {
      accounts.value = await tradeApi.getAccounts()
    } catch (error) {
      console.error('获取账户列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  const fetchAccount = async (accountId) => {
    loading.value = true
    try {
      currentAccount.value = await tradeApi.getAccount(accountId)
    } catch (error) {
      console.error('获取账户详情失败:', error)
    } finally {
      loading.value = false
    }
  }

  const createAccount = async (accountData) => {
    loading.value = true
    try {
      const account = await tradeApi.createAccount(accountData)
      await fetchAccounts()
      return account
    } catch (error) {
      console.error('创建账户失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    accounts,
    currentAccount,
    loading,
    fetchAccounts,
    fetchAccount,
    createAccount
  }
})

