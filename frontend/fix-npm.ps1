# 修复 npm 执行策略问题的脚本
# 需要以管理员身份运行 PowerShell

Write-Host "正在设置 PowerShell 执行策略..." -ForegroundColor Yellow

# 设置执行策略为 RemoteSigned（推荐）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

Write-Host "执行策略已设置为 RemoteSigned" -ForegroundColor Green
Write-Host "现在可以运行 npm 命令了！" -ForegroundColor Green
Write-Host ""
Write-Host "请运行以下命令安装依赖：" -ForegroundColor Cyan
Write-Host "  cd frontend" -ForegroundColor Cyan
Write-Host "  npm install" -ForegroundColor Cyan

