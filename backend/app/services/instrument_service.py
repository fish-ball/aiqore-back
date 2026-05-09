"""标的信息服务"""
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import logging

from app.constants.exchanges import (
    MARKET_TO_EXCHANGE_CODE,
    SUFFIX_TO_EXCHANGE_CODE,
    get_exchange_def,
    normalize_exchange_code,
)
from app.libs.data_source.models.enums import InstrumentType
from app.libs.data_source.models.instrument import DataSourceInstrument
from app.models.instrument import Instrument, infer_asset_class_from_instrument_type
from app.libs.data_source.models.enums import AssetClass

logger = logging.getLogger(__name__)


def map_detail_to_instrument_type(instrument_type: str, sector: str = "") -> InstrumentType:
    """将数据源详情中的 InstrumentType 字段及板块辅助信息映射为 InstrumentType。"""
    if not instrument_type:
        if "基金" in sector:
            return InstrumentType.FUND
        if "可转债" in sector or "转债" in sector:
            return InstrumentType.BOND
        if "债" in sector:
            return InstrumentType.BOND
        if "期货" in sector:
            return InstrumentType.FUTURE
        if "期权" in sector:
            return InstrumentType.OPTION
        return InstrumentType.STOCK
    u = instrument_type.upper()
    if "CONVERTIBLE" in u:
        return InstrumentType.BOND
    if "FUTURE" in u:
        return InstrumentType.FUTURE
    if "OPTION" in u:
        return InstrumentType.OPTION
    if "ETF" in u:
        return InstrumentType.ETF
    if "LOF" in u or "FUND" in u:
        return InstrumentType.FUND
    if "BOND" in u:
        return InstrumentType.BOND
    if "INDEX" in u:
        return InstrumentType.INDEX
    if "WARRANT" in u:
        return InstrumentType.STOCK
    if "STOCK" in u:
        return InstrumentType.STOCK
    return InstrumentType.STOCK


def generate_abbreviation(name: str) -> str:
    """
    根据证券名称生成字母简写

    例如：中国中免 -> ZGZM
    """
    try:
        from pypinyin import lazy_pinyin, Style

        chinese_chars = "".join([c for c in name if "\u4e00" <= c <= "\u9fff"])
        if not chinese_chars:
            return ""

        pinyin_list = lazy_pinyin(chinese_chars, style=Style.FIRST_LETTER)
        abbreviation = "".join(pinyin_list).upper()
        return abbreviation
    except ImportError:
        logger.warning("pypinyin未安装，无法生成字母简写")
        return ""
    except Exception as e:
        logger.warning(f"生成字母简写失败: {e}")
        return ""


def resolve_exchange_code_for_instrument(
    *,
    market: str,
    detail_exchange_id: Optional[Any],
    code: str,
) -> Optional[str]:
    """
    解析标的对应的规范 exchange_code。
    优先级：详情中的交易所标识 ExchangeID（含别名）> 代码后缀 > 现货 market（SH/SZ/BJ）。
    """
    if detail_exchange_id is not None:
        canonical = normalize_exchange_code(str(detail_exchange_id).strip())
        if canonical and get_exchange_def(canonical):
            return canonical

    if code and "." in code:
        suf = code.rsplit(".", 1)[1].strip().lower()
        ex = SUFFIX_TO_EXCHANGE_CODE.get(suf)
        if ex and get_exchange_def(ex):
            return ex

    m = (market or "").strip().upper()
    if m in MARKET_TO_EXCHANGE_CODE:
        ex = MARKET_TO_EXCHANGE_CODE[m]
        if get_exchange_def(ex):
            return ex

    return None


def ensure_exchange_code_for_instrument(
    *,
    market: str,
    detail_exchange_id: Optional[Any],
    code: str,
    existing_exchange_code: Optional[str],
) -> str:
    """
    得到可写入主表的 exchange_code：先解析；否则保留已有（若在目录内）；再按现货市场与期货兜底。
    """
    resolved = resolve_exchange_code_for_instrument(
        market=market, detail_exchange_id=detail_exchange_id, code=code
    )
    if resolved:
        return resolved
    if existing_exchange_code:
        ex = normalize_exchange_code(existing_exchange_code)
        if ex and get_exchange_def(ex):
            return ex
    m = (market or "").strip().upper()
    if m in MARKET_TO_EXCHANGE_CODE:
        return MARKET_TO_EXCHANGE_CODE[m]
    if get_exchange_def("SHFE"):
        return "SHFE"
    return "SSE"


class InstrumentService:
    """标的信息服务。"""

    def _extract_field_from_detail(self, detail: Any, field: str, default=None):
        """从 detail（DataSourceInstrument 或旧版 dict）中提取与迅投键名对应的字段值"""
        if detail is None:
            return default
        if isinstance(detail, DataSourceInstrument):
            if field == "InstrumentName":
                return detail.name if detail.name else default
            if field == "InstrumentType":
                return detail.instrument_type if detail.instrument_type else default
            if field == "ExchangeID":
                return detail.exchange_id if detail.exchange_id else default
            if field == "OpenDate":
                return detail.open_date if detail.open_date is not None else default
            if field == "ExpiryDate":
                return detail.expiry_date if detail.expiry_date is not None else default
            if field == "LastPrice":
                return detail.last_price if detail.last_price is not None else default
            return default
        if isinstance(detail, dict):
            return detail.get(field, default)
        return default

    def _safe_float(self, value, default=0.0):
        """安全转换为浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _safe_datetime(self, value):
        """安全转换为日期时间"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            if isinstance(value, str):
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            return None
        except Exception:
            return None

    def update_instruments_from_data(
        self,
        db: Session,
        rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        将已获取的标的列表及详情写入数据库（不依赖具体数据源，供抽象层调用）。
        每项须含 symbol（与 code 同义）、market、sector、detail（detail 可为 None）。
        """
        created_count = 0
        updated_count = 0
        error_count = 0
        try:
            for sec_data in rows:
                code = sec_data.get("symbol")
                if not code:
                    continue
                detail = sec_data.get("detail")
                try:
                    row = db.query(Instrument).filter(Instrument.code == code).first()

                    name = self._extract_field_from_detail(detail, "InstrumentName", code)
                    market_code = sec_data.get("market", "SH" if code.endswith(".SH") else "SZ")
                    instrument_type_raw = self._extract_field_from_detail(detail, "InstrumentType", "")
                    sector = sec_data.get("sector", "")
                    inst_type = map_detail_to_instrument_type(instrument_type_raw, sector)
                    inst_type_val = inst_type.value
                    asset_class_val = infer_asset_class_from_instrument_type(inst_type).value

                    abbreviation = ""
                    if name and name != code:
                        abbreviation = generate_abbreviation(name)

                    raw_exchange_id = self._extract_field_from_detail(detail, "ExchangeID")
                    open_date = self._safe_datetime(self._extract_field_from_detail(detail, "OpenDate"))
                    expire_date = self._safe_datetime(self._extract_field_from_detail(detail, "ExpiryDate"))
                    last_price = self._safe_float(self._extract_field_from_detail(detail, "LastPrice"))
                    if last_price == 0.0:
                        last_price = None

                    fk_exchange_code = ensure_exchange_code_for_instrument(
                        market=market_code,
                        detail_exchange_id=raw_exchange_id,
                        code=code,
                        existing_exchange_code=row.exchange_code if row else None,
                    )

                    if row:
                        needs_update = False
                        if row.name != name:
                            row.name = name
                            needs_update = True
                        if row.exchange_code != fk_exchange_code:
                            row.exchange_code = fk_exchange_code
                            needs_update = True
                        if row.asset_class != asset_class_val:
                            row.asset_class = asset_class_val
                            needs_update = True
                        if row.instrument_type != inst_type_val:
                            row.instrument_type = inst_type_val
                            needs_update = True
                        if open_date is not None and row.open_date != open_date:
                            row.open_date = open_date
                            needs_update = True
                        if expire_date is not None and row.expire_date != expire_date:
                            row.expire_date = expire_date
                            needs_update = True
                        if abbreviation and row.abbreviation != abbreviation:
                            row.abbreviation = abbreviation
                            needs_update = True
                        if last_price is not None and last_price > 0:
                            if row.last_price != last_price:
                                row.last_price = last_price
                                needs_update = True
                        if needs_update:
                            row.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        row = Instrument(
                            code=code,
                            name=name,
                            exchange_code=fk_exchange_code,
                            asset_class=asset_class_val,
                            instrument_type=inst_type_val,
                            open_date=open_date,
                            expire_date=expire_date,
                            abbreviation=abbreviation or None,
                            last_price=last_price if last_price and last_price > 0 else None,
                            is_active=True,
                        )
                        db.add(row)
                        created_count += 1

                    if (created_count + updated_count) % 100 == 0:
                        db.commit()
                        logger.info(f"已处理 {created_count + updated_count} 条记录...")

                except Exception as e:
                    error_count += 1
                    logger.warning(f"处理标的 {code} 失败: {e}")
                    import traceback

                    logger.debug(traceback.format_exc())
                    continue

            db.commit()

            logger.info(f"更新完成: 总计 {len(rows)}, 新增 {created_count}, 更新 {updated_count}, 错误 {error_count}")

            return {
                "success": True,
                "message": "更新成功",
                "total": len(rows),
                "created": created_count,
                "updated": updated_count,
                "errors": error_count,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"更新标的信息失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0,
            }

    def search_instruments(self, db: Session, keyword: str, limit: int = 50) -> List[Instrument]:
        """搜索标的（代码、名称、缩写）。"""
        keyword = keyword.strip()
        if not keyword:
            return []

        keyword_upper = keyword.upper()
        conditions = [
            Instrument.code.ilike(f"%{keyword_upper}%"),
            Instrument.name.ilike(f"%{keyword}%"),
            Instrument.abbreviation.ilike(f"%{keyword_upper}%"),
        ]

        return (
            db.query(Instrument)
            .filter(Instrument.is_active.is_(True), or_(*conditions))
            .limit(limit)
            .all()
        )

    def get_instrument_by_code(self, db: Session, code: str) -> Optional[Instrument]:
        """根据标的代码查询。"""
        try:
            return db.query(Instrument).filter(Instrument.code == code).first()
        except Exception as e:
            logger.error(f"获取标的失败: {e}")
            return None

    def get_instruments_by_market(self, db: Session, market: str, limit: int = 100) -> List[Instrument]:
        """按市场后缀筛选，如 SH / SZ。"""
        try:
            m = (market or "").strip().upper()
            if not m:
                return []
            suffix = f".{m}"
            return (
                db.query(Instrument)
                .filter(Instrument.code.endswith(suffix), Instrument.is_active.is_(True))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"获取标的列表失败: {e}")
            return []

    def filter_by_market_layer(self, query, layer: AssetClass):
        """
        按 AssetClass 过滤。
        EQUITY / FUTURE / OPTION：按 instrument_type 桶（与行情缓存三大类一致）。
        其余：按 instruments.asset_class 列与枚举 value 匹配。
        """
        if layer == AssetClass.FUTURE:
            return query.filter(Instrument.instrument_type == InstrumentType.FUTURE.value)
        if layer == AssetClass.OPTION:
            return query.filter(Instrument.instrument_type == InstrumentType.OPTION.value)
        if layer == AssetClass.EQUITY:
            return query.filter(
                Instrument.instrument_type.notin_([InstrumentType.FUTURE.value, InstrumentType.OPTION.value])
            )
        if layer == AssetClass.COMMODITY:
            return query.filter(Instrument.asset_class == AssetClass.COMMODITY.value)
        if layer == AssetClass.DEBT:
            return query.filter(Instrument.asset_class == AssetClass.DEBT.value)
        return query.filter(Instrument.asset_class == layer.value)


instrument_service = InstrumentService()
