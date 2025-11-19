"""任务锁工具

使用Redis实现分布式锁，确保同类任务只能有一个在运行
"""
import redis
import time
import uuid
import logging
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


class TaskLock:
    """任务锁类"""
    
    def __init__(self, task_name: str, timeout: int = 7200):
        """
        初始化任务锁
        
        Args:
            task_name: 任务名称（用于生成锁的key）
            timeout: 锁的超时时间（秒），默认2小时
        """
        self.task_name = task_name
        self.lock_key = f"task_lock:{task_name}"
        self.timeout = timeout
        self.lock_value = str(uuid.uuid4())  # 唯一标识，用于安全释放锁
        self.redis_client = None
        self._acquired = False
    
    def _get_redis_client(self):
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
        return self.redis_client
    
    def acquire(self) -> bool:
        """
        获取锁
        
        Returns:
            True: 成功获取锁
            False: 锁已被占用
        """
        try:
            r = self._get_redis_client()
            # 使用SET命令实现原子性锁：NX表示只在key不存在时设置，EX设置过期时间
            result = r.set(self.lock_key, self.lock_value, nx=True, ex=self.timeout)
            
            if result:
                self._acquired = True
                logger.info(f"任务锁已获取: {self.lock_key}")
                return True
            else:
                logger.warning(f"任务锁已被占用: {self.lock_key}")
                return False
        except Exception as e:
            logger.error(f"获取任务锁失败: {e}")
            # 如果Redis连接失败，为了安全起见，返回False
            return False
    
    def release(self):
        """释放锁"""
        if not self._acquired:
            return
        
        try:
            r = self._get_redis_client()
            # 使用Lua脚本确保原子性：只有锁的值匹配时才删除
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            r.eval(lua_script, 1, self.lock_key, self.lock_value)
            self._acquired = False
            logger.info(f"任务锁已释放: {self.lock_key}")
        except Exception as e:
            logger.error(f"释放任务锁失败: {e}")
    
    def is_locked(self) -> bool:
        """
        检查锁是否被占用（不一定是当前实例持有的）
        
        Returns:
            True: 锁被占用
            False: 锁未被占用
        """
        try:
            r = self._get_redis_client()
            return r.exists(self.lock_key) > 0
        except Exception as e:
            logger.error(f"检查任务锁状态失败: {e}")
            # 如果检查失败，为了安全起见，假设锁被占用
            return True
    
    def get_lock_info(self) -> Optional[dict]:
        """
        获取锁的信息（如果被占用）
        
        Returns:
            dict: 包含锁的值和剩余TTL，如果锁未被占用则返回None
        """
        try:
            r = self._get_redis_client()
            if not r.exists(self.lock_key):
                return None
            
            value = r.get(self.lock_key)
            ttl = r.ttl(self.lock_key)
            
            return {
                "value": value,
                "ttl": ttl,
                "lock_key": self.lock_key
            }
        except Exception as e:
            logger.error(f"获取锁信息失败: {e}")
            return None
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.acquire():
            raise RuntimeError(f"无法获取任务锁: {self.lock_key}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
    
    def __del__(self):
        """析构函数，确保锁被释放"""
        if self._acquired:
            try:
                self.release()
            except:
                pass


def check_task_lock(task_name: str) -> Tuple[bool, Optional[str]]:
    """
    检查任务锁状态
    
    Args:
        task_name: 任务名称
    
    Returns:
        tuple: (is_locked, message)
            is_locked: True表示锁被占用，False表示未占用
            message: 错误消息（如果锁被占用）
    """
    lock = TaskLock(task_name)
    if lock.is_locked():
        lock_info = lock.get_lock_info()
        if lock_info:
            ttl = lock_info.get("ttl", 0)
            if ttl > 0:
                minutes = ttl // 60
                seconds = ttl % 60
                message = f"任务 '{task_name}' 正在运行中，预计还需 {minutes} 分 {seconds} 秒完成"
            else:
                message = f"任务 '{task_name}' 正在运行中"
        else:
            message = f"任务 '{task_name}' 正在运行中"
        return True, message
    return False, None

