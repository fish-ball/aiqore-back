"""QMT连接服务"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import os
import sys
from app.config import settings

logger = logging.getLogger(__name__)
# 启用DEBUG日志以便查看QMT返回的数据结构
# logger.setLevel(logging.DEBUG)

# 尝试导入xtquant
try:
    # 添加QMT路径到系统路径
    if os.path.exists(settings.XT_QUANT_PATH):
        qmt_path = os.path.join(settings.XT_QUANT_PATH, "datadir")
        if os.path.exists(qmt_path):
            sys.path.insert(0, qmt_path)
    
    from xtquant import xtdata
    from xtquant.xttype import StockAccount
    XT_QUANT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"xtquant未安装或不可用: {e}")
    XT_QUANT_AVAILABLE = False
    xtdata = None


class QMTService:
    """国金QMT服务"""
    
    def __init__(self):
        self.host = settings.QMT_HOST
        self.port = settings.QMT_PORT
        self.user = settings.QMT_USER
        self.password = settings.QMT_PASSWORD
        self.xt_quant_path = settings.XT_QUANT_PATH
        self.xt_quant_acct = settings.XT_QUANT_ACCT
        self.connected = False
        self._client = None
    
    def connect(self) -> bool:
        """
        连接QMT
        
        Returns:
            是否连接成功
        """
        if not XT_QUANT_AVAILABLE:
            logger.error("xtquant未安装或不可用，请确保QMT客户端已安装")
            return False
        
        try:
            # xtdata不需要显式连接，直接使用即可
            # 但可以测试一下是否能正常调用
            self._client = xtdata
            self.connected = True
            logger.info(f"QMT服务已就绪，路径: {self.xt_quant_path}")
            return True
        except Exception as e:
            logger.error(f"连接QMT失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开QMT连接"""
        self.connected = False
        self._client = None
        logger.info("已断开QMT连接")
    
    def get_stock_list(self, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有类型的证券列表（股票、基金、债券、期货、期权等）
        
        Args:
            market: 市场代码，'SH' 或 'SZ'，None表示全部
            
        Returns:
            证券列表，每个元素包含 symbol, market, instrument_type 等信息
        """
        if not XT_QUANT_AVAILABLE:
            logger.error("xtquant不可用")
            return []
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            all_securities = []
            seen_symbols = set()  # 用于去重
            
            # 方法1: 尝试动态获取所有可用板块列表
            sectors = []
            try:
                if hasattr(xtdata, 'get_sector_list'):
                    all_sectors = xtdata.get_sector_list()
                    if all_sectors:
                        sectors = list(all_sectors)
                        logger.info(f"动态获取到 {len(sectors)} 个板块")
            except Exception as e:
                logger.debug(f"动态获取板块列表失败: {e}")
            
            # 如果动态获取失败，使用预定义的板块列表（使用 MiniQMT 实际支持的板块名称）
            if not sectors:
                sectors = [
                    "沪深A股",      # A股股票
                    "沪深B股",      # B股股票
                    "沪深ETF",      # 所有ETF基金（包含深市和沪市）
                    "深市ETF",      # 深市ETF基金
                    "沪市ETF",      # 沪市ETF基金
                    "沪深基金",     # 所有基金（包含ETF、LOF等）
                    "深市基金",     # 深市基金
                    "沪市基金",     # 沪市基金
                    "沪深转债",     # 可转换债券
                    "沪深债券",     # 所有债券
                    "沪市债券",     # 沪市债券
                    "沪深指数",     # 指数
                    "沪市指数",     # 沪市指数
                    "创业板",       # 创业板股票
                    "上证A股",      # 上证A股
                    "上证B股",      # 上证B股
                    "上证期权",     # 上证期权
                    "上证转债",     # 上证转债
                ]
                logger.info(f"使用预定义板块列表，共 {len(sectors)} 个板块")
            
            # 方法2: 通过板块获取证券列表
            for sector in sectors:
                try:
                    securities = xtdata.get_stock_list_in_sector(sector)
                    if securities:
                        for sec in securities:
                            if isinstance(sec, str) and sec not in seen_symbols:
                                # 判断市场
                                if sec.endswith(".SH"):
                                    sec_market = "SH"
                                elif sec.endswith(".SZ"):
                                    sec_market = "SZ"
                                elif sec.endswith(".BJ"):
                                    sec_market = "BJ"  # 北交所
                                else:
                                    sec_market = "SH"  # 默认
                                
                                # 根据市场过滤
                                if market is None or sec_market == market:
                                    all_securities.append({
                                        "symbol": sec,
                                        "market": sec_market,
                                        "sector": sector
                                    })
                                    seen_symbols.add(sec)
                except Exception as e:
                    logger.debug(f"获取板块 '{sector}' 失败: {e}")
                    continue
            
            # 方法3: 尝试通过 get_instrument_list 获取所有标的（如果API支持）
            try:
                if hasattr(xtdata, 'get_instrument_list'):
                    # 尝试获取所有交易所的标的
                    exchanges = ['SSE', 'SZSE', 'BSE']  # 上交所、深交所、北交所
                    for exchange in exchanges:
                        try:
                            instruments = xtdata.get_instrument_list(exchange)
                            if instruments:
                                for inst in instruments:
                                    if isinstance(inst, str) and inst not in seen_symbols:
                                        if inst.endswith(".SH"):
                                            inst_market = "SH"
                                        elif inst.endswith(".SZ"):
                                            inst_market = "SZ"
                                        elif inst.endswith(".BJ"):
                                            inst_market = "BJ"
                                        else:
                                            inst_market = "SH"
                                        
                                        if market is None or inst_market == market:
                                            all_securities.append({
                                                "symbol": inst,
                                                "market": inst_market,
                                                "sector": "全部标的"
                                            })
                                            seen_symbols.add(inst)
                        except Exception as e:
                            logger.debug(f"获取交易所 {exchange} 标的列表失败: {e}")
                            continue
            except Exception as e:
                logger.debug(f"使用 get_instrument_list 失败: {e}")
            
            # 方法4: 如果仍然没有数据，尝试获取一些常见标的作为示例
            if not all_securities:
                logger.warning("未能通过板块获取证券列表，尝试备用方法...")
                # 备用方案：尝试获取一些常见标的
                test_symbols = [
                    "000001.SZ", "600000.SH",  # A股
                    "510300.SH", "159919.SZ",  # ETF
                    "110001.SH", "127003.SZ",  # 可转债
                ]
                for symbol in test_symbols:
                    if symbol not in seen_symbols:
                        symbol_market = "SH" if symbol.endswith(".SH") else "SZ"
                        if market is None or symbol_market == market:
                            all_securities.append({
                                "symbol": symbol,
                                "market": symbol_market,
                                "sector": "示例标的"
                            })
                            seen_symbols.add(symbol)
            
            logger.info(f"获取到 {len(all_securities)} 只证券（去重后）")
            return all_securities
            
        except Exception as e:
            logger.error(f"获取证券列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息
        
        Args:
            symbol: 股票代码，如 '000001.SZ'
            
        Returns:
            股票信息字典
        """
        if not XT_QUANT_AVAILABLE:
            return None
        
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # 获取股票信息
            # 注意：xtquant的API可能不同，需要根据实际API调整
            info = {
                "symbol": symbol,
                "name": symbol,  # 默认使用代码，后续可以通过其他方式获取名称
                "market": "SH" if symbol.endswith(".SH") else "SZ"
            }
            
            # 尝试获取更多信息
            # 可以通过行情接口获取名称等信息
            return info
            
        except Exception as e:
            logger.error(f"获取股票信息失败 {symbol}: {e}")
            return None
    
    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账户信息
        
        Args:
            account_id: 账户ID
            
        Returns:
            账户信息字典
        """
        if not XT_QUANT_AVAILABLE:
            return None
        
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # TODO: 实际调用QMT API获取账户信息
            # 需要使用xttrader模块
            return {
                "account_id": account_id,
                "balance": 100000.0,
                "available": 50000.0,
                "frozen": 0.0,
                "market_value": 50000.0,
                "total_asset": 100000.0
            }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return None
    
    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        获取持仓信息
        
        Args:
            account_id: 账户ID
            
        Returns:
            持仓列表
        """
        if not XT_QUANT_AVAILABLE:
            return []
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            # TODO: 实际调用QMT API获取持仓
            return []
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            return []
    
    def get_market_data(
        self, 
        symbol: str, 
        period: str = "1d", 
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取行情数据
        
        Args:
            symbol: 证券代码，如 '000001.SZ'
            period: 周期，如 '1m', '5m', '1d'
            count: 数据条数
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            行情数据列表
        """
        if not XT_QUANT_AVAILABLE:
            return None
        
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # 下载历史数据
            data = xtdata.get_market_data(
                stock_list=[symbol],
                period=period,
                count=count,
                start_time=start_time,
                end_time=end_time
            )
            
            if not data or symbol not in data:
                return []
            
            # 转换为标准格式
            # pandas DataFrame在Python 3中默认使用Unicode，无需编码转换
            result = []
            df = data[symbol]
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    time_val = row.get("time", "")
                    result.append({
                        "time": time_val,
                        "date": str(time_val)[:10] if hasattr(time_val, "__str__") else "",
                        "open": float(row.get("open", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "close": float(row.get("close", 0)),
                        "volume": int(row.get("volume", 0)),
                        "amount": float(row.get("amount", 0))
                    })
            
            # pandas DataFrame在Python 3中默认使用Unicode，无需编码转换
            return result
        except Exception as e:
            logger.error(f"获取行情数据失败 {symbol}: {e}")
            return None
    
    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        获取实时行情
        
        Args:
            symbols: 证券代码列表
            
        Returns:
            实时行情字典，key为证券代码
        """
        if not XT_QUANT_AVAILABLE:
            return None
        
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # 获取实时行情（注意：get_full_tick不返回名称）
            # Python 3中字典的字符串值默认已经是Unicode，无需编码转换
            quotes = xtdata.get_full_tick(symbols)
            
            # 批量获取股票名称（使用get_instrument_detail）
            names = {}
            if hasattr(xtdata, 'get_instrument_detail'):
                for symbol in symbols:
                    try:
                        detail = xtdata.get_instrument_detail(symbol)
                        # Python 3中字典的字符串值默认已经是Unicode，无需编码转换
                        if detail and isinstance(detail, dict):
                            instrument_name = detail.get("InstrumentName", "")
                            if instrument_name:
                                names[symbol] = instrument_name
                    except Exception as e:
                        logger.debug(f"获取 {symbol} 名称失败: {e}")
            
            result = {}
            for symbol in symbols:
                # 从get_instrument_detail获取名称
                name = names.get(symbol, "")
                
                if quotes and symbol in quotes:
                    tick = quotes[symbol]
                    
                    # 获取价格数据（根据实际测试结果，字段名是lastPrice, lastClose等）
                    if isinstance(tick, dict):
                        last_price = float(tick.get("lastPrice", 0))
                        open_price = float(tick.get("open", 0))
                        high = float(tick.get("high", 0))
                        low = float(tick.get("low", 0))
                        pre_close = float(tick.get("lastClose", 0))  # 注意：QMT返回的是lastClose，不是preClose
                        volume = int(tick.get("volume", 0))
                        amount = float(tick.get("amount", 0))
                    else:
                        # 如果不是字典，尝试其他方式
                        last_price = open_price = high = low = pre_close = 0.0
                        volume = 0
                        amount = 0.0
                        logger.warning(f"未知的tick类型: {type(tick)}")
                    
                    result[symbol] = {
                        "symbol": symbol,
                        "name": name,
                        "last_price": last_price,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "pre_close": pre_close,
                        "volume": volume,
                        "amount": amount,
                        "time": datetime.now().isoformat()
                    }
                else:
                    # 如果没有实时行情，返回空数据
                    result[symbol] = {
                        "symbol": symbol,
                        "name": name,  # 即使没有行情，也尝试返回名称
                        "last_price": 0.0,
                        "open": 0.0,
                        "high": 0.0,
                        "low": 0.0,
                        "pre_close": 0.0,
                        "volume": 0,
                        "amount": 0.0,
                        "time": datetime.now().isoformat()
                    }
            
            return result
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            
        Returns:
            股票列表
        """
        if not XT_QUANT_AVAILABLE:
            return []
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            # 获取所有股票
            all_stocks = self.get_stock_list()
            
            # 过滤匹配的股票
            results = []
            keyword_upper = keyword.upper()
            matched_symbols = []
            
            for stock in all_stocks:
                symbol = stock.get("symbol", "")
                # 匹配代码
                if keyword_upper in symbol.upper():
                    matched_symbols.append(symbol)
                    results.append({
                        "symbol": symbol,
                        "name": "",  # 先设为空，稍后批量获取
                        "market": stock.get("market", "")
                    })
            
            # 批量获取匹配股票的名称（使用get_instrument_detail）
            if matched_symbols and XT_QUANT_AVAILABLE and hasattr(xtdata, 'get_instrument_detail'):
                try:
                    for symbol in matched_symbols:
                        try:
                            detail = xtdata.get_instrument_detail(symbol)
                            # Python 3中字典的字符串值默认已经是Unicode，无需编码转换
                            if detail and isinstance(detail, dict):
                                instrument_name = detail.get("InstrumentName", "")
                                if instrument_name:
                                    # 更新对应结果的名称
                                    for result in results:
                                        if result["symbol"] == symbol:
                                            result["name"] = instrument_name
                                            break
                        except Exception as e:
                            logger.debug(f"获取 {symbol} 名称失败: {e}")
                except Exception as e:
                    logger.warning(f"批量获取股票名称失败: {e}")
            
            return results[:50]  # 限制返回50条
            
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []


# 全局QMT服务实例
qmt_service = QMTService()
