"""初始化 celery-results 数据库表"""
import sys
from app.database import engine
from app.config import settings
from sqlalchemy import inspect as sqlalchemy_inspect, text

def init_celery_results():
    """初始化 celery-results 数据库表"""
    try:
        # 检查表是否已存在
        inspector = sqlalchemy_inspect(engine)
        existing_tables = inspector.get_table_names()
        
        table_name = 'celery_taskmeta'  # celery-results 使用的表名
        
        if table_name in existing_tables:
            print(f"[OK] 表 '{table_name}' 已存在，无需初始化")
            # 检查表结构
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            print(f"  表列: {', '.join(columns)}")
            return
        
        # 创建表（使用 celery-results 的标准表结构）
        print(f"正在创建表 '{table_name}'...")
        
        # celery-results 的标准表结构
        create_table_sql = """
        CREATE TABLE celery_taskmeta (
            id INTEGER NOT NULL PRIMARY KEY,
            task_id VARCHAR(255) NOT NULL UNIQUE,
            status VARCHAR(50) NOT NULL,
            result TEXT,
            traceback TEXT,
            date_done TIMESTAMP,
            task_name VARCHAR(255),
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # 对于 PostgreSQL，使用 SERIAL 而不是 INTEGER
        if 'postgresql' in settings.DATABASE_URL:
            create_table_sql = """
            CREATE TABLE celery_taskmeta (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL UNIQUE,
                status VARCHAR(50) NOT NULL,
                result TEXT,
                traceback TEXT,
                date_done TIMESTAMP,
                task_name VARCHAR(255),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        print(f"[OK] 表 '{table_name}' 创建成功！")
        
        # 创建索引以提高查询性能
        print("正在创建索引...")
        try:
            with engine.connect() as conn:
                # 为 task_id 创建索引（已通过 UNIQUE 约束自动创建）
                # 为 task_name 创建索引
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_celery_taskmeta_task_name ON {table_name}(task_name)"))
                # 为 date_done 创建索引
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_celery_taskmeta_date_done ON {table_name}(date_done)"))
                # 为 status 创建索引
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_celery_taskmeta_status ON {table_name}(status)"))
                conn.commit()
            print("[OK] 索引创建成功！")
        except Exception as e:
            print(f"[WARN] 创建索引时出现警告: {e}")
        
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 50)
    print("初始化 celery-results 数据库表")
    print("=" * 50)
    db_info = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
    print(f"数据库: {db_info}")
    print()
    init_celery_results()
    print()
    print("初始化完成！")

