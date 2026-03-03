"""数据源连接模型：QMT、聚宽、tushare 等连接配置，支持行情源/交易源角色"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class DataSourceConnection(Base):
    """数据源连接配置（QMT 等可参数化，预留聚宽、tushare）"""
    __tablename__ = "data_source_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="显示名称")
    source_type = Column(String(32), nullable=False, index=True, comment="数据源类型: qmt, joinquant, tushare")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_quote_source = Column(Boolean, default=False, nullable=False, comment="是否作为行情源")
    is_trading_source = Column(Boolean, default=False, nullable=False, comment="是否作为交易驱动源")

    # QMT/miniQMT 专用（source_type=qmt 时使用）。xtquant 本地连接仅用 xt_quant_path、xt_quant_acct；host/port/user/password 为预留
    host = Column(String(255), nullable=True, comment="预留，miniQMT 本地连接不使用")
    port = Column(Integer, nullable=True, comment="预留，miniQMT 本地连接不使用")
    user = Column(String(100), nullable=True, comment="预留")
    password = Column(String(255), nullable=True, comment="可选，登录在 miniQMT 客户端完成")
    xt_quant_path = Column(String(500), nullable=True, comment="miniQMT userdata_mini 路径，必填")
    xt_quant_acct = Column(String(50), nullable=True, comment="资金账号，交易/订阅时使用")

    # 其他数据源可存 JSON，首期可不建
    # config = Column(JSON, nullable=True, comment="类型相关扩展配置")

    description = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<DataSourceConnection(id={self.id}, name={self.name}, source_type={self.source_type})>"
