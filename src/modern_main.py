"""
现代界面主程序入口
"""
import argparse
import sys

from .modern_stock import ModernStock


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="现代界面股票数据查询程序")
    parser.add_argument(
        "-c", "--codes",
        help="股票代码列表,使用逗号分隔",
        type=str,
        required=True
    )
    parser.add_argument(
        "-i", "--interval",
        help="数据更新间隔(秒)[已废弃，保留兼容性]",
        type=float,
        default=6.0
    )
    parser.add_argument(
        "-t", "--threads",
        help="线程数量",
        type=int,
        default=3
    )
    return parser.parse_args()

def check_code_format(code: str) -> bool:
    """检查股票代码格式是否正确"""
    if not code.startswith(('sh', 'sz')):
        return False
    
    # 检查数字部分
    num_part = code[2:]
    if not num_part.isdigit() or len(num_part) != 6:
        return False
    
    return True

def main():
    """主函数"""
    args = parse_args()
    codes = args.codes.split(",")
    
    # 检查股票代码格式
    invalid_codes = [code for code in codes if not check_code_format(code)]
    if invalid_codes:
        print(f"错误: 以下股票代码格式不正确: {', '.join(invalid_codes)}")
        print("格式要求: sh开头表示上海股票,sz开头表示深圳股票,后接6位数字")
        sys.exit(1)
        
    print(f"正在查询股票: {', '.join(codes)}")
    
    # 初始化ModernStock对象并显示股票数据
    try:
        stock = ModernStock(codes[0], args.threads)
        stock.display_stocks(codes)
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()