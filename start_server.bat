@echo off
chcp 65001 >nul
echo ========================================
echo 启动 FastAPI 服务器 (使用 UV)
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

echo 启动服务器...
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 按 Ctrl+C 停止服务器
echo.

uv run python run.py

pause

