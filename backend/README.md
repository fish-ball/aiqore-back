# AIQore 后端（backend）

本目录为 AIQore 项目的 Python 后端根目录。

- 代码目录：`app/`
- 数据库迁移：`alembic/`
- 回测代码：`backtest/`
- 辅助脚本：`scripts/`

在本目录下使用 UV 相关命令，例如：

```bash
uv sync
uv run python run.py
uv run alembic upgrade head
```

更多整体说明见仓库根目录的 `README.md` 与 `docs/` 文档。

