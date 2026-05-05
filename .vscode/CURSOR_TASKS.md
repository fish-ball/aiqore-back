# Cursor/VSCode 任务配置说明

本项目已配置好基于 UV 的启动脚本，可以直接在 Cursor/VSCode 中使用。

## 使用方法

### 方式一：通过命令面板

1. 按 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (Mac) 打开命令面板
2. 输入 `Tasks: Run Task`
3. 选择以下任务之一：

### 方式二：通过快捷键

- `Ctrl+Shift+B` - 运行默认构建任务（启动 FastAPI 服务器）

### 方式三：通过调试面板

1. 按 `F5` 或点击左侧调试图标
2. 选择调试配置并运行

## 可用任务列表

### 基础任务

#### 1. **UV: 同步依赖**
- 同步项目依赖，创建/更新虚拟环境
- 命令：`uv sync`

#### 2. **UV: 启动 FastAPI 服务器** (默认构建任务)
- 启动 FastAPI 开发服务器
- 服务地址：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 命令：`uv run python run.py`

#### 3. **UV: 启动 Celery Worker**
- 启动 Celery 异步任务处理器
- 命令：`uv run celery -A app.celery_app worker --loglevel=info --pool=solo`

#### 4. **UV: 启动服务器和 Celery Worker**
- 同时启动 FastAPI 服务器和 Celery Worker（并行运行）

### 数据库任务

#### 5. **UV: Alembic 升级数据库**
- 执行数据库迁移
- 命令：`uv run alembic upgrade head`

#### 6. **UV: Alembic 创建迁移**
- 自动生成数据库迁移文件
- 会提示输入迁移消息

### 依赖管理任务

#### 7. **UV: 添加依赖包**
- 添加新的 Python 包到项目
- 会提示输入包名称
- 命令：`uv add <package>`

#### 8. **UV: 移除依赖包**
- 从项目中移除 Python 包
- 会提示输入包名称
- 命令：`uv remove <package>`

#### 9. **UV: 更新所有依赖**
- 更新所有依赖到最新版本
- 命令：`uv sync --upgrade`

### 开发任务

#### 10. **UV: 运行 Python 脚本**
- 使用 UV 运行当前打开的 Python 文件
- 命令：`uv run python <file>`

### 前端任务

#### 11. **前端: 安装依赖**
- 安装前端项目依赖
- 命令：`npm install` (在 frontend 目录)

#### 12. **前端: 启动开发服务器**
- 启动 Vite 开发服务器
- 前端地址：http://localhost:3000 (或 Vite 配置的端口)
- 命令：`npm run dev` (在 frontend 目录)

#### 13. **前端: 构建生产版本**
- 构建前端生产版本
- 输出目录：`frontend/dist`
- 命令：`npm run build` (在 frontend 目录)

#### 14. **前端: 预览构建结果**
- 预览构建后的生产版本
- 命令：`npm run preview` (在 frontend 目录)

### 组合任务

#### 15. **启动完整开发环境**
- 同时启动 FastAPI 服务器和前端开发服务器
- 并行运行，适合完整开发环境

#### 16. **启动完整环境（含 Celery）**
- 同时启动 FastAPI 服务器、Celery Worker 和前端开发服务器
- 并行运行，完整的开发环境

## 调试配置

### 1. **Python: FastAPI (UV)**
- 调试 FastAPI 应用
- 支持热重载
- 断点调试

### 2. **Python: 当前文件 (UV)**
- 调试当前打开的 Python 文件
- 使用项目虚拟环境

### 3. **Python: Celery Worker (UV)**
- 调试 Celery Worker
- 支持断点调试异步任务

### 4. **前端: 启动开发服务器**
- 启动前端开发服务器
- 自动打开浏览器
- 支持热重载

## 配置说明

### tasks.json
包含所有可运行的任务定义，支持：
- 并行执行多个任务
- 输入提示（包名称、迁移消息等）
- 后台运行（服务器、Worker）
- 专用终端面板

### launch.json
包含调试配置，支持：
- FastAPI 应用调试
- Celery Worker 调试
- 当前文件调试
- 断点调试

### settings.json
已配置：
- Python 解释器路径（指向 `.venv`）
- 终端环境变量
- 文件关联（pyproject.toml, uv.lock）

## 快速开始

1. **首次使用**：
   - 运行任务：`UV: 同步依赖`
   - 运行任务：`UV: Alembic 升级数据库`

2. **日常开发**：
   - 按 `Ctrl+Shift+B` 启动后端服务器
   - 运行任务：`前端: 启动开发服务器` 启动前端
   - 或运行任务：`启动完整开发环境` 同时启动前后端
   - 或运行任务：`启动完整环境（含 Celery）` 启动所有服务

3. **调试**：
   - 按 `F5` 选择调试配置
   - 设置断点进行调试

## 注意事项

1. **后端**：
   - 确保已安装 UV：`pip install uv`
   - 首次运行会自动创建虚拟环境
   - 服务器和 Worker 任务会在后台运行，可在终端面板查看输出

2. **前端**：
   - 确保已安装 Node.js 和 npm
   - 首次运行需要先执行 `前端: 安装依赖`
   - 前端开发服务器默认运行在 http://localhost:3000

3. **通用**：
   - 使用 `Ctrl+C` 停止运行中的任务
   - 组合任务会并行启动多个服务，每个服务在独立的终端面板中运行

