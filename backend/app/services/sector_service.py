"""板块信息服务"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.models import AssetClass, DataSourceSector, DataSourceType, InstrumentType
from app.models.sector import Sector

logger = logging.getLogger(__name__)


def _count_sector_tree(nodes: List[DataSourceSector]) -> int:
    """递归统计适配器返回的板块节点总数（含子节点）。"""
    n = 0
    for item in nodes:
        n += 1
        n += _count_sector_tree(item.children)
    return n


def _asset_class_value(ac: AssetClass | str) -> str:
    if isinstance(ac, AssetClass):
        return ac.value
    return str(ac)


def _instrument_type_value(it: InstrumentType | str) -> str:
    if isinstance(it, InstrumentType):
        return it.value
    return str(it)


def sector_to_public_dict(sector: Sector, *, include_children: bool = False) -> Dict[str, Any]:
    """API 用扁平字典。"""
    item: Dict[str, Any] = {
        "id": sector.id,
        "name": sector.name,
        "alias": sector.alias,
        "source": sector.source,
        "asset_class": sector.asset_class,
        "instrument_type": sector.instrument_type,
        "parent_id": sector.parent_id,
        "remark": sector.remark,
        "created_at": sector.created_at.isoformat() if sector.created_at else None,
        "updated_at": sector.updated_at.isoformat() if sector.updated_at else None,
    }
    if include_children:
        item["children"] = [
            {
                "id": c.id,
                "name": c.name,
                "alias": c.alias,
                "source": c.source,
                "asset_class": c.asset_class,
                "instrument_type": c.instrument_type,
                "parent_id": c.parent_id,
                "remark": c.remark,
            }
            for c in sector.children
        ]
    return item


class SectorService:
    """板块信息服务（写库逻辑依赖 DataSourceAdapter，由调用方注入实现）。"""

    def sync_sectors_from_adapter(self, db: Session, adapter: DataSourceAdapter) -> Dict[str, Any]:
        """
        使用适配器返回的板块树写入数据库。
        以 (source, alias) 为联合唯一键，并按 children 维护 parent_id 层级。
        """
        try:
            source_enum = DataSourceType(adapter.name)
        except ValueError:
            return {
                "success": False,
                "message": f"适配器 name 不在 DataSourceType 中: {adapter.name!r}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0,
            }

        source_str = source_enum.value
        try:
            roots = adapter.get_sector_list()
            if not roots:
                return {
                    "success": False,
                    "message": "数据源不支持 get_sector_list 或未返回板块数据",
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "errors": 0,
                }

            created_count = 0
            updated_count = 0
            error_count = 0

            def sync_tree(
                nodes: List[DataSourceSector],
                parent_id: Optional[int],
            ) -> None:
                nonlocal created_count, updated_count, error_count
                for node in nodes:
                    if not node.alias or not isinstance(node.alias, str):
                        error_count += 1
                        logger.warning("跳过无效板块节点: %r", node)
                        continue
                    try:
                        row = (
                            db.query(Sector)
                            .filter(Sector.source == source_str, Sector.alias == node.alias)
                            .first()
                        )
                        ac_val = _asset_class_value(node.asset_class)
                        it_val = _instrument_type_value(node.instrument_type)
                        display_name = (node.name or "").strip() or node.alias

                        if row:
                            changed = False
                            if row.name != display_name:
                                row.name = display_name
                                changed = True
                            if row.asset_class != ac_val:
                                row.asset_class = ac_val
                                changed = True
                            if row.instrument_type != it_val:
                                row.instrument_type = it_val
                                changed = True
                            if row.parent_id != parent_id:
                                row.parent_id = parent_id
                                changed = True
                            if changed:
                                row.updated_at = datetime.now()
                                updated_count += 1
                            db.flush()
                            node_id = row.id
                        else:
                            s_new = Sector(
                                name=display_name,
                                alias=node.alias,
                                source=source_str,
                                asset_class=ac_val,
                                instrument_type=it_val,
                                parent_id=parent_id,
                            )
                            db.add(s_new)
                            db.flush()
                            node_id = s_new.id
                            created_count += 1

                        sync_tree(node.children, node_id)
                    except Exception as e:
                        error_count += 1
                        logger.warning("处理板块 %s 失败: %s", node.alias, e)

            sync_tree(roots, None)
            db.commit()

            total_nodes = _count_sector_tree(roots)
            logger.info(
                "板块同步完成: 节点 %s, 新增 %s, 更新 %s, 错误 %s",
                total_nodes,
                created_count,
                updated_count,
                error_count,
            )

            return {
                "success": True,
                "message": "同步成功",
                "total": total_nodes,
                "created": created_count,
                "updated": updated_count,
                "errors": error_count,
            }

        except Exception as e:
            db.rollback()
            logger.exception("同步板块失败")
            return {
                "success": False,
                "message": f"同步失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0,
            }

    def get_sectors(
        self,
        db: Session,
        source: Optional[str] = None,
        asset_class: Optional[str] = None,
        instrument_type: Optional[str] = None,
    ) -> List[Sector]:
        """获取板块列表（可选按 source、asset_class、instrument_type 过滤）。"""
        try:
            q = db.query(Sector).order_by(Sector.source, Sector.alias)
            if source is not None and source != "":
                q = q.filter(Sector.source == source.strip().lower())
            if asset_class is not None and asset_class != "":
                q = q.filter(Sector.asset_class == asset_class.strip())
            if instrument_type is not None and instrument_type != "":
                q = q.filter(Sector.instrument_type == instrument_type.strip().upper())
            return q.all()
        except Exception as e:
            logger.error("获取板块列表失败: %s", e)
            return []

    def get_sector(self, db: Session, source: str, alias: str) -> Optional[Sector]:
        """按数据源与 alias 查询。"""
        try:
            key = (source or "").strip().lower()
            al = (alias or "").strip()
            if not key or not al:
                return None
            return (
                db.query(Sector)
                .filter(Sector.source == key, Sector.alias == al)
                .first()
            )
        except Exception as e:
            logger.error("获取板块失败: %s", e)
            return None

    def get_sector_by_name(self, db: Session, name: str) -> Optional[Sector]:
        """兼容：按显示名称查找（若有重名仅返回第一条）。"""
        try:
            return db.query(Sector).filter(Sector.name == name).first()
        except Exception as e:
            logger.error("获取板块失败: %s", e)
            return None

    def update_sector_remark(
        self,
        db: Session,
        source: str,
        alias: str,
        remark: Optional[str],
    ) -> Optional[Sector]:
        """更新板块用户备注；remark 可为 None 表示清空。"""
        row = self.get_sector(db, source, alias)
        if not row:
            return None
        row.remark = remark
        db.commit()
        db.refresh(row)
        return row

    def get_sector_statistics(self, db: Session) -> Dict[str, Any]:
        """按 source、asset_class 汇总数量。"""
        try:
            rows = db.query(Sector).all()
            return {
                "total_sectors": len(rows),
                "by_source": dict(Counter(s.source for s in rows)),
                "by_asset_class": dict(Counter(s.asset_class for s in rows)),
                "by_instrument_type": dict(Counter(s.instrument_type for s in rows)),
            }
        except Exception as e:
            logger.error("获取板块统计失败: %s", e)
            return {
                "total_sectors": 0,
                "by_source": {},
                "by_asset_class": {},
                "by_instrument_type": {},
            }


sector_service = SectorService()
