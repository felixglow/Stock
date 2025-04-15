"""
股票数据获取和处理模块
"""
import threading
import time
import os
from datetime import datetime, timedelta
from queue import Queue
from typing import Dict, List, Optional, Tuple

# 强制使用合适的后端
os.environ['MPLBACKEND'] = 'MacOSX'  # MacOS系统
# os.environ['MPLBACKEND'] = 'TkAgg'   # 其他系统

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests
import json

# 添加中文字体支持
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'Arial Unicode MS']  # 优先使用微软雅黑字体
plt.rcParams['axes.unicode_minus'] = False

# 常量定义
MAX_FIELDS = 32
MAX_HISTORY = 100
UPDATE_INTERVAL = 6  # 更新间隔(秒)
PLOT_WIDTH = 0.8  # K线图宽度
PLOT_WIDTH_SHADOW = 0.2  # K线图影线宽度

class Worker(threading.Thread):
    """工作线程类"""
    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue
        self.daemon = True

    def run(self):
        while True:
            func, args = self.queue.get()
            try:
                func(*args)
            finally:
                self.queue.task_done()

class Stock:
    """股票数据处理类"""
    def __init__(self, code: str, thread_num: int = 3):
        """初始化股票数据处理对象"""
        self.code = code
        self.queue = Queue()
        self.threads = [Worker(self.queue) for _ in range(thread_num)]
        for thread in self.threads:
            thread.start()

        # 数据存储
        self.price_history: Dict[str, List[float]] = {}
        self.time_history: Dict[str, List[datetime]] = {}
        self.current_name = ""
        self.current_prices: Dict[str, float] = {}
        self.change_pcts: Dict[str, float] = {}
        
        # 日K线数据
        self.daily_data: Dict[str, pd.DataFrame] = {}

    def create_figure(self):
        """创建图表"""
        # 创建图表，只包含K线图
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        
        self.fig.canvas.manager.set_window_title('股票日K线图')
        
        # 初始提示文本
        self.ax.text(0.5, 0.5, '正在加载数据...', 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   transform=self.ax.transAxes,
                   fontsize=14)

    def value_get(
        self, code: str, code_index: int
    ) -> Tuple[int, Optional[Tuple[str, float, float]]]:
        """获取股票数据"""
        try:
            url = f"http://hq.sinajs.cn/list={code}"
            response = requests.get(url, headers={
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
            })
            response.encoding = 'gbk'
            
            data_str = response.text
            if "var hq_str_" not in data_str:
                print(f"API返回格式不正确: {data_str[:100]}")
                return code_index, None
                
            # 从返回结果中提取数据字符串
            data_parts = data_str.split('="')
            if len(data_parts) < 2:
                return code_index, None
                
            data = data_parts[1].split('",')[0].split(',')
            
            if len(data) < 32:  # 确保数据完整
                print(f"数据不完整，长度为{len(data)}")
                return code_index, None
                
            name = data[0]
            yesterday_close = float(data[2])
            current_price = float(data[3])
            change = round((current_price - yesterday_close) / yesterday_close * 100, 2)
            
            return code_index, (name, current_price, change)
        except Exception as e:
            print(f"获取实时数据出错: {e}")
            return code_index, None
            
    def get_daily_k_data(self, code: str) -> pd.DataFrame:
        """获取日K线数据"""
        try:
            # 提取股票代码
            stock_code = code[2:]  # 去掉sh或sz前缀
            
            # 东方财富网API接口，提供更可靠的历史K线数据
            market = "1" if code.startswith("sh") else "0"
            url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{stock_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&end=20500101&lmt=30"
            
            print(f"请求日K线数据URL: {url}")
            
            response = requests.get(url)
            data = response.json()
            
            if 'data' not in data or data['data'] is None or 'klines' not in data['data']:
                print(f"无法获取K线数据: {json.dumps(data)[:200]}")
                return pd.DataFrame()
            
            klines = data['data']['klines']
            print(f"成功获取到{len(klines)}条K线数据记录")
            
            # 解析K线数据
            ohlc_data = []
            for line in klines:
                parts = line.split(',')
                if len(parts) >= 6:
                    date = parts[0]
                    ohlc_data.append({
                        'date': datetime.strptime(date, '%Y-%m-%d'),
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5])
                    })
            
            # 创建DataFrame
            df = pd.DataFrame(ohlc_data)
            
            if not df.empty:
                # 设置日期为索引
                df.set_index('date', inplace=True)
                print("日K线数据列:", df.columns.tolist())
                print(f"数据范围: {df.index.min()} 到 {df.index.max()}")
            
            return df
        except Exception as e:
            print(f"获取日K线数据出错: {str(e)}")
            # 返回空DataFrame
            return pd.DataFrame()

    def display_stock_info(self):
        """显示股票信息"""
        for code, price in self.current_prices.items():
            change = self.change_pcts.get(code, 0.0)
            change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
            
            # 打印股票信息到控制台
            print(f"\n{'='*50}")
            print(f"股票名称: {self.current_name}")
            print(f"当前价格: {price:.2f} ({change_str})")
            print(f"{'='*50}")
            
            if hasattr(self, 'fig') and self.fig is not None:
                try:
                    # 设置窗口标题
                    self.fig.canvas.manager.set_window_title(f"{self.current_name} - 日K线图")
                except Exception as e:
                    print(f"无法设置窗口标题: {e}")

    def plot_daily_k(self):
        """绘制日K线图"""
        if not hasattr(self, 'fig') or self.fig is None:
            self.create_figure()
            
        try:
            # 清除图表
            self.ax.clear()
            
            # 获取第一个股票代码
            if not self.price_history:
                return
                
            first_code = next(iter(self.price_history.keys()))
            
            # 如果没有日K线数据，尝试获取
            if first_code not in self.daily_data or self.daily_data[first_code].empty:
                self.daily_data[first_code] = self.get_daily_k_data(first_code)
                
            df = self.daily_data[first_code]
            
            if df.empty:
                self.ax.text(0.5, 0.5, '暂无日K线数据', horizontalalignment='center', 
                            verticalalignment='center', transform=self.ax.transAxes,
                            fontsize=14)
                self.ax.grid(True)
                return
                
            # 分离上涨和下跌数据
            up = df[df.close >= df.open]
            down = df[df.close < df.open]
            
            # 绘制上涨K线（红色）
            for idx, row in up.iterrows():
                self.ax.bar(idx, row.close-row.open, PLOT_WIDTH, bottom=row.open, color='red')
                self.ax.bar(idx, row.high-row.close, PLOT_WIDTH_SHADOW, bottom=row.close, color='red')
                self.ax.bar(idx, row.low-row.open, PLOT_WIDTH_SHADOW, bottom=row.open, color='red')
            
            # 绘制下跌K线（绿色）
            for idx, row in down.iterrows():
                self.ax.bar(idx, row.close-row.open, PLOT_WIDTH, bottom=row.open, color='green')
                self.ax.bar(idx, row.high-row.open, PLOT_WIDTH_SHADOW, bottom=row.open, color='green')
                self.ax.bar(idx, row.low-row.close, PLOT_WIDTH_SHADOW, bottom=row.close, color='green')
            
            # 设置X轴为日期格式
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))  # 每3天显示一个标签
            
            plt.xticks(rotation=45)
            
            # 设置Y轴范围
            min_price = df.low.min()
            max_price = df.high.max()
            price_range = max_price - min_price
            if price_range > 0:
                self.ax.set_ylim([min_price - price_range * 0.05, max_price + price_range * 0.05])
            
            # 添加价格信息到标题位置
            for code, price in self.current_prices.items():
                change = self.change_pcts.get(code, 0.0)
                change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
                
                # 设置价格文本颜色（只有涨跌幅的颜色变化）
                price_color = 'green' if change < 0 else ('red' if change > 0 else 'black')
                
                # 标题位置的y坐标常量
                TITLE_Y_POS = 0.96
                
                # 添加涨跌箭头
                arrow = "↑" if change > 0 else ("↓" if change < 0 else "→")
                
                # 不使用任何图表内的标题
                self.ax.set_title("")
                
                # 创建单行标题，所有内容放在一起
                self.fig.suptitle(f"{self.current_name}    {price:.2f} {arrow} {change_str}", 
                               fontsize=16, fontweight='bold', 
                               x=0.5, y=TITLE_Y_POS)
                
                # 为标题的不同部分添加不同颜色
                title_obj = self.fig.axes[0].get_title()
                self.fig.texts = []  # 清除之前的所有文本
                
                # 计算标题部分的水平位置，使其更居中
                # 使用固定间距代替基于文本长度的计算
                name_pos = 0.50  # 股票名称靠左一些
                price_pos = 0.51  # 价格靠右一些
                
                # 添加股票名称部分（黑色）
                self.fig.text(name_pos, TITLE_Y_POS, f"{self.current_name}", 
                           fontsize=16, fontweight='bold', color='black', 
                           ha='right', va='center')
                
                # 添加价格和涨跌幅部分（带颜色和箭头）
                self.fig.text(price_pos, TITLE_Y_POS, f"{price:.2f} {arrow} {change_str}", 
                           fontsize=16, fontweight='bold', color=price_color, 
                           ha='left', va='center')
            
            self.ax.set_xlabel('日期')
            self.ax.set_ylabel('价格 (元)')
            self.ax.grid(True)
            
            # 调整布局，为顶部标题留出空间
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            
        except Exception as e:
            print(f"绘制K线图出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def __add_work(self, code: str, code_index: int):
        """添加工作任务"""
        self.queue.put((self.value_get, (code, code_index)))

    def display_stocks(self, codes: List[str], interval: float = UPDATE_INTERVAL):
        """显示股票数据"""
        print("程序启动中，正在初始化...")
        print("正在准备加载数据...")
        
        for code in codes:
            self.price_history[code] = []
            self.time_history[code] = []
            
            # 初始化加载日K线数据
            try:
                print(f"初始化加载{code}的日K线数据...")
                self.daily_data[code] = self.get_daily_k_data(code)
                if self.daily_data[code].empty:
                    print(f"警告: 未能获取到{code}的日K线数据")
                else:
                    print(f"成功加载了{len(self.daily_data[code])}条日K线数据")
            except Exception as e:
                print(f"初始加载{code}日K线数据失败: {str(e)}")

        print("\n数据加载中...")
        
        # 获取实时价格数据（只获取一次）
        for i, code in enumerate(codes):
            self.__add_work(code, i)
        self.queue.join()

        # 获取并处理价格数据
        for code in codes:
            result = self.value_get(code, 0)
            if result[1]:
                _, (name, price, change) = result
                self.current_name = name
                self.current_prices[code] = price
                self.change_pcts[code] = change
                self.price_history[code].append(price)
                self.time_history[code].append(datetime.now())

        # 显示股票信息
        self.display_stock_info()
        
        print("\n准备生成K线图...")
        
        # 在绘图前创建图表
        self.create_figure()
        
        # 更新图表
        self.plot_daily_k()
        
        # 保存图表为图片文件
        try:
            filename = f"{self.current_name}_日K线图.png"
            plt.savefig(filename)
            print(f"\n图表已保存为文件: {filename}")
            print(f"请在当前目录查看该文件以查看K线图。")
        except Exception as save_error:
            print(f"保存图表时出错: {save_error}")
        
        print("\n尝试显示图表窗口...")
        print("如果窗口未显示，请查看已保存的图片文件。")
        print("按Ctrl+C终止程序。")
        
        # 尝试显示图表，阻塞直到窗口关闭
        try:
            plt.tight_layout()
            plt.show(block=True)
        except KeyboardInterrupt:
            print("\n程序已被用户终止")
        except Exception as e:
            print(f"显示图表时出错: {e}")
            print(f"请直接查看保存的图片文件: {filename}")