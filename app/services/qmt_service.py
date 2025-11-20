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
        获取股票列表
        
        Args:
            market: 市场代码，'SH' 或 'SZ'，None表示全部
            
        Returns:
            股票列表，每个元素包含 symbol, name 等信息
        """
        if not XT_QUANT_AVAILABLE:
            logger.error("xtquant不可用")
            return []
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            stocks = []
            
            # 尝试多种方式获取股票列表
            try:
                # 方法1: 获取板块股票列表
                all_stocks = xtdata.get_stock_list_in_sector("沪深A股")
                if all_stocks:
                    for stock in all_stocks:
                        if isinstance(stock, str):
                            stock_market = "SH" if stock.endswith(".SH") else "SZ"
                            if market is None or stock_market == market:
                                stocks.append({
                                    "symbol": stock,
                                    "market": stock_market
                                })
            except Exception as e1:
                logger.warning(f"方法1获取股票列表失败: {e1}")
                try:
                    # 方法2: 通过下载数据获取（获取最近有交易的股票）
                    # 这是一个备用方案，可能不完整
                    test_symbols = ["000001.SZ", "600000.SH", "000002.SZ", "600001.SH"]
                    for symbol in test_symbols:
                        stock_market = "SH" if symbol.endswith(".SH") else "SZ"
                        if market is None or stock_market == market:
                            stocks.append({
                                "symbol": symbol,
                                "market": stock_market
                            })
                except Exception as e2:
                    logger.error(f"方法2也失败: {e2}")
            
            # 如果仍然没有数据，返回空列表
            if not stocks:
                logger.warning("未能获取到股票列表，可能需要手动配置或检查QMT连接")
            
            # Python 3中字符串和pandas DataFrame默认已经是Unicode，无需编码转换
            logger.info(f"获取到 {len(stocks)} 只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
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
