"""启动应用"""
import os
import sys
import uvicorn
from app.config import settings

# 确保使用UTF-8编码
if sys.platform == 'win32':
    # Windows系统默认编码可能是GBK，强制设置为UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 设置标准输出和错误输出的编码
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        # 确保uvicorn使用UTF-8编码
        # log_config=None  # 使用默认日志配置，但确保编码正确
    )

