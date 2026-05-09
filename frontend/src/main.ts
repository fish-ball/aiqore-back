// 原始清理 css，优先级最低
import 'normalize.css'

// 创建 VueApp 实例
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)
// ;(window as any).app = app // eslint-disable-line

import { createPinia } from 'pinia'

const pinia = createPinia()
app.use(pinia)

// 项目级别的第三方插件，作为基础能力提前引入
import '@imengyu/vue3-context-menu/lib/vue3-context-menu.css'
import ContextMenu from '@imengyu/vue3-context-menu'

app.use(ContextMenu)

// https://www.npmjs.com/package/@guolao/vue-monaco-editor
import { install as VueMonacoEditorPlugin } from '@guolao/vue-monaco-editor'

app.use(VueMonacoEditorPlugin, {
  paths: {
    // vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.43.0/min/vs',
    vs: '/vs',
  },
})

// 引入 VueCore 启动
import VueCore from '@iottest/vue-core/src'
import config from '@/config'

app.use(VueCore, { config })

// 最后才导入项目 css，确保优先级更高
import './assets/styles/main.scss'

import { DataSourceRequiredError } from '@/stores/dataSource'

// 顶栏未选数据源时 requireDataSourceId 会抛错；模板里 @click 往往不 await，避免未处理的 Promise 拒绝刷屏
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason instanceof DataSourceRequiredError) {
    event.preventDefault()
  }
})
