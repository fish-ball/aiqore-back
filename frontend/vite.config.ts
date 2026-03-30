import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    port: Number(process.env.PORT || 8080),
    open: false, // 禁用自动打开浏览器
    fs: {
      strict: false
    },
    strictPort: true,
    watch: {
      // 监听软连接指向的实际路径，确保代码变化能实时生效
      followSymlinks: true,
    },
    proxy: {
      '/api': {
        target: process.env.PROXY_API_ROOT || 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // 将请求中的原始 Host 头设置到后端请求中
            if (req.headers['host']) {
              proxyReq.setHeader('Host', req.headers['host'])
            }
          })
        },
      },
      '/docs': {
        target: process.env.PROXY_API_ROOT || 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // 将请求中的原始 Host 头设置到后端请求中
            if (req.headers['host']) {
              proxyReq.setHeader('Host', req.headers['host'])
            }
          })
        },
      },
    },
  },
  plugins: [
    vue(),
    vueJsx(),
    vueDevTools(),
    ...(process.env.VITE_DEV_SSL === '1' ? [basicSsl()] : []),
  ],
  css: {
    preprocessorOptions: {
      scss: { api: 'modern-compiler' },
    },
  },
  build: {
    sourcemap: true,
  },
  optimizeDeps: {
    // 强制重新构建，确保软连接的代码变化能实时生效（开发时使用）
    // Vite 会自动发现并预构建 CommonJS 模块，无需显式声明
    force: true,
    // highlight.js 为 CommonJS，需预构建以正确转换为 ESM（@iottest/vue-core 的 ContentRenderer 依赖）
    include: ['highlight.js'],
  },
  resolve: {
    alias: {
      '@/types': fileURLToPath(new URL('./src/types', import.meta.url)),
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // 确保核心依赖从项目的 node_modules 解析，避免版本冲突
    // npm 的依赖解析机制已经能处理 peerDependencies，这里只需要处理核心框架依赖
    dedupe: ['vue', 'vue-router', 'pinia'],
    // 不保留软连接，让 Vite 跟随软连接到实际路径
    // 这样文件监听和 HMR 才能正常工作
    preserveSymlinks: false,
    // 优先使用 ES 模块版本，确保 CommonJS 模块能正确转换
    conditions: ['import', 'module', 'browser', 'default'],
  },
})
