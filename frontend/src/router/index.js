import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Accounts from '../views/Accounts.vue'
import Positions from '../views/Positions.vue'
import Trades from '../views/Trades.vue'
import Analysis from '../views/Analysis.vue'
import SecurityList from '../views/SecurityList.vue'
import SecurityDetail from '../views/SecurityDetail.vue'
import Sectors from '../views/Sectors.vue'
import DataSourceConnections from '../views/DataSourceConnections.vue'
import DataSourceDebug from '../views/DataSourceDebug.vue'
import TaskManager from '../views/TaskManager.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/accounts',
    name: 'Accounts',
    component: Accounts
  },
  {
    path: '/positions',
    name: 'Positions',
    component: Positions
  },
  {
    path: '/trades',
    name: 'Trades',
    component: Trades
  },
  {
    path: '/securities',
    name: 'SecurityList',
    component: SecurityList
  },
  {
    path: '/security/:symbol',
    name: 'SecurityDetail',
    component: SecurityDetail
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: Analysis
  },
  {
    path: '/sectors',
    name: 'Sectors',
    component: Sectors
  },
  {
    path: '/data-sources',
    name: 'DataSourceConnections',
    component: DataSourceConnections
  },
  {
    path: '/data-sources/debug/:id',
    name: 'DataSourceDebug',
    component: DataSourceDebug
  },
  {
    path: '/tasks',
    name: 'TaskManager',
    component: TaskManager
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

