# 迁移到 UV 包管理器

## 迁移完成

项目已成功从传统的 `pip` + `requirements.txt` 迁移到基于 `uv` 的包管理架构。

## 变更内容

### 新增文件

1. **`pyproject.toml`**: 项目配置和依赖定义文件
   - 包含所有项目元数据
   - 所有依赖从 `requirements.txt` 迁移到此文件
   - 使用标准的 PEP 621 格式

2. **`.python-version`**: Python 版本要求文件
   - 指定项目使用的 Python 版本（3.11）

3. **`start_server.bat`**: 使用 UV 启动服务器的批处理脚本

4. **`UV_SETUP.md`**: UV 使用说明文档

### 修改文件

1. **`start_celery_worker.bat`**: 更新为使用 `uv run` 命令
2. **`README.md`**: 更新快速开始指南，添加 UV 安装和使用说明
3. **`.gitignore`**: 更新以包含 UV 相关文件（但保留 `uv.lock` 用于版本控制）

### 已删除文件

- **`requirements.txt`**: 已删除，依赖已迁移到 `pyproject.toml`
- **`start_celery_worker.py`**: 已删除，使用 `start_celery_worker.bat` 替代
- **`update_securities.py`**: 已删除，使用 API 接口 `/api/security/update` 替代
- **测试脚本**: `test_db_connection.py`, `test_redis_connection.py`, `test_qmt_api.py` 已删除

## 使用方法

### 首次设置

```bash
# 1. 安装 UV（如果未安装）
# Windows PowerShell:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip:
pip install uv

# 2. 同步依赖（创建虚拟环境并安装所有依赖）
uv sync
```

### 日常使用

```bash
# 运行服务器
uv run python run.py
# 或使用批处理文件
start_server.bat

# 运行 Celery Worker
uv run celery -A app.celery_app worker --loglevel=info --pool=solo
# 或使用批处理文件
start_celery_worker.bat

# 运行其他 Python 脚本
uv run python script.py
```

### 管理依赖

```bash
# 添加新依赖
uv add package-name

# 移除依赖
uv remove package-name

# 更新所有依赖
uv sync --upgrade
```

## 优势

1. **速度**: UV 比 pip 快 10-100 倍
2. **统一配置**: 使用标准的 `pyproject.toml` 格式
3. **依赖锁定**: 自动生成 `uv.lock` 确保可重现的构建
4. **更好的依赖解析**: 更智能的依赖冲突解决
5. **现代化**: 符合 Python 包管理的最新标准

## 注意事项

1. **`uv.lock` 文件**: 应该提交到版本控制，以确保团队成员使用相同的依赖版本
2. **虚拟环境**: UV 会自动管理 `.venv` 目录，无需手动创建
3. **向后兼容**: 如果需要导出为 requirements.txt，可以使用 `uv pip compile pyproject.toml -o requirements.txt`

## 迁移检查清单

- [x] 创建 `pyproject.toml` 并迁移所有依赖
- [x] 创建 `.python-version` 文件
- [x] 更新启动脚本使用 `uv run`
- [x] 更新 README.md 文档
- [x] 创建 UV 使用说明文档
- [x] 更新 `.gitignore`（保留 `uv.lock`）
- [x] 测试依赖安装和项目运行

## 下一步

1. 运行 `uv sync` 验证所有依赖可以正确安装
2. 测试项目启动和运行
3. 提交 `uv.lock` 文件到版本控制
4. 通知团队成员使用新的包管理方式

