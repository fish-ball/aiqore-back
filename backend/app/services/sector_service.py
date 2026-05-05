"""板块信息服务"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import copy

from sqlalchemy.orm import Session

from app.libs.data_source.adapter.base import SecuritiesDataSourceAdapter
from app.models.sector import Sector

logger = logging.getLogger(__name__)


def sector_stats(sector: Sector) -> Dict[str, Any]:
    """读取 metadata.stats（兼容空）。"""
    raw = sector.sector_meta or {}
    return dict(raw.get("stats") or {})


def sector_to_public_dict(sector: Sector, *, include_children: bool = False) -> Dict[str, Any]:
    """API 用扁平字典（stats 展开 + 原始 metadata）。"""
    stats = sector_stats(sector)
    last_sync = stats.get("last_sync_at")
    if last_sync is not None and hasattr(last_sync, "isoformat"):
        last_sync = last_sync.isoformat()
    item: Dict[str, Any] = {
        "id": sector.id,
        "name": sector.name,
        "alias": sector.alias,
        "parent_id": sector.parent_id,
        "metadata": sector.sector_meta,
        "category": stats.get("category"),
        "market": stats.get("market"),
        "security_count": stats.get("security_count") or 0,
        "is_active": stats.get("is_active", 1),
        "last_sync_at": last_sync,
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
                "parent_id": c.parent_id,
                "remark": c.remark,
            }
            for c in sector.children
        ]
    return item


class SectorService:
    """板块信息服务（写库逻辑只依赖 SecuritiesDataSourceAdapter，具体实现由调用方注入）。"""

    def sync_sectors_from_adapter(
        self,
        db: Session,
        adapter: SecuritiesDataSourceAdapter,
        *,
        source_key: str,
    ) -> Dict[str, Any]:
        """
        使用已构造的证券数据源适配器将板块列表写入数据库（alias = 数据源板块键）。
        source_key：写入 sector_meta.sources 的键，与数据源注册名一致（如 qmt、joinquant）。
        """
        key = (source_key or "").strip().lower()
        if not key:
            return {
                "success": False,
                "message": "source_key 不能为空",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0,
            }
        try:
            sectors = adapter.get_sector_list()
            if not sectors:
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

            category_keywords = {
                "股票": ["A股", "B股", "创业板"],
                "基金": ["基金", "ETF", "LOF"],
                "债券": ["债券", "转债", "国债", "企业债", "公司债"],
                "期货": ["期货", "上期所", "大商所", "郑商所", "中金所", "能源中心"],
                "期权": ["期权"],
                "指数": ["指数"],
            }

            def get_category(sector_name: str) -> str:
                for category, keywords in category_keywords.items():
                    for keyword in keywords:
                        if keyword in sector_name:
                            return category
                return "其他"

            def get_market(sector_name: str) -> Optional[str]:
                if "沪市" in sector_name or "上证" in sector_name:
                    return "SH"
                if "深市" in sector_name or "深证" in sector_name:
                    return "SZ"
                if "北交所" in sector_name or "BJ" in sector_name:
                    return "BJ"
                if "沪深" in sector_name:
                    return None
                return None

            for sector_name in sectors:
                if not sector_name or not isinstance(sector_name, str):
                    continue

                try:
                    row = db.query(Sector).filter(Sector.alias == sector_name).first()

                    security_count = 0
                    try:
                        securities = adapter.get_stock_list(sector=sector_name)
                        if securities:
                            security_count = len(securities)
                    except Exception as e:
                        logger.debug("获取板块 %s 证券数量失败: %s", sector_name, e)

                    category = get_category(sector_name)
                    market = get_market(sector_name)
                    now_iso = datetime.now().isoformat()

                    if row:
                        meta = copy.deepcopy(row.sector_meta) if row.sector_meta else {}
                        stats = dict(meta.get("stats") or {})
                        stats.update(
                            {
                                "security_count": security_count,
                                "category": category,
                                "market": market,
                                "last_sync_at": now_iso,
                                "is_active": stats.get("is_active", 1),
                            }
                        )
                        meta["stats"] = stats
                        sources = dict(meta.get("sources") or {})
                        sources[key] = {"sector_key": sector_name}
                        meta["sources"] = sources

                        needs = False
                        if row.sector_meta != meta:
                            row.sector_meta = meta
                            needs = True
                        if needs:
                            row.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        meta = {
                            "stats": {
                                "security_count": security_count,
                                "category": category,
                                "market": market,
                                "last_sync_at": now_iso,
                                "is_active": 1,
                            },
                            "sources": {key: {"sector_key": sector_name}},
                        }
                        db.add(
                            Sector(
                                name=sector_name,
                                alias=sector_name,
                                parent_id=None,
                                sector_meta=meta,
                            )
                        )
                        created_count += 1

                except Exception as e:
                    error_count += 1
                    logger.warning("处理板块 %s 失败: %s", sector_name, e)

            db.commit()

            logger.info(
                "板块同步完成: 总计 %s, 新增 %s, 更新 %s, 错误 %s",
                len(sectors),
                created_count,
                updated_count,
                error_count,
            )

            return {
                "success": True,
                "message": "同步成功",
                "total": len(sectors),
                "created": created_count,
                "updated": updated_count,
                "errors": error_count,
            }

        except Exception as e:
            db.rollback()
            logger.error("同步板块失败: %s", e)
            import traceback

            logger.error(traceback.format_exc())
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
        category: Optional[str] = None,
        market: Optional[str] = None,
        is_active: Optional[int] = None,
    ) -> List[Sector]:
        """获取板块列表（可选按 metadata.stats 过滤）。"""
        try:
            rows = db.query(Sector).order_by(Sector.alias).all()
            if category is None and market is None and is_active is None:
                return rows

            out: List[Sector] = []
            for s in rows:
                st = sector_stats(s)
                if category is not None and st.get("category") != category:
                    continue
                if market is not None:
                    if st.get("market") != market:
                        continue
                if is_active is not None:
                    if int(st.get("is_active", 1)) != int(is_active):
                        continue
                out.append(s)
            return out
        except Exception as e:
            logger.error("获取板块列表失败: %s", e)
            return []

    def get_sector_by_alias(self, db: Session, alias: str) -> Optional[Sector]:
        """根据唯一 alias 查询（与数据源侧板块键一致）。"""
        try:
            return db.query(Sector).filter(Sector.alias == alias).first()
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

    def update_sector_remark(self, db: Session, alias: str, remark: Optional[str]) -> Optional[Sector]:
        """更新板块用户备注；remark 可为 None 表示清空。"""
        row = self.get_sector_by_alias(db, alias)
        if not row:
            return None
        row.remark = remark
        db.commit()
        db.refresh(row)
        return row

    def get_sector_statistics(self, db: Session) -> Dict[str, Any]:
        """板块汇总统计（基于 metadata.stats）。"""
        try:
            rows = db.query(Sector).all()
            active_rows = [s for s in rows if int(sector_stats(s).get("is_active", 1)) == 1]
            total_securities = sum(int(sector_stats(s).get("security_count") or 0) for s in active_rows)

            category_stats: Dict[str, Dict[str, int]] = {}
            for sector in active_rows:
                st = sector_stats(sector)
                cat = st.get("category") or "其他"
                if cat not in category_stats:
                    category_stats[cat] = {"count": 0, "securities": 0}
                category_stats[cat]["count"] += 1
                category_stats[cat]["securities"] += int(st.get("security_count") or 0)

            return {
                "total_sectors": len(active_rows),
                "total_securities": total_securities,
                "category_stats": category_stats,
            }
        except Exception as e:
            logger.error("获取板块统计失败: %s", e)
            return {
                "total_sectors": 0,
                "total_securities": 0,
                "category_stats": {},
            }


sector_service = SectorService()
