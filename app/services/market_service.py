"""行情服务"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from app.services.data_source import get_default_qmt_adapter
from app.services.security_service import security_service
import logging

logger = logging.getLogger(__name__)


class MarketService:
    """行情服务"""

    def __init__(self):
        self._qmt = None

    @property
    def qmt(self):
        """懒加载 QMT 适配器，避免启动时阻塞。"""
        if self._qmt is None:
            self._qmt = get_default_qmt_adapter()
        return self._qmt

    def get_realtime_quote(self, symbols: List[str], db: Optional[Session] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            symbols: 证券代码列表，如 ['000001.SZ', '600000.SH']
            db: 数据库会话（可选，用于获取证券名称）
            
        Returns:
            实时行情字典
        """
        try:
            quotes = self.qmt.get_realtime_quote(symbols)
            if quotes is None:
                return {}
            
            # 格式化返回数据（Python 3中字符串默认是Unicode）
            result = {}
            for symbol, quote in quotes.items():
                # 如果QMT返回的名称为空，尝试从数据库获取
                name = quote.get("name", "")
                if not name and db:
                    security = security_service.get_security_by_symbol(db, symbol)
                    if security:
                        name = security.name or ""
                
                pre_close = float(quote.get("pre_close", 0))
                last_price = float(quote.get("last_price", 0))
                change = last_price - pre_close
                change_pct = (change / pre_close * 100) if pre_close > 0 else 0
                
                result[symbol] = {
                    "symbol": symbol,
                    "name": name or symbol,
                    "last_price": last_price,
                    "open": float(quote.get("open", 0)),
                    "high": float(quote.get("high", 0)),
                    "low": float(quote.get("low", 0)),
                    "pre_close": pre_close,
                    "volume": int(quote.get("volume", 0)),
                    "amount": float(quote.get("amount", 0)),
                    "change": change,
                    "change_percent": change_pct,
                    "time": quote.get("time", datetime.now().isoformat())
                }
            return result
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return {}
    
    def get_kline_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 证券代码
            period: 周期，'1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M'
            count: 数据条数
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            
        Returns:
            K线数据列表
        """
        try:
            # 转换日期格式为QMT需要的格式
            start_time = None
            end_time = None
            if start_date:
                start_time = f"{start_date} 00:00:00"
            if end_date:
                end_time = f"{end_date} 23:59:59"
            
            data = self.qmt.get_klines_data(symbol, period, count, start_time, end_time)
            if data is None:
                return []
            
            # 格式化数据
            result = []
            for item in data:
                time_str = item.get("time", "")
                if isinstance(time_str, datetime):
                    time_str = time_str.strftime("%Y-%m-%d %H:%M:%S")
                elif hasattr(time_str, 'strftime'):
                    time_str = time_str.strftime("%Y-%m-%d %H:%M:%S")
                
                result.append({
                    "time": time_str,
                    "date": time_str[:10] if len(time_str) >= 10 else time_str,
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("close", 0)),
                    "volume": int(item.get("volume", 0)),
                    "amount": float(item.get("amount", 0))
                })
            
            # 如果指定了日期范围，进行过滤
            if start_date or end_date:
                df = pd.DataFrame(result)
                if 'time' in df.columns and len(df) > 0:
                    df['time'] = pd.to_datetime(df['time'], errors='coerce')
                    if start_date:
                        df = df[df['time'] >= pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df['time'] <= pd.to_datetime(end_date)]
                    result = df.to_dict('records')
            
            return result
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []
    
    def search_stocks(self, keyword: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            db: 数据库会话（可选，优先从数据库搜索）
            
        Returns:
            股票列表
        """
        try:
            results = []
            symbols_to_fetch_name = []  # 需要获取名称的证券代码列表
            
            # 优先从数据库搜索
            if db:
                securities = security_service.search_securities(db, keyword, limit=50)
                for security in securities:
                    name = security.name
                    # 如果数据库中的名称为空或等于代码，标记需要从QMT获取
                    if not name or name == security.symbol or name.strip() == "":
                        symbols_to_fetch_name.append(security.symbol)
                        name = ""  # 暂时设为空，稍后从QMT获取
                    
                    results.append({
                        "symbol": security.symbol,
                        "name": name,
                        "market": security.market
                    })
            
            # 如果数据库没有结果，从QMT搜索（Python 3中字符串默认是Unicode）
            if not results:
                qmt_results = self.qmt.search_stocks(keyword)
                for stock in qmt_results:
                    symbol = stock.get("symbol", "")
                    name = stock.get("name", "")
                    # 如果QMT返回的名称为空，标记需要获取
                    if not name or name == symbol or name.strip() == "":
                        symbols_to_fetch_name.append(symbol)
                        name = ""
                    
                    results.append({
                        "symbol": symbol,
                        "name": name,
                        "market": stock.get("market", "")
                    })
            
            # 批量获取缺失的名称（从实时行情）
            if symbols_to_fetch_name:
                try:
                    # 分批获取，避免一次请求太多
                    batch_size = 10
                    for i in range(0, len(symbols_to_fetch_name), batch_size):
                        batch_symbols = symbols_to_fetch_name[i:i+batch_size]
                        quotes = self.qmt.get_realtime_quote(batch_symbols)
                        if quotes:
                            # 更新结果中的名称（Python 3中字符串默认是Unicode）
                            for result in results:
                                if not result.get("name") or result["name"] == result["symbol"]:
                                    symbol = result["symbol"]
                                    if symbol in quotes:
                                        quote_name = quotes[symbol].get("name", "")
                                        if quote_name and quote_name != symbol and quote_name.strip():
                                            result["name"] = quote_name
                                    
                                    # 如果还是没有名称，尝试从数据库再次获取
                                    if (not result.get("name") or result["name"] == symbol) and db:
                                        security = security_service.get_security_by_symbol(db, symbol)
                                        if security and security.name and security.name != symbol and security.name.strip():
                                            result["name"] = security.name
                except Exception as e:
                    logger.warning(f"获取证券名称失败: {e}")
            
            return results
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []


# 全局行情服务实例
market_service = MarketService()

