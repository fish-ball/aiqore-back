import type { RouteRecordRaw } from 'vue-router'

/**
 * 管理后台路由：与 PageAdminBase 侧栏路径一致，子路由使用相对 path，便于嵌套。
 * 懒加载组件使用相对路径（相对本文件 ./admin/...），与目录结构绑定更清晰。
 * meta.icon 为 Element Plus Icons 组件名的 kebab 形式（与侧栏展示对应）。
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'admin',
    component: () => import('./admin/PageAdminBase.vue'),
    redirect: '/dashboard',
    meta: {
      title: '管理后台',
      icon: 'monitor',
      order: 0,
    },
    children: [
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('./admin/Dashboard.vue'),
        meta: {
          title: '仪表盘',
          icon: 'odometer',
          order: 1,
        },
      },
      {
        path: 'account',
        name: 'admin-account-list',
        component: () => import('./admin/AccountList.vue'),
        meta: {
          title: '账户管理',
          icon: 'wallet',
          order: 2,
        },
      },
      {
        path: 'position',
        name: 'admin-position-list',
        component: () => import('./admin/PositionList.vue'),
        meta: {
          title: '持仓管理',
          icon: 'box',
          order: 3,
        },
      },
      {
        path: 'trades',
        name: 'admin-trades',
        component: () => import('./admin/Trades.vue'),
        meta: {
          title: '交易记录',
          icon: 'document',
          order: 4,
        },
      },
      {
        path: 'securities',
        name: 'admin-securities',
        component: () => import('./admin/SecurityList.vue'),
        meta: {
          title: '证券列表',
          icon: 'list',
          order: 5,
        },
      },
      {
        path: 'security/:symbol',
        name: 'admin-security-detail',
        component: () => import('./admin/SecurityDetail.vue'),
        props: true,
        meta: {
          title: '证券详情',
          icon: 'document',
          order: 50,
        },
      },
      {
        path: 'sectors',
        name: 'admin-sectors',
        component: () => import('./admin/Sectors.vue'),
        meta: {
          title: '板块管理',
          icon: 'list',
          order: 6,
        },
      },
      {
        path: 'data-sources',
        name: 'admin-data-sources',
        component: () => import('./admin/DataSourceConnections.vue'),
        meta: {
          title: '数据源连接',
          icon: 'connection',
          order: 7,
        },
      },
      {
        path: 'data-sources/debug/:id',
        name: 'admin-data-source-debug',
        component: () => import('./admin/DataSourceDebug.vue'),
        meta: {
          title: '数据源调试',
          icon: 'setting',
          order: 51,
        },
      },
      {
        path: 'tasks',
        name: 'admin-tasks',
        component: () => import('./admin/TaskManager.vue'),
        meta: {
          title: '任务管理',
          icon: 'timer',
          order: 8,
        },
      },
      {
        path: 'strategies',
        name: 'admin-strategies',
        component: () => import('./admin/StrategyManagement.vue'),
        meta: {
          title: '策略管理',
          icon: 'operation',
          order: 9,
        },
      },
      {
        path: 'backtest-records',
        name: 'admin-backtest-records',
        component: () => import('./admin/BacktestRecords.vue'),
        meta: {
          title: '回测记录',
          icon: 'histogram',
          order: 10,
        },
      },
      {
        path: 'analysis',
        name: 'admin-analysis',
        component: () => import('./admin/Analysis.vue'),
        meta: {
          title: '数据分析',
          icon: 'data-analysis',
          order: 11,
        },
      },
    ],
  },
]

export default routes
