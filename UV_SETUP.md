# UV 包管理配置说明

本项目已迁移到基于 [uv](https://github.com/astral-sh/uv) 的包管理架构。

## 什么是 UV？

UV 是一个极快的 Python 包管理器和项目管理工具，由 Astral 开发（Ruff 的同一团队）。它比 pip 快 10-100 倍。

## 安装 UV

### Windows

使用 PowerShell：
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或使用 pip：
```bash
pip install uv
```

### Linux/macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 项目设置

### 1. 同步依赖

首次设置或更新依赖：
```bash
uv sync
```

这会：
- 创建虚拟环境（如果不存在）
- 安装所有依赖
- 生成 `uv.lock` 锁定文件

### 2. 激活虚拟环境

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

或者直接使用 uv 运行命令（无需激活）：
```bash
uv run python app/main.py
```

### 3. 添加新依赖

```bash
uv add package-name
```

例如：
```bash
uv add requests
```

### 4. 移除依赖

```bash
uv remove package-name
```

### 5. 更新依赖

```bash
uv sync --upgrade
```

### 6. 运行项目

```bash
# 使用 uv 运行（推荐，自动使用虚拟环境）
uv run python run.py

# 或激活虚拟环境后运行
.venv\Scripts\activate  # Windows
python run.py
```

### 7. 运行 Celery Worker

```bash
uv run celery -A app.celery_app worker --loglevel=info --pool=solo
```

## 项目结构

- `pyproject.toml`: 项目配置和依赖定义
- `.python-version`: Python 版本要求
- `uv.lock`: 依赖锁定文件（自动生成，应提交到版本控制）

## 从 requirements.txt 迁移

项目已从 `requirements.txt` 迁移到 `pyproject.toml`。`requirements.txt` 已删除，所有依赖现在由 `pyproject.toml` 管理。

## 优势

1. **速度**: 比 pip 快 10-100 倍
2. **统一配置**: 使用标准的 `pyproject.toml`
3. **依赖锁定**: 自动生成 `uv.lock` 确保可重现的构建
4. **更好的依赖解析**: 更智能的依赖冲突解决

## 常见问题

### Q: 如何查看已安装的包？
```bash
uv pip list
```

### Q: 如何导出为 requirements.txt（如果需要）？
```bash
uv pip compile pyproject.toml -o requirements.txt
```

### Q: 如何更新所有依赖到最新版本？
```bash
uv sync --upgrade
```

### Q: 如何指定 Python 版本？
编辑 `.python-version` 文件，或使用：
```bash
uv python install 3.11
```

