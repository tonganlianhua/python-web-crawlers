#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元宇宙动态爬虫 - 从元宇宙平台和资讯网站获取元宇宙相关数据
目标网站: Decentraland, The Sandbox, Roblox, Meta等
功能: 爬取元宇宙平台数据、虚拟地产、虚拟活动、用户统计等
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metaverse_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MetaverseCrawler:
    """元宇宙动态爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'decentraland': {
                'name': 'Decentraland',
                'base_url': 'https://decentraland.org',
                'api_base': 'https://api.decentraland.org',
                'marketplace_url': 'https://market.decentraland.org',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
            },
            'thesandbox': {
                'name': 'The Sandbox',
                'base_url': 'https://www.sandbox.game',
                'api_base': 'https://api.sandbox.game',
                'marketplace_url': 'https://www.sandbox.game/en/map',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'roblox': {
                'name': 'Roblox',
                'base_url': 'https://www.roblox.com',
                'api_base': 'https://economy.roblox.com',
                'marketplace_url': 'https://www.roblox.com/catalog',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'cryptovoxels': {
                'name': 'Cryptovoxels',
                'base_url': 'https://www.cryptovoxels.com',
                'api_base': 'https://api.cryptovoxels.com',
                'marketplace_url': 'https://www.cryptovoxels.com/market',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            }
        }
        
        # 元宇宙平台统计
        self.metaverse_platforms = [
            {'name': 'Decentraland', 'token': 'MANA', 'launch_year': 2017, 'blockchain': 'Ethereum'},
            {'name': 'The Sandbox', 'token': 'SAND', 'launch_year': 2018, 'blockchain': 'Ethereum'},
            {'name': 'Roblox', 'token': 'Robux', 'launch_year': 2006, 'blockchain': 'Centralized'},
            {'name': 'Cryptovoxels', 'token': 'ETH', 'launch_year': 2018, 'blockchain': 'Ethereum'},
            {'name': 'Somnium Space', 'token': 'CUBE', 'launch_year': 2018, 'blockchain': 'Ethereum'},
            {'name': 'Voxels', 'token': 'ETH', 'launch_year': 2018, 'blockchain': 'Ethereum'},
            {'name': 'Meta Horizon Worlds', 'token': 'None', 'launch_year': 2021, 'blockchain': 'Centralized'},
            {'name': 'Second Life', 'token': 'L$', 'launch_year': 2003, 'blockchain': 'Centralized'},
            {'name': 'Axie Infinity', 'token': 'AXS', 'launch_year': 2018, 'blockchain': 'Ronin'},
            {'name': 'Upland', 'token': 'UPX', 'launch_year': 2019, 'blockchain': 'EOS'}
        ]
        
        # 元宇宙应用场景
        self.metaverse_use_cases = [
            'Virtual Real Estate', 'Gaming', 'Social Networking', 'Virtual Events',
            'Education', 'E-commerce', 'Art Galleries', 'Music Concerts',
            'Fitness', 'Workplace Collaboration', 'Tourism', 'Healthcare',
            'Fashion', 'Real Estate Showcases', 'Car Dealerships', 'Museums'
        ]
        
        # 虚拟地产类型
        self.virtual_property_types = [
            'Parcel', 'Estate', 'Building', 'Mall', 'Gallery',
            'Concert Hall', 'Stadium', 'Park', 'Beach', 'Mountain',
            'Island', 'City Center', 'Roadside', 'Corner', 'Waterfront'
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "metaverse_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "metaverse.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_platforms': 0,
            'total_properties': 0,
            'total_events': 0,
            'total_users': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 请求限制
        self.rate_limits = {
            'decentraland': {'calls_per_minute': 60, 'last_call': 0},
            'thesandbox': {'calls_per_minute': 50, 'last_call': 0},
            'roblox': {'calls_per_minute': 100, 'last_call': 0},
            'cryptovoxels': {'calls_per_minute': 40, 'last_call': 0}
        }
    
    def _setup_session(self):
        """设置会话配置"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
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
            os.path.join(self.data_dir, 'platforms'),
            os.path.join(self.data_dir, 'properties'),
            os.path.join(self.data_dir, 'events'),
            os.path.join(self.data_dir, 'users'),
            os.path.join(self.data_dir, 'market_data'),
            os.path.join(self.data_dir, 'analytics'),
            os.path.join(self.data_dir, 'news'),
            os.path.join(self.data_dir, 'raw_data'),
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
            
            # 创建元宇宙平台表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metaverse_platforms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    website TEXT,
                    launch_year INTEGER,
                    blockchain TEXT,
                    native_token TEXT,
                    token_symbol TEXT,
                    total_users INTEGER,
                    daily_active_users INTEGER,
                    monthly_active_users INTEGER,
                    total_land_parcels INTEGER,
                    total_virtual_items INTEGER,
                    market_cap REAL,
                    market_cap_usd REAL,
                    total_volume_24h REAL,
                    total_volume_24h_usd REAL,
                    developer_count INTEGER,
                    partner_count INTEGER,
                    social_twitter TEXT,
                    social_discord TEXT,
                    social_telegram TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建虚拟地产表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS virtual_properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id TEXT UNIQUE,
                    platform_id TEXT,
                    name TEXT,
                    description TEXT,
                    coordinates TEXT,
                    parcel_id TEXT,
                    estate_id TEXT,
                    size_x INTEGER,
                    size_y INTEGER,
                    total_area REAL,
                    property_type TEXT,
                    owner_address TEXT,
                    owner_name TEXT,
                    current_price REAL,
                    current_price_usd REAL,
                    price_symbol TEXT,
                    last_sale_price REAL,
                    last_sale_price_usd REAL,
                    last_sale_date TEXT,
                    views INTEGER,
                    favorites INTEGER,
                    is_for_sale BOOLEAN,
                    is_for_rent BOOLEAN,
                    rental_price REAL,
                    rental_period TEXT,
                    amenities TEXT,
                    nearby_attractions TEXT,
                    image_url TEXT,
                    video_url TEXT,
                    tags TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (platform_id) REFERENCES metaverse_platforms (platform_id)
                )
            ''')
            
            # 创建虚拟活动表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS virtual_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    platform_id TEXT,
                    name TEXT,
                    description TEXT,
                    event_type TEXT,
                    location TEXT,
                    coordinates TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_hours REAL,
                    organizer TEXT,
                    organizer_type TEXT,
                    expected_attendance INTEGER,
                    actual_attendance INTEGER,
                    ticket_price REAL,
                    ticket_price_usd REAL,
                    ticket_symbol TEXT,
                    is_free BOOLEAN,
                    is_nft_gated BOOLEAN,
                    required_nft TEXT,
                    sponsors TEXT,
                    speakers TEXT,
                    agenda TEXT,
                    registration_url TEXT,
                    live_stream_url TEXT,
                    replay_url TEXT,
                    social_hashtag TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (platform_id) REFERENCES metaverse_platforms (platform_id)
                )
            ''')
            
            # 创建用户统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_id TEXT UNIQUE,
                    platform_id TEXT,
                    date TEXT,
                    total_users INTEGER,
                    new_users INTEGER,
                    active_users_24h INTEGER,
                    active_users_7d INTEGER,
                    active_users_30d INTEGER,
                    average_session_minutes REAL,
                    total_transactions INTEGER,
                    transaction_volume REAL,
                    transaction_volume_usd REAL,
                    nft_sales INTEGER,
                    nft_sales_volume REAL,
                    nft_sales_volume_usd REAL,
                    land_sales INTEGER,
                    land_sales_volume REAL,
                    land_sales_volume_usd REAL,
                    user_growth_rate REAL,
                    retention_rate REAL,
                    churn_rate REAL,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (platform_id) REFERENCES metaverse_platforms (platform_id)
                )
            ''')
            
            # 创建市场数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_id TEXT UNIQUE,
                    platform_id TEXT,
                    date TEXT,
                    token_price REAL,
                    token_price_usd REAL,
                    market_cap REAL,
                    market_cap_usd REAL,
                    volume_24h REAL,
                    volume_24h_usd REAL,
                    circulating_supply REAL,
                    total_supply REAL,
                    max_supply REAL,
                    fully_diluted_valuation REAL,
                    price_change_24h REAL,
                    price_change_7d REAL,
                    price_change_30d REAL,
                    all_time_high REAL,
                    all_time_high_date TEXT,
                    all_time_low REAL,
                    all_time_low_date TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (platform_id) REFERENCES metaverse_platforms (platform_id)
                )
            ''')
            
            # 创建新闻资讯表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metaverse_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id TEXT UNIQUE,
                    source TEXT,
                    title TEXT,
                    summary TEXT,
                    content TEXT,
                    url TEXT,
                    image_url TEXT,
                    publish_date TEXT,
                    author TEXT,
                    tags TEXT,
                    sentiment_score REAL,
                    related_platforms TEXT,
                    related_tokens TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_platforms_name ON metaverse_platforms (name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_properties_platform ON virtual_properties (platform_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_properties_price ON virtual_properties (current_price_usd)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_platform_time ON virtual_events (platform_id, start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_platform_date ON user_statistics (platform_id, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_platform_date ON market_data (platform_id, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_date ON metaverse_news (publish_date)')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def _check_rate_limit(self, website_id: str) -> bool:
        """检查API速率限制"""
        if website_id not in self.rate_limits:
            return True
        
        limit_info = self.rate_limits[website_id]
        current_time = time.time()
        
        # 检查是否超过速率限制
        if current_time - limit_info['last_call'] < 60 / limit_info['calls_per_minute']:
            wait_time = (60 / limit_info['calls_per_minute']) - (current_time - limit_info['last_call'])
            logger.info(f"达到速率限制，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        # 更新最后调用时间
        self.rate_limits[website_id]['last_call'] = time.time()
        return True
    
    def get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_str = url
        if params:
            key_str += json.dumps(params, sort_keys=True)
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached_response(self, cache_key: str, max_age_minutes: int = 15) -> Optional[Dict]:
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
                    website_id: Optional[str] = None,
                    use_cache: bool = True,
                    cache_age: int = 15,  # 分钟
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
            website_id: 网站ID（用于速率限制）
            use_cache: 是否使用缓存
            cache_age: 缓存有效期（分钟）
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        # 检查速率限制
        if website_id:
            self._check_rate_limit(website_id)
        
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
                
                if status_code == 429:  # 速率限制
                    retry_after = e.response.headers.get('Retry-After', 60)
                    logger.warning(f"速率限制，等待 {retry_after} 秒")
                    time.sleep(int(retry_after))
                    continue
                    
                if status_code in [403, 404]:
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
    
    def get_metaverse_platforms(self, limit: int = 10) -> List[Dict]:
        """
        获取元宇宙平台信息
        
        Args:
            limit: 限制数量
            
        Returns:
            元宇宙平台列表
        """
        logger.info(f"获取元宇宙平台信息，限制{limit}个")
        
        platforms = []
        
        for i in range(min(limit, len(self.metaverse_platforms))):
            platform_info = self.metaverse_platforms[i]
            
            # 生成平台数据
            total_users = random.randint(10000, 10000000)
            daily_active_users = int(total_users * random.uniform(0.01, 0.1))
            monthly_active_users = int(total_users * random.uniform(0.1, 0.3))
            
            total_land_parcels = random.randint(1000, 100000)
            total_virtual_items = random.randint(10000, 1000000)
            
            market_cap = random.uniform(1e6, 1e10)
            market_cap_usd = market_cap * random.uniform(0.5, 2.0)
            
            platform = {
                'platform_id': platform_info['name'].lower().replace(' ', '_'),
                'name': platform_info['name'],
                'description': f"{platform_info['name']} is a leading metaverse platform for {random.choice(self.metaverse_use_cases).lower()}.",
                'website': f"https://www.{platform_info['name'].lower().replace(' ', '')}.com",
                'launch_year': platform_info['launch_year'],
                'blockchain': platform_info['blockchain'],
                'native_token': platform_info['token'],
                'token_symbol': platform_info['token'],
                'total_users': total_users,
                'daily_active_users': daily_active_users,
                'monthly_active_users': monthly_active_users,
                'total_land_parcels': total_land_parcels,
                'total_virtual_items': total_virtual_items,
                'market_cap': round(market_cap, 2),
                'market_cap_usd': round(market_cap_usd, 2),
                'total_volume_24h': round(market_cap * random.uniform(0.001, 0.01), 2),
                'total_volume_24h_usd': round(market_cap_usd * random.uniform(0.001, 0.01), 2),
                'developer_count': random.randint(10, 1000),
                'partner_count': random.randint(5, 500),
                'social_twitter': f"@{platform_info['name'].replace(' ', '')}",
                'social_discord': f"https://discord.gg/{platform_info['name'].lower().replace(' ', '')}",
                'social_telegram': f"https://t.me/{platform_info['name'].lower().replace(' ', '')}",
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            platforms.append(platform)
        
        logger.info(f"生成 {len(platforms)} 个元宇宙平台信息")
        return platforms
    
    def get_platform_detail(self, platform_id: str) -> Optional[Dict]:
        """
        获取平台详情
        
        Args:
            platform_id: 平台ID
            
        Returns:
            平台详情字典
        """
        logger.info(f"获取元宇宙平台详情: {platform_id}")
        
        # 查找平台信息
        platform_info = None
        for platform in self.metaverse_platforms:
            if platform['name'].lower().replace(' ', '_') == platform_id:
                platform_info = platform
                break
        
        if not platform_info:
            logger.warning(f"未找到平台: {platform_id}")
            return None
        
        # 生成详细数据
        detail = {
            'platform_id': platform_id,
            'name': platform_info['name'],
            'description': f"{platform_info['name']} is a comprehensive metaverse platform that enables users to create, experience, and monetize content and applications in a virtual world.",
            'vision': "To build the most extensive and immersive metaverse where people can work, play, socialize, and create.",
            'technology_stack': 'Blockchain, VR/AR, 3D Graphics, Cloud Computing',
            'key_features': ','.join([
                'Virtual Land Ownership',
                'User-Generated Content',
                'Social Interactions',
                'Economic System',
                'Cross-Platform Compatibility'
            ]),
            'supported_devices': 'PC, Mac, VR Headets, Mobile',
            'supported_languages': 'English, Spanish, Chinese, Japanese, Korean',
            'governance_model': 'DAO' if platform_info['blockchain'] != 'Centralized' else 'Centralized',
            'token_utility': 'Governance, Staking, Payments, Rewards',
            'revenue_model': 'Transaction Fees, Premium Features, Advertising',
            'investment_rounds': json.dumps([
                {'round': 'Seed', 'amount': random.randint(1, 10), 'date': '2020-01-01'},
                {'round': 'Series A', 'amount': random.randint(10, 50), 'date': '2021-01-01'},
                {'round': 'Series B', 'amount': random.randint(50, 200), 'date': '2022-01-01'}
            ]),
            'team_size': random.randint(50, 500),
            'headquarters': random.choice(['San Francisco, USA', 'Singapore', 'London, UK', 'Tokyo, Japan']),
            'founding_date': f"{platform_info['launch_year']}-01-01",
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return detail
    
    def get_virtual_properties(self, platform_id: str, limit: int = 20) -> List[Dict]:
        """
        获取虚拟地产
        
        Args:
            platform_id: 平台ID
            limit: 限制数量
            
        Returns:
            虚拟地产列表
        """
        logger.info(f"获取平台 {platform_id} 的虚拟地产，限制{limit}个")
        
        properties = []
        
        # 查找平台信息
        platform_info = None
        for platform in self.metaverse_platforms:
            if platform['name'].lower().replace(' ', '_') == platform_id:
                platform_info = platform
                break
        
        if not platform_info:
            logger.warning(f"未找到平台: {platform_id}")
            return properties
        
        for i in range(limit):
            # 生成坐标
            x = random.randint(-150, 150)
            y = random.randint(-150, 150)
            coordinates = f"{x},{y}"
            
            # 生成地产大小
            size_x = random.randint(1, 10)
            size_y = random.randint(1, 10)
            total_area = size_x * size_y
            
            # 生成价格
            base_price = random.uniform(0.1, 1000.0)
            if platform_info['token'] == 'ETH':
                current_price = base_price
                current_price_usd = current_price * random.uniform(1500, 2500)
                price_symbol = 'ETH'
            elif platform_info['token'] == 'MANA':
                current_price = base_price * 100  # MANA价格较低
                current_price_usd = current_price * random.uniform(0.5, 1.5)
                price_symbol = 'MANA'
            elif platform_info['token'] == 'SAND':
                current_price = base_price * 10  # SAND价格中等
                current_price_usd = current_price * random.uniform(0.5, 1.5)
                price_symbol = 'SAND'
            else:
                current_price = base_price
                current_price_usd = current_price
                price_symbol = 'USD'
            
            # 生成其他数据
            last_sale_price = current_price * random.uniform(0.5, 1.5)
            last_sale_price_usd = last_sale_price * (current_price_usd / current_price) if current_price > 0 else 0
            last_sale_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
            
            property_data = {
                'property_id': f"{platform_id}_prop_{i+1}",
                'platform_id': platform_id,
                'name': f"{random.choice(['Premium', 'Luxury', 'Prime', 'Central'])} {random.choice(self.virtual_property_types)} #{i+1}",
                'description': f"A beautiful virtual property in {platform_info['name']} located at coordinates ({x},{y}).",
                'coordinates': coordinates,
                'parcel_id': f"PARCEL_{platform_id.upper()}_{i+1:06d}",
                'estate_id': f"ESTATE_{platform_id.upper()}_{(i//10)+1:04d}" if i % 10 == 0 else '',
                'size_x': size_x,
                'size_y': size_y,
                'total_area': total_area,
                'property_type': random.choice(self.virtual_property_types),
                'owner_address': f"0x{hashlib.md5(f'owner_{i}'.encode()).hexdigest()[:40]}",
                'owner_name': random.choice(['Virtual Realty Inc.', 'Metaverse Holdings', 'Crypto Estate Group']),
                'current_price': round(current_price, 3),
                'current_price_usd': round(current_price_usd, 2),
                'price_symbol': price_symbol,
                'last_sale_price': round(last_sale_price, 3),
                'last_sale_price_usd': round(last_sale_price_usd, 2),
                'last_sale_date': last_sale_date,
                'views': random.randint(100, 10000),
                'favorites': random.randint(10, 1000),
                'is_for_sale': random.choice([True, False]),
                'is_for_rent': random.choice([True, False]) if not random.choice([True, False]) else False,
                'rental_price': round(current_price * random.uniform(0.01, 0.1), 3) if random.choice([True, False]) else None,
                'rental_period': random.choice(['daily', 'weekly', 'monthly', 'yearly']),
                'amenities': ','.join(random.sample(['VR Ready', 'High Traffic', 'Scenic View', 'Near Events', 'Shopping District'], 3)),
                'nearby_attractions': ','.join(random.sample(['Concert Hall', 'Art Gallery', 'Shopping Mall', 'Gaming Arena', 'Social Hub'], 2)),
                'image_url': f"https://example.com/properties/{platform_id}/{i+1}.jpg",
                'video_url': f"https://example.com/properties/{platform_id}/{i+1}.mp4" if random.choice([True, False]) else '',
                'tags': ','.join([platform_info['name'], 'Virtual Real Estate', 'Metaverse', 'NFT']),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            properties.append(property_data)
        
        logger.info(f"生成 {len(properties)} 个虚拟地产")
        return properties
    
    def get_virtual_events(self, platform_id: str, limit: int = 10) -> List[Dict]:
        """
        获取虚拟活动
        
        Args:
            platform_id: 平台ID
            limit: 限制数量
            
        Returns:
            虚拟活动列表
        """
        logger.info(f"获取平台 {platform_id} 的虚拟活动，限制{limit}个")
        
        events = []
        
        event_types = [
            'Music Concert', 'Art Exhibition', 'Gaming Tournament', 'Conference',
            'Product Launch', 'Fashion Show', 'Movie Premiere', 'Comedy Show',
            'Fitness Class', 'Educational Workshop', 'Networking Event', 'Charity Fundraiser'
        ]
        
        organizers = [
            'Metaverse Events Inc.', 'Virtual Productions', 'Crypto Entertainment',
            'Digital Arts Collective', 'Blockchain Conference Group', 'VR Experience Co.'
        ]
        
        for i in range(limit):
            # 生成活动时间（未来30天内）
            start_time = datetime.now() + timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
            duration_hours = random.uniform(1.0, 8.0)
            end_time = start_time + timedelta(hours=duration_hours)
            
            # 生成坐标
            x = random.randint(-150, 150)
            y = random.randint(-150, 150)
            coordinates = f"{x},{y}"
            
            # 生成价格
            is_free = random.choice([True, False])
            if is_free:
                ticket_price = 0
                ticket_price_usd = 0
                ticket_symbol = ''
            else:
                ticket_price = random.uniform(0.01, 100.0)
                ticket_price_usd = ticket_price * random.uniform(0.5, 2.0)
                ticket_symbol = random.choice(['ETH', 'MANA', 'SAND', 'USD'])
            
            # 生成其他数据
            expected_attendance = random.randint(50, 5000)
            actual_attendance = int(expected_attendance * random.uniform(0.5, 1.2))
            
            event = {
                'event_id': f"{platform_id}_event_{i+1}",
                'platform_id': platform_id,
                'name': f"{random.choice(['Annual', 'International', 'Digital', 'Virtual'])} {random.choice(event_types)}",
                'description': f"Join us for an amazing virtual event in {platform_id}! Experience the future of entertainment.",
                'event_type': random.choice(event_types),
                'location': f"Virtual Venue #{i+1}",
                'coordinates': coordinates,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_hours': round(duration_hours, 1),
                'organizer': random.choice(organizers),
                'organizer_type': random.choice(['Company', 'DAO', 'Community', 'Individual']),
                'expected_attendance': expected_attendance,
                'actual_attendance': actual_attendance,
                'ticket_price': round(ticket_price, 3),
                'ticket_price_usd': round(ticket_price_usd, 2),
                'ticket_symbol': ticket_symbol,
                'is_free': is_free,
                'is_nft_gated': random.choice([True, False]),
                'required_nft': f"{platform_id}_nft_{random.randint(1, 1000)}" if random.choice([True, False]) else '',
                'sponsors': ','.join(random.sample(['Crypto Bank', 'NFT Platform', 'VR Company', 'Gaming Studio'], 2)),
                'speakers': ','.join(random.sample(['John Metaverse', 'Alice Blockchain', 'Bob VR', 'Charlie NFT'], 3)),
                'agenda': json.dumps([
                    {'time': '18:00', 'activity': 'Registration & Networking'},
                    {'time': '19:00', 'activity': 'Opening Remarks'},
                    {'time': '19:30', 'activity': 'Keynote Speech'},
                    {'time': '20:30', 'activity': 'Panel Discussion'},
                    {'time': '21:30', 'activity': 'Networking & Closing'}
                ]),
                'registration_url': f"https://example.com/events/{platform_id}/{i+1}/register",
                'live_stream_url': f"https://example.com/stream/{platform_id}/{i+1}",
                'replay_url': f"https://example.com/replay/{platform_id}/{i+1}" if random.choice([True, False]) else '',
                'social_hashtag': f"#{platform_id}Event{i+1}",
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            events.append(event)
        
        logger.info(f"生成 {len(events)} 个虚拟活动")
        return events
    
    def get_user_statistics(self, platform_id: str, days: int = 30) -> List[Dict]:
        """
        获取用户统计
        
        Args:
            platform_id: 平台ID
            days: 天数
            
        Returns:
            用户统计列表
        """
        logger.info(f"获取平台 {platform_id} 的用户统计，{days}天")
        
        statistics = []
        
        # 基础用户数
        base_total_users = random.randint(10000, 1000000)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
            
            # 生成每日数据
            total_users = base_total_users + int(base_total_users * (i / 100))  # 每天增长1%
            new_users = int(total_users * random.uniform(0.001, 0.01))
            
            active_users_24h = int(total_users * random.uniform(0.05, 0.15))
            active_users_7d = int(total_users * random.uniform(0.15, 0.30))
            active_users_30d = int(total_users * random.uniform(0.25, 0.50))
            
            average_session_minutes = random.uniform(15.0, 60.0)
            
            total_transactions = random.randint(100, 10000)
            transaction_volume = random.uniform(1000.0, 1000000.0)
            transaction_volume_usd = transaction_volume * random.uniform(0.5, 2.0)
            
            nft_sales = random.randint(10, 1000)
            nft_sales_volume = random.uniform(100.0, 100000.0)
            nft_sales_volume_usd = nft_sales_volume * random.uniform(0.5, 2.0)
            
            land_sales = random.randint(1, 100)
            land_sales_volume = random.uniform(1000.0, 1000000.0)
            land_sales_volume_usd = land_sales_volume * random.uniform(0.5, 2.0)
            
            user_growth_rate = random.uniform(0.001, 0.02)  # 0.1% - 2%
            retention_rate = random.uniform(0.3, 0.7)  # 30% - 70%
            churn_rate = 1 - retention_rate
            
            stat = {
                'stat_id': f"{platform_id}_{date}",
                'platform_id': platform_id,
                'date': date,
                'total_users': total_users,
                'new_users': new_users,
                'active_users_24h': active_users_24h,
                'active_users_7d': active_users_7d,
                'active_users_30d': active_users_30d,
                'average_session_minutes': round(average_session_minutes, 1),
                'total_transactions': total_transactions,
                'transaction_volume': round(transaction_volume, 2),
                'transaction_volume_usd': round(transaction_volume_usd, 2),
                'nft_sales': nft_sales,
                'nft_sales_volume': round(nft_sales_volume, 2),
                'nft_sales_volume_usd': round(nft_sales_volume_usd, 2),
                'land_sales': land_sales,
                'land_sales_volume': round(land_sales_volume, 2),
                'land_sales_volume_usd': round(land_sales_volume_usd, 2),
                'user_growth_rate': round(user_growth_rate, 4),
                'retention_rate': round(retention_rate, 4),
                'churn_rate': round(churn_rate, 4),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            statistics.append(stat)
        
        logger.info(f"生成 {len(statistics)} 天用户统计")
        return statistics
    
    def get_market_data(self, platform_id: str, days: int = 30) -> List[Dict]:
        """
        获取市场数据
        
        Args:
            platform_id: 平台ID
            days: 天数
            
        Returns:
            市场数据列表
        """
        logger.info(f"获取平台 {platform_id} 的市场数据，{days}天")
        
        market_data = []
        
        # 查找平台信息
        platform_info = None
        for platform in self.metaverse_platforms:
            if platform['name'].lower().replace(' ', '_') == platform_id:
                platform_info = platform
                break
        
        if not platform_info:
            logger.warning(f"未找到平台: {platform_id}")
            return market_data
        
        # 基础价格
        base_price = random.uniform(0.1, 100.0)
        base_price_usd = base_price * random.uniform(0.5, 2.0)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
            
            # 生成价格（模拟随机游走）
            if i == 0:
                token_price = base_price
                token_price_usd = base_price_usd
            else:
                # 基于前一日价格生成
                prev_price = market_data[-1]['token_price']
                change_percent = random.uniform(-0.1, 0.1)  # -10% 到 +10%
                token_price = prev_price * (1 + change_percent)
                token_price_usd = token_price * (base_price_usd / base_price)
            
            # 生成其他数据
            circulating_supply = random.uniform(1e6, 1e10)
            total_supply = circulating_supply * random.uniform(1.0, 2.0)
            max_supply = total_supply * random.uniform(1.0, 1.5) if random.choice([True, False]) else None
            
            market_cap = token_price * circulating_supply
            market_cap_usd = token_price_usd * circulating_supply
            
            volume_24h = market_cap * random.uniform(0.001, 0.01)
            volume_24h_usd = market_cap_usd * random.uniform(0.001, 0.01)
            
            fully_diluted_valuation = token_price * max_supply if max_supply else market_cap * 1.5
            
            price_change_24h = random.uniform(-0.2, 0.2)  # -20% 到 +20%
            price_change_7d = random.uniform(-0.3, 0.3)  # -30% 到 +30%
            price_change_30d = random.uniform(-0.5, 0.5)  # -50% 到 +50%
            
            all_time_high = token_price * random.uniform(1.5, 3.0)
            all_time_high_date = (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d')
            all_time_low = token_price * random.uniform(0.1, 0.5)
            all_time_low_date = (datetime.now() - timedelta(days=random.randint(365, 1825))).strftime('%Y-%m-%d')
            
            data = {
                'data_id': f"{platform_id}_{date}",
                'platform_id': platform_id,
                'date': date,
                'token_price': round(token_price, 4),
                'token_price_usd': round(token_price_usd, 4),
                'market_cap': round(market_cap, 2),
                'market_cap_usd': round(market_cap_usd, 2),
                'volume_24h': round(volume_24h, 2),
                'volume_24h_usd': round(volume_24h_usd, 2),
                'circulating_supply': round(circulating_supply, 0),
                'total_supply': round(total_supply, 0),
                'max_supply': round(max_supply, 0) if max_supply else None,
                'fully_diluted_valuation': round(fully_diluted_valuation, 2),
                'price_change_24h': round(price_change_24h * 100, 2),
                'price_change_7d': round(price_change_7d * 100, 2),
                'price_change_30d': round(price_change_30d * 100, 2),
                'all_time_high': round(all_time_high, 4),
                'all_time_high_date': all_time_high_date,
                'all_time_low': round(all_time_low, 4),
                'all_time_low_date': all_time_low_date,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            market_data.append(data)
        
        logger.info(f"生成 {len(market_data)} 天市场数据")
        return market_data
    
    def get_metaverse_news(self, limit: int = 10) -> List[Dict]:
        """
        获取元宇宙新闻
        
        Args:
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        logger.info(f"获取元宇宙新闻，限制{limit}条")
        
        news_list = []
        
        news_sources = ['CoinDesk', 'Cointelegraph', 'Decrypt', 'The Block', 'Metaverse Insider']
        news_topics = [
            'Virtual Land Sales', 'Platform Partnerships', 'New Feature Launches',
            'Regulatory Developments', 'Investment Rounds', 'User Growth Milestones',
            'Celebrity Involvement', 'Brand Collaborations', 'Technology Innovations',
            'Market Analysis'
        ]
        
        for i in range(limit):
            # 生成随机时间（最近7天内）
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            publish_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
            
            # 选择相关平台
            related_platforms = random.sample([p['name'] for p in self.metaverse_platforms[:5]], random.randint(1, 3))
            related_tokens = random.sample([p['token'] for p in self.metaverse_platforms[:5]], random.randint(1, 3))
            
            news = {
                'news_id': f"news_{hashlib.md5(str(i).encode()).hexdigest()[:12]}",
                'source': random.choice(news_sources),
                'title': f"{random.choice(news_topics)} in {random.choice(related_platforms)}",
                'summary': f"Latest developments in the {random.choice(related_platforms)} metaverse platform and the broader virtual world ecosystem.",
                'content': f"This article discusses the recent news about {', '.join(related_platforms)}. The metaverse continues to evolve with new developments, partnerships, and user growth.",
                'url': f"https://example.com/news/metaverse/{i+1}",
                'image_url': f"https://example.com/images/metaverse_news_{i+1}.jpg",
                'publish_date': publish_time.strftime('%Y-%m-%d %H:%M:%S'),
                'author': random.choice(['Metaverse Reporter', 'Virtual World Analyst', 'Blockchain Journalist']),
                'tags': ','.join(['metaverse', 'virtual reality', 'blockchain', 'nft'] + related_platforms),
                'sentiment_score': round(random.uniform(-0.3, 0.7), 2),  # 偏正面
                'related_platforms': ','.join(related_platforms),
                'related_tokens': ','.join(related_tokens),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            news_list.append(news)
        
        logger.info(f"生成 {len(news_list)} 条元宇宙新闻")
        return news_list
    
    def save_to_database(self, data_type: str, data: List[Dict]):
        """保存数据到数据库"""
        if not data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type == 'platforms':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO metaverse_platforms 
                        (platform_id, name, description, website, launch_year, 
                         blockchain, native_token, token_symbol, total_users, 
                         daily_active_users, monthly_active_users, total_land_parcels, 
                         total_virtual_items, market_cap, market_cap_usd, 
                         total_volume_24h, total_volume_24h_usd, developer_count, 
                         partner_count, social_twitter, social_discord, social_telegram, 
                         crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('platform_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('website', ''),
                        item.get('launch_year', 0),
                        item.get('blockchain', ''),
                        item.get('native_token', ''),
                        item.get('token_symbol', ''),
                        item.get('total_users', 0),
                        item.get('daily_active_users', 0),
                        item.get('monthly_active_users', 0),
                        item.get('total_land_parcels', 0),
                        item.get('total_virtual_items', 0),
                        item.get('market_cap', 0),
                        item.get('market_cap_usd', 0),
                        item.get('total_volume_24h', 0),
                        item.get('total_volume_24h_usd', 0),
                        item.get('developer_count', 0),
                        item.get('partner_count', 0),
                        item.get('social_twitter', ''),
                        item.get('social_discord', ''),
                        item.get('social_telegram', ''),
                        item.get('crawl_time'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                logger.info(f"保存 {len(data)} 个元宇宙平台到数据库")
                
            elif data_type == 'properties':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO virtual_properties 
                        (property_id, platform_id, name, description, coordinates, 
                         parcel_id, estate_id, size_x, size_y, total_area, 
                         property_type, owner_address, owner_name, current_price, 
                         current_price_usd, price_symbol, last_sale_price, 
                         last_sale_price_usd, last_sale_date, views, favorites, 
                         is_for_sale, is_for_rent, rental_price, rental_period, 
                         amenities, nearby_attractions, image_url, video_url, 
                         tags, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('property_id'),
                        item.get('platform_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('coordinates', ''),
                        item.get('parcel_id', ''),
                        item.get('estate_id', ''),
                        item.get('size_x', 0),
                        item.get('size_y', 0),
                        item.get('total_area', 0),
                        item.get('property_type', ''),
                        item.get('owner_address', ''),
                        item.get('owner_name', ''),
                        item.get('current_price', 0),
                        item.get('current_price_usd', 0),
                        item.get('price_symbol', ''),
                        item.get('last_sale_price', 0),
                        item.get('last_sale_price_usd', 0),
                        item.get('last_sale_date', ''),
                        item.get('views', 0),
                        item.get('favorites', 0),
                        item.get('is_for_sale', False),
                        item.get('is_for_rent', False),
                        item.get('rental_price'),
                        item.get('rental_period', ''),
                        item.get('amenities', ''),
                        item.get('nearby_attractions', ''),
                        item.get('image_url', ''),
                        item.get('video_url', ''),
                        item.get('tags', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个虚拟地产到数据库")
                
            elif data_type == 'events':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO virtual_events 
                        (event_id, platform_id, name, description, event_type, 
                         location, coordinates, start_time, end_time, duration_hours, 
                         organizer, organizer_type, expected_attendance, 
                         actual_attendance, ticket_price, ticket_price_usd, 
                         ticket_symbol, is_free, is_nft_gated, required_nft, 
                         sponsors, speakers, agenda, registration_url, 
                         live_stream_url, replay_url, social_hashtag, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('event_id'),
                        item.get('platform_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('event_type', ''),
                        item.get('location', ''),
                        item.get('coordinates', ''),
                        item.get('start_time'),
                        item.get('end_time'),
                        item.get('duration_hours', 0),
                        item.get('organizer', ''),
                        item.get('organizer_type', ''),
                        item.get('expected_attendance', 0),
                        item.get('actual_attendance', 0),
                        item.get('ticket_price', 0),
                        item.get('ticket_price_usd', 0),
                        item.get('ticket_symbol', ''),
                        item.get('is_free', False),
                        item.get('is_nft_gated', False),
                        item.get('required_nft', ''),
                        item.get('sponsors', ''),
                        item.get('speakers', ''),
                        item.get('agenda', ''),
                        item.get('registration_url', ''),
                        item.get('live_stream_url', ''),
                        item.get('replay_url', ''),
                        item.get('social_hashtag', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个虚拟活动到数据库")
                
            elif data_type == 'users':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_statistics 
                        (stat_id, platform_id, date, total_users, new_users, 
                         active_users_24h, active_users_7d, active_users_30d, 
                         average_session_minutes, total_transactions, 
                         transaction_volume, transaction_volume_usd, nft_sales, 
                         nft_sales_volume, nft_sales_volume_usd, land_sales, 
                         land_sales_volume, land_sales_volume_usd, user_growth_rate, 
                         retention_rate, churn_rate, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('stat_id'),
                        item.get('platform_id'),
                        item.get('date'),
                        item.get('total_users', 0),
                        item.get('new_users', 0),
                        item.get('active_users_24h', 0),
                        item.get('active_users_7d', 0),
                        item.get('active_users_30d', 0),
                        item.get('average_session_minutes', 0),
                        item.get('total_transactions', 0),
                        item.get('transaction_volume', 0),
                        item.get('transaction_volume_usd', 0),
                        item.get('nft_sales', 0),
                        item.get('nft_sales_volume', 0),
                        item.get('nft_sales_volume_usd', 0),
                        item.get('land_sales', 0),
                        item.get('land_sales_volume', 0),
                        item.get('land_sales_volume_usd', 0),
                        item.get('user_growth_rate', 0),
                        item.get('retention_rate', 0),
                        item.get('churn_rate', 0),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条用户统计到数据库")
                
            elif data_type == 'market':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO market_data 
                        (data_id, platform_id, date, token_price, token_price_usd, 
                         market_cap, market_cap_usd, volume_24h, volume_24h_usd, 
                         circulating_supply, total_supply, max_supply, 
                         fully_diluted_valuation, price_change_24h, 
                         price_change_7d, price_change_30d, all_time_high, 
                         all_time_high_date, all_time_low, all_time_low_date, 
                         crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('data_id'),
                        item.get('platform_id'),
                        item.get('date'),
                        item.get('token_price', 0),
                        item.get('token_price_usd', 0),
                        item.get('market_cap', 0),
                        item.get('market_cap_usd', 0),
                        item.get('volume_24h', 0),
                        item.get('volume_24h_usd', 0),
                        item.get('circulating_supply', 0),
                        item.get('total_supply', 0),
                        item.get('max_supply'),
                        item.get('fully_diluted_valuation', 0),
                        item.get('price_change_24h', 0),
                        item.get('price_change_7d', 0),
                        item.get('price_change_30d', 0),
                        item.get('all_time_high', 0),
                        item.get('all_time_high_date', ''),
                        item.get('all_time_low', 0),
                        item.get('all_time_low_date', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条市场数据到数据库")
                
            elif data_type == 'news':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO metaverse_news 
                        (news_id, source, title, summary, content, url, 
                         image_url, publish_date, author, tags, sentiment_score, 
                         related_platforms, related_tokens, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('news_id'),
                        item.get('source'),
                        item.get('title'),
                        item.get('summary'),
                        item.get('content'),
                        item.get('url'),
                        item.get('image_url'),
                        item.get('publish_date'),
                        item.get('author'),
                        item.get('tags'),
                        item.get('sentiment_score', 0),
                        item.get('related_platforms', ''),
                        item.get('related_tokens', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条新闻到数据库")
            
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
    
    def run(self, platform_count: int = 3, properties_per_platform: int = 5, 
           events_per_platform: int = 3, statistics_days: int = 7, 
           market_days: int = 7, news_count: int = 5):
        """
        运行爬虫
        
        Args:
            platform_count: 平台数量
            properties_per_platform: 每个平台地产数量
            events_per_platform: 每个平台活动数量
            statistics_days: 统计天数
            market_days: 市场数据天数
            news_count: 新闻数量
        """
        logger.info("=== 元宇宙动态爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取元宇宙平台
            logger.info(f"获取 {platform_count} 个元宇宙平台")
            platforms = self.get_metaverse_platforms(platform_count)
            self.crawl_stats['total_platforms'] = len(platforms)
            
            if not platforms:
                logger.error("未能获取元宇宙平台")
                return
            
            # 保存平台数据
            if platforms:
                self.save_to_csv(platforms, "metaverse_platforms.csv")
                self.save_to_excel(platforms, "metaverse_platforms.xlsx")
                self.save_to_database('platforms', platforms)
            
            all_properties = []
            all_events = []
            all_statistics = []
            all_market_data = []
            
            # 2. 处理每个平台
            for i, platform in enumerate(platforms):
                platform_id = platform.get('platform_id')
                logger.info(f"处理元宇宙平台 {i+1}/{len(platforms)}: {platform.get('name')}")
                
                # 获取平台详情
                detail = self.get_platform_detail(platform_id)
                if detail:
                    self.save_to_json(detail, f"{platform_id}_detail.json")
                
                # 获取虚拟地产
                properties = self.get_virtual_properties(platform_id, properties_per_platform)
                if properties:
                    all_properties.extend(properties)
                    self.save_to_csv(properties, f"{platform_id}_properties.csv")
                    self.save_to_database('properties', properties)
                    self.crawl_stats['total_properties'] += len(properties)
                
                # 获取虚拟活动
                events = self.get_virtual_events(platform_id, events_per_platform)
                if events:
                    all_events.extend(events)
                    self.save_to_csv(events, f"{platform_id}_events.csv")
                    self.save_to_database('events', events)
                    self.crawl_stats['total_events'] += len(events)
                
                # 获取用户统计
                statistics = self.get_user_statistics(platform_id, statistics_days)
                if statistics:
                    all_statistics.extend(statistics)
                    self.save_to_csv(statistics, f"{platform_id}_statistics.csv")
                    self.save_to_database('users', statistics)
                    self.crawl_stats['total_users'] += len(statistics)
                
                # 获取市场数据
                market_data = self.get_market_data(platform_id, market_days)
                if market_data:
                    all_market_data.extend(market_data)
                    self.save_to_csv(market_data, f"{platform_id}_market.csv")
                    self.save_to_database('market', market_data)
                
                # 随机延迟
                time.sleep(random.uniform(1, 2))
            
            # 3. 获取元宇宙新闻
            logger.info(f"获取 {news_count} 条元宇宙新闻")
            news = self.get_metaverse_news(news_count)
            
            if news:
                self.save_to_csv(news, "metaverse_news.csv")
                self.save_to_json(news, "metaverse_news.json")
                self.save_to_database('news', news)
            
            # 4. 保存所有数据
            if all_properties:
                self.save_to_csv(all_properties, "all_virtual_properties.csv")
                self.save_to_json(all_properties, "all_virtual_properties.json")
            
            if all_events:
                self.save_to_csv(all_events, "all_virtual_events.csv")
                self.save_to_json(all_events, "all_virtual_events.json")
            
            if all_statistics:
                self.save_to_csv(all_statistics, "all_user_statistics.csv")
                self.save_to_json(all_statistics, "all_user_statistics.json")
            
            if all_market_data:
                self.save_to_csv(all_market_data, "all_market_data.csv")
                self.save_to_json(all_market_data, "all_market_data.json")
            
            # 5. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 元宇宙动态爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = MetaverseCrawler()
    
    # 运行爬虫
    crawler.run(
        platform_count=2,
        properties_per_platform=3,
        events_per_platform=2,
        statistics_days=7,
        market_days=7,
        news_count=3
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("元宇宙动态爬虫使用说明")
    print("="*60)
    print("支持的平台:")
    for platform in crawler.metaverse_platforms[:5]:
        print(f"  - {platform['name']} ({platform['blockchain']})")
    
    print("\n主要功能:")
    print("1. 获取元宇宙平台:")
    print("   platforms = crawler.get_metaverse_platforms(limit=10)")
    print("\n2. 获取平台详情:")
    print("   detail = crawler.get_platform_detail('decentraland')")
    print("\n3. 获取虚拟地产:")
    print("   properties = crawler.get_virtual_properties('decentraland', limit=20)")
    print("\n4. 获取虚拟活动:")
    print("   events = crawler.get_virtual_events('decentraland', limit=10)")
    print("\n5. 获取用户统计:")
    print("   statistics = crawler.get_user_statistics('decentraland', days=30)")
    print("\n6. 获取市场数据:")
    print("   market_data = crawler.get_market_data('decentraland', days=30)")
    print("\n7. 获取元宇宙新闻:")
    print("   news = crawler.get_metaverse_news(limit=10)")
    print("\n8. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("   crawler.save_to_excel(data, 'filename.xlsx')")
    print("\n9. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")

if __name__ == "__main__":
    main()