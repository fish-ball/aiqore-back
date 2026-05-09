"""任务规格注册表

用于对外暴露可调用任务的说明、参数定义等结构化信息。
目前主要覆盖标的行情数据相关的 Celery 任务。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TaskParamSpec(BaseModel):
    """任务参数规格描述。"""

    name: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None


class TaskSpec(BaseModel):
    """任务规格描述。"""

    name: str  # 对前端暴露的逻辑任务名称
    celery_name: str  # 对应 Celery 任务名称
    title: str  # 任务中文名称/标题
    description: Optional[str] = None  # 任务用途说明
    category: Optional[str] = None  # 任务分类（如：instrument）
    params: List[TaskParamSpec] = []


_TASK_SPECS: Dict[str, TaskSpec] = {}


def _register(spec: TaskSpec) -> None:
    """注册单个任务规格。"""
    _TASK_SPECS[spec.name] = spec


# === 标的行情数据相关任务 ===
_register(
    TaskSpec(
        name="update_bulk_instrument_info",
        celery_name="task_update_bulk_instrument_info",
        title="批量更新证券基础信息",
        description="从指定数据源批量同步证券列表及基础信息到数据库。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="market",
                type="string",
                required=False,
                default=None,
                description="市场代码，例如 SZ、SH；为空时同步全部市场。",
            ),
            TaskParamSpec(
                name="sector",
                type="string",
                required=False,
                default=None,
                description="板块名称，仅同步指定板块内的证券。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_single_instrument_all_data",
        celery_name="task_update_single_instrument_all_data",
        title="更新单个证券全量数据",
        description="更新单个证券的日/周/月 K 线、全部分时数据以及除权数据。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="symbol",
                type="string",
                required=True,
                description="证券代码，例如 000001.SZ。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地缓存。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_single_instrument_kdata",
        celery_name="task_update_single_instrument_kdata",
        title="更新单个证券某周期 K 线",
        description="更新单个证券在指定周期内的 K 线数据（1d/1w/1M）。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="symbol",
                type="string",
                required=True,
                description="证券代码，例如 000001.SZ。",
            ),
            TaskParamSpec(
                name="market_layer",
                type="string",
                required=True,
                description="证券大类：Equity（权益类）、Future（期货类）、Option（期权类）。",
            ),
            TaskParamSpec(
                name="period",
                type="string",
                required=True,
                description="周期：1d、1w、1M。",
            ),
            TaskParamSpec(
                name="start_date",
                type="string",
                required=False,
                default=None,
                description="开始日期，格式 YYYY-MM-DD。",
            ),
            TaskParamSpec(
                name="end_date",
                type="string",
                required=False,
                default=None,
                description="结束日期，格式 YYYY-MM-DD。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地缓存。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_single_instrument_tick_for_date",
        celery_name="task_update_single_instrument_tick_for_date",
        title="更新单个证券某日分时",
        description="拉取并落盘单个证券在指定交易日的分时数据。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="symbol",
                type="string",
                required=True,
                description="证券代码，例如 000001.SZ。",
            ),
            TaskParamSpec(
                name="trade_date",
                type="string",
                required=True,
                description="交易日，格式 YYYY-MM-DD 或 YYYYMMDD。",
            ),
            TaskParamSpec(
                name="market_layer",
                type="string",
                required=True,
                description="证券大类：Equity（权益类）、Future（期货类）、Option（期权类）。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地缓存。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_single_instrument_tick_full",
        celery_name="task_update_single_instrument_tick_full",
        title="补全单个证券全部分时",
        description="按日线 parquet 中的交易日补全该证券的全部分时数据。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="symbol",
                type="string",
                required=True,
                description="证券代码，例如 000001.SZ。",
            ),
            TaskParamSpec(
                name="market_layer",
                type="string",
                required=True,
                description="证券大类：Equity（权益类）、Future（期货类）、Option（期权类）。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地缓存。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_bulk_instrument_all_data",
        celery_name="task_update_bulk_instrument_all_data",
        title="批量更新证券全量数据",
        description="批量更新指定类型证券（或给定列表）的日/周/月 K 线、分时数据以及除权数据。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="market_layer",
                type="string",
                required=True,
                description="证券大类：Equity、Future、Option；与 symbols 配合筛选待更新标的。",
            ),
            TaskParamSpec(
                name="symbols",
                type="array[string]",
                required=False,
                default=None,
                description="待更新的标的代码列表；为空则更新该 market_layer 下全部有效标的。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地缓存。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="update_single_instrument_divid_factors",
        celery_name="task_update_single_instrument_divid_factors",
        title="更新单个证券除权数据",
        description="拉取并落盘单个证券的除权数据，写入对应目录的 divid_factors.parquet。",
        category="instrument",
        params=[
            TaskParamSpec(
                name="symbol",
                type="string",
                required=True,
                description="证券代码，例如 000001.SZ。",
            ),
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
            TaskParamSpec(
                name="start_date",
                type="string",
                required=False,
                default=None,
                description="开始日期，格式 YYYY-MM-DD；为空时由数据源决定默认范围。",
            ),
            TaskParamSpec(
                name="end_date",
                type="string",
                required=False,
                default=None,
                description="结束日期，格式 YYYY-MM-DD；为空时由数据源决定默认范围。",
            ),
            TaskParamSpec(
                name="force_update",
                type="boolean",
                required=False,
                default=False,
                description="是否强制重新拉取并覆盖本地除权数据。",
            ),
        ],
    )
)

_register(
    TaskSpec(
        name="sync_sectors",
        celery_name="task_sync_sectors",
        title="同步板块列表",
        description="从指定数据源拉取板块名称列表并写入数据库，更新证券数量等统计信息。",
        category="sector",
        params=[
            TaskParamSpec(
                name="source_id",
                type="integer",
                required=True,
                description="数据源连接 ID（data_sources.id，须启用）。",
            ),
        ],
    )
)

# === 回测任务 ===
_register(
    TaskSpec(
        name="run_backtest",
        celery_name="task_run_backtest",
        title="执行回测任务",
        description="根据已创建的 BackTestTask 记录执行回测（加载数据、运行 Backtrader 策略、写回结果）。",
        category="backtest",
        params=[
            TaskParamSpec(
                name="backtest_task_id",
                type="string",
                required=True,
                description="回测任务 UUID，由「发起回测」接口创建后获得。",
            ),
        ],
    )
)


def list_task_specs() -> List[TaskSpec]:
    """返回所有已注册任务规格列表。"""
    return list(_TASK_SPECS.values())


def get_task_spec(name: str) -> Optional[TaskSpec]:
    """根据逻辑任务名称获取任务规格。"""
    return _TASK_SPECS.get(name)


def list_task_specs_dict() -> List[Dict[str, Any]]:
    """以纯 dict 形式返回任务规格，便于 API JSON 序列化。"""
    return [spec.model_dump() for spec in _TASK_SPECS.values()]


