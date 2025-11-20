import os
import sys
import locale

# 修复 Windows 中文系统下的编码问题
# 在导入 Alembic 之前设置环境变量，强制使用 UTF-8 编码
# 这样可以避免 Alembic 使用 locale 编码（GBK）读取 UTF-8 配置文件时出错
if sys.platform == 'win32':
    # 设置环境变量，让 Python 使用 UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 尝试设置 locale 为 UTF-8（如果系统支持）
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            pass  # 如果都失败，继续使用默认 locale

# 猴子补丁：修复 Alembic 的编码问题
# 在导入 Alembic 之前，修改其兼容性代码，强制使用 UTF-8 而不是 locale 编码
try:
    import alembic.util.compat as alembic_compat
    # 保存原始函数
    _original_read_config_parser = alembic_compat.read_config_parser
    
    # 创建新的函数，强制使用 UTF-8
    def _patched_read_config_parser(file_config, file_argument):
        """修复后的 read_config_parser，强制使用 UTF-8 编码"""
        import configparser
        # 如果是 Python 3.10+，使用 UTF-8 而不是 locale
        if sys.version_info >= (3, 10):
            # 对于单个文件，直接使用 UTF-8 读取
            if isinstance(file_argument, (str, os.PathLike)):
                file_argument = [file_argument]
            result = []
            for file_path in file_argument:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_config.read_file(f)
                    result.append(str(file_path))
                except Exception:
                    # 如果 UTF-8 失败，尝试使用原始方法
                    try:
                        return _original_read_config_parser(file_config, file_argument)
                    except:
                        pass
            return result
        else:
            # Python 3.9 及以下，使用原始方法
            return _original_read_config_parser(file_config, file_argument)
    
    # 应用猴子补丁
    alembic_compat.read_config_parser = _patched_read_config_parser
except Exception:
    # 如果猴子补丁失败，继续使用原始行为
    pass

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.config import settings
from app.models import Account, Trade, Position, Security, Sector

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 设置数据库URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# 注意：fileConfig 在读取配置文件时也可能遇到编码问题
# Python 3.10+ 支持 encoding 参数
if config.config_file_name is not None:
    try:
        # Python 3.10+ 支持 encoding 参数
        if sys.version_info >= (3, 10):
            fileConfig(config.config_file_name, encoding='utf-8')
        else:
            fileConfig(config.config_file_name)
    except (UnicodeDecodeError, TypeError) as e:
        # 如果 fileConfig 不支持 encoding 参数或仍然出错，尝试其他方法
        try:
            fileConfig(config.config_file_name)
        except Exception:
            # 如果都失败，跳过日志配置（不影响迁移功能）
            import warnings
            warnings.warn(f"无法读取日志配置文件，跳过日志配置: {e}")

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

