"""行情服务"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from app.services.qmt_service import qmt_service
import logging

logger = logging.getLogger(__name__)


class MarketService:
    """行情服务"""
    
    def __init__(self):
        self.qmt = qmt_service
    
    def get_realtime_quote(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            symbols: 证券代码列表，如 ['000001.SZ', '600000.SH']
            
        Returns:
            实时行情字典
        """
        try:
            quotes = self.qmt.get_realtime_quote(symbols)
            if quotes is None:
                return {}
            
            # 格式化返回数据
            result = {}
            for symbol, quote in quotes.items():
                result[symbol] = {
                    "symbol": quote.get("symbol"),
                    "name": quote.get("name", ""),
                    "last_price": float(quote.get("last_price", 0)),
                    "open": float(quote.get("open", 0)),
                    "high": float(quote.get("high", 0)),
                    "low": float(quote.get("low", 0)),
                    "pre_close": float(quote.get("pre_close", 0)),
                    "volume": int(quote.get("volume", 0)),
                    "amount": float(quote.get("amount", 0)),
                    "change": float(quote.get("last_price", 0)) - float(quote.get("pre_close", 0)),
                    "change_pct": (
                        (float(quote.get("last_price", 0)) - float(quote.get("pre_close", 0))) 
                        / float(quote.get("pre_close", 1)) * 100
                        if quote.get("pre_close", 0) > 0 else 0
                    ),
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
            data = self.qmt.get_market_data(symbol, period, count)
            if data is None:
                return []
            
            # 格式化数据
            result = []
            for item in data:
                result.append({
                    "time": item.get("time", ""),
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
                df['time'] = pd.to_datetime(df['time'])
                if start_date:
                    df = df[df['time'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['time'] <= pd.to_datetime(end_date)]
                result = df.to_dict('records')
            
            return result
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            
        Returns:
            股票列表
        """
        try:
            # TODO: 实现股票搜索功能
            # 可以通过QMT API或本地数据库搜索
            return []
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []


# 全局行情服务实例
market_service = MarketService()

