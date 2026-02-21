from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
import time

# 最基本连接测试
miniqmt_path = r'C:\国金证券QMT交易端\userdata_mini'
account_id = '39271919'

trader = XtQuantTrader(miniqmt_path, int(time.time()))
trader.start()

account = StockAccount(account_id, 'STOCK')
result = trader.connect()

if result == 0:
    print("连接成功！")
    
    # 获取持仓
    positions = trader.query_stock_positions(account)
    print(f"持仓数量: {len(positions)}")
    
    for pos in positions:
        print(f"股票: {pos.stock_code}, 数量: {pos.volume}")
else:
    print(f"连接失败，错误码: {result}")

trader.stop()