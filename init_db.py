"""初始化数据库"""
from app.database import engine, Base
from app.models import Account, Trade, Position

def init_db():
    """创建所有数据库表"""
    # 创建业务表
    Base.metadata.create_all(bind=engine)
    print("业务表初始化完成！")
    
    # 初始化 celery-results 表
    try:
        from init_celery_results import init_celery_results
        print()
        init_celery_results()
    except Exception as e:
        print(f"警告: celery-results 表初始化失败: {e}")
    
    print()
    print("数据库初始化完成！")

if __name__ == "__main__":
    init_db()

