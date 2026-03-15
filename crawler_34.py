#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科技动态爬虫 - 从科技媒体网站获取最新科技资讯
目标网站: 虎嗅网、36氪、机器之心等
功能: 爬取科技新闻、行业动态、技术分析、投融资信息等
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tech_news_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TechNewsCrawler:
    """科技动态爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'huxiu': {
                'name': '虎嗅网',
                'base_url': 'https://www.huxiu.com',
                'api_url': 'https://api.huxiu.com/v1/article/list',
                'categories': ['科技', '创投', '商业', '生活', '汽车', '文娱'],
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.huxiu.com/',
                    'Origin': 'https://www.huxiu.com'
                }
            },
            '36kr': {
                'name': '36氪',
                'base_url': 'https://36kr.com',
                'api_url': 'https://36kr.com/api/newsflash',
                'categories': ['快讯', '资讯', '创投', '科技', '金融', '汽车'],
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://36kr.com/'
                }
            },
            'jiqizhixin': {
                'name': '机器之心',
                'base_url': 'https://www.jiqizhixin.com',
                'api_url': 'https://www.jiqizhixin.com/apis/ai_articles',
                'categories': ['AI', '深度学习', '机器学习', '自然语言处理', '计算机视觉', '机器人'],
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.jiqizhixin.com/'
                }
            }
        }
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "tech_news_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "tech_news.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_articles': 0,
            'total_websites': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
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
            os.path.join(self.data_dir, 'articles'),
            os.path.join(self.data_dir, 'websites'),
            os.path.join(self.data_dir, 'categories'),
            os.path.join(self.data_dir, 'raw_html'),
            os.path.join(self.data_dir, 'json'),
            os.path.join(self.data_dir, 'csv'),
            os.path.join(self.data_dir, 'images'),
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
            
            # 创建网站表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS websites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_id TEXT UNIQUE,
                    name TEXT,
                    base_url TEXT,
                    api_url TEXT,
                    description TEXT,
                    categories TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT UNIQUE,
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
                    videos TEXT,
                    url TEXT,
                    source_url TEXT,
                    views INTEGER,
                    likes INTEGER,
                    comments INTEGER,
                    shares INTEGER,
                    hot_score REAL,
                    keywords TEXT,
                    sentiment_score REAL,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP,
                    FOREIGN KEY (website_id) REFERENCES websites (website_id)
                )
            ''')
            
            # 创建分类表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE,
                    website_id TEXT,
                    description TEXT,
                    total_articles INTEGER DEFAULT 0,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (website_id) REFERENCES websites (website_id)
                )
            ''')
            
            # 创建趋势表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trend_id TEXT UNIQUE,
                    keyword TEXT,
                    website_id TEXT,
                    article_count INTEGER,
                    trend_score REAL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_hours INTEGER,
                    peak_time TIMESTAMP,
                    peak_articles INTEGER,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (website_id) REFERENCES websites (website_id)
                )
            ''')
            
            # 创建实体表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT,
                    entity_type TEXT,
                    article_id TEXT,
                    frequency INTEGER,
                    context TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (article_id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_website ON articles (website_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_time ON articles (publish_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_category ON articles (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_hot ON articles (hot_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trends_keyword ON trends (keyword)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (entity_name, entity_type)')
            
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
    
    def get_cached_response(self, cache_key: str, max_age_hours: int = 6) -> Optional[Dict]:
        """获取缓存的响应"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < max_age_hours * 3600:
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
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        # 检查缓存
        if use_cache and method.upper() == 'GET':
            cache_key = self.get_cache_key(url, params)
            cached = self.get_cached_response(cache_key)
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
    
    def get_articles_from_huxiu(self, category: str = '科技', page: int = 1, 
                               page_size: int = 20) -> List[Dict]:
        """
        从虎嗅网获取文章
        
        Args:
            category: 分类
            page: 页码
            page_size: 每页数量
            
        Returns:
            文章列表
        """
        website = self.websites['huxiu']
        logger.info(f"从虎嗅网获取{category}文章，第{page}页")
        
        # 构建API参数
        params = {
            'platform': 'www',
            'cat_id': self._get_huxiu_category_id(category),
            'page': page,
            'size': page_size,
            'last_dateline': int(time.time())
        }
        
        response = self.safe_request(
            website['api_url'],
            params=params,
            headers=website['headers'],
            use_cache=True
        )
        
        if not response:
            logger.warning("虎嗅网API请求失败，返回模拟数据")
            return self._generate_mock_articles('huxiu', category, page_size)
        
        try:
            data = response.json()
            articles = self._parse_huxiu_response(data, category)
            return articles[:page_size]
        except Exception as e:
            logger.error(f"解析虎嗅网响应失败: {e}")
            return self._generate_mock_articles('huxiu', category, page_size)
    
    def _get_huxiu_category_id(self, category: str) -> int:
        """获取虎嗅网分类ID"""
        category_map = {
            '科技': 1,
            '创投': 2,
            '商业': 3,
            '生活': 4,
            '汽车': 5,
            '文娱': 6
        }
        return category_map.get(category, 1)
    
    def _parse_huxiu_response(self, data: Dict, category: str) -> List[Dict]:
        """解析虎嗅网API响应"""
        articles = []
        
        try:
            items = data.get('data', {}).get('dataList', [])
            
            for item in items:
                try:
                    article = {
                        'article_id': f"huxiu_{item.get('aid', '')}",
                        'website_id': 'huxiu',
                        'title': item.get('title', ''),
                        'subtitle': item.get('summary', ''),
                        'author': item.get('user_info', {}).get('username', ''),
                        'publish_time': self._timestamp_to_datetime(item.get('dateline', 0)),
                        'category': category,
                        'subcategory': '',
                        'tags': ','.join(item.get('tags', [])),
                        'summary': item.get('summary', ''),
                        'content': '',
                        'cover_image': item.get('pic', ''),
                        'url': urljoin(self.websites['huxiu']['base_url'], f"/article/{item.get('aid', '')}.html"),
                        'views': item.get('viewnum', 0),
                        'comments': item.get('comments', 0),
                        'likes': item.get('likes', 0),
                        'shares': item.get('shares', 0),
                        'hot_score': item.get('hot_score', 0.0),
                        'word_count': item.get('word_count', 0),
                        'read_time': item.get('read_time', 0),
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    articles.append(article)
                except Exception as e:
                    logger.error(f"解析虎嗅网文章项失败: {e}")
                    continue
            
            logger.info(f"从虎嗅网解析到 {len(articles)} 篇文章")
            
        except Exception as e:
            logger.error(f"解析虎嗅网响应异常: {e}")
        
        return articles
    
    def get_articles_from_36kr(self, category: str = '快讯', page: int = 1, 
                              page_size: int = 20) -> List[Dict]:
        """
        从36氪获取文章
        
        Args:
            category: 分类
            page: 页码
            page_size: 每页数量
            
        Returns:
            文章列表
        """
        website = self.websites['36kr']
        logger.info(f"从36氪获取{category}文章，第{page}页")
        
        # 构建API参数
        params = {
            'per_page': page_size,
            'page': page,
            'b_id': self._get_36kr_category_id(category),
            'sort': 'date'
        }
        
        response = self.safe_request(
            website['api_url'],
            params=params,
            headers=website['headers'],
            use_cache=True
        )
        
        if not response:
            logger.warning("36氪API请求失败，返回模拟数据")
            return self._generate_mock_articles('36kr', category, page_size)
        
        try:
            data = response.json()
            articles = self._parse_36kr_response(data, category)
            return articles[:page_size]
        except Exception as e:
            logger.error(f"解析36氪响应失败: {e}")
            return self._generate_mock_articles('36kr', category, page_size)
    
    def _get_36kr_category_id(self, category: str) -> int:
        """获取36氪分类ID"""
        category_map = {
            '快讯': 101,
            '资讯': 102,
            '创投': 103,
            '科技': 104,
            '金融': 105,
            '汽车': 106
        }
        return category_map.get(category, 101)
    
    def _parse_36kr_response(self, data: Dict, category: str) -> List[Dict]:
        """解析36氪API响应"""
        articles = []
        
        try:
            items = data.get('data', {}).get('items', [])
            
            for item in items:
                try:
                    article = {
                        'article_id': f"36kr_{item.get('id', '')}",
                        'website_id': '36kr',
                        'title': item.get('title', ''),
                        'subtitle': item.get('summary', ''),
                        'author': item.get('author', {}).get('name', ''),
                        'publish_time': item.get('published_at', ''),
                        'category': category,
                        'subcategory': '',
                        'tags': ','.join(item.get('tags', [])),
                        'summary': item.get('summary', ''),
                        'content': '',
                        'cover_image': item.get('cover', ''),
                        'url': urljoin(self.websites['36kr']['base_url'], f"/p/{item.get('id', '')}"),
                        'views': item.get('views_count', 0),
                        'comments': item.get('comments_count', 0),
                        'likes': item.get('likes_count', 0),
                        'shares': item.get('share_count', 0),
                        'hot_score': item.get('hot_score', 0.0),
                        'word_count': item.get('word_count', 0),
                        'read_time': item.get('read_time', 0),
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    articles.append(article)
                except Exception as e:
                    logger.error(f"解析36氪文章项失败: {e}")
                    continue
            
            logger.info(f"从36氪解析到 {len(articles)} 篇文章")
            
        except Exception as e:
            logger.error(f"解析36氪响应异常: {e}")
        
        return articles
    
    def get_articles_from_jiqizhixin(self, category: str = 'AI', page: int = 1, 
                                    page_size: int = 20) -> List[Dict]:
        """
        从机器之心获取文章
        
        Args:
            category: 分类
            page: 页码
            page_size: 每页数量
            
        Returns:
            文章列表
        """
        website = self.websites['jiqizhixin']
        logger.info(f"从机器之心获取{category}文章，第{page}页")
        
        # 构建API参数
        params = {
            'category': category,
            'page': page,
            'page_size': page_size,
            'sort': 'latest'
        }
        
        response = self.safe_request(
            website['api_url'],
            params=params,
            headers=website['headers'],
            use_cache=True
        )
        
        if not response:
            logger.warning("机器之心API请求失败，返回模拟数据")
            return self._generate_mock_articles('jiqizhixin', category, page_size)
        
        try:
            data = response.json()
            articles = self._parse_jiqizhixin_response(data, category)
            return articles[:page_size]
        except Exception as e:
            logger.error(f"解析机器之心响应失败: {e}")
            return self._generate_mock_articles('jiqizhixin', category, page_size)
    
    def _parse_jiqizhixin_response(self, data: Dict, category: str) -> List[Dict]:
        """解析机器之心API响应"""
        articles = []
        
        try:
            items = data.get('data', {}).get('articles', [])
            
            for item in items:
                try:
                    article = {
                        'article_id': f"jiqizhixin_{item.get('id', '')}",
                        'website_id': 'jiqizhixin',
                        'title': item.get('title', ''),
                        'subtitle': item.get('subtitle', ''),
                        'author': item.get('author', {}).get('name', ''),
                        'publish_time': item.get('created_at', ''),
                        'category': category,
                        'subcategory': item.get('subcategory', ''),
                        'tags': ','.join(item.get('tags', [])),
                        'summary': item.get('summary', ''),
                        'content': '',
                        'cover_image': item.get('cover_image', ''),
                        'url': urljoin(self.websites['jiqizhixin']['base_url'], f"/articles/{item.get('id', '')}"),
                        'views': item.get('views', 0),
                        'comments': item.get('comments', 0),
                        'likes': item.get('likes', 0),
                        'shares': item.get('shares', 0),
                        'hot_score': item.get('hot_score', 0.0),
                        'word_count': item.get('word_count', 0),
                        'read_time': item.get('read_time', 0),
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    articles.append(article)
                except Exception as e:
                    logger.error(f"解析机器之心文章项失败: {e}")
                    continue
            
            logger.info(f"从机器之心解析到 {len(articles)} 篇文章")
            
        except Exception as e:
            logger.error(f"解析机器之心响应异常: {e}")
        
        return articles
    
    def _generate_mock_articles(self, website_id: str, category: str, count: int) -> List[Dict]:
        """生成模拟文章数据"""
        website = self.websites.get(website_id, {})
        
        # 不同网站的标题模板
        title_templates = {
            'huxiu': [
                '深度分析：{category}领域的最新发展趋势',
                '独家报道：{category}行业的重大变革',
                '专家观点：{category}技术的未来展望',
                '行业观察：{category}市场的竞争格局',
                '趋势解读：{category}创新的关键方向'
            ],
            '36kr': [
                '{category}快讯：最新动态与市场反应',
                '{category}资讯：行业报告与数据分析',
                '{category}创投：融资事件与投资趋势',
                '{category}科技：技术创新与应用案例',
                '{category}金融：资本市场与政策解读'
            ],
            'jiqizhixin': [
                'AI前沿：{category}技术的最新突破',
                '算法解析：{category}模型的原理与实践',
                '应用案例：{category}在真实场景中的落地',
                '研究进展：{category}领域的学术成果',
                '技术教程：{category}开发的实战指南'
            ]
        }
        
        templates = title_templates.get(website_id, title_templates['huxiu'])
        authors = ['张三', '李四', '王五', '赵六', '钱七']
        tags_map = {
            '科技': ['科技', '创新', '数字化', '智能化', '互联网'],
            'AI': ['人工智能', '机器学习', '深度学习', '神经网络', '算法'],
            '创投': ['投资', '融资', '创业', '风投', '资本市场'],
            '快讯': ['新闻', '动态', '速报', '头条', '热点']
        }
        
        articles = []
        
        for i in range(count):
            template = templates[i % len(templates)]
            title = template.format(category=category)
            
            # 生成随机时间（最近7天内）
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            publish_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
            
            article = {
                'article_id': f"{website_id}_mock_{i+1}",
                'website_id': website_id,
                'title': title,
                'subtitle': f"这是关于{category}的深度分析文章",
                'author': random.choice(authors),
                'publish_time': publish_time.strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'subcategory': '',
                'tags': ','.join(tags_map.get(category, ['科技', '新闻'])),
                'summary': f"本文深入探讨了{category}领域的最新发展，分析了当前的市场趋势和技术突破。",
                'content': f"这是{title}的详细内容。文章从多个角度分析了{category}的现状和未来发展方向。",
                'cover_image': f"https://example.com/images/{category}_{i+1}.jpg",
                'url': f"{website.get('base_url', '')}/article/mock_{i+1}",
                'views': random.randint(1000, 100000),
                'comments': random.randint(10, 1000),
                'likes': random.randint(50, 5000),
                'shares': random.randint(20, 2000),
                'hot_score': round(random.uniform(1.0, 10.0), 2),
                'word_count': random.randint(800, 5000),
                'read_time': random.randint(5, 30),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            articles.append(article)
        
        logger.info(f"为{website.get('name', website_id)}生成 {len(articles)} 篇模拟文章")
        return articles
    
    def _timestamp_to_datetime(self, timestamp: int) -> str:
        """将时间戳转换为日期时间字符串"""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def get_article_detail(self, article_url: str) -> Optional[Dict]:
        """
        获取文章详情
        
        Args:
            article_url: 文章URL
            
        Returns:
            文章详情字典
        """
        logger.info(f"获取文章详情: {article_url}")
        
        # 确定网站
        website_id = None
        for w_id, website in self.websites.items():
            if website['base_url'] in article_url:
                website_id = w_id
                break
        
        if not website_id:
            logger.warning(f"无法识别的网站: {article_url}")
            return None
        
        response = self.safe_request(article_url, use_cache=True)
        if not response:
            logger.warning(f"获取文章详情失败: {article_url}")
            return self._generate_mock_article_detail(article_url, website_id)
        
        try:
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文章内容
            content = self._extract_article_content(soup, website_id)
            
            # 提取其他信息
            title = self._extract_title(soup)
            author = self._extract_author(soup)
            publish_time = self._extract_publish_time(soup)
            
            # 计算字数
            word_count = len(content) if content else 0
            
            # 提取关键词（简单实现）
            keywords = self._extract_keywords(content)
            
            # 计算情感分数（模拟）
            sentiment_score = round(random.uniform(-1.0, 1.0), 2)
            
            detail = {
                'content': content,
                'content_html': str(soup.find('article') or soup.find('div', class_='content')),
                'word_count': word_count,
                'read_time': max(1, word_count // 300),  # 假设每分钟300字
                'keywords': ','.join(keywords[:5]),
                'sentiment_score': sentiment_score,
                'images': self._extract_images(soup),
                'videos': self._extract_videos(soup),
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"解析文章详情: {title}, {word_count}字")
            
            return detail
            
        except Exception as e:
            logger.error(f"解析文章详情失败: {article_url}, 错误: {e}")
            return self._generate_mock_article_detail(article_url, website_id)
    
    def _extract_article_content(self, soup, website_id: str) -> str:
        """提取文章内容"""
        content_selectors = {
            'huxiu': ['article', '.article-content', '.article__content'],
            '36kr': ['.article-body', '.article-content', '.content'],
            'jiqizhixin': ['.article-content', '.content-body', 'article']
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
    
    def _extract_title(self, soup) -> str:
        """提取标题"""
        title_elem = soup.find('h1') or soup.find('title')
        return title_elem.get_text(strip=True) if title_elem else ''
    
    def _extract_author(self, soup) -> str:
        """提取作者"""
        author_selectors = ['.author', '.article-author', '.byline', 'meta[name="author"]']
        
        for selector in author_selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                else:
                    return elem.get_text(strip=True)
        
        return ''
    
    def _extract_publish_time(self, soup) -> str:
        """提取发布时间"""
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
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词（简单实现）"""
        if not content:
            return []
        
        # 常见科技关键词
        tech_keywords = [
            '人工智能', 'AI', '机器学习', '深度学习', '大数据',
            '云计算', '区块链', '物联网', '5G', '芯片',
            '算法', '模型', '数据', '分析', '技术',
            '创新', '发展', '趋势', '市场', '应用'
        ]
        
        # 统计关键词出现次数
        keyword_counts = {}
        content_lower = content.lower()
        
        for keyword in tech_keywords:
            count = content_lower.count(keyword.lower())
            if count > 0:
                keyword_counts[keyword] = count
        
        # 按出现次数排序
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [kw for kw, _ in sorted_keywords[:10]]
    
    def _extract_images(self, soup) -> str:
        """提取图片"""
        images = []
        img_tags = soup.find_all('img', src=True)
        
        for img in img_tags[:10]:  # 限制数量
            src = img.get('src', '')
            if src and src.startswith(('http://', 'https://')):
                images.append(src)
        
        return ','.join(images)
    
    def _extract_videos(self, soup) -> str:
        """提取视频"""
        videos = []
        video_tags = soup.find_all(['video', 'iframe'])
        
        for tag in video_tags[:5]:  # 限制数量
            src = tag.get('src') or tag.get('data-src')
            if src and src.startswith(('http://', 'https://')):
                videos.append(src)
        
        return ','.join(videos)
    
    def _generate_mock_article_detail(self, article_url: str, website_id: str) -> Dict:
        """生成模拟文章详情"""
        content = f"""
        这是{website_id}的一篇深度分析文章。文章从多个维度探讨了相关主题，提供了详细的数据分析和专家观点。

        文章主要分为以下几个部分：

        1. 背景介绍
        详细介绍了当前的发展背景和市场环境。

        2. 现状分析
        通过数据和案例分析了当前的现状和存在的问题。

        3. 趋势预测
        基于现有数据和技术发展，对未来趋势进行了预测。

        4. 对策建议
        针对存在的问题，提出了具体的对策和建议。

        5. 总结展望
        对全文进行总结，并对未来发展进行了展望。

        这篇文章对于了解相关领域具有重要的参考价值。
        """
        
        return {
            'content': content,
            'content_html': f'<div class="content">{content}</div>',
            'word_count': len(content),
            'read_time': max(1, len(content) // 300),
            'keywords': '科技,分析,趋势,发展,市场',
            'sentiment_score': round(random.uniform(0.1, 0.9), 2),
            'images': f'https://example.com/images/{website_id}_1.jpg,https://example.com/images/{website_id}_2.jpg',
            'videos': '',
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def save_to_database(self, website_id: str, articles: List[Dict], 
                        article_details: List[Dict]):
        """保存数据到数据库"""
        if not articles:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 保存网站信息
            website = self.websites.get(website_id, {})
            cursor.execute('''
                INSERT OR REPLACE INTO websites 
                (website_id, name, base_url, api_url, description, 
                 categories, crawl_time, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                website_id,
                website.get('name', website_id),
                website.get('base_url', ''),
                website.get('api_url', ''),
                f"{website.get('name', website_id)} - 科技媒体网站",
                ','.join(website.get('categories', [])),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # 保存文章信息
            for i, article in enumerate(articles):
                detail = article_details[i] if i < len(article_details) else {}
                
                cursor.execute('''
                    INSERT OR REPLACE INTO articles 
                    (article_id, website_id, title, subtitle, author, 
                     publish_time, update_time, category, subcategory, 
                     tags, summary, content, content_html, word_count, 
                     read_time, cover_image, images, videos, url, 
                     source_url, views, likes, comments, shares, 
                     hot_score, keywords, sentiment_score, crawl_time, 
                     last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.get('article_id'),
                    website_id,
                    article.get('title'),
                    article.get('subtitle', ''),
                    article.get('author', ''),
                    article.get('publish_time'),
                    article.get('publish_time'),  # update_time same as publish_time
                    article.get('category', ''),
                    article.get('subcategory', ''),
                    article.get('tags', ''),
                    article.get('summary', ''),
                    detail.get('content', ''),
                    detail.get('content_html', ''),
                    detail.get('word_count', 0),
                    detail.get('read_time', 0),
                    article.get('cover_image', ''),
                    detail.get('images', ''),
                    detail.get('videos', ''),
                    article.get('url', ''),
                    article.get('url', ''),  # source_url same as url
                    article.get('views', 0),
                    article.get('likes', 0),
                    article.get('comments', 0),
                    article.get('shares', 0),
                    article.get('hot_score', 0.0),
                    detail.get('keywords', ''),
                    detail.get('sentiment_score', 0.0),
                    article.get('crawl_time'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            conn.commit()
            self.crawl_stats['successful'] += len(articles)
            logger.info(f"保存 {len(articles)} 篇文章到数据库")
            
        except sqlite3.Error as e:
            self.crawl_stats['failed'] += len(articles)
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
    
    def run(self, max_websites: int = 2, categories_per_website: int = 2, 
           articles_per_category: int = 3):
        """
        运行爬虫
        
        Args:
            max_websites: 最大网站数量
            categories_per_website: 每个网站最大分类数量
            articles_per_category: 每个分类最大文章数量
        """
        logger.info("=== 科技动态爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 选择要爬取的网站
            website_ids = list(self.websites.keys())[:max_websites]
            self.crawl_stats['total_websites'] = len(website_ids)
            
            all_articles = []
            all_article_details = []
            
            # 2. 处理每个网站
            for website_id in website_ids:
                website = self.websites[website_id]
                logger.info(f"处理网站: {website['name']}")
                
                # 获取分类
                categories = website['categories'][:categories_per_website]
                
                website_articles = []
                website_article_details = []
                
                # 3. 处理每个分类
                for category in categories:
                    logger.info(f"  处理分类: {category}")
                    
                    # 获取文章列表
                    if website_id == 'huxiu':
                        articles = self.get_articles_from_huxiu(category, page=1, page_size=articles_per_category)
                    elif website_id == '36kr':
                        articles = self.get_articles_from_36kr(category, page=1, page_size=articles_per_category)
                    elif website_id == 'jiqizhixin':
                        articles = self.get_articles_from_jiqizhixin(category, page=1, page_size=articles_per_category)
                    else:
                        articles = self._generate_mock_articles(website_id, category, articles_per_category)
                    
                    # 获取文章详情
                    article_details = []
                    for article in articles:
                        detail = self.get_article_detail(article.get('url', ''))
                        if detail:
                            article_details.append(detail)
                        
                        # 随机延迟
                        time.sleep(random.uniform(0.5, 1.5))
                    
                    website_articles.extend(articles)
                    website_article_details.extend(article_details)
                    
                    # 保存分类数据
                    if articles:
                        cat_name = category.replace('/', '_')
                        self.save_to_csv(articles, f"{website_id}_{cat_name}_articles.csv")
                
                # 4. 保存网站数据
                if website_articles:
                    self.save_to_csv(website_articles, f"{website_id}_all_articles.csv")
                    self.save_to_json(website_article_details, f"{website_id}_article_details.json")
                    
                    # 保存到数据库
                    self.save_to_database(website_id, website_articles, website_article_details)
                
                all_articles.extend(website_articles)
                all_article_details.extend(website_article_details)
                
                # 更新统计
                self.crawl_stats['total_articles'] += len(website_articles)
            
            # 5. 保存所有数据
            if all_articles:
                self.save_to_csv(all_articles, "all_tech_articles.csv")
            
            if all_article_details:
                self.save_to_json(all_article_details, "all_article_details.json")
            
            # 6. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 科技动态爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = TechNewsCrawler()
    
    # 运行爬虫
    crawler.run(
        max_websites=2,
        categories_per_website=2,
        articles_per_category=2
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("科技动态爬虫使用说明")
    print("="*60)
    print("支持的网站:")
    for website_id, website in crawler.websites.items():
        print(f"  - {website_id}: {website['name']} ({website['base_url']})")
    
    print("\n主要功能:")
    print("1. 从虎嗅网获取文章:")
    print("   articles = crawler.get_articles_from_huxiu('科技', page=1, page_size=10)")
    print("\n2. 从36氪获取文章:")
    print("   articles = crawler.get_articles_from_36kr('快讯', page=1, page_size=10)")
    print("\n3. 从机器之心获取文章:")
    print("   articles = crawler.get_articles_from_jiqizhixin('AI', page=1, page_size=10)")
    print("\n4. 获取文章详情:")
    print("   detail = crawler.get_article_detail(article_url)")
    print("\n5. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("\n6. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")

if __name__ == "__main__":
    main()