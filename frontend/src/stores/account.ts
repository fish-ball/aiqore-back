import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tradeApi } from '../api/trade'

interface Account {
  id?: number | string
  [key: string]: unknown
}

export const useAccountStore = defineStore('account', () => {
  const accounts = ref<Account[]>([])
  const currentAccount = ref<Account | null>(null)
  const loading = ref(false)

  const fetchAccounts = async () => {
    loading.value = true
    try {
      accounts.value = (await tradeApi.getAccounts()) as unknown as Account[]
    } catch (error) {
      console.error('获取账户列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  const fetchAccount = async (accountId: number | string) => {
    loading.value = true
    try {
      currentAccount.value = (await tradeApi.getAccount(accountId)) as unknown as Account
    } catch (error) {
      console.error('获取账户详情失败:', error)
    } finally {
      loading.value = false
    }
  }

  const createAccount = async (accountData: Record<string, unknown>) => {
    loading.value = true
    try {
      const account = (await tradeApi.createAccount(accountData)) as unknown as Account
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

