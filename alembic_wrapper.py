#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alembic 编码修复包装脚本
在 Windows 中文系统上，强制使用 UTF-8 编码读取配置文件
"""
import os
import sys
import locale

# 在导入 Alembic 之前修复编码问题
if sys.platform == 'win32':
    # 方法1: 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 方法2: 尝试修改 locale（如果系统支持）
    try:
        # 尝试设置为 UTF-8 locale
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            # 如果都失败，使用猴子补丁修改 Alembic 的兼容性代码
            pass

# 方法3: 猴子补丁 - 在导入 Alembic 之前修改其兼容性代码
# 这必须在导入 alembic 之前执行
import alembic.util.compat as alembic_compat

# 保存原始函数
_original_read_config_parser = alembic_compat.read_config_parser

def _patched_read_config_parser(file_config, file_argument):
    """修复后的 read_config_parser，强制使用 UTF-8 编码"""
    import configparser
    
    # Python 3.10+ 使用 encoding 参数
    if sys.version_info >= (3, 10):
        # 将单个文件路径转换为列表
        if isinstance(file_argument, (str, os.PathLike)):
            file_argument = [file_argument]
        elif not isinstance(file_argument, (list, tuple)):
            file_argument = list(file_argument)
        
        # 使用 UTF-8 编码读取每个文件
        result = []
        for file_path in file_argument:
            file_path_str = str(file_path)
            try:
                # 尝试使用 UTF-8 编码读取
                with open(file_path_str, 'r', encoding='utf-8') as f:
                    file_config.read_file(f)
                result.append(file_path_str)
            except UnicodeDecodeError:
                # 如果 UTF-8 失败，尝试 GBK（向后兼容）
                try:
                    with open(file_path_str, 'r', encoding='gbk') as f:
                        file_config.read_file(f)
                    result.append(file_path_str)
                except Exception as e:
                    # 如果都失败，使用原始方法
                    print(f"Warning: Failed to read {file_path_str} with UTF-8 or GBK: {e}", file=sys.stderr)
                    try:
                        return _original_read_config_parser(file_config, file_argument)
                    except:
                        pass
            except Exception as e:
                # 其他错误，使用原始方法
                print(f"Warning: Error reading {file_path_str}: {e}", file=sys.stderr)
                try:
                    return _original_read_config_parser(file_config, file_argument)
                except:
                    pass
        
        return result if result else _original_read_config_parser(file_config, file_argument)
    else:
        # Python 3.9 及以下，使用原始方法
        return _original_read_config_parser(file_config, file_argument)

# 应用猴子补丁
alembic_compat.read_config_parser = _patched_read_config_parser

# 现在可以安全地导入和运行 Alembic
from alembic.config import main

if __name__ == '__main__':
    # 运行 Alembic，传递所有命令行参数
    sys.exit(main())

