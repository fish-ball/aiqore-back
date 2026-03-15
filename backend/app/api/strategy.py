"""策略管理 API：增删查改，策略名称 / 策略类型 / 代码 script"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.strategy import Strategy, STRATEGY_TYPE_BACKTRADER

router = APIRouter(prefix="", tags=["策略管理"])

# 允许的策略类型枚举，当前仅 backtrader
ALLOWED_STRATEGY_TYPES = (STRATEGY_TYPE_BACKTRADER,)


# ---------- Pydantic 模型 ----------


class StrategyBase(BaseModel):
    """策略基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    strategy_type: str = Field(..., description="策略类型: backtrader")
    script: Optional[str] = Field(None, description="策略代码 script")


class StrategyCreate(StrategyBase):
    """创建策略"""
    pass


class StrategyUpdate(BaseModel):
    """更新策略（全部可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    strategy_type: Optional[str] = None
    script: Optional[str] = None


def _model_to_item(m: Strategy) -> dict:
    """ORM 转响应字典"""
    return {
        "id": m.id,
        "name": m.name,
        "strategy_type": m.strategy_type,
        "script": m.script,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.get("/list")
async def list_strategies(
    strategy_type: Optional[str] = Query(None, description="按策略类型筛选"),
    db: Session = Depends(get_db),
):
    """获取策略列表，支持按类型筛选"""
    q = db.query(Strategy)
    if strategy_type is not None:
        q = q.filter(Strategy.strategy_type == strategy_type)
    rows = q.order_by(Strategy.id).all()
    items = [_model_to_item(r) for r in rows]
    return {"code": 0, "data": {"items": items, "total": len(items)}, "message": "success"}


@router.post("/strategies")
async def create_strategy(body: StrategyCreate, db: Session = Depends(get_db)):
    """新建策略"""
    if body.strategy_type not in ALLOWED_STRATEGY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"strategy_type 须为 {', '.join(ALLOWED_STRATEGY_TYPES)} 之一",
        )
    strategy = Strategy(
        name=body.name,
        strategy_type=body.strategy_type,
        script=body.script,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return {"code": 0, "data": _model_to_item(strategy), "message": "success"}


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """获取单条策略"""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {"code": 0, "data": _model_to_item(s), "message": "success"}


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    body: StrategyUpdate,
    db: Session = Depends(get_db),
):
    """更新策略"""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    update_data = body.model_dump(exclude_unset=True)
    if "strategy_type" in update_data and update_data["strategy_type"] not in ALLOWED_STRATEGY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"strategy_type 须为 {', '.join(ALLOWED_STRATEGY_TYPES)} 之一",
        )
    for k, v in update_data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return {"code": 0, "data": _model_to_item(s), "message": "success"}


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(s)
    db.commit()
    return {"code": 0, "data": None, "message": "success"}
