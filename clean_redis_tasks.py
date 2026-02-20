"""清理 Redis 中的旧 Celery 任务记录"""
import redis
from app.config import settings
import json

def clean_old_tasks():
    """清理 Redis 中的旧任务记录"""
    print("=" * 60)
    print("清理 Redis 中的旧 Celery 任务记录")
    print("=" * 60)
    
    # 连接 Redis
    r = redis.from_url(settings.REDIS_URL, decode_responses=False)
    
    try:
        # 测试连接
        r.ping()
        print("[OK] Redis 连接成功")
    except Exception as e:
        print(f"[ERROR] Redis 连接失败: {e}")
        return
    
    # Celery 任务结果存储在 Redis 中，key 格式为: celery-task-meta-{task_id}
    # 查找所有任务记录
    pattern = "celery-task-meta-*"
    keys = list(r.keys(pattern))
    
    print(f"\n找到 {len(keys)} 个任务记录")
    
    if not keys:
        print("没有需要清理的任务记录")
        return
    
    # 清理所有任务记录
    deleted_count = 0
    error_count = 0
    
    for key in keys:
        try:
            # 尝试读取任务记录
            value = r.get(key)
            if value:
                try:
                    # 尝试解析 JSON
                    data = json.loads(value)
                    # 检查是否是格式不正确的记录
                    if isinstance(data, dict) and 'result' in data:
                        result = data.get('result')
                        # 如果是异常信息，检查格式
                        if isinstance(result, dict) and 'error' in result:
                            if 'exc_type' not in result:
                                # 格式不正确的记录，删除
                                r.delete(key)
                                deleted_count += 1
                                print(f"[DELETED] {key.decode() if isinstance(key, bytes) else key}")
                except (json.JSONDecodeError, TypeError):
                    # 无法解析的记录，删除
                    r.delete(key)
                    deleted_count += 1
                    print(f"[DELETED] {key.decode() if isinstance(key, bytes) else key} (无法解析)")
        except Exception as e:
            error_count += 1
            print(f"[ERROR] 处理 {key} 时出错: {e}")
    
    print(f"\n清理完成:")
    print(f"  - 删除记录数: {deleted_count}")
    print(f"  - 错误数: {error_count}")
    print(f"  - 剩余记录数: {len(keys) - deleted_count}")
    
    # 如果需要清理所有任务记录，可以取消下面的注释
    # print("\n清理所有剩余任务记录...")
    # remaining_keys = list(r.keys(pattern))
    # for key in remaining_keys:
    #     try:
    #         r.delete(key)
    #     except Exception as e:
    #         print(f"[ERROR] 删除 {key} 时出错: {e}")
    # print(f"[OK] 已清理 {len(remaining_keys)} 个剩余任务记录")

if __name__ == "__main__":
    clean_old_tasks()

