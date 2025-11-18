# 数据库配置说明

## WSL Docker PostgreSQL 配置

### 当前PostgreSQL容器信息
- 容器名：`postgres`
- 数据库名：`mydb`
- 用户名：`postgres`
- 密码：`postgres`
- 端口：5432（容器内部）

### ✅ 当前配置：使用WSL IP直接连接

**已配置为使用WSL IP地址直接连接，无需端口映射！**

当前配置（`.env`文件）：
```
DB_HOST=172.30.37.138
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=mydb
```

**优势：**
- ✅ 无需端口映射
- ✅ 直接使用WSL网络IP
- ✅ PostgreSQL已配置为允许外部连接

**验证连接：**
```powershell
# 测试端口连通性
Test-NetConnection -ComputerName 172.30.37.138 -Port 5432

# 测试数据库连接（需要安装psql或使用Python）
python -c "from app.database import engine; print(engine.connect())"
```

### 其他连接方式（可选）

#### 方式1：使用localhost（需要端口映射）

如果希望使用localhost，需要映射端口：

```bash
wsl docker stop postgres
wsl docker rm postgres
wsl docker run -d --name postgres -e POSTGRES_DB=mydb -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:latest
```

然后在 `.env` 中设置：
```
DB_HOST=localhost
```

#### 方式2：从WSL内部访问（使用容器名）

如果应用在WSL内运行，可以直接使用容器名：

在 `.env` 文件中设置：
```
DB_HOST=postgres
DB_PORT=5432
```

### 验证连接

#### 方法1：使用测试脚本（推荐）

```bash
# 先安装依赖
pip install -r requirements.txt

# 运行测试脚本
python test_db_connection.py
```

#### 方法2：从WSL测试

```bash
wsl docker exec -it postgres psql -U postgres -d mydb -c "SELECT version();"
```

#### 方法3：测试端口连通性

```powershell
Test-NetConnection -ComputerName 172.30.37.138 -Port 5432
```

### 初始化数据库

配置完成后，初始化数据库表：

```bash
# 方法1：使用初始化脚本
python init_db.py

# 方法2：使用Alembic（推荐，支持版本管理）
alembic upgrade head
```

### 注意事项

⚠️ **WSL IP地址可能会变化**

如果WSL重启，IP地址可能会改变。如果连接失败，请：

1. 检查当前WSL IP：
   ```bash
   wsl hostname -I
   ```

2. 更新 `.env` 文件中的 `DB_HOST` 为新的IP地址

3. 或者考虑使用端口映射方式（使用localhost）

