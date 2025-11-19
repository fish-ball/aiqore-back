# AIQore 前端应用

基于 Vue3 + Vite + Element Plus 的个人投资管理系统前端界面。

## 功能特性

- 📊 **仪表盘** - 查看账户概览和最近交易
- 💼 **账户管理** - 创建和管理投资账户
- 📈 **持仓管理** - 查看和同步持仓信息
- 📝 **交易记录** - 记录和查询交易历史
- 📉 **行情查询** - 实时行情和K线图表
- 📊 **数据分析** - 账户分析和盈亏趋势

## 技术栈

- Vue 3.3+ (Composition API)
- Vite 5.0+
- Vue Router 4.2+
- Pinia 2.1+ (状态管理)
- Element Plus 2.4+ (UI组件库)
- ECharts 5.4+ (图表库)
- Axios 1.6+ (HTTP客户端)

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

前端应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口封装
│   │   ├── index.js      # Axios 配置
│   │   ├── trade.js      # 交易相关 API
│   │   ├── market.js     # 行情相关 API
│   │   └── analysis.js   # 分析相关 API
│   ├── stores/           # Pinia 状态管理
│   │   ├── index.js      # Pinia 实例
│   │   └── account.js    # 账户状态
│   ├── views/            # 页面组件
│   │   ├── Dashboard.vue # 仪表盘
│   │   ├── Accounts.vue  # 账户管理
│   │   ├── Positions.vue # 持仓管理
│   │   ├── Trades.vue    # 交易记录
│   │   ├── Market.vue    # 行情查询
│   │   └── Analysis.vue  # 数据分析
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── App.vue           # 根组件
│   ├── main.js           # 入口文件
│   └── style.css         # 全局样式
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
└── package.json          # 项目配置
```

## 配置说明

### API 代理

前端开发服务器已配置代理，将 `/api` 请求转发到后端服务器 `http://localhost:8000`。

如需修改后端地址，请编辑 `vite.config.js` 中的 `server.proxy` 配置。

### 后端服务

确保后端 FastAPI 服务正在运行在 `http://localhost:8000`。

## 使用说明

1. **启动后端服务**
   ```bash
   # 在项目根目录
   python run.py
   # 或
   uvicorn app.main:app --reload
   ```

2. **启动前端服务**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **访问应用**
   打开浏览器访问 `http://localhost:3000`

## 注意事项

- 确保后端服务已启动并配置了 CORS
- 首次使用需要创建账户
- 部分功能需要 QMT 服务支持

