"""证券相关异步任务"""
from app.utils.task_decorator import task
from app.database import SessionLocal
from app.services.security_service import security_service
from app.models.security import Security
from app.services.qmt_service import qmt_service
from app.utils.task_lock import TaskLock
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@task(display_name="同步证券列表", category="证券管理", bind=True, name="update_securities")
def update_securities_task(self, market=None):
    """
    同步证券列表
    
    异步更新证券基础信息任务
    
    Args:
        market: 市场代码，'SH' 或 'SZ'，None表示全部
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
        # 更新任务状态
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 0, "status": "开始获取股票列表..."})
        
        # 获取QMT股票列表
        stocks = qmt_service.get_stock_list(market)
        
        if not stocks:
            return {
                "success": False,
                "message": "未获取到股票列表，请检查QMT连接",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0
            }
        
        total = len(stocks)
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": total, "status": f"获取到 {total} 只股票，开始更新..."}
        )
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        # 批量获取股票名称（每批100个）
        batch_size = 100
        symbols_batch = []
        names_map = {}
        
        # 先批量获取所有股票的名称
        for i, stock_data in enumerate(stocks):
            symbol = stock_data.get("symbol")
            if not symbol:
                continue
            
            symbols_batch.append(symbol)
            
            # 每批处理一次
            if len(symbols_batch) >= batch_size or i == len(stocks) - 1:
                try:
                    # 使用get_instrument_detail批量获取名称
                    try:
                        from xtquant import xtdata
                        if hasattr(xtdata, 'get_instrument_detail'):
                            for sym in symbols_batch:
                                try:
                                    detail = xtdata.get_instrument_detail(sym)
                                    if detail and isinstance(detail, dict):
                                        instrument_name = detail.get("InstrumentName", "")
                                        if instrument_name:
                                            names_map[sym] = instrument_name
                                except:
                                    pass
                    except:
                        pass
                except Exception as e:
                    logger.debug(f"批量获取名称失败: {e}")
                
                symbols_batch = []
                
                # 更新进度
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": total,
                        "status": f"正在获取股票名称... ({i + 1}/{total})"
                    }
                )
        
        # 如果批量获取失败，尝试从实时行情获取（但这样会很慢）
        if not names_map and len(stocks) > 0:
            logger.info("尝试从实时行情获取名称...")
            # 只获取前100个作为示例
            sample_symbols = [s.get("symbol") for s in stocks[:100] if s.get("symbol")]
            if sample_symbols:
                quotes = qmt_service.get_realtime_quote(sample_symbols)
                if quotes:
                    for sym, quote in quotes.items():
                        if quote.get("name"):
                            names_map[sym] = quote.get("name")
        
        # 处理每个股票
        for idx, stock_data in enumerate(stocks):
            symbol = stock_data.get("symbol")
            if not symbol:
                continue
            
            try:
                # 查询是否已存在
                security = db.query(Security).filter(Security.symbol == symbol).first()
                
                # 获取名称（优先从批量获取的map中取，否则使用代码）
                name = names_map.get(symbol, symbol)
                
                # 如果还是没有名称，尝试单独获取
                if name == symbol:
                    try:
                        from xtquant import xtdata
                        if hasattr(xtdata, 'get_instrument_detail'):
                            detail = xtdata.get_instrument_detail(symbol)
                            if detail and isinstance(detail, dict):
                                instrument_name = detail.get("InstrumentName", "")
                                if instrument_name:
                                    name = instrument_name
                    except:
                        pass
                
                market_code = stock_data.get("market", "SH" if symbol.endswith(".SH") else "SZ")
                
                if security:
                    # 更新现有记录
                    if security.name != name or security.market != market_code:
                        security.name = name
                        security.market = market_code
                        security.updated_at = datetime.now()
                        updated_count += 1
                else:
                    # 创建新记录
                    security = Security(
                        symbol=symbol,
                        name=name,
                        market=market_code,
                        security_type="股票",
                        is_active=1
                    )
                    db.add(security)
                    created_count += 1
                
                # 每100条提交一次，避免事务过大
                if (created_count + updated_count) % 100 == 0:
                    db.commit()
                    logger.info(f"已处理 {created_count + updated_count} 条记录...")
                
                # 每50条更新一次进度
                if (idx + 1) % 50 == 0 or idx == len(stocks) - 1:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": idx + 1,
                            "total": total,
                            "status": f"正在更新数据库... ({idx + 1}/{total})"
                        }
                    )
                    
            except Exception as e:
                error_count += 1
                logger.warning(f"处理股票 {symbol} 失败: {e}")
                continue
        
        # 最终提交
        db.commit()
        
        result = {
            "success": True,
            "message": "更新成功",
            "total": total,
            "created": created_count,
            "updated": updated_count,
            "errors": error_count
        }
        
        logger.info(f"更新完成: 总计 {total}, 新增 {created_count}, 更新 {updated_count}, 错误 {error_count}")
        
        # 更新最终状态
        self.update_state(
            state="SUCCESS",
            meta={
                "current": total,
                "total": total,
                "status": "更新完成",
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

