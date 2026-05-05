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
    redirect: '/instruments/stocks',
    meta: {
      title: '管理后台',
      icon: 'monitor',
      order: 0,
    },
    children: [
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
        path: 'trade',
        name: 'admin-trade-list',
        component: () => import('./admin/TradeList.vue'),
        meta: {
          title: '交易记录',
          icon: 'document',
          order: 4,
        },
      },
      {
        path: 'exchanges',
        name: 'admin-exchanges',
        component: () => import('./admin/ExchangeList.vue'),
        meta: {
          title: '交易所',
          icon: 'office-building',
          order: 5,
        },
      },
      {
        path: 'sectors',
        name: 'admin-sectors',
        component: () => import('./admin/SectorList.vue'),
        meta: {
          title: '板块',
          icon: 'grid',
          order: 6,
        },
      },
      {
        path: 'instruments/stocks',
        name: 'admin-instruments-stocks',
        component: () => import('./admin/InstrumentStockList.vue'),
        meta: {
          title: '股票',
          icon: 'coin',
          order: 65,
        },
      },
      {
        path: 'instruments/etf-options',
        name: 'admin-instruments-etf-options',
        component: () => import('./admin/ContractInstrumentStub.vue'),
        meta: {
          title: 'ETF期权',
          icon: 'coin',
          order: 66,
          stubDescription: 'ETF期权列表尚未接入，敬请期待',
        },
      },
      {
        path: 'instruments/futures',
        name: 'admin-instruments-futures',
        component: () => import('./admin/ContractInstrumentStub.vue'),
        meta: {
          title: '期货',
          icon: 'coin',
          order: 67,
          stubDescription: '期货列表尚未接入，敬请期待',
        },
      },
      {
        path: 'instruments/future-options',
        name: 'admin-instruments-future-options',
        component: () => import('./admin/ContractInstrumentStub.vue'),
        meta: {
          title: '期货期权',
          icon: 'coin',
          order: 68,
          stubDescription: '期货期权列表尚未接入，敬请期待',
        },
      },
      {
        path: 'instruments',
        redirect: { name: 'admin-instruments-stocks' },
      },
      {
        path: 'instruments_old',
        name: 'admin-instruments-old',
        component: () => import('./admin/SecurityList.vue'),
        meta: {
          title: '标的列表',
          icon: 'list',
          order: 7,
        },
      },
      {
        path: 'instrument/:symbol',
        name: 'admin-instrument-detail',
        component: () => import('./admin/SecurityDetail.vue'),
        props: true,
        meta: {
          title: '标的详情',
          icon: 'document',
          order: 50,
        },
      },
      {
        path: 'data-sources',
        name: 'admin-data-sources',
        component: () => import('./admin/DataSourceConnectionList.vue'),
        meta: {
          title: '数据源连接',
          icon: 'connection',
          order: 8,
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
        component: () => import('./admin/TaskList.vue'),
        meta: {
          title: '任务管理',
          icon: 'timer',
          order: 9,
        },
      },
      {
        path: 'strategies',
        name: 'admin-strategies',
        component: () => import('./admin/StrategyList.vue'),
        meta: {
          title: '策略管理',
          icon: 'operation',
          order: 10,
        },
      },
      {
        path: 'backtest-records',
        name: 'admin-backtest-records',
        component: () => import('./admin/BacktestRecordList.vue'),
        meta: {
          title: '回测记录',
          icon: 'histogram',
          order: 11,
        },
      },
    ],
  },
]

export default routes
