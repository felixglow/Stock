# 实时股票查询工具

## 项目简介
这是一个基于命令行的实时股票价格查询工具，支持同时查询多支股票，数据来源为新浪股票API。本工具包括传统K线图和现代化界面两种显示方式。

## 功能特点
- 实时查询股票价格
- 默认包含沪指、深指查询
- 支持多股票同时查询
- 可配置查询间隔和线程数
- K线图形象直观展示股票走势
- 现代化界面提供更美观的数据展示

## 安装说明
1. 克隆仓库：
```bash
# 从Gitee克隆
git clone https://gitee.com/your-username/stock-query.git
cd stock-query
```

2. 安装依赖：
```bash
# 使用 Python3 安装依赖
python3 -m pip install -r requirements.txt

# 可选：更新 pip 到最新版本
python3 -m pip install --upgrade pip
```

## 使用方法
```bash
# 基本使用 - 传统界面
python3 -m src.main -c sz000816

# 使用现代化界面
python3 -m src.modern_main -c sz000816

# 查询多支股票
python3 -m src.main -c sh601003,sz000816,sz000778

# 自定义查询间隔和线程数
python3 -m src.main -c sz000816 -t 4 -s 3
```

### 命令行参数
- `-c, --codes`: 股票代码（必需），多个代码用逗号分隔
- `-s, --interval`: 查询间隔（秒），默认6秒
- `-t, --threads`: 线程数，默认3个线程
- `-h, --help`: 显示帮助信息

## 项目结构
```
stock-query/
├── src/
│   ├── __init__.py
│   ├── main.py         # 传统界面入口
│   ├── modern_main.py  # 现代化界面入口
│   ├── stock.py        # 传统股票数据处理
│   └── modern_stock.py # 现代化股票数据处理
├── tests/              # 单元测试
├── charts/             # 生成的图表保存目录
├── requirements.txt    # 依赖包列表
├── pyproject.toml      # 项目配置
└── README.md           # 项目说明
```

## 技术实现
- 使用新浪股票API获取实时数据
- 多线程并发查询
- Matplotlib生成可视化图表
- Pandas处理和分析股票数据
- 线程池实现高效数据获取
- 优雅的命令行参数处理

## Gitee代码管理
将代码提交到公司Gitee服务器的步骤：

1. 在Gitee上创建一个新仓库

2. 配置本地仓库的远程地址：
```bash
# 添加Gitee远程仓库
git remote add gitee https://gitee.com/your-username/stock-query.git
```

3. 初次提交代码：
```bash
# 初始化本地仓库(如果尚未初始化)
git init

# 添加所有文件
git add .

# 提交更改
git commit -m "初始提交：实时股票查询工具"

# 推送到Gitee
git push -u gitee master
```

4. 后续更新：
```bash
git add .
git commit -m "更新说明"
git push gitee master
```

## 注意事项
- 投资需谨慎，股市有风险。本工具仅供参考，不构成任何投资建议。
- 本工具需要 Python 3.6 或更高版本。
- 如果遇到权限问题，可能需要使用 `sudo python3 -m pip install -r requirements.txt` 进行安装。
- 图表保存在当前目录或charts目录中，可通过查看对应的PNG文件查看。

---

# 实时股票查询工具（中文说明）

## 项目简介
本项目是一款基于命令行的实时股票价格查询工具，可以同时查询多支股票的实时价格和K线走势，数据来源为新浪财经API。工具提供传统和现代化两种界面风格，满足不同用户的使用需求。

## 主要功能
- 实时获取股票价格数据
- 以K线图形式直观展示股票走势
- 支持多股票并行查询
- 默认包含沪深指数信息
- 可自定义查询间隔和线程数
- 提供传统与现代化两种界面风格

## 安装步骤
1. 从Gitee克隆代码：
```bash
git clone https://gitee.com/your-username/stock-query.git
cd stock-query
```

2. 安装依赖包：
```bash
python3 -m pip install -r requirements.txt
```

## 使用指南
```bash
# 使用传统界面查询单只股票
python3 -m src.main -c sz000858

# 使用现代化界面查询股票
python3 -m src.modern_main -c sz000858

# 同时查询多只股票
python3 -m src.main -c sh601003,sz000858,sz002230

# 自定义刷新间隔(3秒)和线程数(4个)
python3 -m src.main -c sz000858 -t 4 -s 3
```

### 参数说明
- `-c, --codes`: 股票代码，必填参数，多个代码用逗号分隔
- `-s, --interval`: 数据刷新间隔（秒），默认6秒
- `-t, --threads`: 线程数量，默认3个线程
- `-h, --help`: 显示帮助信息

## 代码结构
本项目采用模块化设计，主要包含以下组件：
```
├── src/                  # 源代码目录
│   ├── main.py           # 传统界面入口
│   ├── modern_main.py    # 现代界面入口
│   ├── stock.py          # 传统股票数据处理
│   └── modern_stock.py   # 现代股票数据处理
├── tests/                # 测试代码
├── charts/               # 图表保存目录
└── example_*.png         # 示例图片
```

## Gitee代码管理
将代码推送到公司Gitee服务器的操作步骤：

1. 在公司Gitee上创建新仓库

2. 添加Gitee远程地址：
```bash
git remote add gitee http://gitee.company.com/your-name/stock-tool.git
```

3. 推送代码到Gitee服务器：
```bash
git push -u gitee master
```

## 使用须知
- 本工具仅供学习和参考，投资有风险，决策需谨慎
- 需要Python 3.6或更高版本
- 生成的图表文件默认保存在当前目录或charts目录中
- 如遇显示问题，可查看生成的PNG图片文件
=======
# Stock
终端实时获取股票价格
====================
给有需要的朋友,投资需谨慎。

用途:
----
    实时查询股票价格，默认查询了沪指、深指
    结果输出到终端
    stock_terminal1.py 增加了实时涨幅和昨日收盘价

使用:
----
    需要安装requests库
    支持命令行多参数，如果需要帮助：
        python stock_terminal.py -h
    设置查询代码（必传）   -c   
    设置查询时间间隔（默认6秒）   -s   
    设置线程数（默认3）（如果有需要）   -t    
    
    查询 智慧农业 sz000816
    例如:
        python stock_terminal.py -c sz000816 -t 4 -s 3
    
    支持查询多个股票
    例如:
        python stock_terminal.py -c sh601003,sz000816,sz000778

实现:
----
    通过调用新浪股票API，实时查询股票价格
    支持查询多支股票，通过threading多线程同时查询结果
    通过Queue实现线程池
    requests请求接口
    optparse实现命令行参数处理
