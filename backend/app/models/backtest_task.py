"""回测任务模型：UUID 主键，外键 Strategy/证券，回测参数与 script 快照"""
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


def _gen_uuid():
    return str(uuid.uuid4())


class BackTestTask(Base):
    """回测任务：关联策略与证券，存储参数与执行结果"""
    __tablename__ = "backtest_tasks"

    id = Column(String(36), primary_key=True, default=_gen_uuid, comment="UUID 主键")
    strategy_id = Column(String(36), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True, comment="策略 ID，删除策略后可空")
    security_id = Column(Integer, ForeignKey("securities.id", ondelete="SET NULL"), nullable=True, index=True, comment="证券 ID，可空")
    security_symbol = Column(String(64), nullable=True, comment="证券代码缓存")
    security_name = Column(String(100), nullable=True, comment="证券名称缓存")

    start_date = Column(String(10), nullable=False, comment="回测开始日期 YYYY-MM-DD")
    end_date = Column(String(10), nullable=False, comment="回测结束日期 YYYY-MM-DD")
    initial_cash = Column(Float, nullable=False, default=1000000.0, comment="初始资金")
    commission = Column(Float, nullable=False, default=0.0002, comment="手续费")
    position_pct = Column(Integer, nullable=False, default=95, comment="仓位比例，如 95 表示 95%")

    script = Column(Text, nullable=True, comment="策略代码快照，创建时从 Strategy.script 复制")

    status = Column(String(20), nullable=False, default="pending", index=True, comment="pending/running/success/failure")
    celery_task_id = Column(String(255), nullable=True, comment="Celery 任务 ID")
    result = Column(JSON, nullable=True, comment="回测结果或错误信息 JSON")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<BackTestTask(id={self.id}, status={self.status})>"
