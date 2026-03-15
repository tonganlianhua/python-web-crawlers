# Python爬虫程序汇总 (crawler_11.py - crawler_20.py)

本目录包含了10个实用的Python爬虫程序，每个程序都有完整的功能、错误处理和详细注释。这些爬虫覆盖了不同的网站和数据类型。

## 爬虫列表

### 1. crawler_11.py - 天气预报爬虫
**功能**: 获取中国主要城市天气预报
**网站**: 中国天气网 (http://www.weather.com.cn)
**特性**:
- 获取今日天气、温度、风向、空气质量等信息
- 支持多个城市批量查询
- 数据保存为JSON格式
- 完整的错误处理和日志记录

### 2. crawler_12.py - 股票数据爬虫
**功能**: 获取A股实时行情数据
**网站**: 东方财富网 (http://quote.eastmoney.com)
**特性**:
- 获取股票实时价格、涨跌幅、成交量、市值等信息
- 支持多只股票批量查询
- 数据保存为JSON和CSV格式
- 提供K线数据接口（简化版）

### 3. crawler_13.py - 电影信息爬虫
**功能**: 获取豆瓣电影信息
**网站**: 豆瓣电影 (https://movie.douban.com)
**特性**:
- 获取电影评分、简介、演员、评论等信息
- 支持电影搜索和详情获取
- 获取短评和评论数据
- 数据保存为JSON格式

### 4. crawler_14.py - GitHub数据爬虫
**功能**: 获取GitHub仓库和用户信息
**网站**: GitHub (https://github.com)
**特性**:
- 获取仓库信息、用户信息、README内容
- 获取issues和贡献者信息
- 支持仓库搜索和语言统计
- 支持GitHub API认证

### 5. crawler_15.py - Reddit帖子爬虫
**功能**: 获取Reddit热门帖子和评论
**网站**: Reddit (https://www.reddit.com)
**特性**:
- 获取热门帖子、最新帖子、顶部帖子
- 获取帖子评论（支持递归解析）
- 获取子版块和用户信息
- 支持OAuth2认证和速率限制

### 6. crawler_16.py - 技术博客爬虫
**功能**: 获取技术博客文章
**网站**: CSDN、博客园、掘金、SegmentFault、InfoQ等
**特性**:
- 自动检测博客平台
- 获取文章标题、作者、内容、标签等信息
- 支持多个平台的解析器
- 数据保存为JSON格式

### 7. crawler_17.py - 商品价格监控爬虫
**功能**: 监控电商平台商品价格
**网站**: 京东、淘宝、天猫、亚马逊、苏宁易购等
**特性**:
- 监控商品价格变化、库存状态、促销信息
- 价格历史记录和变化分析
- 支持多商品批量监控
- 价格超过阈值时记录变化

### 8. crawler_18.py - 招聘信息爬虫
**功能**: 获取各大招聘网站职位信息
**网站**: 智联招聘、前程无忧、BOSS直聘、拉勾网、猎聘网等
**特性**:
- 搜索职位、获取职位详情
- 多条件筛选（薪资、经验、学历等）
- 职位市场分析（薪资分析、公司分析等）
- 数据保存为JSON格式

### 9. crawler_19.py - 学术论文爬虫
**功能**: 获取学术论文信息
**网站**: arXiv、Semantic Scholar、DBLP、Crossref等
**特性**:
- 搜索论文、获取论文详情
- 获取最新论文和研究趋势分析
- 从摘要中提取关键词
- 多平台支持

### 10. crawler_20.py - 实时汇率爬虫
**功能**: 获取全球货币汇率数据
**网站**: 欧洲央行、ExchangeRate-API、Open Exchange Rates、中国银行、XE.com等
**特性**:
- 获取实时汇率、历史汇率
- 货币换算和汇率趋势分析
- 多数据源支持
- 数据缓存和导出功能

## 共同特性

所有爬虫程序都包含以下特性：

1. **完整的错误处理**: 使用try-except捕获各种异常，确保程序稳定性
2. **详细的日志记录**: 使用Python标准logging模块记录运行日志
3. **配置化管理**: 支持超时设置、User-Agent自定义等配置
4. **数据持久化**: 支持将数据保存为JSON文件
5. **模块化设计**: 代码结构清晰，易于维护和扩展
6. **注释完善**: 每个函数和类都有详细的文档字符串注释
7. **类型提示**: 使用Python类型提示提高代码可读性
8. **速率限制**: 合理设置请求间隔，避免被封IP

## 使用说明

### 基本使用方法

```python
# 以天气预报爬虫为例
from crawler_11 import WeatherCrawler

# 创建爬虫实例
crawler = WeatherCrawler(timeout=15)

# 获取单个城市的天气
weather_data = crawler.fetch_weather("北京")

# 获取多个城市的天气
cities = ["上海", "广州", "深圳"]
all_weather = crawler.get_multiple_cities_weather(cities)

# 保存数据
crawler.save_to_json(weather_data)
```

### 运行所有爬虫演示

每个爬虫文件都包含一个`main()`函数，可以直接运行查看演示效果：

```bash
# 运行单个爬虫演示
python crawler_11.py

# 运行所有爬虫演示（可以创建批处理脚本）
for i in {11..20}; do
    python crawler_$i.py
done
```

## 依赖库

主要依赖库：
- `requests`: HTTP请求库
- `beautifulsoup4`: HTML解析库
- `feedparser`: RSS/Atom解析库（用于arXiv）
- `pandas`: 数据处理库（部分爬虫使用）

## 注意事项

1. **遵守robots.txt**: 使用前请检查目标网站的robots.txt文件
2. **设置合理延迟**: 避免请求过快导致IP被封
3. **处理反爬机制**: 部分网站可能有反爬措施，需要相应处理
4. **API密钥**: 部分服务需要API密钥（如Open Exchange Rates）
5. **数据更新**: 网站结构可能变化，需要定期更新解析规则

## 扩展建议

1. **数据库支持**: 可以将数据保存到SQLite、MySQL等数据库
2. **定时任务**: 使用cron或APScheduler实现定时爬取
3. **Web界面**: 添加Flask或Django Web界面
4. **API服务**: 将爬虫封装为REST API服务
5. **分布式爬虫**: 使用Scrapy-Redis等实现分布式爬取

## 许可证

这些爬虫程序仅供学习和研究使用，请遵守相关法律法规和网站的使用条款。