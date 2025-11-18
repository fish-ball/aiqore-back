"""测试数据库连接"""
import sys
import os

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

try:
    from app.config import settings
    from app.database import engine
    from sqlalchemy import text
    
    print("=" * 50)
    print("数据库配置信息")
    print("=" * 50)
    print(f"数据库URL: {settings.DATABASE_URL}")
    print(f"主机: {settings.DB_HOST}")
    print(f"端口: {settings.DB_PORT}")
    print(f"数据库: {settings.DB_NAME}")
    print(f"用户: {settings.DB_USER}")
    print("=" * 50)
    
    print("\n正在测试数据库连接...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print("[OK] 连接成功！")
        print(f"PostgreSQL版本: {version}")
        print("\n数据库连接正常，可以开始使用！")
        
except ImportError as e:
    print(f"[ERROR] 导入错误: {e}")
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] 连接失败: {e}")
    print("\n请检查:")
    print("1. PostgreSQL容器是否运行: wsl docker ps | findstr postgres")
    print("2. WSL IP地址是否正确: wsl hostname -I")
    print("3. 端口是否可访问: Test-NetConnection -ComputerName 172.30.37.138 -Port 5432")
    sys.exit(1)

