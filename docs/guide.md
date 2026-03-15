---
layout: page
title: 使用指南
permalink: /guide/
---

# 📖 使用指南

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip 包管理器
- Git（可选）

### 2. 安装步骤

```bash
# 克隆项目
git clone https://github.com/tonganlianhua/python-web-crawlers.git
cd python-web-crawlers

# 安装依赖
pip install -r requirements.txt

# 或者使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 基本使用

```python
# 导入爬虫模块
from crawler_01 import NewsCrawler

# 创建爬虫实例
crawler = NewsCrawler()

# 运行爬虫
data = crawler.fetch_news()

# 保存数据
crawler.save_data(data, "news_data.json")
```

## 🐍 爬虫示例

### 示例1：新闻爬虫

```python
# crawler_01.py 使用示例
import crawler_01

# 获取今日头条热点新闻
news_crawler = crawler_01.NewsCrawler()
hot_news = news_crawler.fetch_hot_news()

# 打印结果
for news in hot_news[:5]:
    print(f"标题: {news.title}")
    print(f"热度: {news.hot_value}")
    print(f"链接: {news.url}")
    print("-" * 50)
```

### 示例2：天气爬虫

```python
# crawler_11.py 使用示例
import crawler_11

# 获取天气数据
weather_crawler = crawler_11.WeatherCrawler()
weather_data = weather_crawler.get_weather("北京")

# 显示天气信息
print(f"城市: {weather_data.city}")
print(f"温度: {weather_data.temperature}°C")
print(f"天气: {weather_data.condition}")
print(f"湿度: {weather_data.humidity}%")
```

### 示例3：批量运行

```python
# run_all.py 使用示例
import run_all

# 创建运行器
runner = run_all.CrawlerRunner(max_workers=5)

# 运行所有爬虫
results = runner.run_all()

# 查看结果
print(f"成功数: {results['success']}")
print(f"失败数: {results['failed']}")
```

## 🔧 配置说明

### 配置文件

编辑 `config.py` 文件可以自定义爬虫行为：

```python
# 请求配置
REQUEST_TIMEOUT = 30      # 请求超时时间（秒）
REQUEST_DELAY = 1.0       # 请求延迟（秒）
REQUEST_RETRY = 3         # 重试次数

# 代理配置
PROXY_ENABLED = False     # 是否启用代理
PROXY_URL = "http://127.0.0.1:7890"  # 代理地址

# 数据存储
SAVE_FORMAT = "json"      # 数据保存格式
DATA_DIR = "./data"       # 数据保存目录
```

### 环境变量

也可以通过环境变量配置：

```bash
# Windows
set CRAWLER_PROXY_ENABLED=true
set CRAWLER_PROXY_URL=http://127.0.0.1:7890

# Linux/Mac
export CRAWLER_PROXY_ENABLED=true
export CRAWLER_PROXY_URL=http://127.0.0.1:7890
```

## 🛠️ 高级功能

### 1. 自定义爬虫

```python
from utils import make_request, save_data
from config import HEADERS

class CustomCrawler:
    def __init__(self, url):
        self.url = url
    
    def fetch_data(self):
        response = make_request(self.url)
        if response:
            # 解析数据
            data = self.parse_data(response.text)
            return data
        return None
    
    def parse_data(self, html):
        # 自定义解析逻辑
        # 使用BeautifulSoup或正则表达式
        pass
```

### 2. 定时任务

```python
import schedule
import time
from crawler_01 import NewsCrawler

def daily_news_job():
    crawler = NewsCrawler()
    news = crawler.fetch_hot_news()
    crawler.save_data(news, f"news_{time.strftime('%Y%m%d')}.json")
    print("新闻数据已更新")

# 每天9点运行
schedule.every().day.at("09:00").do(daily_news_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. 数据监控

```python
import pandas as pd
import matplotlib.pyplot as plt
from crawler_12 import StockCrawler

# 获取股票数据
stock_crawler = StockCrawler()
stock_data = stock_crawler.get_stock_data("000001")

# 转换为DataFrame
df = pd.DataFrame(stock_data)

# 绘制价格走势图
plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['close'])
plt.title('股票价格走势')
plt.xlabel('日期')
plt.ylabel('价格')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('stock_price.png')
```

## ⚠️ 注意事项

### 1. 遵守robots.txt
所有爬虫都考虑了目标网站的robots.txt规则

### 2. 设置合理延迟
避免对目标网站造成过大压力：

```python
# 推荐设置
REQUEST_DELAY = 1.0  # 1秒延迟
REQUEST_RETRY = 3    # 3次重试
```

### 3. 使用代理
高频率访问时建议使用代理：

```python
# 启用代理
PROXY_ENABLED = True
PROXY_URL = "http://your-proxy:port"
```

### 4. 数据使用
- 仅用于学习和研究目的
- 遵守相关法律法规
- 尊重数据隐私

## 🆘 故障排除

### 常见问题

1. **网络连接失败**
   - 检查网络连接
   - 验证代理设置
   - 尝试使用VPN

2. **解析错误**
   - 检查HTML结构是否变化
   - 更新解析规则
   - 使用备用解析方法

3. **数据保存失败**
   - 检查目录权限
   - 验证文件路径
   - 检查磁盘空间

### 获取帮助

- 查看项目 [Issues](https://github.com/tonganlianhua/python-web-crawlers/issues)
- 提交 [Bug报告](https://github.com/tonganlianhua/python-web-crawlers/issues/new)
- 查看 [FAQ](faq.md)

---

**🎯 开始使用这些强大的爬虫工具吧！**