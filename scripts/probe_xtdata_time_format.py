# -*- coding: utf-8 -*-
"""
探测 xtdata.get_market_data 返回的 time 列实际类型与值，便于统一归一化逻辑。
运行：在项目根目录执行 uv run python scripts/probe_xtdata_time_format.py
需配置环境或修改下方 XT_QUANT_PATH。
"""
import sys
from pathlib import Path

# 确保项目根在 path 中
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

def main():
    import os
    from app.config import settings
    from app.services.data_source.sync import _resolve_config
    from app.services.data_source.adapter import get_adapter
    from app.database import SessionLocal

    path = getattr(settings, "XT_QUANT_PATH", None) or os.environ.get("XT_QUANT_PATH", "")
    if not path or not Path(path).is_dir():
        print("未配置 XT_QUANT_PATH 或路径不存在，请设置环境变量或 app 配置")
        return

    db = SessionLocal()
    try:
        config, err = _resolve_config(db, "qmt", None)
        if err:
            print("解析数据源失败:", err)
            return
        adapter = get_adapter("qmt", config)
        rows = adapter.get_market_data("000001.SZ", period="1d", count=3)
        if not rows:
            print("get_market_data 返回空，请确认 QMT 已启动且已下载 000001.SZ 日线")
            return
        print("返回行数:", len(rows))
        for i, row in enumerate(rows[:3]):
            t = row.get("time")
            d = row.get("date")
            print(f"  row[{i}] time: type={type(t).__name__!r}, repr={repr(t)[:80]}")
            print(f"           date: type={type(d).__name__!r}, repr={repr(d)[:80]}")
            if hasattr(t, "dtype"):
                print(f"           time.dtype: {getattr(t, 'dtype', None)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
