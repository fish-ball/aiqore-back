<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">
          <el-icon><TrendCharts /></el-icon>
          AIQore - 个人投资管理系统
        </h1>
        <div class="header-actions">
          <el-button type="primary" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="200px" class="app-sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/accounts">
            <el-icon><Wallet /></el-icon>
            <span>账户管理</span>
          </el-menu-item>
          <el-menu-item index="/positions">
            <el-icon><Box /></el-icon>
            <span>持仓管理</span>
          </el-menu-item>
          <el-menu-item index="/trades">
            <el-icon><Document /></el-icon>
            <span>交易记录</span>
          </el-menu-item>
          <el-menu-item index="/market">
            <el-icon><DataLine /></el-icon>
            <span>行情查询</span>
          </el-menu-item>
          <el-menu-item index="/securities">
            <el-icon><List /></el-icon>
            <span>证券列表</span>
          </el-menu-item>
          <el-menu-item index="/analysis">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据分析</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><Operation /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAccountStore } from './stores/account'

const route = useRoute()
const accountStore = useAccountStore()

const activeMenu = computed(() => route.path)

const refreshData = () => {
  accountStore.fetchAccounts()
  ElMessage.success('数据已刷新')
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 20px;
}

.app-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.app-sidebar {
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.app-main {
  padding: 20px;
  background-color: #f5f7fa;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

