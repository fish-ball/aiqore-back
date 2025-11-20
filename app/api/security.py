"""证券信息API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
from app.database import get_db
from app.services.security_service import security_service
from app.models.security import Security

router = APIRouter(prefix="/api/security", tags=["证券信息"])
logger = logging.getLogger(__name__)


@router.post("/update")
async def update_securities(
    market: Optional[str] = Query(None, description="市场代码，SH或SZ，不传则更新全部")
):
    """
    从QMT更新证券基础信息（异步任务）
    
    Args:
        market: 市场代码，可选
    """
    try:
        from app.tasks.security_tasks import update_securities_task
        from app.utils.task_lock import check_task_lock
        
        # 检查任务锁
        task_name = "update_securities"
        is_locked, lock_message = check_task_lock(task_name)
        
        if is_locked:
            raise HTTPException(
                status_code=409,  # 409 Conflict
                detail=lock_message or f"任务 '{task_name}' 正在运行中，请等待完成后再试"
            )
        
        # 启动异步任务
        task = update_securities_task.delay(market)
        
        return {
            "code": 0,
            "data": {
                "task_id": task.id,
                "status": "PENDING"
            },
            "message": "任务已提交，正在后台处理"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交更新任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.get("/list")
async def get_securities(
    market: Optional[str] = Query(None, description="市场代码"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取证券列表
    
    Args:
        market: 市场代码
        limit: 返回数量
        offset: 偏移量
    """
    try:
        query = db.query(Security).filter(Security.is_active == 1)
        
        if market:
            query = query.filter(Security.market == market)
        
        total = query.count()
        securities = query.order_by(Security.symbol).offset(offset).limit(limit).all()
        
        # 转换为字典格式，确保可以序列化
        items = []
        for sec in securities:
            items.append({
                "id": sec.id,
                "symbol": sec.symbol,
                "name": sec.name,
                "market": sec.market,
                "security_type": sec.security_type,
                "industry": sec.industry,
                "is_active": sec.is_active,
                "abbreviation": sec.abbreviation,
                "created_at": sec.created_at.isoformat() if sec.created_at else None,
                "updated_at": sec.updated_at.isoformat() if sec.updated_at else None
            })
        
        return {
            "code": 0,
            "data": {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            "message": "success"
        }
    except Exception as e:
        import traceback
        logger.error(f"获取列表失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/search")
async def search_securities(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    搜索证券
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量限制
    """
    securities = security_service.search_securities(db, keyword, limit)
    
    # 转换为字典格式
    items = []
    for sec in securities:
        items.append({
            "id": sec.id,
            "symbol": sec.symbol,
            "name": sec.name,
            "market": sec.market,
            "security_type": sec.security_type,
            "industry": sec.industry,
            "is_active": sec.is_active,
            "abbreviation": sec.abbreviation
        })
    
    return {
        "code": 0,
        "data": items,
        "message": "success"
    }


@router.get("/{symbol}")
async def get_security(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    获取证券详情
    
    Args:
        symbol: 证券代码
    """
    try:
        security = security_service.get_security_by_symbol(db, symbol)
        if not security:
            raise HTTPException(status_code=404, detail="证券不存在")
        
        # 转换为字典格式
        security_dict = {
            "id": security.id,
            "symbol": security.symbol,
            "name": security.name,
            "market": security.market,
            "security_type": security.security_type,
            "industry": security.industry,
            "list_date": security.list_date.isoformat() if security.list_date else None,
            "delist_date": security.delist_date.isoformat() if security.delist_date else None,
            "is_active": security.is_active,
            "pinyin": security.pinyin,
            "abbreviation": security.abbreviation,
            "description": security.description,
            "created_at": security.created_at.isoformat() if security.created_at else None,
            "updated_at": security.updated_at.isoformat() if security.updated_at else None
        }
        
        return {
            "code": 0,
            "data": security_dict,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")

