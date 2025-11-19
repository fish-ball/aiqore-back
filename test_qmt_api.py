"""测试QMT API，查看实际返回的数据结构"""
import sys
import os
import json
from datetime import datetime

# 添加QMT路径
qmt_path = r"C:\国金证券QMT交易端\userdata_mini\datadir"
if os.path.exists(qmt_path):
    sys.path.insert(0, qmt_path)

try:
    from xtquant import xtdata
    print("[OK] xtquant 导入成功")
except ImportError as e:
    print(f"[ERROR] xtquant 导入失败: {e}")
    print("请确保QMT客户端已安装并运行")
    sys.exit(1)

def test_get_full_tick():
    """测试获取实时行情"""
    print("\n" + "="*60)
    print("测试 get_full_tick 接口")
    print("="*60)
    
    test_symbols = ["601888.SH", "000001.SZ", "600000.SH"]
    
    try:
        quotes = xtdata.get_full_tick(test_symbols)
        print(f"\n返回类型: {type(quotes)}")
        print(f"返回数据:\n{json.dumps(quotes, indent=2, ensure_ascii=False, default=str)}")
        
        if quotes:
            print("\n详细分析:")
            for symbol in test_symbols:
                if symbol in quotes:
                    tick = quotes[symbol]
                    print(f"\n{symbol}:")
                    print(f"  类型: {type(tick)}")
                    if isinstance(tick, dict):
                        print(f"  所有字段: {list(tick.keys())}")
                        for key, value in tick.items():
                            print(f"    {key}: {value} (类型: {type(value).__name__})")
                    elif hasattr(tick, '__dict__'):
                        print(f"  所有属性: {dir(tick)}")
                        print(f"  __dict__: {tick.__dict__}")
                    else:
                        print(f"  数据: {tick}")
                else:
                    print(f"\n{symbol}: 不在返回结果中")
    except Exception as e:
        print(f"[ERROR] 调用失败: {e}")
        import traceback
        traceback.print_exc()

def test_get_market_data():
    """测试获取K线数据"""
    print("\n" + "="*60)
    print("测试 get_market_data 接口")
    print("="*60)
    
    test_symbol = "601888.SH"
    
    try:
        data = xtdata.get_market_data(
            stock_list=[test_symbol],
            period="1d",
            count=5
        )
        print(f"\n返回类型: {type(data)}")
        if data:
            print(f"返回的key: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            if isinstance(data, dict) and test_symbol in data:
                df = data[test_symbol]
                print(f"DataFrame类型: {type(df)}")
                if hasattr(df, 'head'):
                    print(f"前5行数据:\n{df.head()}")
                    print(f"列名: {list(df.columns)}")
                    print(f"数据类型:\n{df.dtypes}")
    except Exception as e:
        print(f"[ERROR] 调用失败: {e}")
        import traceback
        traceback.print_exc()

def test_get_stock_list():
    """测试获取股票列表"""
    print("\n" + "="*60)
    print("测试 get_stock_list_in_sector 接口")
    print("="*60)
    
    try:
        stocks = xtdata.get_stock_list_in_sector("沪深A股")
        print(f"\n返回类型: {type(stocks)}")
        print(f"返回数量: {len(stocks) if stocks else 0}")
        if stocks:
            print(f"前10个: {stocks[:10]}")
            # 检查是否包含601888.SH
            if "601888.SH" in stocks:
                print("[OK] 601888.SH 在列表中")
            else:
                print("[WARN] 601888.SH 不在列表中")
    except Exception as e:
        print(f"[ERROR] 调用失败: {e}")
        import traceback
        traceback.print_exc()

def test_other_apis():
    """测试其他可能的API"""
    print("\n" + "="*60)
    print("测试其他可能的API")
    print("="*60)
    
    test_symbol = "601888.SH"
    
    # 测试可能的API
    apis_to_test = [
        "get_instrument_detail",
        "get_stock_info",
        "get_instrument_list",
        "download_min_data",
    ]
    
    for api_name in apis_to_test:
        if hasattr(xtdata, api_name):
            print(f"\n找到API: {api_name}")
            try:
                func = getattr(xtdata, api_name)
                # 尝试不同的调用方式
                if api_name == "download_min_data":
                    result = func(test_symbol, period='1m', count=1)
                elif api_name == "get_instrument_detail":
                    result = func(test_symbol)
                    print(f"  返回类型: {type(result)}")
                    if isinstance(result, dict):
                        print(f"  所有字段: {list(result.keys())}")
                        for key, value in result.items():
                            print(f"    {key}: {value} (类型: {type(value).__name__})")
                    else:
                        print(f"  返回数据: {result}")
                    continue
                else:
                    result = func([test_symbol])
                
                print(f"  返回类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"  返回的key: {list(result.keys())[:5]}")
                    if test_symbol in result:
                        print(f"  {test_symbol}的数据: {result[test_symbol]}")
                elif result is not None:
                    print(f"  返回数据: {result}")
            except Exception as e:
                print(f"  调用失败: {e}")

def main():
    print("QMT API 测试工具")
    print("="*60)
    
    # 测试各个接口
    test_get_full_tick()
    test_get_market_data()
    test_get_stock_list()
    test_other_apis()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n请将上述输出结果提供给开发人员，以便调整代码。")

if __name__ == "__main__":
    main()

