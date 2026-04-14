"""策略管理 API：增删查改，策略名称 / 策略类型 / 代码 script"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
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


def _query_strategies_page(
    db: Session,
    strategy_type: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[List[dict], int]:
    q = db.query(Strategy)
    if strategy_type is not None:
        q = q.filter(Strategy.strategy_type == strategy_type)
    total = q.count()
    offset = (page - 1) * page_size
    rows = q.order_by(Strategy.id).offset(offset).limit(page_size).all()
    return [_model_to_item(r) for r in rows], total


@router.get("/strategies")
async def list_strategies_collection(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=500, description="每页条数"),
    strategy_type: Optional[str] = Query(None, description="按策略类型筛选"),
    db: Session = Depends(get_db),
):
    """策略列表（分页），与 vue-core ListView 约定一致。"""
    results, count = _query_strategies_page(db, strategy_type, page, page_size)
    return {"results": results, "count": count}


@router.get("/list")
async def list_strategies(
    page: int = Query(1, ge=1, description="页码（从 1 起）"),
    page_size: int = Query(50, ge=1, le=500, description="每页条数"),
    strategy_type: Optional[str] = Query(None, description="按策略类型筛选"),
    db: Session = Depends(get_db),
):
    """兼容旧路径，与 GET /strategies 相同。"""
    results, count = _query_strategies_page(db, strategy_type, page, page_size)
    return {"results": results, "count": count}


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
    return _model_to_item(strategy)


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """获取单条策略"""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    return _model_to_item(s)


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
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
    return _model_to_item(s)


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """删除策略"""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(s)
    db.commit()
    return {"deleted": True, "id": strategy_id}
