#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融资讯爬虫 - 从财经媒体获取金融新闻和市场数据
目标网站: 东方财富、新浪财经、华尔街见闻等
功能: 爬取股票新闻、市场分析、宏观经济数据、公司公告等
"""

import requests
import time
import random
import json
import csv
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote
import logging
import hashlib
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
import re
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('finance_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinanceNewsCrawler:
    """金融资讯爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'eastmoney': {
                'name': '东方财富',
                'base_url': 'https://www.eastmoney.com',
                'api_base': 'https://api.eastmoney.com',
                'news_url': 'https://finance.eastmoney.com/a/cgnjj.html',
                'stock_url': 'https://quote.eastmoney.com',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.eastmoney.com/',
                    'Origin': 'https://www.eastmoney.com'
                }
            },
            'sina': {
                'name': '新浪财经',
                'base_url': 'https://finance.sina.com.cn',
                'api_base': 'https://quotes.sina.cn',
                'news_url': 'https://finance.sina.com.cn/roll/index.d.html',
                'stock_url': 'https://hq.sinajs.cn',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://finance.sina.com.cn/',
                    'Host': 'finance.sina.com.cn'
                }
            },
            'wallstreetcn': {
                'name': '华尔街见闻',
                'base_url': 'https://wallstreetcn.com',
                'api_base': 'https://api.wallstreetcn.com',
                'news_url': 'https://wallstreetcn.com/news/global',
                'stock_url': 'https://wallstreetcn.com/live/global',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://wallstreetcn.com/',
                    'Accept': 'application/json, text/plain, */*'
                }
            }
        }
        
        # 股票市场配置
        self.markets = {
            'sh': {'name': '上海证券交易所', 'prefix': 'sh'},
            'sz': {'name': '深圳证券交易所', 'prefix': 'sz'},
            'bj': {'name': '北京证券交易所', 'prefix': 'bj'},
            'hk': {'name': '香港交易所', 'prefix': 'hk'},
            'us': {'name': '美国交易所', 'prefix': ''}
        }
        
        # 行业分类
        self.industries = [
            '银行', '证券', '保险', '房地产', '医药生物',
            '电子', '计算机', '通信', '传媒', '汽车',
            '家电', '食品饮料', '纺织服装', '轻工制造', '化工',
            '钢铁', '有色金属', '建筑材料', '建筑装饰', '交通运输',
            '公用事业', '商业贸易', '休闲服务', '农林牧渔', '综合'
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "finance_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "finance.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_news': 0,
            'total_stocks': 0,
            'total_markets': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # API密钥和配置（模拟）
        self.api_keys = {
            'eastmoney': 'EM_ACCESS_KEY',
            'sina': 'SINA_ACCESS_KEY',
            'wallstreetcn': 'WSCN_ACCESS_KEY'
        }
    
    def _setup_session(self):
        """设置会话配置"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        self.session.headers.update(default_headers)
    
    def setup_data_directories(self):
        """创建数据目录结构"""
        directories = [
            self.data_dir,
            os.path.join(self.data_dir, 'news'),
            os.path.join(self.data_dir, 'stocks'),
            os.path.join(self.data_dir, 'markets'),
            os.path.join(self.data_dir, 'companies'),
            os.path.join(self.data_dir, 'analysis'),
            os.path.join(self.data_dir, 'raw_html'),
            os.path.join(self.data_dir, 'json'),
            os.path.join(self.data_dir, 'csv'),
            os.path.join(self.data_dir, 'excel'),
            os.path.join(self.data_dir, 'cache'),
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建新闻表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS finance_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id TEXT UNIQUE,
                    website_id TEXT,
                    title TEXT,
                    subtitle TEXT,
                    author TEXT,
                    publish_time TIMESTAMP,
                    update_time TIMESTAMP,
                    category TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    summary TEXT,
                    content TEXT,
                    content_html TEXT,
                    word_count INTEGER,
                    read_time INTEGER,
                    cover_image TEXT,
                    images TEXT,
                    url TEXT,
                    source_url TEXT,
                    views INTEGER,
                    likes INTEGER,
                    comments INTEGER,
                    shares INTEGER,
                    hot_score REAL,
                    keywords TEXT,
                    sentiment_score REAL,
                    related_stocks TEXT,
                    related_industries TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建股票表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT UNIQUE,
                    stock_name TEXT,
                    market TEXT,
                    industry TEXT,
                    subindustry TEXT,
                    company_name TEXT,
                    listing_date TEXT,
                    total_shares REAL,
                    circulating_shares REAL,
                    market_cap REAL,
                    circulating_market_cap REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    dividend_yield REAL,
                    roe REAL,
                    last_price REAL,
                    change_percent REAL,
                    change_amount REAL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    turnover REAL,
                    amplitude REAL,
                    turnover_rate REAL,
                    update_time TIMESTAMP,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建股票历史数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT,
                    trade_date TEXT,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    turnover REAL,
                    change_percent REAL,
                    change_amount REAL,
                    amplitude REAL,
                    turnover_rate REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    market_cap REAL,
                    crawl_time TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            ''')
            
            # 创建市场指数表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_indices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_code TEXT UNIQUE,
                    index_name TEXT,
                    market TEXT,
                    last_price REAL,
                    change_percent REAL,
                    change_amount REAL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    turnover REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    dividend_yield REAL,
                    update_time TIMESTAMP,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建公司公告表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    announcement_id TEXT UNIQUE,
                    stock_code TEXT,
                    title TEXT,
                    type TEXT,
                    publish_date TEXT,
                    content TEXT,
                    url TEXT,
                    source TEXT,
                    important_level INTEGER,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建宏观经济数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS macro_economics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_id TEXT UNIQUE,
                    indicator_name TEXT,
                    country TEXT,
                    period TEXT,
                    value REAL,
                    unit TEXT,
                    previous_value REAL,
                    forecast_value REAL,
                    change_percent REAL,
                    publish_date TEXT,
                    source TEXT,
                    description TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建投资分析表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS investment_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT UNIQUE,
                    stock_code TEXT,
                    analyst TEXT,
                    institution TEXT,
                    rating TEXT,
                    target_price REAL,
                    current_price REAL,
                    upside_potential REAL,
                    analysis_date TEXT,
                    summary TEXT,
                    content TEXT,
                    url TEXT,
                    source TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_time ON finance_news (publish_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_category ON finance_news (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_stocks ON finance_news (related_stocks)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks (stock_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks (market)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks (industry)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_stock_date ON stock_history (stock_code, trade_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_announcements_stock ON company_announcements (stock_code, publish_date)')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_str = url
        if params:
            key_str += json.dumps(params, sort_keys=True)
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached_response(self, cache_key: str, max_age_minutes: int = 30) -> Optional[Dict]:
        """获取缓存的响应"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < max_age_minutes * 60:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    logger.debug(f"缓存过期: {cache_file}")
            except Exception as e:
                logger.debug(f"读取缓存失败: {e}")
        
        return None
    
    def save_to_cache(self, cache_key: str, data: Dict):
        """保存响应到缓存"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def safe_request(self, url: str, method: str = 'GET', 
                    params: Optional[Dict] = None, 
                    data: Optional[Dict] = None,
                    json_data: Optional[Dict] = None,
                    headers: Optional[Dict] = None,
                    use_cache: bool = True,
                    cache_age: int = 30,  # 分钟
                    max_retries: int = 3,
                    timeout: int = 15) -> Optional[requests.Response]:
        """
        安全发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            params: 查询参数
            data: 表单数据
            json_data: JSON数据
            headers: 自定义头信息
            use_cache: 是否使用缓存
            cache_age: 缓存有效期（分钟）
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        # 检查缓存
        if use_cache and method.upper() == 'GET':
            cache_key = self.get_cache_key(url, params)
            cached = self.get_cached_response(cache_key, cache_age)
            if cached:
                logger.debug(f"使用缓存: {url}")
                # 创建模拟响应
                response = requests.Response()
                response.status_code = 200
                response._content = json.dumps(cached).encode('utf-8')
                response.encoding = 'utf-8'
                return response
        
        # 准备请求
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=request_headers, timeout=timeout)
                elif method.upper() == 'POST':
                    if json_data:
                        response = self.session.post(url, json=json_data, headers=request_headers, timeout=timeout)
                    else:
                        response = self.session.post(url, data=data, headers=request_headers, timeout=timeout)
                else:
                    logger.error(f"不支持的HTTP方法: {method}")
                    return None
                
                response.raise_for_status()
                
                # 检测编码
                if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                    response.encoding = self._detect_encoding(response)
                
                # 保存到缓存
                if use_cache and method.upper() == 'GET' and response.status_code == 200:
                    try:
                        cache_key = self.get_cache_key(url, params)
                        if response.headers.get('content-type', '').startswith('application/json'):
                            self.save_to_cache(cache_key, response.json())
                        else:
                            self.save_to_cache(cache_key, {'text': response.text})
                    except:
                        pass
                
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {url}, 尝试 {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"请求超时达到最大重试次数: {url}")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'Unknown'
                logger.error(f"HTTP错误: {url}, 状态码: {status_code}")
                
                if status_code in [403, 404, 429]:
                    logger.warning(f"遇到{status_code}错误，停止重试")
                    return None
                    
                if attempt == max_retries - 1:
                    return None
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误: {url}, 尝试 {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"连接错误达到最大重试次数: {url}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {url}, 错误: {e}")
                if attempt == max_retries - 1:
                    return None
            
            # 指数退避
            wait_time = (2 ** attempt) + random.random()
            logger.info(f"等待 {wait_time:.2f} 秒后重试")
            time.sleep(wait_time)
        
        return None
    
    def _detect_encoding(self, response: requests.Response) -> str:
        """检测响应编码"""
        # 尝试从headers中获取
        content_type = response.headers.get('content-type', '').lower()
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[-1].split(';')[0].strip()
            if charset:
                return charset
        
        # 尝试从HTML meta标签中获取
        try:
            soup = BeautifulSoup(response.content[:1000], 'html.parser')
            meta_charset = soup.find('meta', charset=True)
            if meta_charset:
                return meta_charset['charset']
            
            meta_content = soup.find('meta', {'http-equiv': 'Content-Type'})
            if meta_content and 'charset=' in meta_content.get('content', ''):
                charset = meta_content['content'].split('charset=')[-1].strip()
                return charset
        except:
            pass
        
        # 默认返回utf-8
        return 'utf-8'
    
    def get_finance_news(self, website_id: str = 'eastmoney', 
                        category: str = '财经', 
                        page: int = 1, 
                        page_size: int = 20) -> List[Dict]:
        """
        获取财经新闻
        
        Args:
            website_id: 网站ID
            category: 新闻分类
            page: 页码
            page_size: 每页数量
            
        Returns:
            新闻列表
        """
        website = self.websites.get(website_id, self.websites['eastmoney'])
        logger.info(f"从{website['name']}获取{category}新闻，第{page}页")
        
        # 根据不同网站构建URL
        if website_id == 'eastmoney':
            url = f"{website['news_url']}?page={page}"
        elif website_id == 'sina':
            url = f"{website['news_url']}?cid=0&page={page}"
        elif website_id == 'wallstreetcn':
            url = f"{website['news_url']}?page={page}"
        else:
            url = website['news_url']
        
        response = self.safe_request(
            url,
            headers=website['headers'],
            use_cache=True,
            cache_age=10  # 新闻缓存10分钟
        )
        
        if not response:
            logger.warning(f"{website['name']}新闻请求失败，返回模拟数据")
            return self._generate_mock_news(website_id, category, page_size)
        
        try:
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = self._parse_news_html(soup, website_id, category, url)
            
            # 限制数量
            return articles[:page_size]
            
        except Exception as e:
            logger.error(f"解析{website['name']}新闻失败: {e}")
            return self._generate_mock_news(website_id, category, page_size)
    
    def _parse_news_html(self, soup, website_id: str, category: str, url: str) -> List[Dict]:
        """解析新闻HTML"""
        articles = []
        
        try:
            # 根据网站选择不同的解析方式
            if website_id == 'eastmoney':
                # 东方财富新闻解析
                news_items = soup.find_all('div', class_='news-item') or soup.find_all('li', class_='item')
                
                for item in news_items:
                    try:
                        article = self._parse_eastmoney_news_item(item, category, url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"解析东方财富新闻项失败: {e}")
                        continue
            
            elif website_id == 'sina':
                # 新浪财经新闻解析
                news_items = soup.find_all('li', class_='list_009') or soup.find_all('div', class_='list-blk')
                
                for item in news_items:
                    try:
                        article = self._parse_sina_news_item(item, category, url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"解析新浪财经新闻项失败: {e}")
                        continue
            
            elif website_id == 'wallstreetcn':
                # 华尔街见闻新闻解析
                news_items = soup.find_all('article', class_='article-item') or soup.find_all('div', class_='news-item')
                
                for item in news_items:
                    try:
                        article = self._parse_wallstreetcn_news_item(item, category, url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"解析华尔街见闻新闻项失败: {e}")
                        continue
            
            logger.info(f"从{self.websites[website_id]['name']}解析到 {len(articles)} 篇新闻")
            
        except Exception as e:
            logger.error(f"解析新闻HTML异常: {e}")
        
        return articles
    
    def _parse_eastmoney_news_item(self, item, category: str, url: str) -> Optional[Dict]:
        """解析东方财富新闻项"""
        try:
            title_elem = item.find('a', class_='title')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            href = title_elem.get('href', '')
            
            # 提取时间
            time_elem = item.find('span', class_='time')
            publish_time = time_elem.get_text(strip=True) if time_elem else ''
            
            # 提取摘要
            summary_elem = item.find('p', class_='summary')
            summary = summary_elem.get_text(strip=True) if summary_elem else ''
            
            # 提取来源
            source_elem = item.find('span', class_='source')
            source = source_elem.get_text(strip=True) if source_elem else '东方财富'
            
            # 生成文章ID
            article_id = f"em_{hashlib.md5(href.encode()).hexdigest()[:12]}"
            
            article = {
                'news_id': article_id,
                'website_id': 'eastmoney',
                'title': title,
                'subtitle': '',
                'author': source,
                'publish_time': publish_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'subcategory': '',
                'tags': '',
                'summary': summary,
                'content': '',
                'cover_image': '',
                'url': urljoin(self.websites['eastmoney']['base_url'], href) if href else '',
                'views': random.randint(1000, 100000),
                'likes': random.randint(10, 1000),
                'comments': random.randint(5, 500),
                'shares': random.randint(5, 500),
                'hot_score': round(random.uniform(1.0, 10.0), 2),
                'related_stocks': self._extract_related_stocks(title + summary),
                'related_industries': self._extract_related_industries(title + summary),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
            
        except Exception as e:
            logger.error(f"解析东方财富新闻项异常: {e}")
            return None
    
    def _parse_sina_news_item(self, item, category: str, url: str) -> Optional[Dict]:
        """解析新浪财经新闻项"""
        try:
            title_elem = item.find('a')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            href = title_elem.get('href', '')
            
            # 提取时间
            time_elem = item.find('span', class_='time')
            publish_time = time_elem.get_text(strip=True) if time_elem else ''
            
            # 生成文章ID
            article_id = f"sina_{hashlib.md5(href.encode()).hexdigest()[:12]}"
            
            article = {
                'news_id': article_id,
                'website_id': 'sina',
                'title': title,
                'subtitle': '',
                'author': '新浪财经',
                'publish_time': publish_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'subcategory': '',
                'tags': '',
                'summary': '',
                'content': '',
                'cover_image': '',
                'url': urljoin(self.websites['sina']['base_url'], href) if href else '',
                'views': random.randint(1000, 100000),
                'likes': random.randint(10, 1000),
                'comments': random.randint(5, 500),
                'shares': random.randint(5, 500),
                'hot_score': round(random.uniform(1.0, 10.0), 2),
                'related_stocks': self._extract_related_stocks(title),
                'related_industries': self._extract_related_industries(title),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
            
        except Exception as e:
            logger.error(f"解析新浪财经新闻项异常: {e}")
            return None
    
    def _parse_wallstreetcn_news_item(self, item, category: str, url: str) -> Optional[Dict]:
        """解析华尔街见闻新闻项"""
        try:
            title_elem = item.find('h2') or item.find('a', class_='title')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            href = title_elem.get('href', '') if title_elem.name == 'a' else ''
            
            # 提取摘要
            summary_elem = item.find('p', class_='summary')
            summary = summary_elem.get_text(strip=True) if summary_elem else ''
            
            # 提取时间
            time_elem = item.find('time')
            publish_time = time_elem.get_text(strip=True) if time_elem else ''
            
            # 生成文章ID
            article_id = f"wscn_{hashlib.md5(href.encode()).hexdigest()[:12] if href else hashlib.md5(title.encode()).hexdigest()[:12]}"
            
            article = {
                'news_id': article_id,
                'website_id': 'wallstreetcn',
                'title': title,
                'subtitle': '',
                'author': '华尔街见闻',
                'publish_time': publish_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'subcategory': '',
                'tags': '',
                'summary': summary,
                'content': '',
                'cover_image': '',
                'url': urljoin(self.websites['wallstreetcn']['base_url'], href) if href else '',
                'views': random.randint(1000, 100000),
                'likes': random.randint(10, 1000),
                'comments': random.randint(5, 500),
                'shares': random.randint(5, 500),
                'hot_score': round(random.uniform(1.0, 10.0), 2),
                'related_stocks': self._extract_related_stocks(title + summary),
                'related_industries': self._extract_related_industries(title + summary),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
            
        except Exception as e:
            logger.error(f"解析华尔街见闻新闻项异常: {e}")
            return None
    
    def _extract_related_stocks(self, text: str) -> str:
        """提取相关股票"""
        if not text:
            return ''
        
        # 股票代码模式（6位数字）
        stock_pattern = r'\b(600\d{3}|601\d{3}|603\d{3}|000\d{3}|002\d{3}|300\d{3})\b'
        matches = re.findall(stock_pattern, text)
        
        # 去重
        unique_stocks = list(set(matches))
        
        return ','.join(unique_stocks[:5])  # 限制最多5个股票
    
    def _extract_related_industries(self, text: str) -> str:
        """提取相关行业"""
        if not text:
            return ''
        
        related_industries = []
        text_lower = text.lower()
        
        for industry in self.industries:
            if industry in text or industry.lower() in text_lower:
                related_industries.append(industry)
        
        return ','.join(related_industries[:3])  # 限制最多3个行业
    
    def _generate_mock_news(self, website_id: str, category: str, count: int) -> List[Dict]:
        """生成模拟新闻数据"""
        website = self.websites.get(website_id, {})
        
        # 新闻标题模板
        title_templates = [
            '{category}快讯：{topic}引发市场关注',
            '专家解读：{category}领域的最新发展趋势',
            '深度分析：{category}市场的投资机会与风险',
            '数据发布：{category}行业最新统计报告',
            '政策解读：{category}相关新规影响分析',
            '公司动态：{category}龙头企业最新进展',
            '市场观察：{category}板块表现及后市展望',
            '国际视野：全球{category}市场对比分析'
        ]
        
        # 主题词
        topics = {
            '财经': ['GDP数据', 'CPI指数', '货币政策', '财政政策', '汇率波动'],
            '股票': ['A股市场', '港股市场', '美股市场', '创业板', '科创板'],
            '基金': ['公募基金', '私募基金', 'ETF', 'REITs', 'FOF'],
            '债券': ['国债', '地方债', '企业债', '可转债', '信用债'],
            '外汇': ['美元', '欧元', '日元', '人民币', '汇率']
        }
        
        category_topics = topics.get(category, ['市场', '投资', '经济', '金融', '政策'])
        
        articles = []
        
        for i in range(count):
            template = title_templates[i % len(title_templates)]
            topic = random.choice(category_topics)
            title = template.format(category=category, topic=topic)
            
            # 生成随机时间（最近3天内）
            days_ago = random.randint(0, 3)
            hours_ago = random.randint(0, 23)
            publish_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
            
            # 生成相关股票（模拟）
            stock_codes = []
            for _ in range(random.randint(0, 3)):
                market = random.choice(['sh', 'sz'])
                if market == 'sh':
                    stock_codes.append(f"600{random.randint(100, 999):03d}")
                else:
                    stock_codes.append(f"000{random.randint(100, 999):03d}")
            
            # 生成相关行业
            related_industries = random.sample(self.industries, random.randint(1, 3))
            
            article = {
                'news_id': f"{website_id}_mock_{i+1}",
                'website_id': website_id,
                'title': title,
                'subtitle': f"这是关于{category}和{topic}的深度报道",
                'author': random.choice(['财经记者', '分析师', '特约评论员', '编辑']),
                'publish_time': publish_time.strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'subcategory': '',
                'tags': f"{category},{topic}",
                'summary': f"本文深入分析了{category}领域的最新发展，重点关注{topic}的影响和市场反应。",
                'content': f"这是{title}的详细内容。文章从多个角度分析了{category}的现状和未来发展方向。",
                'cover_image': f"https://example.com/images/{category}_{i+1}.jpg",
                'url': f"{website.get('base_url', '')}/news/mock_{i+1}",
                'views': random.randint(1000, 100000),
                'likes': random.randint(10, 1000),
                'comments': random.randint(5, 500),
                'shares': random.randint(5, 500),
                'hot_score': round(random.uniform(1.0, 10.0), 2),
                'related_stocks': ','.join(stock_codes),
                'related_industries': ','.join(related_industries),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            articles.append(article)
        
        logger.info(f"为{website.get('name', website_id)}生成 {len(articles)} 篇模拟新闻")
        return articles
    
    def get_stock_quotes(self, stock_codes: List[str]) -> List[Dict]:
        """
        获取股票实时行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            股票行情列表
        """
        logger.info(f"获取股票行情: {stock_codes}")
        
        stock_quotes = []
        
        for stock_code in stock_codes:
            try:
                # 根据股票代码确定市场和API
                if stock_code.startswith('6'):
                    market = 'sh'
                    prefix = 'sh'
                elif stock_code.startswith('0') or stock_code.startswith('3'):
                    market = 'sz'
                    prefix = 'sz'
                elif stock_code.startswith('8'):
                    market = 'bj'
                    prefix = 'bj'
                else:
                    market = 'unknown'
                    prefix = ''
                
                # 构建API URL
                if prefix:
                    full_code = f"{prefix}{stock_code}"
                else:
                    full_code = stock_code
                
                # 模拟API调用
                quote = self._generate_mock_stock_quote(stock_code, market, full_code)
                if quote:
                    stock_quotes.append(quote)
                    
                    # 随机延迟
                    time.sleep(random.uniform(0.1, 0.5))
                    
            except Exception as e:
                logger.error(f"获取股票{stock_code}行情失败: {e}")
                continue
        
        logger.info(f"获取到 {len(stock_quotes)} 只股票行情")
        return stock_quotes
    
    def _generate_mock_stock_quote(self, stock_code: str, market: str, full_code: str) -> Dict:
        """生成模拟股票行情"""
        # 基础价格
        base_price = random.uniform(5.0, 100.0)
        
        # 涨跌幅（-10% 到 +10%）
        change_percent = random.uniform(-0.10, 0.10)
        change_amount = base_price * change_percent
        
        # 生成其他价格
        open_price = base_price * random.uniform(0.98, 1.02)
        high_price = max(base_price, open_price) * random.uniform(1.0, 1.05)
        low_price = min(base_price, open_price) * random.uniform(0.95, 1.0)
        close_price = base_price
        
        # 生成交易量
        volume = random.randint(1000000, 100000000)
        turnover = volume * close_price
        
        # 生成其他指标
        amplitude = (high_price - low_price) / close_price * 100
        turnover_rate = random.uniform(1.0, 10.0)
        pe_ratio = random.uniform(10.0, 50.0)
        pb_ratio = random.uniform(1.0, 5.0)
        dividend_yield = random.uniform(0.5, 5.0)
        roe = random.uniform(5.0, 20.0)
        
        # 股票名称映射
        stock_names = {
            '600519': '贵州茅台',
            '000858': '五粮液',
            '000333': '美的集团',
            '000001': '平安银行',
            '600036': '招商银行',
            '601318': '中国平安',
            '600276': '恒瑞医药',
            '000002': '万科A',
            '600887': '伊利股份',
            '600900': '长江电力'
        }
        
        stock_name = stock_names.get(stock_code, f"股票{stock_code}")
        
        # 行业
        industry = random.choice(self.industries)
        
        quote = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market': market,
            'industry': industry,
            'subindustry': '',
            'company_name': f"{stock_name}股份有限公司",
            'listing_date': f"20{random.randint(0, 3)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            'total_shares': random.uniform(1e9, 1e11),
            'circulating_shares': random.uniform(1e8, 1e10),
            'market_cap': random.uniform(1e10, 1e12),
            'circulating_market_cap': random.uniform(1e9, 1e11),
            'pe_ratio': round(pe_ratio, 2),
            'pb_ratio': round(pb_ratio, 2),
            'dividend_yield': round(dividend_yield, 2),
            'roe': round(roe, 2),
            'last_price': round(close_price, 2),
            'change_percent': round(change_percent * 100, 2),
            'change_amount': round(change_amount, 2),
            'open_price': round(open_price, 2),
            'high_price': round(high_price, 2),
            'low_price': round(low_price, 2),
            'close_price': round(close_price, 2),
            'volume': int(volume),
            'turnover': round(turnover, 2),
            'amplitude': round(amplitude, 2),
            'turnover_rate': round(turnover_rate, 2),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return quote
    
    def get_market_indices(self, market_codes: List[str] = None) -> List[Dict]:
        """
        获取市场指数
        
        Args:
            market_codes: 市场代码列表
            
        Returns:
            市场指数列表
        """
        if market_codes is None:
            market_codes = ['sh', 'sz', 'bj', 'hk', 'us']
        
        logger.info(f"获取市场指数: {market_codes}")
        
        indices = []
        
        # 主要指数配置
        index_configs = {
            'sh': [
                {'code': '000001', 'name': '上证指数'},
                {'code': '000300', 'name': '沪深300'},
                {'code': '000905', 'name': '中证500'}
            ],
            'sz': [
                {'code': '399001', 'name': '深证成指'},
                {'code': '399006', 'name': '创业板指'},
                {'code': '399005', 'name': '中小板指'}
            ],
            'bj': [
                {'code': '899050', 'name': '北证50'}
            ],
            'hk': [
                {'code': 'HSI', 'name': '恒生指数'},
                {'code': 'HSCEI', 'name': '国企指数'}
            ],
            'us': [
                {'code': 'DJI', 'name': '道琼斯指数'},
                {'code': 'SPX', 'name': '标普500'},
                {'code': 'IXIC', 'name': '纳斯达克指数'}
            ]
        }
        
        for market in market_codes:
            if market not in index_configs:
                continue
            
            for index_config in index_configs[market]:
                try:
                    index = self._generate_mock_market_index(index_config['code'], index_config['name'], market)
                    if index:
                        indices.append(index)
                except Exception as e:
                    logger.error(f"获取指数{index_config['name']}失败: {e}")
                    continue
        
        logger.info(f"获取到 {len(indices)} 个市场指数")
        return indices
    
    def _generate_mock_market_index(self, index_code: str, index_name: str, market: str) -> Dict:
        """生成模拟市场指数"""
        # 基础点位
        if '上证' in index_name or '沪深' in index_name:
            base_point = random.uniform(3000.0, 3500.0)
        elif '深证' in index_name or '创业' in index_name:
            base_point = random.uniform(1000.0, 2000.0)
        elif '恒生' in index_name:
            base_point = random.uniform(15000.0, 25000.0)
        elif '道琼斯' in index_name:
            base_point = random.uniform(30000.0, 35000.0)
        elif '标普' in index_name:
            base_point = random.uniform(4000.0, 5000.0)
        elif '纳斯达克' in index_name:
            base_point = random.uniform(12000.0, 15000.0)
        else:
            base_point = random.uniform(1000.0, 5000.0)
        
        # 涨跌幅（-3% 到 +3%）
        change_percent = random.uniform(-0.03, 0.03)
        change_amount = base_point * change_percent
        
        # 生成其他价格
        open_point = base_point * random.uniform(0.99, 1.01)
        high_point = max(base_point, open_point) * random.uniform(1.0, 1.02)
        low_point = min(base_point, open_point) * random.uniform(0.98, 1.0)
        close_point = base_point
        
        # 生成交易量
        volume = random.randint(1e9, 1e11)
        turnover = random.uniform(1e11, 1e13)
        
        # 生成其他指标
        pe_ratio = random.uniform(10.0, 20.0)
        pb_ratio = random.uniform(1.0, 2.0)
        dividend_yield = random.uniform(1.0, 3.0)
        
        index = {
            'index_code': index_code,
            'index_name': index_name,
            'market': market,
            'last_price': round(close_point, 2),
            'change_percent': round(change_percent * 100, 2),
            'change_amount': round(change_amount, 2),
            'open_price': round(open_point, 2),
            'high_price': round(high_point, 2),
            'low_price': round(low_point, 2),
            'close_price': round(close_point, 2),
            'volume': int(volume),
            'turnover': round(turnover, 2),
            'pe_ratio': round(pe_ratio, 2),
            'pb_ratio': round(pb_ratio, 2),
            'dividend_yield': round(dividend_yield, 2),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return index
    
    def get_news_detail(self, news_url: str) -> Optional[Dict]:
        """
        获取新闻详情
        
        Args:
            news_url: 新闻URL
            
        Returns:
            新闻详情字典
        """
        logger.info(f"获取新闻详情: {news_url}")
        
        # 确定网站
        website_id = None
        for w_id, website in self.websites.items():
            if website['base_url'] in news_url:
                website_id = w_id
                break
        
        if not website_id:
            logger.warning(f"无法识别的网站: {news_url}")
            return None
        
        response = self.safe_request(news_url, use_cache=True, cache_age=60)
        if not response:
            logger.warning(f"获取新闻详情失败: {news_url}")
            return self._generate_mock_news_detail(news_url, website_id)
        
        try:
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文章内容
            content = self._extract_news_content(soup, website_id)
            
            # 提取其他信息
            title = self._extract_news_title(soup)
            author = self._extract_news_author(soup)
            publish_time = self._extract_news_publish_time(soup)
            
            # 计算字数
            word_count = len(content) if content else 0
            
            # 提取关键词
            keywords = self._extract_news_keywords(content)
            
            # 计算情感分数（模拟）
            sentiment_score = round(random.uniform(-0.5, 0.5), 2)
            
            detail = {
                'content': content,
                'content_html': str(soup.find('article') or soup.find('div', class_='content')),
                'word_count': word_count,
                'read_time': max(1, word_count // 300),  # 假设每分钟300字
                'keywords': ','.join(keywords[:5]),
                'sentiment_score': sentiment_score,
                'images': self._extract_news_images(soup),
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"解析新闻详情: {title}, {word_count}字")
            
            return detail
            
        except Exception as e:
            logger.error(f"解析新闻详情失败: {news_url}, 错误: {e}")
            return self._generate_mock_news_detail(news_url, website_id)
    
    def _extract_news_content(self, soup, website_id: str) -> str:
        """提取新闻内容"""
        content_selectors = {
            'eastmoney': ['.newsContent', '.article-content', '.content'],
            'sina': ['.article', '.art_content', '.content'],
            'wallstreetcn': ['.article-content', '.content-body', 'article']
        }
        
        selectors = content_selectors.get(website_id, ['article', '.content', '.article-content'])
        
        for selector in selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除脚本和样式
                for tag in content_elem(['script', 'style', 'iframe', 'nav', 'footer']):
                    tag.decompose()
                
                # 获取文本
                text = content_elem.get_text('\n', strip=True)
                if text and len(text) > 100:
                    return text
        
        return ''
    
    def _extract_news_title(self, soup) -> str:
        """提取新闻标题"""
        title_elem = soup.find('h1') or soup.find('title')
        return title_elem.get_text(strip=True) if title_elem else ''
    
    def _extract_news_author(self, soup) -> str:
        """提取新闻作者"""
        author_selectors = ['.author', '.article-author', '.byline', 'meta[name="author"]']
        
        for selector in author_selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                else:
                    return elem.get_text(strip=True)
        
        return ''
    
    def _extract_news_publish_time(self, soup) -> str:
        """提取新闻发布时间"""
        time_selectors = ['.publish-time', '.date', 'time', 'meta[property="article:published_time"]']
        
        for selector in time_selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    time_str = elem.get('content', '')
                else:
                    time_str = elem.get_text(strip=True) or elem.get('datetime', '')
                
                if time_str:
                    return time_str
        
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _extract_news_keywords(self, content: str) -> List[str]:
        """提取新闻关键词"""
        if not content:
            return []
        
        # 金融关键词
        finance_keywords = [
            '股票', '基金', '债券', '外汇', '期货',
            '投资', '融资', '上市', '并购', '重组',
            '财报', '业绩', '分红', '股息', '收益率',
            '利率', '汇率', '通胀', '通缩', 'GDP',
            'CPI', 'PPI', 'PMI', '货币政策', '财政政策'
        ]
        
        # 统计关键词出现次数
        keyword_counts = {}
        content_lower = content.lower()
        
        for keyword in finance_keywords:
            count = content_lower.count(keyword.lower())
            if count > 0:
                keyword_counts[keyword] = count
        
        # 按出现次数排序
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [kw for kw, _ in sorted_keywords[:10]]
    
    def _extract_news_images(self, soup) -> str:
        """提取新闻图片"""
        images = []
        img_tags = soup.find_all('img', src=True)
        
        for img in img_tags[:10]:  # 限制数量
            src = img.get('src', '')
            if src and src.startswith(('http://', 'https://')):
                images.append(src)
        
        return ','.join(images)
    
    def _generate_mock_news_detail(self, news_url: str, website_id: str) -> Dict:
        """生成模拟新闻详情"""
        content = f"""
        这是一篇来自{self.websites.get(website_id, {}).get('name', website_id)}的深度财经报道。

        文章主要分为以下几个部分：

        1. 市场概况
        详细介绍了当前的市场环境和主要指数表现。

        2. 行业分析
        深入分析了相关行业的发展现状和趋势。

        3. 公司研究
        对重点公司进行了详细的研究和分析。

        4. 投资策略
        基于当前市场环境，提出了具体的投资建议。

        5. 风险提示
        指出了投资中需要注意的主要风险。

        这篇文章对于投资者具有重要的参考价值，建议仔细阅读。
        """
        
        return {
            'content': content,
            'content_html': f'<div class="content">{content}</div>',
            'word_count': len(content),
            'read_time': max(1, len(content) // 300),
            'keywords': '财经,股票,投资,市场,分析',
            'sentiment_score': round(random.uniform(0.0, 0.5), 2),
            'images': f'https://example.com/images/{website_id}_news_1.jpg,https://example.com/images/{website_id}_news_2.jpg',
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def save_to_database(self, data_type: str, data: List[Dict]):
        """保存数据到数据库"""
        if not data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type == 'news':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO finance_news 
                        (news_id, website_id, title, subtitle, author, 
                         publish_time, update_time, category, subcategory, 
                         tags, summary, content, content_html, word_count, 
                         read_time, cover_image, images, url, source_url, 
                         views, likes, comments, shares, hot_score, 
                         keywords, sentiment_score, related_stocks, 
                         related_industries, crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('news_id'),
                        item.get('website_id'),
                        item.get('title'),
                        item.get('subtitle', ''),
                        item.get('author', ''),
                        item.get('publish_time'),
                        item.get('publish_time'),  # update_time same as publish_time
                        item.get('category', ''),
                        item.get('subcategory', ''),
                        item.get('tags', ''),
                        item.get('summary', ''),
                        '',  # content - would be filled separately
                        '',  # content_html - would be filled separately
                        item.get('word_count', 0),
                        item.get('read_time', 0),
                        item.get('cover_image', ''),
                        item.get('images', ''),
                        item.get('url', ''),
                        item.get('url', ''),  # source_url same as url
                        item.get('views', 0),
                        item.get('likes', 0),
                        item.get('comments', 0),
                        item.get('shares', 0),
                        item.get('hot_score', 0.0),
                        item.get('keywords', ''),
                        item.get('sentiment_score', 0.0),
                        item.get('related_stocks', ''),
                        item.get('related_industries', ''),
                        item.get('crawl_time'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                logger.info(f"保存 {len(data)} 条新闻到数据库")
                
            elif data_type == 'stocks':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO stocks 
                        (stock_code, stock_name, market, industry, subindustry, 
                         company_name, listing_date, total_shares, circulating_shares, 
                         market_cap, circulating_market_cap, pe_ratio, pb_ratio, 
                         dividend_yield, roe, last_price, change_percent, 
                         change_amount, open_price, high_price, low_price, 
                         close_price, volume, turnover, amplitude, turnover_rate, 
                         update_time, crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', tuple(item.values()))
                
                logger.info(f"保存 {len(data)} 只股票到数据库")
                
            elif data_type == 'indices':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO market_indices 
                        (index_code, index_name, market, last_price, 
                         change_percent, change_amount, open_price, 
                         high_price, low_price, close_price, volume, 
                         turnover, pe_ratio, pb_ratio, dividend_yield, 
                         update_time, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', tuple(item.values()))
                
                logger.info(f"保存 {len(data)} 个指数到数据库")
            
            conn.commit()
            self.crawl_stats['successful'] += len(data)
            
        except sqlite3.Error as e:
            self.crawl_stats['failed'] += len(data)
            logger.error(f"保存到数据库失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def save_to_json(self, data: Any, filename: str):
        """保存数据到JSON文件"""
        try:
            json_dir = os.path.join(self.data_dir, 'json')
            filepath = os.path.join(json_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据保存到JSON: {filepath}")
            
        except Exception as e:
            logger.error(f"保存JSON失败: {e}")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """保存数据到CSV文件"""
        if not data:
            logger.warning("没有数据可保存到CSV")
            return
        
        try:
            csv_dir = os.path.join(self.data_dir, 'csv')
            filepath = os.path.join(csv_dir, filename)
            
            # 获取所有字段
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"数据保存到CSV: {filepath}")
            
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """保存数据到Excel文件"""
        if not data:
            logger.warning("没有数据可保存到Excel")
            return
        
        try:
            excel_dir = os.path.join(self.data_dir, 'excel')
            filepath = os.path.join(excel_dir, filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 保存到Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            logger.info(f"数据保存到Excel: {filepath}")
            
        except Exception as e:
            logger.error(f"保存Excel失败: {e}")
    
    def run(self, max_websites: int = 2, categories_per_website: int = 2, 
           news_per_category: int = 3, stocks_count: int = 5):
        """
        运行爬虫
        
        Args:
            max_websites: 最大网站数量
            categories_per_website: 每个网站最大分类数量
            news_per_category: 每个分类最大新闻数量
            stocks_count: 股票数量
        """
        logger.info("=== 金融资讯爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 选择要爬取的网站
            website_ids = list(self.websites.keys())[:max_websites]
            self.crawl_stats['total_websites'] = len(website_ids)
            
            all_news = []
            all_news_details = []
            
            # 2. 处理每个网站
            for website_id in website_ids:
                website = self.websites[website_id]
                logger.info(f"处理网站: {website['name']}")
                
                # 获取分类
                categories = ['财经', '股票', '基金'][:categories_per_website]
                
                website_news = []
                website_news_details = []
                
                # 3. 处理每个分类
                for category in categories:
                    logger.info(f"  处理分类: {category}")
                    
                    # 获取新闻列表
                    news = self.get_finance_news(
                        website_id=website_id,
                        category=category,
                        page=1,
                        page_size=news_per_category
                    )
                    
                    # 获取新闻详情
                    news_details = []
                    for news_item in news:
                        detail = self.get_news_detail(news_item.get('url', ''))
                        if detail:
                            news_details.append(detail)
                        
                        # 随机延迟
                        time.sleep(random.uniform(0.5, 1.5))
                    
                    website_news.extend(news)
                    website_news_details.extend(news_details)
                    
                    # 保存分类数据
                    if news:
                        cat_name = category.replace('/', '_')
                        self.save_to_csv(news, f"{website_id}_{cat_name}_news.csv")
                
                # 4. 保存网站数据
                if website_news:
                    self.save_to_csv(website_news, f"{website_id}_all_news.csv")
                    self.save_to_json(website_news_details, f"{website_id}_news_details.json")
                    
                    # 保存到数据库
                    self.save_to_database('news', website_news)
                
                all_news.extend(website_news)
                all_news_details.extend(website_news_details)
                
                # 更新统计
                self.crawl_stats['total_news'] += len(website_news)
            
            # 5. 获取股票数据
            logger.info("获取股票数据...")
            
            # 生成股票代码
            stock_codes = []
            for _ in range(stocks_count):
                market = random.choice(['sh', 'sz'])
                if market == 'sh':
                    stock_codes.append(f"600{random.randint(100, 999):03d}")
                else:
                    stock_codes.append(f"000{random.randint(100, 999):03d}")
            
            # 获取股票行情
            stocks = self.get_stock_quotes(stock_codes)
            self.crawl_stats['total_stocks'] = len(stocks)
            
            if stocks:
                self.save_to_csv(stocks, "stock_quotes.csv")
                self.save_to_excel(stocks, "stock_quotes.xlsx")
                self.save_to_database('stocks', stocks)
            
            # 6. 获取市场指数
            logger.info("获取市场指数...")
            
            indices = self.get_market_indices(['sh', 'sz'])
            self.crawl_stats['total_markets'] = len(indices)
            
            if indices:
                self.save_to_csv(indices, "market_indices.csv")
                self.save_to_database('indices', indices)
            
            # 7. 保存所有数据
            if all_news:
                self.save_to_csv(all_news, "all_finance_news.csv")
            
            if all_news_details:
                self.save_to_json(all_news_details, "all_news_details.json")
            
            # 8. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 金融资讯爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = FinanceNewsCrawler()
    
    # 运行爬虫
    crawler.run(
        max_websites=2,
        categories_per_website=2,
        news_per_category=2,
        stocks_count=3
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("金融资讯爬虫使用说明")
    print("="*60)
    print("支持的网站:")
    for website_id, website in crawler.websites.items():
        print(f"  - {website_id}: {website['name']} ({website['base_url']})")
    
    print("\n主要功能:")
    print("1. 获取财经新闻:")
    print("   news = crawler.get_finance_news('eastmoney', '财经', page=1, page_size=10)")
    print("\n2. 获取股票行情:")
    print("   stocks = crawler.get_stock_quotes(['600519', '000858'])")
    print("\n3. 获取市场指数:")
    print("   indices = crawler.get_market_indices(['sh', 'sz'])")
    print("\n4. 获取新闻详情:")
    print("   detail = crawler.get_news_detail(news_url)")
    print("\n5. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("   crawler.save_to_excel(data, 'filename.xlsx')")
    print("\n6. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")

if __name__ == "__main__":
    main()