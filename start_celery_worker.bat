@echo off
chcp 65001 >nul
echo ========================================
echo 启动 Celery Worker (使用 UV)
echo ========================================
echo.

REM 检查是否安装了uv
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未安装 uv，请先安装: https://github.com/astral-sh/uv
    echo 或使用: pip install uv
    pause
    exit /b 1
)

REM 检查是否已同步依赖
if not exist ".venv" (
    echo [提示] 首次运行，正在同步依赖...
    uv sync
)

echo [1/2] 检查 Redis 连接...
uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, password=None, db=0); r.ping(); print('[OK] Redis 连接成功')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] Redis 连接失败，请确保 Redis 正在运行
    echo 如果 Redis 在 WSL 中，请确保端口已映射或使用 WSL IP
)

echo.
echo [2/2] 启动 Celery Worker...
echo 按 Ctrl+C 停止 Worker
echo.

uv run celery -A app.celery_app worker --loglevel=info --pool=solo

pause

