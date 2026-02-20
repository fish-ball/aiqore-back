"""证券相关异步任务"""
from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.security_service import security_service
from app.utils.task_lock import TaskLock
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="update_securities")
def update_securities_task(self, market=None, sector=None):
    """
    同步证券列表
    
    异步更新证券基础信息任务
    
    Args:
        market: 市场代码，'SH' 或 'SZ'，None表示全部
        sector: 板块名称，如果指定则只同步该板块的证券
    """
    task_name = "update_securities"
    task_lock = TaskLock(task_name, timeout=7200)  # 2小时超时
    
    # 尝试获取锁
    if not task_lock.acquire():
        error_msg = f"任务 '{task_name}' 已在运行中，无法重复执行"
        logger.warning(error_msg)
        # 对于业务逻辑失败，使用 SUCCESS 状态但返回失败结果
        # 这样可以避免 Celery 尝试解析异常信息格式
        result = {
            "success": False,
            "message": error_msg,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0
        }
        # 更新为 SUCCESS 状态，但结果中包含失败信息
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "任务冲突",
                "result": result
            }
        )
        return result
    
    db = SessionLocal()
    try:
        # 任务启动时立即更新状态，确保在Redis中创建任务记录
        # 这样任务列表API就能立即看到这个任务
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 0,
                "status": "任务已启动，开始获取股票列表..."
            }
        )
        
        # 直接调用 security_service 的更新方法
        # 该方法已经支持所有类型的标的和完整的原始数据保存
        result = security_service.update_securities_from_qmt(db, market, sector)
        
        # 更新最终状态
        if result.get("success"):
            self.update_state(
                state="SUCCESS",
                meta={
                    "current": result.get("total", 0),
                    "total": result.get("total", 0),
                    "status": "更新完成",
                    "result": result
                }
            )
        else:
            # 对于业务逻辑失败（非异常），使用 SUCCESS 状态但结果中包含失败信息
            # 这样可以避免 Celery 尝试解析异常信息格式
            self.update_state(
                state="SUCCESS",
                meta={
                    "status": "更新失败",
                    "result": result
                }
            )
        
        return result
        
    except Exception as e:
        logger.error(f"异步更新证券信息失败: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(error_traceback)
        
        # 对于真正的异常，直接抛出让 Celery 自动处理
        # Celery 会自动格式化异常信息，避免格式错误
        # 这样前端可以通过查询任务状态获取异常信息
        raise
    finally:
        # 确保释放锁
        task_lock.release()
        db.close()

