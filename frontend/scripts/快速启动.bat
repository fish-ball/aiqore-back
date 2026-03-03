@echo off
chcp 65001 >nul
echo ========================================
echo AIQore 前端项目 - 快速启动脚本
echo ========================================
echo.

REM 检查 Node.js 是否安装
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] 检查 Node.js 版本...
node -v
npm -v
echo.

echo [2/3] 安装依赖包...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo.

echo [3/3] 启动开发服务器...
echo 前端应用将在 http://localhost:3000 启动
echo 按 Ctrl+C 停止服务器
echo.
call npm run dev

pause

