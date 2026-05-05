# AIQore 后端（backend）

Python / FastAPI 根目录：`app/`、迁移 `alembic/`（回测逻辑在 `app/services/backtest` 与 `app/api/backtest`）。

在 `backend/` 下使用 UV，例如：

```bash
uv sync
uv run python run.py
uv run alembic upgrade head
```

日常启动与数据库任务以仓库根目录 `.vscode/tasks.json` 为准；整体说明见 [docs/README.md](../docs/README.md)。
