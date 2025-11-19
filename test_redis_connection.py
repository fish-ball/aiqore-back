"""测试Redis连接"""
import sys
from app.config import settings

def test_redis():
    """测试Redis连接"""
    try:
        import redis
        print(f"测试Redis连接...")
        print(f"地址: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        print(f"密码: {'已设置' if settings.REDIS_PASSWORD else '未设置'}")
        
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # 测试连接
        r.ping()
        print("[OK] Redis连接成功！")
        
        # 测试写入和读取
        r.set("test_key", "test_value", ex=10)
        value = r.get("test_key")
        print(f"[OK] 测试读写成功: {value}")
        
        return True
    except ImportError:
        print("[ERROR] 未安装redis库，请运行: pip install redis")
        return False
    except Exception as e:
        print(f"[ERROR] Redis连接失败: {e}")
        print("\n请检查:")
        print("1. Redis是否正在运行")
        print("2. Redis配置是否正确")
        print("3. 如果Redis在WSL，请确保端口已映射或使用WSL IP")
        return False

if __name__ == "__main__":
    success = test_redis()
    sys.exit(0 if success else 1)

