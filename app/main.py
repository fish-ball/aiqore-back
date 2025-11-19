"""FastAPI主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import market, trade, analysis, security, debug, task

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基于国金QMT驱动的个人投资管理系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(market.router)
app.include_router(trade.router)
app.include_router(analysis.router)
app.include_router(security.router)
app.include_router(task.router)

# 调试路由（仅在开发环境使用）
if settings.DEBUG:
    app.include_router(debug.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "个人投资系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

