"""更新证券基础信息脚本"""
import sys
from app.database import SessionLocal
from app.services.security_service import security_service

def main():
    """主函数"""
    db = SessionLocal()
    try:
        print("开始更新证券基础信息...")
        print("=" * 50)
        
        # 更新全部市场
        result = security_service.update_securities_from_qmt(db, market=None)
        
        print(f"更新结果:")
        print(f"  总计: {result['total']} 只")
        print(f"  新增: {result['created']} 只")
        print(f"  更新: {result['updated']} 只")
        print(f"  状态: {'成功' if result['success'] else '失败'}")
        
        if not result['success']:
            print(f"  错误: {result.get('message', '未知错误')}")
            sys.exit(1)
        
        print("=" * 50)
        print("更新完成！")
        
    except Exception as e:
        print(f"更新失败: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

