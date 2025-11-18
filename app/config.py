"""应用配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "个人投资系统"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./investment.db"
    
    # QMT配置
    QMT_HOST: str = "127.0.0.1"
    QMT_PORT: int = 7709
    QMT_USER: Optional[str] = None
    QMT_PASSWORD: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

