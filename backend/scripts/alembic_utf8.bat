@echo off
REM Alembic UTF-8 编码修复启动脚本
REM 在运行 Alembic 命令前设置 UTF-8 编码环境变量

REM 设置 Python IO 编码为 UTF-8
set PYTHONIOENCODING=utf-8

REM 设置控制台代码页为 UTF-8（可选，用于显示中文）
chcp 65001 >nul 2>&1

REM 运行 Alembic 命令，传递所有参数
alembic %*

