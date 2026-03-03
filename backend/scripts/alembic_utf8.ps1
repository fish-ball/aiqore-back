# Alembic UTF-8 编码修复启动脚本 (PowerShell)
# 在运行 Alembic 命令前设置 UTF-8 编码环境变量

# 设置 Python IO 编码为 UTF-8
$env:PYTHONIOENCODING = "utf-8"

# 设置控制台输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 运行 Alembic 命令，传递所有参数
& alembic $args

