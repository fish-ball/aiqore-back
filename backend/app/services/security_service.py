"""证券信息服务"""
from typing import List, Dict, Any, Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import logging
from app.models.security import (
    Security,
    SecuritySourceQmt,
    SecurityTradingRules,
    SecurityQuoteSnapshot,
    SecurityStock,
    SecurityFund,
    SecurityBond,
    SecurityConvertible,
    SecurityOption,
    SecurityFuture,
)
from app.services.data_source import get_default_qmt_adapter
from app.models.security import SecurityType
from app.services.security_exchange_resolve import ensure_exchange_code_for_security

logger = logging.getLogger(__name__)

# 写入类型扩展子表时使用的细分类（与 QMT InstrumentType 对应）
_ExtensionKind = Optional[Literal["stock", "fund", "bond", "convertible", "option", "future"]]


def generate_abbreviation(name: str) -> str:
    """
    根据证券名称生成字母简写
    
    例如：中国中免 -> ZGZM
    
    Args:
        name: 证券名称（中文）
        
    Returns:
        字母简写（大写）
    """
    try:
        from pypinyin import lazy_pinyin, Style
        
        # 过滤掉非中文字符（如数字、字母、标点等）
        chinese_chars = ''.join([c for c in name if '\u4e00' <= c <= '\u9fff'])
        if not chinese_chars:
            return ""
        
        # 获取每个字的拼音首字母
        pinyin_list = lazy_pinyin(chinese_chars, style=Style.FIRST_LETTER)
        # 组合成简写并转为大写
        abbreviation = ''.join(pinyin_list).upper()
        return abbreviation
    except ImportError:
        logger.warning("pypinyin未安装，无法生成字母简写")
        return ""
    except Exception as e:
        logger.warning(f"生成字母简写失败: {e}")
        return ""


class SecurityService:
    """证券信息服务"""

    def __init__(self):
        self._qmt = None

    @property
    def qmt(self):
        """懒加载 QMT 适配器，避免启动时阻塞。"""
        if self._qmt is None:
            self._qmt = get_default_qmt_adapter()
        return self._qmt

    def _map_instrument_to_extension_kind(self, instrument_type: str, sector: str = "") -> _ExtensionKind:
        """
        解析用于写入类型扩展子表的细分类（stock/fund/bond/convertible/option/future）。
        返回 None 表示不写子表（与原逻辑中指数、权证一致）。
        """
        if not instrument_type:
            if "基金" in sector:
                return "fund"
            if "可转债" in sector or "转债" in sector:
                return "convertible"
            if "债" in sector:
                return "bond"
            if "期货" in sector:
                return "future"
            if "期权" in sector:
                return "option"
            return "stock"
        u = instrument_type.upper()
        for key, ext in (
            ("CONVERTIBLE", "convertible"),
            ("FUTURE", "future"),
            ("OPTION", "option"),
            ("ETF", "fund"),
            ("LOF", "fund"),
            ("FUND", "fund"),
            ("BOND", "bond"),
            ("INDEX", None),
            ("WARRANT", None),
            ("STOCK", "stock"),
        ):
            if key in u:
                return ext
        return "stock"

    def _map_instrument_type_to_security_type(self, instrument_type: str, sector: str = "") -> SecurityType:
        """
        将 QMT 的 InstrumentType（及板块辅助信息）映射为证券大类 SecurityType。
        """
        ext = self._map_instrument_to_extension_kind(instrument_type, sector)
        if ext == "future":
            return SecurityType.Future
        if ext == "option":
            return SecurityType.Option
        return SecurityType.Equity
    
    def _extract_field_from_detail(self, detail: Dict[str, Any], field: str, default=None):
        """从 detail 字典中提取字段值"""
        if not detail or not isinstance(detail, dict):
            return default
        return detail.get(field, default)
    
    def _safe_float(self, value, default=0.0):
        """安全转换为浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value, default=0):
        """安全转换为整数"""
        if value is None:
            return default
        try:
            return int(value)
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
                # 尝试多种日期格式
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            return None
        except Exception:
            return None
    
    def update_securities_from_data(
        self,
        db: Session,
        securities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        将已获取的证券列表及详情写入数据库（不依赖具体数据源，供抽象层调用）。
        每项须含 symbol、market、sector、detail（detail 可为 None）。
        """
        created_count = 0
        updated_count = 0
        error_count = 0
        try:
            for sec_data in securities:
                symbol = sec_data.get("symbol")
                if not symbol:
                    continue
                detail = sec_data.get("detail")
                try:
                    # 查询是否已存在
                    security = db.query(Security).filter(Security.symbol == symbol).first()
                    
                    # 提取基本信息
                    name = self._extract_field_from_detail(detail, "InstrumentName", symbol)
                    market_code = sec_data.get("market", "SH" if symbol.endswith(".SH") else "SZ")
                    instrument_type = self._extract_field_from_detail(detail, "InstrumentType", "")
                    sector = sec_data.get("sector", "")
                    security_category = self._map_instrument_type_to_security_type(instrument_type, sector)
                    security_type = security_category.value
                    ext_kind = self._map_instrument_to_extension_kind(instrument_type, sector)
                    
                    # 生成字母简写
                    abbreviation = ""
                    if name and name != symbol:
                        abbreviation = generate_abbreviation(name)
                    
                    # 提取所有原始数据字段（QMT 交易所代码写入 source_qmt.exchange_id 字符串列）
                    qmt_exchange_code = self._extract_field_from_detail(detail, "ExchangeID")
                    product_id = self._extract_field_from_detail(detail, "ProductID")
                    currency_id = self._extract_field_from_detail(detail, "CurrencyID")
                    tick_size = self._safe_float(self._extract_field_from_detail(detail, "TickSize"))
                    lot_size = self._safe_int(self._extract_field_from_detail(detail, "LotSize"))
                    price_tick = self._safe_float(self._extract_field_from_detail(detail, "PriceTick"))
                    upper_limit = self._safe_float(self._extract_field_from_detail(detail, "UpperLimit"))
                    lower_limit = self._safe_float(self._extract_field_from_detail(detail, "LowerLimit"))
                    pre_settlement_price = self._safe_float(self._extract_field_from_detail(detail, "PreSettlementPrice"))
                    pre_close_price = self._safe_float(self._extract_field_from_detail(detail, "PreClosePrice"))
                    open_price = self._safe_float(self._extract_field_from_detail(detail, "OpenPrice"))
                    last_price = self._safe_float(self._extract_field_from_detail(detail, "LastPrice"))
                    volume = self._safe_int(self._extract_field_from_detail(detail, "Volume"))
                    amount = self._safe_float(self._extract_field_from_detail(detail, "Amount"))
                    open_interest = self._safe_int(self._extract_field_from_detail(detail, "OpenInterest"))
                    strike_price = self._safe_float(self._extract_field_from_detail(detail, "StrikePrice"))
                    expiry_date = self._safe_datetime(self._extract_field_from_detail(detail, "ExpiryDate"))
                    underlying_symbol = self._extract_field_from_detail(detail, "UnderlyingSymbol")
                    conversion_ratio = self._safe_float(self._extract_field_from_detail(detail, "ConversionRatio"))
                    interest_rate = self._safe_float(self._extract_field_from_detail(detail, "InterestRate"))
                    maturity_date = self._safe_datetime(self._extract_field_from_detail(detail, "MaturityDate"))
                    face_value = self._safe_float(self._extract_field_from_detail(detail, "FaceValue"))
                    fund_type = self._extract_field_from_detail(detail, "FundType")
                    nav = self._safe_float(self._extract_field_from_detail(detail, "NAV"))
                    accumulated_nav = self._safe_float(self._extract_field_from_detail(detail, "AccumulatedNAV"))
                    
                    # 保存完整的原始数据到 JSON 字段
                    raw_data = detail if detail and isinstance(detail, dict) else None

                    fk_exchange_code = ensure_exchange_code_for_security(
                        market=market_code,
                        qmt_exchange_id=qmt_exchange_code,
                        symbol=symbol,
                        existing_exchange_code=security.exchange_code if security else None,
                    )

                    if security:
                        needs_update = False
                        if security.name != name:
                            security.name = name
                            needs_update = True
                        if security.market != market_code:
                            security.market = market_code
                            needs_update = True
                        if security.security_type != security_type:
                            security.security_type = security_type
                            needs_update = True
                        if security.exchange_code != fk_exchange_code:
                            security.exchange_code = fk_exchange_code
                            needs_update = True
                        if abbreviation and security.abbreviation != abbreviation:
                            security.abbreviation = abbreviation
                            needs_update = True
                        if needs_update:
                            security.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        security = Security(
                            symbol=symbol,
                            name=name,
                            market=market_code,
                            exchange_code=fk_exchange_code,
                            security_type=security_type,
                            is_active=1,
                            abbreviation=abbreviation,
                        )
                        db.add(security)
                        db.flush()
                        created_count += 1

                    sid = security.id

                    # 数据源外表 QMT
                    source_qmt = db.query(SecuritySourceQmt).filter(SecuritySourceQmt.security_id == sid).first()
                    if source_qmt:
                        source_qmt.instrument_type = instrument_type
                        source_qmt.exchange_id = qmt_exchange_code
                        source_qmt.product_id = product_id
                        source_qmt.currency_id = currency_id
                        source_qmt.raw_data = raw_data
                        source_qmt.updated_at = datetime.now()
                    else:
                        db.add(SecuritySourceQmt(
                            security_id=sid,
                            instrument_type=instrument_type,
                            exchange_id=qmt_exchange_code,
                            product_id=product_id,
                            currency_id=currency_id,
                            raw_data=raw_data,
                        ))

                    # 交易规则
                    tr = db.query(SecurityTradingRules).filter(SecurityTradingRules.security_id == sid).first()
                    if tr:
                        tr.tick_size = tick_size if tick_size and tick_size > 0 else None
                        tr.lot_size = lot_size if lot_size and lot_size > 0 else None
                        tr.price_tick = price_tick if price_tick and price_tick > 0 else None
                    else:
                        db.add(SecurityTradingRules(
                            security_id=sid,
                            tick_size=tick_size if tick_size and tick_size > 0 else None,
                            lot_size=lot_size if lot_size and lot_size > 0 else None,
                            price_tick=price_tick if price_tick and price_tick > 0 else None,
                        ))

                    # 行情快照
                    qs = db.query(SecurityQuoteSnapshot).filter(SecurityQuoteSnapshot.security_id == sid).first()
                    if qs:
                        qs.upper_limit = upper_limit if upper_limit and upper_limit > 0 else None
                        qs.lower_limit = lower_limit if lower_limit and lower_limit > 0 else None
                        qs.pre_settlement_price = pre_settlement_price if pre_settlement_price and pre_settlement_price > 0 else None
                        qs.pre_close_price = pre_close_price if pre_close_price and pre_close_price > 0 else None
                        qs.open_price = open_price if open_price and open_price > 0 else None
                        qs.last_price = last_price if last_price and last_price > 0 else None
                        qs.volume = volume if volume and volume > 0 else None
                        qs.amount = amount if amount and amount > 0 else None
                        qs.open_interest = open_interest if open_interest and open_interest > 0 else None
                    else:
                        db.add(SecurityQuoteSnapshot(
                            security_id=sid,
                            upper_limit=upper_limit if upper_limit and upper_limit > 0 else None,
                            lower_limit=lower_limit if lower_limit and lower_limit > 0 else None,
                            pre_settlement_price=pre_settlement_price if pre_settlement_price and pre_settlement_price > 0 else None,
                            pre_close_price=pre_close_price if pre_close_price and pre_close_price > 0 else None,
                            open_price=open_price if open_price and open_price > 0 else None,
                            last_price=last_price if last_price and last_price > 0 else None,
                            volume=volume if volume and volume > 0 else None,
                            amount=amount if amount and amount > 0 else None,
                            open_interest=open_interest if open_interest and open_interest > 0 else None,
                        ))

                    # 按 InstrumentType 细分类写入扩展表（主表 security_type 仅存 Equity/Future/Option）
                    if ext_kind == "stock":
                        if not db.query(SecurityStock).filter(SecurityStock.security_id == sid).first():
                            db.add(SecurityStock(security_id=sid))
                    elif ext_kind == "fund":
                        ext = db.query(SecurityFund).filter(SecurityFund.security_id == sid).first()
                        if ext:
                            ext.fund_type = fund_type
                            ext.nav = nav if nav and nav > 0 else None
                            ext.accumulated_nav = accumulated_nav if accumulated_nav and accumulated_nav > 0 else None
                        else:
                            db.add(SecurityFund(security_id=sid, fund_type=fund_type, nav=nav if nav and nav > 0 else None, accumulated_nav=accumulated_nav if accumulated_nav and accumulated_nav > 0 else None))
                    elif ext_kind == "bond":
                        ext = db.query(SecurityBond).filter(SecurityBond.security_id == sid).first()
                        if ext:
                            ext.interest_rate = interest_rate if interest_rate and interest_rate > 0 else None
                            ext.maturity_date = maturity_date
                            ext.face_value = face_value if face_value and face_value > 0 else None
                        else:
                            db.add(SecurityBond(security_id=sid, interest_rate=interest_rate if interest_rate and interest_rate > 0 else None, maturity_date=maturity_date, face_value=face_value if face_value and face_value > 0 else None))
                    elif ext_kind == "convertible":
                        ext = db.query(SecurityConvertible).filter(SecurityConvertible.security_id == sid).first()
                        if ext:
                            ext.underlying_symbol = underlying_symbol
                            ext.conversion_ratio = conversion_ratio if conversion_ratio and conversion_ratio > 0 else None
                        else:
                            db.add(SecurityConvertible(security_id=sid, underlying_symbol=underlying_symbol, conversion_ratio=conversion_ratio if conversion_ratio and conversion_ratio > 0 else None))
                    elif ext_kind == "option":
                        ext = db.query(SecurityOption).filter(SecurityOption.security_id == sid).first()
                        if ext:
                            ext.strike_price = strike_price if strike_price and strike_price > 0 else None
                            ext.expiry_date = expiry_date
                            ext.underlying_symbol = underlying_symbol
                        else:
                            db.add(SecurityOption(security_id=sid, strike_price=strike_price if strike_price and strike_price > 0 else None, expiry_date=expiry_date, underlying_symbol=underlying_symbol))
                    elif ext_kind == "future":
                        ext = db.query(SecurityFuture).filter(SecurityFuture.security_id == sid).first()
                        if ext:
                            ext.expiry_date = expiry_date
                        else:
                            db.add(SecurityFuture(security_id=sid, expiry_date=expiry_date))
                    
                    # 每100条提交一次，避免事务过大
                    if (created_count + updated_count) % 100 == 0:
                        db.commit()
                        logger.info(f"已处理 {created_count + updated_count} 条记录...")
                        
                except Exception as e:
                    error_count += 1
                    logger.warning(f"处理证券 {symbol} 失败: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
            
            # 最终提交
            db.commit()
            
            logger.info(f"更新完成: 总计 {len(securities)}, 新增 {created_count}, 更新 {updated_count}, 错误 {error_count}")
            
            return {
                "success": True,
                "message": "更新成功",
                "total": len(securities),
                "created": created_count,
                "updated": updated_count,
                "errors": error_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新证券信息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0
            }

    def search_securities(
        self, 
        db: Session, 
        keyword: str, 
        limit: int = 50
    ) -> List[Security]:
        """
        搜索证券
        
        Args:
            db: 数据库会话
            keyword: 搜索关键词（支持中文、代码、拼音）
            limit: 返回数量限制
            
        Returns:
            证券列表
        """
        keyword = keyword.strip()
        if not keyword:
            return []
        
        keyword_upper = keyword.upper()
        conditions = []
        
        # 代码搜索（不区分大小写）
        conditions.append(Security.symbol.ilike(f"%{keyword_upper}%"))
        
        # 名称搜索（支持中文）
        conditions.append(Security.name.ilike(f"%{keyword}%"))
        
        # 拼音搜索（不区分大小写）
        conditions.append(Security.pinyin.ilike(f"%{keyword_upper}%"))
        
        securities = (
            db.query(Security)
            .filter(Security.is_active == 1, or_(*conditions))
            .limit(limit)
            .all()
        )
        
        return securities
    
    def get_security_by_symbol(self, db: Session, symbol: str) -> Optional[Security]:
        """
        根据代码获取证券信息
        
        Args:
            db: 数据库会话
            symbol: 证券代码
            
        Returns:
            证券对象
        """
        try:
            return db.query(Security).filter(Security.symbol == symbol).first()
        except Exception as e:
            logger.error(f"获取证券信息失败: {e}")
            return None
    
    def get_securities_by_market(
        self, 
        db: Session, 
        market: str, 
        limit: int = 100
    ) -> List[Security]:
        """
        根据市场获取证券列表
        
        Args:
            db: 数据库会话
            market: 市场代码
            limit: 返回数量限制
            
        Returns:
            证券列表
        """
        try:
            return db.query(Security).filter(
                Security.market == market,
                Security.is_active == 1
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"获取证券列表失败: {e}")
            return []


# 全局证券服务实例
security_service = SecurityService()

