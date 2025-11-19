@echo off
chcp 65001 >nul
echo ========================================
echo 启动 Celery Worker
echo ========================================
echo.

REM 检查是否安装了celery
python -c "import celery" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未安装 celery，请先运行: pip install celery redis
    pause
    exit /b 1
)

echo [1/2] 检查 Redis 连接...
python -c "import redis; r = redis.Redis(host='localhost', port=6379, password='redis', db=0); r.ping(); print('[OK] Redis 连接成功')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] Redis 连接失败，请确保 Redis 正在运行
    echo 如果 Redis 在 WSL 中，请确保端口已映射或使用 WSL IP
)

echo.
echo [2/2] 启动 Celery Worker...
echo 按 Ctrl+C 停止 Worker
echo.

celery -A app.celery_app worker --loglevel=info --pool=solo

pause

