import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Accounts from '../views/Accounts.vue'
import Positions from '../views/Positions.vue'
import Trades from '../views/Trades.vue'
import Market from '../views/Market.vue'
import Analysis from '../views/Analysis.vue'

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
    path: '/market',
    name: 'Market',
    component: Market
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: Analysis
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

