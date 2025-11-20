"""FastAPI主应用"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import market, trade, analysis, security, sector, debug

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

