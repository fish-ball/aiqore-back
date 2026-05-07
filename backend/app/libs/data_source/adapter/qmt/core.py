# -*- coding: utf-8 -*-
"""xtdata 加载与进程级缓存。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_xtdata = None
_xtdata_path_loaded: Optional[str] = None


def ensure_xtdata(xt_quant_path: Optional[str]) -> Any:
    """
    确保 xtdata 已加载；使用传入的 xt_quant_path 加入 sys.path 后导入。
    不依赖 app.config，调用方需传入有效路径。
    """
    global _xtdata, _xtdata_path_loaded
    path = (xt_quant_path or "").strip() or None
    if _xtdata is not None:
        return _xtdata
    if not path:
        return None
    base = Path(path)
    if base.is_dir():
        datadir = base / "datadir"
        if datadir.is_dir():
            datadir_str = str(datadir)
            if datadir_str not in sys.path:
                sys.path.insert(0, datadir_str)
                _xtdata_path_loaded = datadir_str
    try:
        from xtquant import xtdata as _xt

        _xtdata = _xt
        return _xtdata
    except ImportError as e:
        logger.warning("xtquant 未安装或不可用: %s", e)
        return None


def reset_xtdata_cache() -> None:
    """清空 xtdata 进程级缓存（供单元测试隔离）。"""
    global _xtdata, _xtdata_path_loaded
    if _xtdata_path_loaded and _xtdata_path_loaded in sys.path:
        try:
            sys.path.remove(_xtdata_path_loaded)
        except ValueError:
            pass
    _xtdata = None
    _xtdata_path_loaded = None
