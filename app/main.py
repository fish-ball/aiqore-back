"""FastAPI主应用"""
from typing import Optional
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine, Base, get_db
from app.api import market, trade, analysis, security, sector, debug, data_source

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基于国金QMT驱动的个人投资管理系统",
    version="1.0.0",
)


class UTF8Middleware(BaseHTTPMiddleware):
    """确保所有响应都使用UTF-8编码"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 确保响应头包含UTF-8编码
        if "content-type" in response.headers:
            content_type = response.headers["content-type"]
            if "charset" not in content_type.lower():
                response.headers["content-type"] = f"{content_type}; charset=utf-8"
        else:
            # 如果没有content-type，根据响应类型设置
            if hasattr(response, "body") and response.body:
                response.headers["content-type"] = "application/json; charset=utf-8"
        return response


# 添加UTF-8编码中间件
app.add_middleware(UTF8Middleware)

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
app.include_router(sector.router)
app.include_router(data_source.router, prefix="/api/data-source")

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


@app.get("/api/data-source/ping")
async def data_source_ping():
    """数据源模块连通性探测"""
    return {"ok": True, "message": "data-source router reachable"}


@app.get("/api/data-source/list")
async def data_source_list_route(
    source_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """数据源连接列表（与 data_source 模块逻辑一致，确保路由一定注册）"""
    return await data_source.list_connections(source_type=source_type, is_active=is_active, db=db)
