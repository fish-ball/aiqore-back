# PowerShell脚本：设置PostgreSQL端口映射

Write-Host "检查PostgreSQL容器状态..." -ForegroundColor Cyan

$containerExists = wsl docker ps -a --filter "name=postgres" --format "{{.Names}}"

if ($containerExists) {
    Write-Host "停止并删除现有容器..." -ForegroundColor Yellow
    wsl docker stop postgres 2>$null
    wsl docker rm postgres 2>$null
}

Write-Host "创建PostgreSQL容器并映射端口 5432..." -ForegroundColor Cyan
wsl docker run -d `
  --name postgres `
  -e POSTGRES_DB=mydb `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 5432:5432 `
  postgres:latest

Write-Host "等待PostgreSQL启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "测试连接..." -ForegroundColor Cyan
$result = wsl docker exec postgres psql -U postgres -d mydb -c "SELECT version();" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PostgreSQL容器已启动，端口已映射到 localhost:5432" -ForegroundColor Green
    Write-Host "现在可以从Windows访问数据库了" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL启动失败，请检查日志：" -ForegroundColor Red
    wsl docker logs postgres
}

