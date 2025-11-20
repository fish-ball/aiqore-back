import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Accounts from '../views/Accounts.vue'
import Positions from '../views/Positions.vue'
import Trades from '../views/Trades.vue'
import Analysis from '../views/Analysis.vue'
import SecurityList from '../views/SecurityList.vue'
import SecurityDetail from '../views/SecurityDetail.vue'
import Sectors from '../views/Sectors.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

