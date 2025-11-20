"""数据库连接和会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 创建数据库引擎
# PostgreSQL连接参数
connect_args = {}
if "postgresql" in settings.DATABASE_URL:
    connect_args = {
        "connect_timeout": 10,
        "client_encoding": "utf8",  # 确保使用UTF-8编码
    }
elif "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

# 确保数据库URL包含编码参数（PostgreSQL）
database_url = settings.DATABASE_URL
if "postgresql" in database_url and "?" not in database_url:
    database_url = f"{database_url}?client_encoding=utf8"
elif "postgresql" in database_url and "client_encoding" not in database_url:
    database_url = f"{database_url}&client_encoding=utf8"

engine = create_engine(
    database_url,
    connect_args=connect_args,
    echo=False,  # 关闭SQL日志输出
    pool_pre_ping=True,  # 连接前ping，自动重连
    pool_size=5,
    max_overflow=10
    # SQLAlchemy 2.x 默认使用 UTF-8 编码，无需显式指定
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

