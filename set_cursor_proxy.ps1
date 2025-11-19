# Cursor 代理环境变量设置脚本
# 使用方法：在 PowerShell 中运行此脚本，然后从该 PowerShell 窗口启动 Cursor

Write-Host "设置 Cursor 代理环境变量..." -ForegroundColor Cyan

# 设置代理环境变量
$env:HTTP_PROXY = "http://127.0.0.1:1080"
$env:HTTPS_PROXY = "http://127.0.0.1:1080"
$env:NO_PROXY = "localhost,127.0.0.1,*.local"

Write-Host "代理已设置:" -ForegroundColor Green
Write-Host "  HTTP_PROXY = $env:HTTP_PROXY"
Write-Host "  HTTPS_PROXY = $env:HTTPS_PROXY"
Write-Host "  NO_PROXY = $env:NO_PROXY"
Write-Host ""
Write-Host "提示: 请从当前 PowerShell 窗口启动 Cursor 以应用代理设置" -ForegroundColor Yellow
Write-Host "命令: cursor ." -ForegroundColor Yellow

