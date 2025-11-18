#!/bin/bash
# 设置PostgreSQL端口映射脚本

echo "检查PostgreSQL容器状态..."
CONTAINER_EXISTS=$(wsl docker ps -a --filter "name=postgres" --format "{{.Names}}")

if [ -n "$CONTAINER_EXISTS" ]; then
    echo "停止并删除现有容器..."
    wsl docker stop postgres 2>/dev/null
    wsl docker rm postgres 2>/dev/null
fi

echo "创建PostgreSQL容器并映射端口 5432..."
wsl docker run -d \
  --name postgres \
  -e POSTGRES_DB=mydb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:latest

echo "等待PostgreSQL启动..."
sleep 5

echo "测试连接..."
wsl docker exec postgres psql -U postgres -d mydb -c "SELECT version();" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL容器已启动，端口已映射到 localhost:5432"
    echo "现在可以从Windows访问数据库了"
else
    echo "✗ PostgreSQL启动失败，请检查日志："
    wsl docker logs postgres
fi

