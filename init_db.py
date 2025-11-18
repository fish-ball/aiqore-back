"""初始化数据库"""
from app.database import engine, Base
from app.models import Account, Trade, Position

def init_db():
    """创建所有数据库表"""
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")

if __name__ == "__main__":
    init_db()

