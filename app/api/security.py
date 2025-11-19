"""证券信息API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.security_service import security_service
from app.models.security import Security

router = APIRouter(prefix="/api/security", tags=["证券信息"])


@router.post("/update")
async def update_securities(
    market: Optional[str] = Query(None, description="市场代码，SH或SZ，不传则更新全部"),
    db: Session = Depends(get_db)
):
    """
    从QMT更新证券基础信息
    
    Args:
        market: 市场代码，可选
    """
    try:
        result = security_service.update_securities_from_qmt(db, market)
        if result["success"]:
            return {
                "code": 0,
                "data": result,
                "message": "更新成功"
            }
        else:
            return {
                "code": 1,
                "data": result,
                "message": result.get("message", "更新失败")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


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
        securities = query.offset(offset).limit(limit).all()
        
        return {
            "code": 0,
            "data": {
                "items": securities,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            "message": "success"
        }
    except Exception as e:
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
    try:
        securities = security_service.search_securities(db, keyword, limit)
        return {
            "code": 0,
            "data": securities,
            "message": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


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
        
        return {
            "code": 0,
            "data": security,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")

