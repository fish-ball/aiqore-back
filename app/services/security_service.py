"""证券信息服务"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import logging
from app.models.security import Security
from app.services.qmt_service import qmt_service

logger = logging.getLogger(__name__)


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
        self.qmt = qmt_service
    
    def _map_instrument_type_to_security_type(self, instrument_type: str, sector: str = "") -> str:
        """
        将 QMT 的 InstrumentType 映射到我们的 security_type
        
        Args:
            instrument_type: QMT 的标的类型
            sector: 板块名称（辅助判断）
            
        Returns:
            证券类型字符串
        """
        if not instrument_type:
            # 根据板块判断
            if "基金" in sector:
                return "基金"
            elif "债" in sector:
                return "债券"
            elif "期货" in sector:
                return "期货"
            elif "期权" in sector:
                return "期权"
            else:
                return "股票"
        
        instrument_type_upper = instrument_type.upper()
        
        # 映射表
        type_mapping = {
            "STOCK": "股票",
            "FUND": "基金",
            "ETF": "基金",
            "LOF": "基金",
            "BOND": "债券",
            "CONVERTIBLE": "可转债",
            "FUTURE": "期货",
            "OPTION": "期权",
            "INDEX": "指数",
            "WARRANT": "权证",
        }
        
        for key, value in type_mapping.items():
            if key in instrument_type_upper:
                return value
        
        return "股票"  # 默认
    
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
    
    def update_securities_from_qmt(
        self, 
        db: Session, 
        market: Optional[str] = None,
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从QMT更新证券基础信息（支持所有类型的标的）
        
        Args:
            db: 数据库会话
            market: 市场代码，'SH' 或 'SZ'，None表示全部
            sector: 板块名称，如果指定则只同步该板块的证券
            
        Returns:
            更新结果统计
        """
        try:
            # 如果指定了板块，只获取该板块的证券
            if sector:
                try:
                    from xtquant import xtdata
                    sector_securities = xtdata.get_stock_list_in_sector(sector)
                    if not sector_securities:
                        return {
                            "success": False,
                            "message": f"板块 '{sector}' 未获取到证券列表",
                            "total": 0,
                            "created": 0,
                            "updated": 0,
                            "errors": 0
                        }
                    # 转换为统一格式
                    securities = []
                    for symbol in sector_securities:
                        if isinstance(symbol, str):
                            sec_market = "SH" if symbol.endswith(".SH") else "SZ" if symbol.endswith(".SZ") else "BJ" if symbol.endswith(".BJ") else "SH"
                            if market is None or sec_market == market:
                                securities.append({
                                    "symbol": symbol,
                                    "market": sec_market,
                                    "sector": sector
                                })
                except Exception as e:
                    logger.error(f"获取板块 '{sector}' 证券列表失败: {e}")
                    return {
                        "success": False,
                        "message": f"获取板块 '{sector}' 证券列表失败: {str(e)}",
                        "total": 0,
                        "created": 0,
                        "updated": 0,
                        "errors": 0
                    }
            else:
                # 获取所有类型的证券列表
                securities = self.qmt.get_stock_list(market)
            
            if not securities:
                return {
                    "success": False,
                    "message": "未获取到证券列表，请检查QMT连接",
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "errors": 0
                }
            
            logger.info(f"开始更新证券信息，共 {len(securities)} 只证券")
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            # 处理每个证券
            for idx, sec_data in enumerate(securities):
                symbol = sec_data.get("symbol")
                if not symbol:
                    continue
                
                try:
                    # 获取标的详细信息
                    detail = None
                    try:
                        from xtquant import xtdata
                        if hasattr(xtdata, 'get_instrument_detail'):
                            detail = xtdata.get_instrument_detail(symbol)
                    except Exception as e:
                        logger.debug(f"获取 {symbol} 详细信息失败: {e}")
                    
                    # 查询是否已存在
                    security = db.query(Security).filter(Security.symbol == symbol).first()
                    
                    # 提取基本信息
                    name = self._extract_field_from_detail(detail, "InstrumentName", symbol)
                    market_code = sec_data.get("market", "SH" if symbol.endswith(".SH") else "SZ")
                    instrument_type = self._extract_field_from_detail(detail, "InstrumentType", "")
                    sector = sec_data.get("sector", "")
                    security_type = self._map_instrument_type_to_security_type(instrument_type, sector)
                    
                    # 生成字母简写
                    abbreviation = ""
                    if name and name != symbol:
                        abbreviation = generate_abbreviation(name)
                    
                    # 提取所有原始数据字段
                    exchange_id = self._extract_field_from_detail(detail, "ExchangeID")
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
                    
                    if security:
                        # 更新现有记录
                        needs_update = False
                        
                        # 更新基本信息
                        if security.name != name:
                            security.name = name
                            needs_update = True
                        if security.market != market_code:
                            security.market = market_code
                            needs_update = True
                        if security.security_type != security_type:
                            security.security_type = security_type
                            needs_update = True
                        if abbreviation and security.abbreviation != abbreviation:
                            security.abbreviation = abbreviation
                            needs_update = True
                        
                        # 更新原始数据字段
                        if security.instrument_type != instrument_type:
                            security.instrument_type = instrument_type
                            needs_update = True
                        if security.exchange_id != exchange_id:
                            security.exchange_id = exchange_id
                            needs_update = True
                        if security.product_id != product_id:
                            security.product_id = product_id
                            needs_update = True
                        if security.currency_id != currency_id:
                            security.currency_id = currency_id
                            needs_update = True
                        if security.tick_size != tick_size:
                            security.tick_size = tick_size
                            needs_update = True
                        if security.lot_size != lot_size:
                            security.lot_size = lot_size
                            needs_update = True
                        if security.price_tick != price_tick:
                            security.price_tick = price_tick
                            needs_update = True
                        if security.upper_limit != upper_limit:
                            security.upper_limit = upper_limit
                            needs_update = True
                        if security.lower_limit != lower_limit:
                            security.lower_limit = lower_limit
                            needs_update = True
                        if security.pre_settlement_price != pre_settlement_price:
                            security.pre_settlement_price = pre_settlement_price
                            needs_update = True
                        if security.pre_close_price != pre_close_price:
                            security.pre_close_price = pre_close_price
                            needs_update = True
                        if security.open_price != open_price:
                            security.open_price = open_price
                            needs_update = True
                        if security.last_price != last_price:
                            security.last_price = last_price
                            needs_update = True
                        if security.volume != volume:
                            security.volume = volume
                            needs_update = True
                        if security.amount != amount:
                            security.amount = amount
                            needs_update = True
                        if security.open_interest != open_interest:
                            security.open_interest = open_interest
                            needs_update = True
                        if security.strike_price != strike_price:
                            security.strike_price = strike_price
                            needs_update = True
                        if security.expiry_date != expiry_date:
                            security.expiry_date = expiry_date
                            needs_update = True
                        if security.underlying_symbol != underlying_symbol:
                            security.underlying_symbol = underlying_symbol
                            needs_update = True
                        if security.conversion_ratio != conversion_ratio:
                            security.conversion_ratio = conversion_ratio
                            needs_update = True
                        if security.interest_rate != interest_rate:
                            security.interest_rate = interest_rate
                            needs_update = True
                        if security.maturity_date != maturity_date:
                            security.maturity_date = maturity_date
                            needs_update = True
                        if security.face_value != face_value:
                            security.face_value = face_value
                            needs_update = True
                        if security.fund_type != fund_type:
                            security.fund_type = fund_type
                            needs_update = True
                        if security.nav != nav:
                            security.nav = nav
                            needs_update = True
                        if security.accumulated_nav != accumulated_nav:
                            security.accumulated_nav = accumulated_nav
                            needs_update = True
                        if security.raw_data != raw_data:
                            security.raw_data = raw_data
                            needs_update = True
                        
                        if needs_update:
                            security.updated_at = datetime.now()
                            updated_count += 1
                    else:
                        # 创建新记录
                        security = Security(
                            symbol=symbol,
                            name=name,
                            market=market_code,
                            security_type=security_type,
                            is_active=1,
                            abbreviation=abbreviation,
                            instrument_type=instrument_type,
                            exchange_id=exchange_id,
                            product_id=product_id,
                            currency_id=currency_id,
                            tick_size=tick_size if tick_size > 0 else None,
                            lot_size=lot_size if lot_size > 0 else None,
                            price_tick=price_tick if price_tick > 0 else None,
                            upper_limit=upper_limit if upper_limit > 0 else None,
                            lower_limit=lower_limit if lower_limit > 0 else None,
                            pre_settlement_price=pre_settlement_price if pre_settlement_price > 0 else None,
                            pre_close_price=pre_close_price if pre_close_price > 0 else None,
                            open_price=open_price if open_price > 0 else None,
                            last_price=last_price if last_price > 0 else None,
                            volume=volume if volume > 0 else None,
                            amount=amount if amount > 0 else None,
                            open_interest=open_interest if open_interest > 0 else None,
                            strike_price=strike_price if strike_price > 0 else None,
                            expiry_date=expiry_date,
                            underlying_symbol=underlying_symbol,
                            conversion_ratio=conversion_ratio if conversion_ratio > 0 else None,
                            interest_rate=interest_rate if interest_rate > 0 else None,
                            maturity_date=maturity_date,
                            face_value=face_value if face_value > 0 else None,
                            fund_type=fund_type,
                            nav=nav if nav > 0 else None,
                            accumulated_nav=accumulated_nav if accumulated_nav > 0 else None,
                            raw_data=raw_data
                        )
                        db.add(security)
                        created_count += 1
                    
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
        
        securities = db.query(Security).filter(
            Security.is_active == 1,
            or_(*conditions)
        ).limit(limit).all()
        
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

