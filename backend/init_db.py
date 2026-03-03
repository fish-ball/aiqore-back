"""初始化数据库"""
from app.database import engine, Base
from app.models import Account, Trade, Position

def init_db():
    """创建所有数据库表"""
    # 创建业务表
    Base.metadata.create_all(bind=engine)
    print("业务表初始化完成！")
    print()
    print("数据库初始化完成！")
    print("注意: Celery任务结果存储在Redis中，无需数据库表")

if __name__ == "__main__":
    init_db()

