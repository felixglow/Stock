# -*-coding:utf-8 -*-
# 
# Created on 2016-03-04, by Kyo
# 

__author__ = 'Kyo'

from datetime import datetime, timedelta
from optparse import OptionParser
from queue import Queue
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
import requests
import sys
import threading
import time

# 添加中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # Mac系统
# plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows系统
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class Worker(threading.Thread):
    """多线程获取"""
    def __init__(self, work_queue, result_queue):
        threading.Thread.__init__(self)
        self.work_queue = work_queue
        self.result_queue = result_queue
        self.start()

    def run(self):
        while True:
            func, arg, code_index = self.work_queue.get()
            res = func(arg, code_index)
            self.result_queue.put(res)
            if self.result_queue.full():
                res = sorted([self.result_queue.get() for i in range(self.result_queue.qsize())], key=lambda s: s[0], reverse=True)
                res.insert(0, ('0', u'名称     股价'))
                print('***** start *****')
                for obj in res:
                    print(obj[1])
                print('***** end *****\n')
            self.work_queue.task_done()


class Stock(object):
    """股票实时价格获取"""

    def __init__(self, code, thread_num):
        self.code = code
        self.work_queue = Queue()
        self.threads = []
        self.__init_thread_poll(thread_num)
        self.price_history = []
        self.time_history = []
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.current_price = None
        # 初始化图表设置
        self.ax1.set_title('实时价格走势')
        self.ax1.set_xlabel('时间')
        self.ax1.set_ylabel('价格(元)')
        self.ax1.grid(True)
        self.ax2.set_title('分时K线图')
        self.ax2.set_xlabel('时间')
        self.ax2.set_ylabel('价格(元)')
        self.ax2.grid(True)

    def __init_thread_poll(self, thread_num):
        self.params = self.code.split(',')
        self.params.extend(['s_sh000001', 's_sz399001'])  # 默认获取沪指、深指
        self.result_queue = Queue(maxsize=len(self.params[::-1]))
        for i in range(thread_num):
            self.threads.append(Worker(self.work_queue, self.result_queue))

    def __add_work(self, stock_code, code_index):
        self.work_queue.put((self.value_get, stock_code, code_index))

    def del_params(self):
        for obj in self.params:
            self.__add_work(obj, self.params.index(obj))

    def wait_all_complete(self):
        for thread in self.threads:
            if thread.isAlive():
                thread.join()

    def update_plot(self, frame):
        if not self.price_history:
            print("Debug - No price history data")  # 添加调试信息
            return
            
        print(f"Debug - Updating plot with {len(self.price_history)} data points")  # 添加调试信息
        
        # 更新实时价格走势图
        self.ax1.clear()
        self.ax1.grid(True)
        
        # 确保有数据再绘制
        if len(self.price_history) > 0:
            time_labels = [t.strftime('%H:%M:%S') for t in self.time_history]
            self.ax1.plot(range(len(time_labels)), self.price_history, 'b-', marker='o')
            self.ax1.set_xticks(range(len(time_labels)))
            self.ax1.set_xticklabels(time_labels, rotation=45, ha='right')
            self.ax1.set_title(f'实时价格走势 - 当前价格: {self.current_price:.2f}')
            
            # 设置合适的Y轴范围
            min_price = min(self.price_history)
            max_price = max(self.price_history)
            price_range = max_price - min_price
            if price_range == 0:
                price_range = 1  # 避免价格相同时范围为0
            self.ax1.set_ylim([min_price - price_range * 0.1, max_price + price_range * 0.1])

        # 更新K线图
        if len(self.price_history) >= 20:
            self.plot_candlestick(self.ax2)
        
        plt.tight_layout()
    
    def plot_candlestick(self, ax):
        # 生成K线图数据
        df = pd.DataFrame({
            'time': self.time_history,
            'price': self.price_history
        })
        df = df.set_index('time')
        df = df.resample('1min').ohlc()  # 1分钟K线
        
        # 绘制K线图
        ax.clear()
        ax.grid(True)
        
        # 格式化时间轴
        time_labels = [t.strftime('%H:%M:%S') for t in df.index]
        x = range(len(time_labels))
        
        width = 0.6
        width2 = 0.1
        
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # 绘制上涨K线（红色）
        for i, (idx, row) in enumerate(up.iterrows()):
            ax.bar(i, row.close-row.open, width, bottom=row.open, color='red')
            ax.bar(i, row.high-row.close, width2, bottom=row.close, color='red')
            ax.bar(i, row.low-row.open, width2, bottom=row.open, color='red')
        
        # 绘制下跌K线（绿色）
        for i, (idx, row) in enumerate(down.iterrows()):
            ax.bar(i, row.close-row.open, width, bottom=row.open, color='green')
            ax.bar(i, row.high-row.open, width2, bottom=row.open, color='green')
            ax.bar(i, row.low-row.close, width2, bottom=row.close, color='green')
        
        ax.set_title('分时K线图')
        ax.set_xlabel('时间')
        ax.set_ylabel('价格(元)')
        
        # 设置时间轴标签
        ax.set_xticks(x)
        ax.set_xticklabels(time_labels, rotation=45, ha='right')
        
        # 自动调整Y轴范围
        if not df.empty:
            mean_price = df.close.mean()
            price_range = df.high.max() - df.low.min()
            ax.set_ylim([mean_price - price_range * 0.6, mean_price + price_range * 0.6])

    def value_get(self, code, code_index):
        slice_num, value_num = 21, 3
        name, now = u'——无——', u'  ——无——'
        if code in ['s_sh000001', 's_sz399001']:
            slice_num = 23
            value_num = 1
        try:
            url = f"http://hq.sinajs.cn/list={code}"
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            r = requests.get(url, headers=headers)
            r.encoding = 'gbk'
            res = r.text.split(',')
            print(f"Debug - Raw data: {r.text}")  # 添加调试信息
            if len(res) > 1:
                name, now = r.text.split(',')[0][slice_num:], r.text.split(',')[value_num]
                try:
                    price = float(now)
                    print(f"Debug - Price: {price}")  # 添加调试信息
                    self.price_history.append(price)
                    self.time_history.append(datetime.now())
                    self.current_price = price
                    # 保持固定长度的历史数据
                    if len(self.price_history) > 100:
                        self.price_history.pop(0)
                        self.time_history.pop(0)
                except ValueError:
                    print(f"无法转换价格: {now}")
        except Exception as e:
            print(f"获取数据错误: {str(e)}")
        return code_index, f"{name} {now}"


if __name__ == '__main__':
    parser = OptionParser(description="Query the stock's value.", usage="%prog [-c] [-s] [-t]", version="%prog 1.0")
    parser.add_option('-c', '--stock-code', dest='codes',
                      help="the stock's code that you want to query.")
    parser.add_option('-s', '--sleep-time', dest='sleep_time', default=6, type="int",
                      help='How long does it take to check one more time.')
    parser.add_option('-t', '--thread-num', dest='thread_num', default=3, type='int',
                      help="thread num.")
    options, args = parser.parse_args(args=sys.argv[1:])

    assert options.codes, "Please enter the stock code!"  # 是否输入股票代码
    codes = options.codes.split(',')
    for code in codes:
        prefix = code[:-6]
        if prefix not in ('sh', 'sz', 's_sh', 's_sz'):
            raise ValueError("请检查股票代码格式是否正确。股票代码应该是6位数字，上海股票以'600'，'601'，'603'开头，深圳股票以'000'或'300'开头")

    stock = Stock(options.codes, options.thread_num)
    
    # 先获取一些初始数据
    stock.del_params()
    time.sleep(1)  # 等待初始数据
    
    # 创建动画，增加更新频率
    ani = FuncAnimation(stock.fig, stock.update_plot, interval=1000)  # 1秒更新一次
    plt.show()

    while True:
        stock.del_params()
        time.sleep(options.sleep_time)