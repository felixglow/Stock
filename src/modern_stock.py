"""
现代化股票界面数据获取和处理模块
参考了主流金融App的设计理念
"""
from datetime import datetime, timedelta
import json
import os
import random
import threading
import time
from queue import Queue
from typing import Dict, List, Optional, Tuple

import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import requests
from scipy.interpolate import make_interp_spline

# 强制使用合适的后端
os.environ['MPLBACKEND'] = 'MacOSX'  # MacOS系统
# os.environ['MPLBACKEND'] = 'TkAgg'   # 其他系统

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

class ModernStock:
    """现代股票数据处理类 - 参考主流股票App的界面设计"""
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
        self.stock_info = {}
        
        # 日K线数据
        self.daily_data: Dict[str, pd.DataFrame] = {}
        
        # 背景颜色和图表样式
        self.bg_color = '#f5f5f5'  # 浅灰色背景
        self.grid_color = '#e0e0e0'  # 网格线颜色
        self.text_color = '#333333'  # 暗灰色文本
        self.up_color = '#ff5d52'
        self.down_color = '#00b07c'

        # 图表相关属性
        self.fig = None
        self.ax = None
        self.infobox_ax = None
        self.text_elements = []
        self.price_text = None
        self.title_text = None
        self.timeframe_ax = None
        self.active_timeframe = "1天"
        self.current_timeframe = "daily"  # 初始化时间周期为日K

    def create_figure(self):
        """创建现代风格图表"""
        # 创建图表和布局
        self.fig = plt.figure(figsize=(12, 8), facecolor=self.bg_color)
        gs = GridSpec(7, 1, height_ratios=[1, 0.3, 0.7, 8, 0.3, 0.3, 3], hspace=0.05)
        
        # 初始化高亮区域存储列表
        self.highlight_area = []
        
        # 顶部标题区域
        self.title_ax = self.fig.add_subplot(gs[0, 0], facecolor=self.bg_color)
        self.title_ax.axis('off')
        
        # 次级标题区域（显示交易所和货币单位）
        self.subtitle_ax = self.fig.add_subplot(gs[1, 0], facecolor=self.bg_color)
        self.subtitle_ax.axis('off')
        
        # 时间周期选择区域 - 移到K线图上方
        self.timeframe_ax = self.fig.add_subplot(gs[2, 0], facecolor=self.bg_color)
        self.timeframe_ax.axis('off')
        
        # 主K线图区域
        self.ax = self.fig.add_subplot(gs[3, 0], facecolor=self.bg_color)
        
        # 空白分隔区域
        self.spacer_ax = self.fig.add_subplot(gs[5, 0], facecolor=self.bg_color)
        self.spacer_ax.axis('off')
        
        # 底部股票详细信息表格区域
        self.details_ax = self.fig.add_subplot(gs[6, 0], facecolor=self.bg_color)
        self.details_ax.axis('off')
        
        # 设置窗口标题
        self.fig.canvas.manager.set_window_title('股票K线图 - 现代界面')
        
        # 初始提示文本
        self.ax.text(0.5, 0.5, '正在加载数据...', 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   transform=self.ax.transAxes,
                   fontsize=14, color=self.text_color)

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
            open_price = float(data[1])
            yesterday_close = float(data[2])
            current_price = float(data[3])
            high_price = float(data[4])
            low_price = float(data[5])
            volume = float(data[8])
            turnover = float(data[9])
            
            change = round((current_price - yesterday_close) / yesterday_close * 100, 2)
            
            # 存储更多股票信息用于显示
            self.stock_info = {
                'name': name,
                'price': current_price,
                'change': change,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'prev_close': yesterday_close,
                'volume': volume,
                'turnover': turnover,
                'code': code
            }
            
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

    def display_stock_header(self):
        """显示股票标题和信息"""
        if not self.stock_info:
            return
            
        # 清空当前标题区域
        self.title_ax.clear()
        self.title_ax.axis('off')
        self.subtitle_ax.clear()
        self.subtitle_ax.axis('off')
        
        name = self.stock_info['name']
        price = self.stock_info['price']
        change = self.stock_info['change']
        change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
        arrow = "↑" if change > 0 else ("↓" if change < 0 else "→")
        
        # 价格颜色
        price_color = self.up_color if change > 0 else (self.down_color if change < 0 else 'black')
        
        # 左侧显示股票名称（大号粗体）
        self.title_ax.text(0.02, 0.5, name, fontsize=28, fontweight='bold', 
                         color='black', ha='left', va='center')
                         
        # 拼音/英文名称移至名称下方，不再显示在标题区域
        
        # 右侧显示价格 - 位置调整为距离右侧更远
        self.title_ax.text(0.75, 0.5, f"{price:.2f}", fontsize=28, 
                          fontweight='bold', color=price_color, 
                          ha='right', va='center')
        
        # 右侧显示涨跌幅 - 位置对应调整
        self.title_ax.text(0.76, 0.15, f"{change_str}", fontsize=14, 
                          color=price_color, ha='left', va='center')
        
        # 将"收盘"标记移至价格左侧
        self.title_ax.text(0.65, 0.5, "收盘", fontsize=12, 
                         color='gray', ha='right', va='center')
        
        # 底部显示交易所和货币单位
        market = "深圳" if self.code.startswith('sz') else "上海"
        self.subtitle_ax.text(0.02, 0.5, f"{market} · CNY", fontsize=12, 
                            color='gray', ha='left', va='center')
        
        # 控制台打印信息
        print(f"\n{'='*50}")
        print(f"股票名称: {name}")
        print(f"当前价格: {price:.2f} ({change_str})")
        print(f"{'='*50}")

    def display_timeframe_buttons(self):
        """显示时间周期选择按钮"""
        if self.timeframe_ax is None:
            return
            
        self.timeframe_ax.clear()
        self.timeframe_ax.axis('off')
        
        timeframes = ["1天", "1周", "1个月", "3个月", "6个月", "年初至今", "1年", "2年", "5年", "10年", "全部"]
        btn_width = 1 / len(timeframes)
        
        # 获取当前活跃的时间周期
        active_timeframe = getattr(self, 'active_timeframe', "1天")
        
        # 先绘制底部背景条
        background = FancyBboxPatch(
            (0, 0.2), 1.0, 0.6,
            boxstyle=f"round,pad=0.02,rounding_size=0.05",
            facecolor='#e8e8e8',
            edgecolor='none',
            alpha=1,
            transform=self.timeframe_ax.transAxes,
            zorder=0
        )
        self.timeframe_ax.add_patch(background)
        
        # 修改间距以避免文本重叠
        for i, tf in enumerate(timeframes):
            # 调整按钮位置，增加间距
            x_start = i * btn_width
            btn_width_adjusted = btn_width * 0.9  # 缩小按钮宽度，留出间隙
            
            # 当前选中的按钮高亮显示
            if tf == active_timeframe:
                # 创建圆角矩形作为按钮背景
                rect = FancyBboxPatch(
                    (x_start+0.005, 0.25), 
                    btn_width_adjusted-0.01, 0.5,
                    boxstyle=f"round,pad=0.02,rounding_size=0.2",
                    facecolor='white',
                    edgecolor='none',
                    alpha=1,
                    transform=self.timeframe_ax.transAxes,
                    zorder=1
                )
                self.timeframe_ax.add_patch(rect)
                color = 'black'
                fontweight = 'bold'
            else:
                # 为其他按钮添加鼠标悬停效果的视觉暗示
                rect = FancyBboxPatch(
                    (x_start+0.005, 0.25), 
                    btn_width_adjusted-0.01, 0.5,
                    boxstyle=f"round,pad=0.02,rounding_size=0.2",
                    facecolor='#e8e8e8',
                    edgecolor='none',
                    alpha=0,  # 透明，仅作为视觉提示
                    transform=self.timeframe_ax.transAxes,
                    zorder=1
                )
                self.timeframe_ax.add_patch(rect)
                color = 'gray'
                fontweight = 'normal'
            
            # 按钮文本字体大小调整
            font_size = 8 if len(tf) > 3 else 9
            
            # 添加文本标签
            self.timeframe_ax.text(x_start+btn_width/2, 0.5, tf, 
                                  fontsize=font_size, ha='center', va='center', 
                                  color=color, fontweight=fontweight,
                                  transform=self.timeframe_ax.transAxes,
                                  zorder=2)
                                  
        # 添加互动提示（仅作为视觉效果，实际功能需要事件处理）
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        
    def _on_hover(self, event):
        """鼠标悬停效果（仅视觉效果）"""
        # 实际实现需与GUI框架集成
        pass
        
    def _on_click(self, event):
        """点击按钮效果（实际功能实现）"""
        if not hasattr(self, 'timeframe_ax') or self.timeframe_ax is None:
            return
            
        if event.inaxes == self.timeframe_ax:
            # 获取点击的坐标
            x_pos = event.xdata
            
            # 计算点击的是哪个按钮
            timeframes = ["1天", "1周", "1个月", "3个月", "6个月", "年初至今", "1年", "2年", "5年", "10年", "全部"]
            btn_width = 1 / len(timeframes)
            selected_index = int(x_pos / btn_width)
            
            if 0 <= selected_index < len(timeframes):
                selected_timeframe = timeframes[selected_index]
                print(f"选择了时间周期: {selected_timeframe}")
                
                # 加载相应周期的数据
                self.load_timeframe_data(selected_timeframe)
                
                # 重新显示时间周期按钮，更新高亮显示
                self.active_timeframe = selected_timeframe
                self.display_timeframe_buttons()
                
                # 更新图表
                self.plot_daily_k()
                
                # 刷新图表
                self.fig.canvas.draw()
    
    def load_timeframe_data(self, timeframe):
        """加载对应时间周期的数据"""
        if not self.stock_info:
            return
            
        # 获取第一个股票代码
        first_code = next(iter(self.price_history.keys()))
        
        # 根据选择的时间周期获取不同的数据
        try:
            # 设置日期范围
            end_date = datetime.now()
            
            if timeframe == "1天":
                # 日内分时数据（模拟，实际应使用分时API）
                print(f"加载{first_code}的分时数据")
                # 获取当天的日K数据
                df = self.get_daily_k_data(first_code)
                
                # 创建模拟的分时数据（每5分钟一个数据点）
                now = datetime.now()
                today_start = datetime(now.year, now.month, now.day, 9, 30)  # 交易开始时间9:30
                today_end = datetime(now.year, now.month, now.day, 15, 0)   # 交易结束时间15:00
                
                # 计算当天的开盘价和昨收价
                if not df.empty:
                    today_open = df.iloc[-1]['open']
                    yesterday_close = df.iloc[-2]['close'] if len(df) > 1 else df.iloc[-1]['open']
                    today_close = self.current_prices[first_code]
                    today_high = df.iloc[-1]['high']
                    today_low = df.iloc[-1]['low']
                else:
                    # 如果没有数据，则使用当前价格模拟
                    today_open = self.current_prices[first_code] * 0.98
                    yesterday_close = self.current_prices[first_code] * 0.97
                    today_close = self.current_prices[first_code]
                    today_high = today_close * 1.02
                    today_low = today_open * 0.98
                
                # 生成交易时间序列（上午9:30-11:30，下午13:00-15:00，每5分钟一个点）
                trading_times = []
                current_time = today_start
                while current_time <= datetime(now.year, now.month, now.day, 11, 30):
                    trading_times.append(current_time)
                    current_time += timedelta(minutes=5)
                
                current_time = datetime(now.year, now.month, now.day, 13, 0)
                while current_time <= today_end:
                    trading_times.append(current_time)
                    current_time += timedelta(minutes=5)
                
                # 生成价格数据（在开盘价和收盘价之间模拟波动）
                intraday_data = []
                price_range = today_high - today_low
                for i, t in enumerate(trading_times):
                    # 根据时间生成一个合理的价格波动
                    progress = i / (len(trading_times) - 1) if len(trading_times) > 1 else 0.5
                    # 添加一些随机波动，但保持整体趋势
                    random_factor = 0.5 + random.random()  # 0.5到1.5之间的随机数
                    if today_close > today_open:
                        # 上涨趋势
                        price = today_open + progress * (today_close - today_open) * random_factor
                    else:
                        # 下跌趋势
                        price = today_open - progress * (today_open - today_close) * random_factor
                    
                    # 确保价格在当日最高价和最低价之间
                    price = max(min(price, today_high), today_low)
                    
                    intraday_data.append({
                        'date': t,
                        'open': price * 0.998,
                        'close': price,
                        'high': price * 1.002,
                        'low': price * 0.997,
                        'volume': random.randint(100000, 1000000)
                    })
                
                # 创建分时数据DataFrame
                intraday_df = pd.DataFrame(intraday_data)
                if not intraday_df.empty:
                    intraday_df.set_index('date', inplace=True)
                    print(f"生成了{len(intraday_df)}个5分钟分时数据点")
                    print(f"分时数据范围: {intraday_df.index.min().strftime('%H:%M')} 到 {intraday_df.index.max().strftime('%H:%M')}")
                
                self.daily_data[first_code] = intraday_df
                self.current_timeframe = "intraday"
                
            elif timeframe == "1周":
                # 过去7天数据，使用半小时的粒度
                start_date = end_date - timedelta(days=7)
                print(f"加载{first_code}的1周数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                # 获取每日K线数据
                daily_df = self.get_daily_k_data(first_code).loc[start_date:]
                
                # 创建半小时粒度数据
                half_hour_data = []
                
                # 对每一天创建半小时数据点
                for day, row in daily_df.iterrows():
                    day_start = datetime(day.year, day.month, day.day, 9, 30)
                    day_end = datetime(day.year, day.month, day.day, 15, 0)
                    
                    # 交易时段分别为9:30-11:30和13:00-15:00
                    current_time = day_start
                    while current_time <= datetime(day.year, day.month, day.day, 11, 30):
                        half_hour_data.append({
                            'date': current_time,
                            'open': row['open'] * (0.995 + 0.01 * random.random()),
                            'close': row['close'] * (0.995 + 0.01 * random.random()),
                            'high': row['high'] * (0.998 + 0.004 * random.random()),
                            'low': row['low'] * (0.998 + 0.004 * random.random()),
                            'volume': row['volume'] / 16 * (0.8 + 0.4 * random.random())
                        })
                        current_time += timedelta(minutes=30)
                    
                    current_time = datetime(day.year, day.month, day.day, 13, 0)
                    while current_time <= day_end:
                        half_hour_data.append({
                            'date': current_time,
                            'open': row['open'] * (0.995 + 0.01 * random.random()),
                            'close': row['close'] * (0.995 + 0.01 * random.random()),
                            'high': row['high'] * (0.998 + 0.004 * random.random()),
                            'low': row['low'] * (0.998 + 0.004 * random.random()),
                            'volume': row['volume'] / 16 * (0.8 + 0.4 * random.random())
                        })
                        current_time += timedelta(minutes=30)
                
                # 创建分时数据DataFrame
                half_hour_df = pd.DataFrame(half_hour_data)
                if not half_hour_df.empty:
                    half_hour_df.set_index('date', inplace=True)
                    print(f"生成了{len(half_hour_df)}个半小时数据点覆盖7天")
                    print(f"数据范围: {half_hour_df.index.min()} 到 {half_hour_df.index.max()}")
                    self.daily_data[first_code] = half_hour_df
                else:
                    # 如果生成失败，使用原始的日K线数据
                    self.daily_data[first_code] = daily_df
                
                self.current_timeframe = "weekly"
                
            elif timeframe == "1个月":
                # 过去30天数据
                start_date = end_date - timedelta(days=30)
                print(f"加载{first_code}的1个月数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=30)
                self.current_timeframe = "monthly"
                
            elif timeframe == "3个月":
                # 过去90天数据
                start_date = end_date - timedelta(days=90)
                print(f"加载{first_code}的3个月数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=90)
                self.current_timeframe = "3month"
                
            elif timeframe == "6个月":
                # 过去180天数据
                start_date = end_date - timedelta(days=180)
                print(f"加载{first_code}的6个月数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=180)
                self.current_timeframe = "6month"
                
            elif timeframe == "年初至今":
                # 当年年初至今数据
                start_date = datetime(end_date.year, 1, 1)
                print(f"加载{first_code}的年初至今数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, start_date=start_date)
                self.current_timeframe = "ytd"
                
            elif timeframe == "1年":
                # 过去365天数据
                start_date = end_date - timedelta(days=365)
                print(f"加载{first_code}的1年数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=365)
                self.current_timeframe = "1year"
                
            elif timeframe == "2年":
                # 过去730天数据
                start_date = end_date - timedelta(days=730)
                print(f"加载{first_code}的2年数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=730)
                self.current_timeframe = "2year"
                
            elif timeframe == "5年":
                # 过去1825天数据
                start_date = end_date - timedelta(days=1825)
                print(f"加载{first_code}的5年数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=1825)
                self.current_timeframe = "5year"
                
            elif timeframe == "10年":
                # 过去3650天数据
                start_date = end_date - timedelta(days=3650)
                print(f"加载{first_code}的10年数据，从{start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=3650)
                self.current_timeframe = "10year"
                
            elif timeframe == "全部":
                # 所有历史数据
                print(f"加载{first_code}的全部历史数据")
                self.daily_data[first_code] = self.get_k_data_by_period(first_code, days=10000)  # 很大的天数，获取尽可能多的数据
                self.current_timeframe = "all"
                
        except Exception as e:
            print(f"加载{timeframe}周期数据出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def get_k_data_by_period(self, code, days=None, start_date=None):
        """根据时间周期获取K线数据"""
        try:
            # 提取股票代码
            stock_code = code[2:]  # 去掉sh或sz前缀
            
            # 设置市场代码
            market = "1" if code.startswith("sh") else "0"
            
            # 根据日期范围设置URL
            if days:
                # 使用天数参数
                lmt = min(days, 5000)  # API限制，避免请求过大
            else:
                # 默认获取30天数据
                lmt = 30
                
            # 东方财富网API接口
            url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{stock_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&end=20500101&lmt={lmt}"
            
            print(f"请求K线数据URL: {url}")
            
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
                
                # 如果指定了开始日期，筛选数据
                if start_date:
                    df = df[df.index >= start_date]
                
                print(f"数据范围: {df.index.min()} 到 {df.index.max()}")
            
            return df
        except Exception as e:
            print(f"获取特定周期K线数据出错: {str(e)}")
            # 返回空DataFrame
            return pd.DataFrame()

    def display_stock_details(self):
        """显示股票详细信息表格"""
        if not self.stock_info or self.details_ax is None:
            return
            
        # 清空当前详情区域
        self.details_ax.clear()
        self.details_ax.axis('off')
        
        # 获取股票信息
        info = self.stock_info
        
        # 计算表格位置和尺寸
        left_items = [
            ('今日开盘价', f"{info.get('open', 0):.2f}"),
            ('今日最高价', f"{info.get('high', 0):.2f}"),
            ('今日最低价', f"{info.get('low', 0):.2f}"),
            ('成交量', f"{int(info.get('volume', 0)/10000)}万"),
            ('市盈率', f"{482.11:.2f}"),
            ('市值', f"{1003}亿")
        ]
        
        right_items = [
            ('52周最高价', f"{59.37:.2f}"),
            ('52周最低价', f"{32.66:.2f}"),
            ('平均成交量', f"{5630}万"),
            ('收益率', f"{0.21}%"),
            ('贝塔系数', f"{0.72}"),
            ('每股收益', f"{0.09}")
        ]
        
        # 绘制表格项目
        for i, (label, value) in enumerate(left_items):
            y_pos = 0.85 - i * 0.15
            # 标签
            self.details_ax.text(0.02, y_pos, label, fontsize=12, 
                              color='gray', ha='left', va='center')
            # 值
            self.details_ax.text(0.48, y_pos, value, fontsize=12, 
                              color='black', ha='right', va='center', 
                              fontweight='bold')
        
        for i, (label, value) in enumerate(right_items):
            y_pos = 0.85 - i * 0.15
            # 标签
            self.details_ax.text(0.52, y_pos, label, fontsize=12, 
                              color='gray', ha='left', va='center')
            # 值
            self.details_ax.text(0.98, y_pos, value, fontsize=12, 
                              color='black', ha='right', va='center',
                              fontweight='bold')
        
        # 添加分隔线
        self.spacer_ax.axhline(y=0.5, color='#dddddd', linestyle='-', linewidth=1)

    def plot_daily_k(self):
        """绘制现代风格日K线图"""
        if not hasattr(self, 'fig') or self.fig is None:
            self.create_figure()
            
        try:
            # 清除K线图区域
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
                           fontsize=14, color=self.text_color)
                return
            
            # 区分是否为分时数据
            is_intraday = self.current_timeframe == "intraday"
            
            # 计算合适的显示间隔，根据数据点数量动态调整
            if is_intraday:
                # 分时数据的间隔设置
                if len(df) <= 12:  # 分时数据通常不会太多
                    interval = 1  # 每个半小时点都显示
                else:
                    interval = 2  # 每小时显示一次
            else:
                # 日K线数据的间隔设置 - 减少标签数量，避免重叠
                if len(df) <= 5:
                    interval = 1  # 数据点很少时每天都显示
                elif len(df) <= 10:
                    interval = 2  # 适当的间隔
                elif len(df) <= 20:
                    interval = 4  # 增加间隔避免重叠
                elif len(df) <= 40:
                    interval = 8  # 更大间隔
                else:
                    interval = max(len(df) // 6, 1)  # 动态计算，确保最多显示6个标签
            
            # 选择要显示的点的索引
            tick_indices = list(range(0, len(df), interval))
            # 确保最后一个点也被显示
            if len(df) - 1 not in tick_indices and len(df) > 0:
                tick_indices.append(len(df) - 1)
            
            # 创建用于点击和悬停事件的空数据点集合，以便后续添加
            self.price_points = []
            
            if is_intraday:
                # 绘制分时图（每半小时一个点）
                line, = self.ax.plot(range(len(df)), df['close'], color='#1E88E5', linewidth=2)
                
                # 创建散点，但初始时不可见，用于鼠标悬停效果
                scatter = self.ax.scatter([], [], s=80, color='#1E88E5', alpha=0, zorder=10)
                self.hover_scatter = scatter
                self.price_line = line
                
                # 设置X轴刻度和标签
                self.ax.set_xticks(tick_indices)
                time_labels = [idx.strftime('%H:%M') for idx in df.index]
                self.ax.set_xticklabels([time_labels[i] for i in tick_indices], rotation=45)
                
                # 移除分时图标题
                pass
            else:
                # 将K线图改为折线图以匹配示例图片的风格
                # 直接使用交易日索引绘制，确保所有点都是实际交易日
                line, = self.ax.plot(range(len(df)), df['close'], color='#1E88E5', linewidth=2)
                
                # 创建散点，但初始时不可见，用于鼠标悬停效果
                scatter = self.ax.scatter([], [], s=80, color='#1E88E5', alpha=0, zorder=10)
                self.hover_scatter = scatter
                self.price_line = line
                
                # 设置X轴刻度和标签
                self.ax.set_xticks(tick_indices)
                
                # 根据时间周期设置不同的日期格式，减少标签内容长度
                if self.current_timeframe in ["daily", "weekly"]:
                    # 日周期只显示日期，不显示月份
                    date_labels = [idx.strftime('%d') for idx in df.index]
                elif self.current_timeframe in ["monthly", "3month", "6month"]:
                    # 月度周期显示"月/日"格式
                    date_labels = [idx.strftime('%m/%d') for idx in df.index]
                else:
                    # 更长周期显示"年/月"格式
                    date_labels = [idx.strftime('%y/%m') for idx in df.index]
                    
                self.ax.set_xticklabels([date_labels[i] for i in tick_indices], rotation=0)
                
                # 移除K线图标题
                pass
            
            # 设置更大的字体，取消旋转以提高可读性
            plt.xticks(fontsize=9, rotation=0)
            plt.yticks(fontsize=10)
            
            # 设置Y轴范围
            min_price = df.low.min()
            max_price = df.high.max()
            price_range = max_price - min_price
            if price_range > 0:
                self.ax.set_ylim([min_price - price_range * 0.05, max_price + price_range * 0.05])
            
            # 设置网格线
            self.ax.grid(True, linestyle='-', alpha=0.3, color=self.grid_color)
            
            # 设置轴标签颜色
            self.ax.tick_params(axis='both', colors=self.text_color)
            
            # 移除Y轴标签
            self.ax.set_ylabel('')
            
            # 在Y轴右侧显示价格
            self.ax.yaxis.tick_right()
            
            # 格式化Y轴，显示整数
            self.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%d'))
            
            # 移除边框
            for spine in ['top', 'right', 'left']:
                self.ax.spines[spine].set_visible(False)
            
            # 在图表右侧显示最新价格线
            if self.stock_info:
                current_price = self.stock_info['price']
                self.ax.axhline(y=current_price, color='lightgray', linestyle='--', alpha=0.8)
                
                # 价格标签位置调整 - 放到右下角
                # 计算合适的标签位置
                x_pos = len(df) - 1  # 使用索引作为x轴位置
                y_pos = min_price + price_range * 0.1  # 放在图表下方10%的位置
                
                self.ax.text(x_pos, y_pos, f"{current_price:.2f}", 
                          fontsize=10, color='black', va='center', ha='right',
                          bbox=dict(facecolor='white', alpha=0.8, pad=1, boxstyle='round'))
                
            # 存储数据用于鼠标交互
            self.df = df
            
            # 添加鼠标悬停事件处理
            self.hover_annotation = self.ax.annotate(
                '', xy=(0, 0), xytext=(10, 10),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#1E88E5', alpha=0.9),
                fontsize=10, color='black',
                ha='center', va='bottom'
            )
            self.hover_annotation.set_visible(False)
            
            # 添加垂直参考线，初始不可见
            self.vline = self.ax.axvline(x=0, color='#1E88E5', linestyle='-', alpha=0.3, visible=False)
            
            # 注册鼠标事件
            self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover_k)
            
            # 显示价格信息和时间周期选择
            self.display_stock_header()
            self.display_timeframe_buttons()
            self.display_stock_details()
            
            # 调整边距，确保图表元素不会重叠
            plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.10, hspace=0.1)
            
        except Exception as e:
            print(f"绘制K线图出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _on_hover_k(self, event):
        """鼠标在K线图上悬停时的事件处理"""
        import numpy as np
        
        if not hasattr(self, 'df') or not event.inaxes or event.inaxes != self.ax:
            # 如果鼠标移出图表区域，隐藏所有交互元素
            if hasattr(self, 'hover_annotation'):
                self.hover_annotation.set_visible(False)
            if hasattr(self, 'hover_scatter'):
                # 使用二维坐标数组来避免索引错误
                self.hover_scatter.set_offsets(np.array([[0, 0]]))
                self.hover_scatter.set_alpha(0)
            if hasattr(self, 'vline'):
                self.vline.set_visible(False)
            
            # 恢复原始线条样式
            if hasattr(self, 'price_line'):
                self.price_line.set_alpha(1.0)
                self.price_line.set_linewidth(2)
                self.price_line.set_zorder(2)
                
            # 彻底清除所有高亮元素
            if hasattr(self, 'highlight_area') and self.highlight_area:
                for patch in self.highlight_area:
                    if patch in self.ax.collections or patch in self.ax.lines:
                        patch.remove()
                self.highlight_area = []
                
            self.fig.canvas.draw_idle()
            return
        
        # 获取鼠标位置对应的数据索引
        x_data = int(round(event.xdata))
        if x_data < 0 or x_data >= len(self.df):
            return
            
        # 获取对应索引的数据点
        df = self.df
        price = df['close'].iloc[x_data]
        date = df.index[x_data]
        
        # 生成悬停信息
        if self.current_timeframe == "intraday":
            hover_text = f'{date.strftime("%H:%M")}\n价格: {price:.2f}'
        else:
            hover_text = f'{date.strftime("%Y-%m-%d")}\n价格: {price:.2f}'
        
        # 更新注释文本内容和位置
        self.hover_annotation.xy = (x_data, price)
        self.hover_annotation.set_text(hover_text)
        self.hover_annotation.set_visible(True)
        
        # 更新散点位置
        self.hover_scatter.set_offsets(np.array([[x_data, price]]))
        self.hover_scatter.set_alpha(1.0)  # 显示散点
        
        # 清除现有的高亮区域
        if hasattr(self, 'highlight_area') and self.highlight_area:
            for patch in self.highlight_area:
                if patch in self.ax.collections or patch in self.ax.lines:
                    patch.remove()
        self.highlight_area = []

        # 获取价格数据和图表底部边界
        ymin, ymax = self.ax.get_ylim()
        
        # 获取原始数据
        all_x = np.array(range(len(self.df)))
        all_y = self.df['close'].values
        
        # 隐藏原始线条，避免线条堆叠
        if hasattr(self, 'price_line'):
            self.price_line.set_alpha(0.3)
        
        # 添加简单的填充效果，使用渐变透明度
        from matplotlib.colors import LinearSegmentedColormap
        
        # 创建线性渐变色谱 - 颜色从浅蓝色到深蓝色
        colors = [(0.78, 0.89, 0.98, 0.05),  # 顶部几乎透明
                  (0.45, 0.69, 0.91, 0.25)]  # 底部半透明
        cmap = LinearSegmentedColormap.from_list('blue_gradient', colors)
        
        # 使用简单的填充区域
        fill = self.ax.fill_between(all_x, all_y, ymin, color='#1E88E5', alpha=0.2, zorder=1)
        self.highlight_area.append(fill)
        
        # 重绘当前曲线 - 简单加粗显示
        line = self.ax.plot(all_x, all_y, '-', color='#1976D2', linewidth=2.5, zorder=4)
        self.highlight_area.extend(line)
        
        # 更新垂直参考线 - 对于垂直线，使用实际数据点的索引位置
        self.vline.set_xdata([x_data, x_data])
        self.vline.set_visible(True)
        
        # 增强显示当前点，使其更大更明显
        self.hover_scatter.set_sizes([150])
        self.hover_scatter.set_facecolor('#1E88E5')
        self.hover_scatter.set_edgecolor('white')
        self.hover_scatter.set_linewidth(1.5)
        self.hover_scatter.set_zorder(10)
        
        # 更新画布
        self.fig.canvas.draw_idle()

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

        print("\n准备生成K线图...")
        
        # 在绘图前创建图表
        self.create_figure()
        
        # 更新图表
        self.plot_daily_k()
        
        # 保存图表为图片文件
        try:
            filename = f"{self.current_name}_日K线图_现代界面.png"
            plt.savefig(filename, facecolor=self.bg_color)
            print(f"\n图表已保存为文件: {filename}")
            print(f"请在当前目录查看该文件以查看K线图。")
        except Exception as save_error:
            print(f"保存图表时出错: {save_error}")
        
        print("\n尝试显示图表窗口...")
        print("如果窗口未显示，请查看已保存的图片文件。")
        print("按Ctrl+C终止程序。")
        
        # 尝试显示图表，阻塞直到窗口关闭
        try:
            plt.show(block=True)
        except KeyboardInterrupt:
            print("\n程序已被用户终止")
        except Exception as e:
            print(f"显示图表时出错: {e}")
            print(f"请直接查看保存的图片文件: {filename}")