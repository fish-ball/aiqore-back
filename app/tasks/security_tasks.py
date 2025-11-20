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
        self.update_state(
            state="FAILURE",
            meta={"error": error_msg, "status": "任务冲突"}
        )
        return {
            "success": False,
            "message": error_msg,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0
        }
    
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
            self.update_state(
                state="FAILURE",
                meta={
                    "error": result.get("message", "更新失败"),
                    "status": "更新失败",
                    "result": result
                }
            )
        
        return result
        
    except Exception as e:
        logger.error(f"异步更新证券信息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "status": "更新失败"}
        )
        return {
            "success": False,
            "message": f"更新失败: {str(e)}",
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0
        }
    finally:
        # 确保释放锁
        task_lock.release()
        db.close()

