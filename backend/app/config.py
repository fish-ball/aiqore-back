"""应用配置管理"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# 项目根目录：app 包上一级
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "个人投资系统"
    DEBUG: bool = True
    
    # 证券数据本地缓存根目录；为空时使用项目根目录下的 data
    DATA_ROOT: Optional[str] = None
    
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "mydb"
    
    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATA_ROOT_PATH(self) -> Path:
        """证券数据本地缓存根目录；DATA_ROOT 为空时使用项目根目录下的 data"""
        if self.DATA_ROOT:
            return Path(self.DATA_ROOT).resolve()
        return _PROJECT_ROOT / "data"
    
    # QMT配置
    QMT_HOST: str = "127.0.0.1"
    QMT_PORT: int = 7709
    QMT_USER: Optional[str] = None
    QMT_PASSWORD: Optional[str] = None
    XT_QUANT_PATH: str = r"C:\国金证券QMT交易端\userdata_mini"
    XT_QUANT_ACCT: str = "39271919"
    
    # Redis配置（用于Celery）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        """构建Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

