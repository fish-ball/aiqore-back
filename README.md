# 个人投资系统（AIQore）

基于国金 QMT 驱动的个人投资管理系统，支持行情浏览、交易管理、持仓跟踪和投资收益分析。

## 快速开始

1. **安装 UV 并同步依赖**：`uv sync`
2. **配置环境**：复制 `.env.example` 为 `.env` 并填写
3. **初始化数据库**：`uv run python init_db.py` 或 `uv run alembic upgrade head`
4. **启动后端**：`uv run python run.py` 或 `start_server.bat`（默认 http://localhost:8000）
5. **启动前端**：`cd frontend && npm install && npm run dev`（默认 http://localhost:3000）
6. **异步任务（可选）**：先启动 Redis，再 `uv run celery -A app.celery_app worker --loglevel=info --pool=solo` 或 `start_celery_worker.bat`

API 文档：http://localhost:8000/docs 、 http://localhost:8000/redoc

## 项目文档

**完整说明与结构请查看 [docs](./docs/README.md) 目录**，包括：

- [架构与概览](./docs/1-架构与概览.md) - 功能、技术栈、项目结构
- [开发与运行](./docs/2-开发与运行.md) - 环境、UV、启动方式
- [数据库与迁移](./docs/3-数据库与迁移.md) - 数据库配置、Alembic、编码问题
- [前端](./docs/4-前端.md) - 前端技术栈与启动
- [API](./docs/5-API.md) - 接口列表与示例
- [QMT 集成](./docs/6-QMT集成.md) - 国金 QMT 接入说明
- [异步任务](./docs/7-异步任务.md) - Celery + Redis 配置与使用

代码改动时请按 [docs/README.md#文档维护说明](./docs/README.md#文档维护说明) 同步更新上述文档。
