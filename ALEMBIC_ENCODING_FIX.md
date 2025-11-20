# Alembic 编码问题分析与解决方案

## 问题描述

在 Windows 中文系统上执行 `alembic upgrade head` 或 `alembic revision` 时，出现以下错误：

```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa8 in position 2389: illegal multibyte sequence
```

## 问题根源

### 1. Windows 中文系统的默认编码

Windows 中文系统的默认 locale 编码是 **GBK (cp936)**，而不是 UTF-8。

```python
import locale
print(locale.getpreferredencoding())  # 输出: cp936 (GBK)
```

### 2. Alembic 的编码处理逻辑

Alembic 在读取配置文件 `alembic.ini` 时，使用了以下逻辑（在 `alembic/util/compat.py` 中）：

```python
def read_config_parser(file_config, file_argument):
    if py310:  # Python 3.10+
        return file_config.read(file_argument, encoding="locale")  # 使用 locale 编码
    else:
        return file_config.read(file_argument)  # 使用系统默认编码
```

### 3. 编码冲突

- **Alembic 使用**: `encoding="locale"` → GBK (cp936)
- **配置文件实际编码**: UTF-8（包含中文注释）
- **结果**: GBK 编码无法正确解析 UTF-8 字符，导致 `UnicodeDecodeError`

## 解决方案

### 方案 1: 使用 Python 包装脚本（推荐）

使用 `alembic_wrapper.py` 脚本代替直接运行 `alembic` 命令：

```bash
# 使用包装脚本
python alembic_wrapper.py upgrade head
python alembic_wrapper.py current
python alembic_wrapper.py revision --autogenerate -m "message"
```

这个脚本在导入 Alembic 之前就修复了编码问题，是最可靠的解决方案。

### 方案 2: 使用批处理脚本（Windows）

使用 `alembic_utf8.bat` 或 `alembic_utf8.ps1`：

```bash
# CMD
alembic_utf8.bat upgrade head

# PowerShell
.\alembic_utf8.ps1 upgrade head
```

### 方案 3: 修改 `alembic/env.py`（已实现，但可能不够）

在 `alembic/env.py` 文件开头添加编码修复代码，但这只在运行迁移时生效，对命令行工具可能无效。

### 方案 4: 设置系统环境变量（可选）

在运行 Alembic 命令前，设置环境变量：

```powershell
# PowerShell
$env:PYTHONIOENCODING = "utf-8"
alembic upgrade head
```

```cmd
# CMD
set PYTHONIOENCODING=utf-8
alembic upgrade head
```

### 方案 3: 确保 `alembic.ini` 文件使用 UTF-8 编码

确保 `alembic.ini` 文件以 UTF-8 编码保存（大多数现代编辑器默认使用 UTF-8）。

## 技术细节

### Alembic 配置文件读取流程

1. Alembic 初始化 `context.config` 对象
2. 调用 `configparser.ConfigParser.read()` 读取 `alembic.ini`
3. Python 3.10+ 使用 `encoding="locale"` 参数
4. Windows 中文系统 locale = GBK
5. GBK 尝试解析 UTF-8 字符 → 失败

### 修复原理

通过在导入 Alembic 之前应用猴子补丁，修改 `alembic.util.compat.read_config_parser` 函数：

- **原始行为**: 使用 `encoding="locale"` (GBK)
- **修复后**: 强制使用 `encoding="utf-8"`

## 验证修复

运行以下命令验证修复是否生效：

```bash
# 测试 Alembic 是否可以正常读取配置
python -c "from alembic import context; print('OK')"

# 运行迁移
alembic upgrade head
```

## 相关文件

- `alembic/env.py` - 包含编码修复代码
- `alembic.ini` - Alembic 配置文件（应使用 UTF-8 编码）
- `alembic/util/compat.py` - Alembic 兼容性代码（第三方库，通过猴子补丁修改）

## 注意事项

1. **向后兼容**: 修复代码包含错误处理，如果修复失败会回退到原始行为
2. **跨平台**: 修复代码只在 Windows 系统上激活，不影响 Linux/Mac
3. **Python 版本**: 主要针对 Python 3.10+，因为只有这个版本才使用 `encoding="locale"`

## 参考

- [Python locale 编码文档](https://docs.python.org/3/library/locale.html)
- [Alembic 配置文件文档](https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file)
- [Python 编码最佳实践](https://docs.python.org/3/howto/unicode.html)

