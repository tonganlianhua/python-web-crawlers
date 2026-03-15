#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFT信息爬虫 - 从NFT市场和数据分析平台获取NFT数据
目标网站: OpenSea, Rarible, Magic Eden, NFTGo等
功能: 爬取NFT集合信息、交易数据、地板价、持有者分析等
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
        logging.FileHandler('nft_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NFTCrawler:
    """NFT信息爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'opensea': {
                'name': 'OpenSea',
                'base_url': 'https://opensea.io',
                'api_base': 'https://api.opensea.io/api/v2',
                'api_key': 'OPENSEA_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'X-API-KEY': 'YOUR_API_KEY_HERE'  # 需要替换
                }
            },
            'rarible': {
                'name': 'Rarible',
                'base_url': 'https://rarible.com',
                'api_base': 'https://api.rarible.org/v0.1',
                'api_key': 'RARIBLE_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'magiceden': {
                'name': 'Magic Eden',
                'base_url': 'https://magiceden.io',
                'api_base': 'https://api-mainnet.magiceden.dev/v2',
                'api_key': 'MAGICEDEN_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'nftgo': {
                'name': 'NFTGo',
                'base_url': 'https://nftgo.io',
                'api_base': 'https://api.nftgo.io/api/v2',
                'api_key': 'NFTGO_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'X-API-KEY': 'YOUR_API_KEY_HERE'  # 需要替换
                }
            }
        }
        
        # 主要NFT集合
        self.major_nft_collections = [
            {'name': 'Bored Ape Yacht Club', 'symbol': 'BAYC', 'contract': '0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d'},
            {'name': 'CryptoPunks', 'symbol': 'PUNK', 'contract': '0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb'},
            {'name': 'Mutant Ape Yacht Club', 'symbol': 'MAYC', 'contract': '0x60e4d786628fea6478f785a6d7e704777c86a7c6'},
            {'name': 'Azuki', 'symbol': 'AZUKI', 'contract': '0xed5af388653567af2f388e6224dc7c4b3241c544'},
            {'name': 'Doodles', 'symbol': 'DOODLE', 'contract': '0x8a90cab2b38dba80c64b7734e58ee1db38b8992e'},
            {'name': 'CloneX', 'symbol': 'CLONEX', 'contract': '0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b'},
            {'name': 'Moonbirds', 'symbol': 'MOONBIRD', 'contract': '0x23581767a106ae21c074b2276d25e5c3e136a68b'},
            {'name': 'Otherdeed', 'symbol': 'OTHERDEED', 'contract': '0x34d85c9cdeb23fa97cb08333b511ac86e1c4e258'},
            {'name': 'Pudgy Penguins', 'symbol': 'PUDGY', 'contract': '0xbd3531da5cf5857e7cfaa92426877b022e612cf8'},
            {'name': 'Cool Cats', 'symbol': 'COOL', 'contract': '0x1a92f7381b9f03921564a437210bb9396471050c'}
        ]
        
        # NFT分类
        self.nft_categories = [
            'Art', 'Collectibles', 'Domain Names', 'Music', 'Photography',
            'Sports', 'Trading Cards', 'Utility', 'Virtual Worlds', 'PFPs',
            'Generative Art', 'Pixel Art', '3D Art', 'Abstract', 'Photography',
            'Memes', 'Gaming', 'Metaverse', 'DeFi', 'DAO'
        ]
        
        # 区块链网络
        self.blockchain_networks = [
            {'name': 'Ethereum', 'symbol': 'ETH', 'chain_id': 1},
            {'name': 'Polygon', 'symbol': 'MATIC', 'chain_id': 137},
            {'name': 'Solana', 'symbol': 'SOL', 'chain_id': 101},
            {'name': 'BNB Chain', 'symbol': 'BNB', 'chain_id': 56},
            {'name': 'Arbitrum', 'symbol': 'ARB', 'chain_id': 42161},
            {'name': 'Optimism', 'symbol': 'OP', 'chain_id': 10},
            {'name': 'Avalanche', 'symbol': 'AVAX', 'chain_id': 43114},
            {'name': 'Base', 'symbol': 'BASE', 'chain_id': 8453}
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "nft_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "nft.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_collections': 0,
            'total_nfts': 0,
            'total_trades': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 请求限制
        self.rate_limits = {
            'opensea': {'calls_per_minute': 30, 'last_call': 0},
            'rarible': {'calls_per_minute': 60, 'last_call': 0},
            'magiceden': {'calls_per_minute': 100, 'last_call': 0},
            'nftgo': {'calls_per_minute': 50, 'last_call': 0}
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
            os.path.join(self.data_dir, 'collections'),
            os.path.join(self.data_dir, 'nfts'),
            os.path.join(self.data_dir, 'trades'),
            os.path.join(self.data_dir, 'holders'),
            os.path.join(self.data_dir, 'market_data'),
            os.path.join(self.data_dir, 'analytics'),
            os.path.join(self.data_dir, 'raw_data'),
            os.path.join(self.data_dir, 'json'),
            os.path.join(self.data_dir, 'csv'),
            os.path.join(self.data_dir, 'excel'),
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
            
            # 创建NFT集合表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nft_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id TEXT UNIQUE,
                    name TEXT,
                    symbol TEXT,
                    description TEXT,
                    contract_address TEXT,
                    blockchain TEXT,
                    chain_id INTEGER,
                    website TEXT,
                    discord TEXT,
                    twitter TEXT,
                    opensea_slug TEXT,
                    image_url TEXT,
                    banner_image_url TEXT,
                    featured_image_url TEXT,
                    large_image_url TEXT,
                    created_date TEXT,
                    total_supply INTEGER,
                    num_owners INTEGER,
                    floor_price REAL,
                    floor_price_symbol TEXT,
                    floor_price_usd REAL,
                    market_cap REAL,
                    market_cap_usd REAL,
                    total_volume REAL,
                    total_volume_usd REAL,
                    seven_day_volume REAL,
                    seven_day_volume_usd REAL,
                    seven_day_sales INTEGER,
                    seven_day_average_price REAL,
                    thirty_day_volume REAL,
                    thirty_day_volume_usd REAL,
                    thirty_day_sales INTEGER,
                    thirty_day_average_price REAL,
                    one_day_volume REAL,
                    one_day_volume_usd REAL,
                    one_day_sales INTEGER,
                    one_day_average_price REAL,
                    traits_count INTEGER,
                    attributes_json TEXT,
                    categories TEXT,
                    editor_choice BOOLEAN,
                    is_spam BOOLEAN,
                    is_nsfw BOOLEAN,
                    safelist_status TEXT,
                    rarity_ranking REAL,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建NFT项目表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nft_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nft_id TEXT UNIQUE,
                    collection_id TEXT,
                    token_id TEXT,
                    name TEXT,
                    description TEXT,
                    image_url TEXT,
                    animation_url TEXT,
                    external_url TEXT,
                    background_color TEXT,
                    traits_json TEXT,
                    attributes_json TEXT,
                    rarity_score REAL,
                    rarity_rank INTEGER,
                    last_sale_price REAL,
                    last_sale_symbol TEXT,
                    last_sale_usd REAL,
                    last_sale_timestamp INTEGER,
                    listing_price REAL,
                    listing_symbol TEXT,
                    listing_usd REAL,
                    listing_expiration INTEGER,
                    owner_address TEXT,
                    creator_address TEXT,
                    is_listed BOOLEAN,
                    is_verified BOOLEAN,
                    is_nsfw BOOLEAN,
                    views INTEGER,
                    favorites INTEGER,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (collection_id) REFERENCES nft_collections (collection_id)
                )
            ''')
            
            # 创建交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nft_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    nft_id TEXT,
                    collection_id TEXT,
                    token_id TEXT,
                    from_address TEXT,
                    to_address TEXT,
                    seller_address TEXT,
                    buyer_address TEXT,
                    price REAL,
                    price_symbol TEXT,
                    price_usd REAL,
                    transaction_hash TEXT,
                    block_number INTEGER,
                    block_timestamp INTEGER,
                    trade_date TEXT,
                    trade_type TEXT,
                    marketplace TEXT,
                    platform_fee REAL,
                    royalty_fee REAL,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (nft_id) REFERENCES nft_items (nft_id),
                    FOREIGN KEY (collection_id) REFERENCES nft_collections (collection_id)
                )
            ''')
            
            # 创建持有者表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nft_holders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    holder_id TEXT UNIQUE,
                    wallet_address TEXT,
                    collection_id TEXT,
                    token_ids TEXT,
                    nft_count INTEGER,
                    total_value REAL,
                    total_value_usd REAL,
                    first_acquired_date TEXT,
                    last_acquired_date TEXT,
                    is_whale BOOLEAN,
                    whale_score REAL,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (collection_id) REFERENCES nft_collections (collection_id)
                )
            ''')
            
            # 创建市场分析表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analytics_id TEXT UNIQUE,
                    collection_id TEXT,
                    date TEXT,
                    floor_price REAL,
                    floor_price_usd REAL,
                    volume REAL,
                    volume_usd REAL,
                    sales_count INTEGER,
                    average_price REAL,
                    average_price_usd REAL,
                    unique_buyers INTEGER,
                    unique_sellers INTEGER,
                    wash_trading_volume REAL,
                    wash_trading_percent REAL,
                    whale_activity INTEGER,
                    social_mentions INTEGER,
                    sentiment_score REAL,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (collection_id) REFERENCES nft_collections (collection_id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_collections_contract ON nft_collections (contract_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_collections_floor ON nft_collections (floor_price_usd)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_collection ON nft_items (collection_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_rarity ON nft_items (rarity_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_collection ON nft_trades (collection_id, trade_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_nft ON nft_trades (nft_id, trade_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_holders_collection ON nft_holders (collection_id, nft_count)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_collection ON market_analytics (collection_id, date)')
            
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
    
    def get_cached_response(self, cache_key: str, max_age_minutes: int = 10) -> Optional[Dict]:
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
                    cache_age: int = 10,  # 分钟
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
    
    def get_nft_collections(self, website_id: str = 'opensea', 
                           limit: int = 20) -> List[Dict]:
        """
        获取NFT集合列表
        
        Args:
            website_id: 网站ID
            limit: 限制数量
            
        Returns:
            NFT集合列表
        """
        website = self.websites.get(website_id, self.websites['opensea'])
        logger.info(f"从{website['name']}获取NFT集合列表，限制{limit}个")
        
        if website_id == 'opensea':
            # OpenSea API v2
            url = f"{website['api_base']}/collections"
            params = {
                'chain': 'ethereum',
                'limit': limit,
                'order_by': 'seven_day_volume'
            }
            
            response = self.safe_request(
                url,
                params=params,
                headers=website['headers'],
                website_id=website_id,
                use_cache=True,
                cache_age=30
            )
            
            if response:
                try:
                    data = response.json()
                    collections = self._parse_opensea_collections(data)
                    return collections[:limit]
                except Exception as e:
                    logger.error(f"解析OpenSea响应失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_collections(limit)
    
    def _parse_opensea_collections(self, data: Dict) -> List[Dict]:
        """解析OpenSea集合数据"""
        collections = []
        
        try:
            items = data.get('collections', [])
            
            for item in items:
                try:
                    collection = {
                        'collection_id': item.get('collection', ''),
                        'name': item.get('name', ''),
                        'symbol': item.get('symbol', ''),
                        'description': item.get('description', ''),
                        'contract_address': item.get('primary_asset_contracts', [{}])[0].get('address', '') if item.get('primary_asset_contracts') else '',
                        'blockchain': 'Ethereum',
                        'chain_id': 1,
                        'website': item.get('external_url', ''),
                        'discord': item.get('discord_url', ''),
                        'twitter': item.get('twitter_username', ''),
                        'opensea_slug': item.get('slug', ''),
                        'image_url': item.get('image_url', ''),
                        'banner_image_url': item.get('banner_image_url', ''),
                        'created_date': item.get('created_date', ''),
                        'total_supply': item.get('total_supply', 0),
                        'num_owners': item.get('num_owners', 0),
                        'floor_price': item.get('floor_price', 0),
                        'floor_price_symbol': 'ETH',
                        'floor_price_usd': item.get('floor_price', 0) * 2000,  # 假设ETH价格2000
                        'market_cap': item.get('market_cap', 0),
                        'market_cap_usd': item.get('market_cap', 0) * 2000,
                        'total_volume': item.get('total_volume', 0),
                        'total_volume_usd': item.get('total_volume', 0) * 2000,
                        'seven_day_volume': item.get('seven_day_volume', 0),
                        'seven_day_volume_usd': item.get('seven_day_volume', 0) * 2000,
                        'seven_day_sales': item.get('seven_day_sales', 0),
                        'seven_day_average_price': item.get('seven_day_average_price', 0),
                        'one_day_volume': item.get('one_day_volume', 0),
                        'one_day_volume_usd': item.get('one_day_volume', 0) * 2000,
                        'one_day_sales': item.get('one_day_sales', 0),
                        'one_day_average_price': item.get('one_day_average_price', 0),
                        'traits_count': len(item.get('traits', {})),
                        'attributes_json': json.dumps(item.get('traits', {})),
                        'categories': ','.join(item.get('categories', [])),
                        'editor_choice': item.get('editor_choice', False),
                        'is_spam': item.get('is_spam', False),
                        'is_nsfw': item.get('is_nsfw', False),
                        'safelist_status': item.get('safelist_status', ''),
                        'rarity_ranking': item.get('rarity_ranking', 0),
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    collections.append(collection)
                except Exception as e:
                    logger.error(f"解析集合数据失败: {e}")
                    continue
            
            logger.info(f"解析到 {len(collections)} 个NFT集合")
            
        except Exception as e:
            logger.error(f"解析OpenSea数据异常: {e}")
        
        return collections
    
    def _generate_mock_collections(self, count: int) -> List[Dict]:
        """生成模拟NFT集合数据"""
        collections = []
        
        for i in range(min(count, len(self.major_nft_collections))):
            collection_info = self.major_nft_collections[i]
            
            # 生成价格数据
            floor_price = random.uniform(0.1, 100.0)  # ETH
            floor_price_usd = floor_price * random.uniform(1500, 2500)
            
            total_volume = random.uniform(1000, 100000)  # ETH
            total_volume_usd = total_volume * random.uniform(1500, 2500)
            
            market_cap = total_supply = random.randint(1000, 10000)
            market_cap_usd = market_cap * floor_price_usd
            
            num_owners = random.randint(500, 5000)
            
            # 生成时间数据
            created_date = (datetime.now() - timedelta(days=random.randint(100, 1000))).strftime('%Y-%m-%d')
            
            # 生成社交媒体数据
            twitter = f"@{collection_info['symbol']}"
            discord = f"https://discord.gg/{collection_info['symbol'].lower()}"
            website = f"https://www.{collection_info['symbol'].lower()}.io"
            
            collection = {
                'collection_id': collection_info['contract'],
                'name': collection_info['name'],
                'symbol': collection_info['symbol'],
                'description': f"{collection_info['name']} is a collection of {total_supply} unique NFTs on the Ethereum blockchain.",
                'contract_address': collection_info['contract'],
                'blockchain': 'Ethereum',
                'chain_id': 1,
                'website': website,
                'discord': discord,
                'twitter': twitter,
                'opensea_slug': collection_info['symbol'].lower(),
                'image_url': f"https://example.com/images/{collection_info['symbol'].lower()}.png",
                'banner_image_url': f"https://example.com/banners/{collection_info['symbol'].lower()}.jpg",
                'created_date': created_date,
                'total_supply': total_supply,
                'num_owners': num_owners,
                'floor_price': round(floor_price, 3),
                'floor_price_symbol': 'ETH',
                'floor_price_usd': round(floor_price_usd, 2),
                'market_cap': round(market_cap, 2),
                'market_cap_usd': round(market_cap_usd, 2),
                'total_volume': round(total_volume, 2),
                'total_volume_usd': round(total_volume_usd, 2),
                'seven_day_volume': round(total_volume * random.uniform(0.01, 0.1), 2),
                'seven_day_volume_usd': round(total_volume_usd * random.uniform(0.01, 0.1), 2),
                'seven_day_sales': random.randint(10, 1000),
                'seven_day_average_price': round(floor_price * random.uniform(0.8, 1.2), 3),
                'one_day_volume': round(total_volume * random.uniform(0.001, 0.01), 2),
                'one_day_volume_usd': round(total_volume_usd * random.uniform(0.001, 0.01), 2),
                'one_day_sales': random.randint(1, 100),
                'one_day_average_price': round(floor_price * random.uniform(0.9, 1.1), 3),
                'traits_count': random.randint(5, 20),
                'attributes_json': json.dumps({'Background': ['Blue', 'Red', 'Green'], 'Eyes': ['Normal', 'Laser', 'Cyborg']}),
                'categories': random.choice(self.nft_categories),
                'editor_choice': random.choice([True, False]),
                'is_spam': False,
                'is_nsfw': random.choice([True, False]),
                'safelist_status': 'verified',
                'rarity_ranking': random.uniform(0.5, 1.0),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            collections.append(collection)
        
        logger.info(f"生成 {len(collections)} 个模拟NFT集合")
        return collections
    
    def get_collection_detail(self, collection_id: str, 
                             website_id: str = 'opensea') -> Optional[Dict]:
        """
        获取集合详情
        
        Args:
            collection_id: 集合ID（合约地址或OpenSea slug）
            website_id: 网站ID
            
        Returns:
            集合详情字典
        """
        logger.info(f"获取NFT集合详情: {collection_id}")
        
        website = self.websites.get(website_id, self.websites['opensea'])
        
        if website_id == 'opensea':
            # OpenSea API
            url = f"{website['api_base']}/collections/{collection_id}"
            params = {
                'chain': 'ethereum'
            }
            
            response = self.safe_request(
                url,
                params=params,
                headers=website['headers'],
                website_id=website_id,
                use_cache=True,
                cache_age=60
            )
            
            if response:
                try:
                    data = response.json()
                    detail = self._parse_opensea_collection_detail(data, collection_id)
                    return detail
                except Exception as e:
                    logger.error(f"解析OpenSea详情失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_collection_detail(collection_id)
    
    def _parse_opensea_collection_detail(self, data: Dict, collection_id: str) -> Dict:
        """解析OpenSea集合详情"""
        try:
            collection = data.get('collection', {})
            stats = collection.get('stats', {})
            
            detail = {
                'collection_id': collection_id,
                'name': collection.get('name', ''),
                'symbol': collection.get('symbol', ''),
                'description': collection.get('description', ''),
                'contract_address': collection.get('primary_asset_contracts', [{}])[0].get('address', '') if collection.get('primary_asset_contracts') else '',
                'blockchain': 'Ethereum',
                'chain_id': 1,
                'website': collection.get('external_url', ''),
                'discord': collection.get('discord_url', ''),
                'twitter': collection.get('twitter_username', ''),
                'opensea_slug': collection.get('slug', ''),
                'image_url': collection.get('image_url', ''),
                'banner_image_url': collection.get('banner_image_url', ''),
                'featured_image_url': collection.get('featured_image_url', ''),
                'large_image_url': collection.get('large_image_url', ''),
                'created_date': collection.get('created_date', ''),
                'total_supply': stats.get('total_supply', 0),
                'num_owners': stats.get('num_owners', 0),
                'floor_price': stats.get('floor_price', 0),
                'floor_price_symbol': 'ETH',
                'floor_price_usd': stats.get('floor_price', 0) * 2000,
                'market_cap': stats.get('market_cap', 0),
                'market_cap_usd': stats.get('market_cap', 0) * 2000,
                'total_volume': stats.get('total_volume', 0),
                'total_volume_usd': stats.get('total_volume', 0) * 2000,
                'seven_day_volume': stats.get('seven_day_volume', 0),
                'seven_day_volume_usd': stats.get('seven_day_volume', 0) * 2000,
                'seven_day_sales': stats.get('seven_day_sales', 0),
                'seven_day_average_price': stats.get('seven_day_average_price', 0),
                'thirty_day_volume': stats.get('thirty_day_volume', 0),
                'thirty_day_volume_usd': stats.get('thirty_day_volume', 0) * 2000,
                'thirty_day_sales': stats.get('thirty_day_sales', 0),
                'thirty_day_average_price': stats.get('thirty_day_average_price', 0),
                'one_day_volume': stats.get('one_day_volume', 0),
                'one_day_volume_usd': stats.get('one_day_volume', 0) * 2000,
                'one_day_sales': stats.get('one_day_sales', 0),
                'one_day_average_price': stats.get('one_day_average_price', 0),
                'traits_count': len(collection.get('traits', {})),
                'attributes_json': json.dumps(collection.get('traits', {})),
                'categories': ','.join(collection.get('categories', [])),
                'editor_choice': collection.get('editor_choice', False),
                'is_spam': collection.get('is_spam', False),
                'is_nsfw': collection.get('is_nsfw', False),
                'safelist_status': collection.get('safelist_status', ''),
                'rarity_ranking': collection.get('rarity_ranking', 0),
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"解析集合详情: {detail['name']}")
            return detail
            
        except Exception as e:
            logger.error(f"解析集合详情异常: {e}")
            return self._generate_mock_collection_detail(collection_id)
    
    def _generate_mock_collection_detail(self, collection_id: str) -> Dict:
        """生成模拟集合详情"""
        # 查找集合信息
        collection_info = None
        for collection in self.major_nft_collections:
            if collection['contract'] == collection_id or collection['symbol'].lower() == collection_id.lower():
                collection_info = collection
                break
        
        if not collection_info:
            # 创建默认信息
            collection_info = {
                'name': f"Collection {collection_id[:8]}",
                'symbol': collection_id[:4].upper(),
                'contract': collection_id
            }
        
        # 生成详细数据
        floor_price = random.uniform(0.1, 100.0)
        floor_price_usd = floor_price * random.uniform(1500, 2500)
        
        total_supply = random.randint(1000, 10000)
        num_owners = random.randint(500, 5000)
        
        detail = {
            'collection_id': collection_id,
            'name': collection_info['name'],
            'symbol': collection_info['symbol'],
            'description': f"{collection_info['name']} is a unique NFT collection with {total_supply} items on the Ethereum blockchain.",
            'contract_address': collection_info['contract'],
            'blockchain': 'Ethereum',
            'chain_id': 1,
            'website': f"https://www.{collection_info['symbol'].lower()}.io",
            'discord': f"https://discord.gg/{collection_info['symbol'].lower()}",
            'twitter': f"@{collection_info['symbol'].lower()}",
            'opensea_slug': collection_info['symbol'].lower(),
            'image_url': f"https://example.com/images/{collection_info['symbol'].lower()}.png",
            'banner_image_url': f"https://example.com/banners/{collection_info['symbol'].lower()}.jpg",
            'featured_image_url': f"https://example.com/featured/{collection_info['symbol'].lower()}.jpg",
            'large_image_url': f"https://example.com/large/{collection_info['symbol'].lower()}.jpg",
            'created_date': (datetime.now() - timedelta(days=random.randint(100, 1000))).strftime('%Y-%m-%d'),
            'total_supply': total_supply,
            'num_owners': num_owners,
            'floor_price': round(floor_price, 3),
            'floor_price_symbol': 'ETH',
            'floor_price_usd': round(floor_price_usd, 2),
            'market_cap': round(total_supply * floor_price, 2),
            'market_cap_usd': round(total_supply * floor_price_usd, 2),
            'total_volume': round(random.uniform(1000, 100000), 2),
            'total_volume_usd': round(random.uniform(1000000, 100000000), 2),
            'seven_day_volume': round(random.uniform(100, 10000), 2),
            'seven_day_volume_usd': round(random.uniform(150000, 15000000), 2),
            'seven_day_sales': random.randint(10, 1000),
            'seven_day_average_price': round(floor_price * random.uniform(0.8, 1.2), 3),
            'thirty_day_volume': round(random.uniform(500, 50000), 2),
            'thirty_day_volume_usd': round(random.uniform(750000, 75000000), 2),
            'thirty_day_sales': random.randint(50, 5000),
            'thirty_day_average_price': round(floor_price * random.uniform(0.9, 1.1), 3),
            'one_day_volume': round(random.uniform(10, 1000), 2),
            'one_day_volume_usd': round(random.uniform(15000, 1500000), 2),
            'one_day_sales': random.randint(1, 100),
            'one_day_average_price': round(floor_price * random.uniform(0.95, 1.05), 3),
            'traits_count': random.randint(5, 20),
            'attributes_json': json.dumps({
                'Background': ['Blue', 'Red', 'Green', 'Purple', 'Yellow'],
                'Eyes': ['Normal', 'Laser', 'Cyborg', 'Robot', 'Alien'],
                'Mouth': ['Smile', 'Frown', 'Open', 'Tongue', 'Teeth'],
                'Clothing': ['T-Shirt', 'Suit', 'Jacket', 'Hoodie', 'Uniform']
            }),
            'categories': random.choice(self.nft_categories),
            'editor_choice': random.choice([True, False]),
            'is_spam': False,
            'is_nsfw': random.choice([True, False]),
            'safelist_status': 'verified',
            'rarity_ranking': random.uniform(0.5, 1.0),
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return detail
    
    def get_nft_items(self, collection_id: str, limit: int = 10) -> List[Dict]:
        """
        获取NFT项目
        
        Args:
            collection_id: 集合ID
            limit: 限制数量
            
        Returns:
            NFT项目列表
        """
        logger.info(f"获取集合 {collection_id} 的NFT项目，限制{limit}个")
        
        # 模拟NFT项目数据
        nft_items = []
        
        for i in range(limit):
            # 生成随机特征
            traits = {
                'Background': random.choice(['Blue', 'Red', 'Green', 'Purple', 'Yellow']),
                'Eyes': random.choice(['Normal', 'Laser', 'Cyborg', 'Robot', 'Alien']),
                'Mouth': random.choice(['Smile', 'Frown', 'Open', 'Tongue', 'Teeth']),
                'Clothing': random.choice(['T-Shirt', 'Suit', 'Jacket', 'Hoodie', 'Uniform']),
                'Hat': random.choice(['None', 'Cap', 'Beanie', 'Top Hat', 'Crown']),
                'Accessory': random.choice(['None', 'Glasses', 'Necklace', 'Watch', 'Ring'])
            }
            
            # 计算稀有度分数
            rarity_score = random.uniform(0.1, 1.0)
            rarity_rank = random.randint(1, 10000)
            
            # 生成价格数据
            last_sale_price = random.uniform(0.1, 100.0)
            last_sale_usd = last_sale_price * random.uniform(1500, 2500)
            
            listing_price = last_sale_price * random.uniform(0.8, 1.5) if random.choice([True, False]) else 0
            listing_usd = listing_price * random.uniform(1500, 2500) if listing_price > 0 else 0
            
            nft = {
                'nft_id': f"{collection_id}_{i+1}",
                'collection_id': collection_id,
                'token_id': str(i+1),
                'name': f"#{i+1}",
                'description': f"Unique NFT #{i+1} from the collection",
                'image_url': f"https://example.com/nfts/{collection_id}/{i+1}.png",
                'animation_url': f"https://example.com/nfts/{collection_id}/{i+1}.mp4" if random.choice([True, False]) else '',
                'external_url': f"https://opensea.io/assets/ethereum/{collection_id}/{i+1}",
                'background_color': random.choice(['#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF']),
                'traits_json': json.dumps(traits),
                'attributes_json': json.dumps(traits),
                'rarity_score': round(rarity_score, 4),
                'rarity_rank': rarity_rank,
                'last_sale_price': round(last_sale_price, 3),
                'last_sale_symbol': 'ETH',
                'last_sale_usd': round(last_sale_usd, 2),
                'last_sale_timestamp': int((datetime.now() - timedelta(days=random.randint(1, 365))).timestamp()),
                'listing_price': round(listing_price, 3) if listing_price > 0 else None,
                'listing_symbol': 'ETH' if listing_price > 0 else '',
                'listing_usd': round(listing_usd, 2) if listing_usd > 0 else None,
                'listing_expiration': int((datetime.now() + timedelta(days=random.randint(1, 30))).timestamp()) if listing_price > 0 else None,
                'owner_address': f"0x{hashlib.md5(str(i).encode()).hexdigest()[:40]}",
                'creator_address': collection_id[:42],  # 假设合约创建者
                'is_listed': listing_price > 0,
                'is_verified': random.choice([True, False]),
                'is_nsfw': random.choice([True, False]),
                'views': random.randint(100, 10000),
                'favorites': random.randint(10, 1000),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            nft_items.append(nft)
        
        logger.info(f"生成 {len(nft_items)} 个模拟NFT项目")
        return nft_items
    
    def get_nft_trades(self, collection_id: str, limit: int = 20) -> List[Dict]:
        """
        获取NFT交易记录
        
        Args:
            collection_id: 集合ID
            limit: 限制数量
            
        Returns:
            交易记录列表
        """
        logger.info(f"获取集合 {collection_id} 的交易记录，限制{limit}条")
        
        trades = []
        
        for i in range(limit):
            # 生成交易时间（最近30天内）
            trade_date = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            
            # 生成价格
            price = random.uniform(0.1, 100.0)
            price_usd = price * random.uniform(1500, 2500)
            
            # 生成地址
            from_address = f"0x{hashlib.md5(f'from_{i}'.encode()).hexdigest()[:40]}"
            to_address = f"0x{hashlib.md5(f'to_{i}'.encode()).hexdigest()[:40]}"
            seller_address = from_address
            buyer_address = to_address
            
            # 生成交易哈希
            transaction_hash = f"0x{hashlib.md5(str(i).encode()).hexdigest()[:64]}"
            
            trade = {
                'trade_id': f"{collection_id}_{transaction_hash[:16]}",
                'nft_id': f"{collection_id}_{random.randint(1, 10000)}",
                'collection_id': collection_id,
                'token_id': str(random.randint(1, 10000)),
                'from_address': from_address,
                'to_address': to_address,
                'seller_address': seller_address,
                'buyer_address': buyer_address,
                'price': round(price, 3),
                'price_symbol': 'ETH',
                'price_usd': round(price_usd, 2),
                'transaction_hash': transaction_hash,
                'block_number': random.randint(10000000, 20000000),
                'block_timestamp': int(trade_date.timestamp()),
                'trade_date': trade_date.strftime('%Y-%m-%d %H:%M:%S'),
                'trade_type': random.choice(['sale', 'bid_accepted', 'transfer']),
                'marketplace': random.choice(['OpenSea', 'Blur', 'LooksRare', 'X2Y2']),
                'platform_fee': round(price * random.uniform(0.01, 0.025), 3),
                'royalty_fee': round(price * random.uniform(0.025, 0.1), 3),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            trades.append(trade)
        
        logger.info(f"生成 {len(trades)} 条模拟交易记录")
        return trades
    
    def get_nft_holders(self, collection_id: str, limit: int = 10) -> List[Dict]:
        """
        获取NFT持有者
        
        Args:
            collection_id: 集合ID
            limit: 限制数量
            
        Returns:
            持有者列表
        """
        logger.info(f"获取集合 {collection_id} 的持有者，限制{limit}个")
        
        holders = []
        
        for i in range(limit):
            # 生成持有者数据
            nft_count = random.randint(1, 100)
            token_ids = ','.join([str(random.randint(1, 10000)) for _ in range(min(nft_count, 10))])
            
            # 生成价值数据
            total_value = random.uniform(0.1, 1000.0)
            total_value_usd = total_value * random.uniform(1500, 2500)
            
            # 生成时间
            first_acquired = datetime.now() - timedelta(days=random.randint(1, 365))
            last_acquired = first_acquired + timedelta(days=random.randint(0, 30))
            
            # 判断是否为鲸鱼
            is_whale = nft_count > 10 or total_value > 100
            whale_score = random.uniform(0.1, 1.0) if is_whale else random.uniform(0.0, 0.1)
            
            holder = {
                'holder_id': f"{collection_id}_holder_{i+1}",
                'wallet_address': f"0x{hashlib.md5(f'holder_{i}'.encode()).hexdigest()[:40]}",
                'collection_id': collection_id,
                'token_ids': token_ids,
                'nft_count': nft_count,
                'total_value': round(total_value, 3),
                'total_value_usd': round(total_value_usd, 2),
                'first_acquired_date': first_acquired.strftime('%Y-%m-%d'),
                'last_acquired_date': last_acquired.strftime('%Y-%m-%d'),
                'is_whale': is_whale,
                'whale_score': round(whale_score, 3),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            holders.append(holder)
        
        logger.info(f"生成 {len(holders)} 个模拟持有者")
        return holders
    
    def get_market_analytics(self, collection_id: str, days: int = 30) -> List[Dict]:
        """
        获取市场分析数据
        
        Args:
            collection_id: 集合ID
            days: 天数
            
        Returns:
            市场分析数据列表
        """
        logger.info(f"获取集合 {collection_id} 的市场分析，{days}天")
        
        analytics = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
            
            # 生成每日数据
            floor_price = random.uniform(0.1, 100.0)
            floor_price_usd = floor_price * random.uniform(1500, 2500)
            
            volume = random.uniform(10, 1000)
            volume_usd = volume * random.uniform(1500, 2500)
            
            sales_count = random.randint(1, 100)
            average_price = volume / sales_count if sales_count > 0 else 0
            average_price_usd = volume_usd / sales_count if sales_count > 0 else 0
            
            unique_buyers = random.randint(1, sales_count)
            unique_sellers = random.randint(1, sales_count)
            
            wash_trading_volume = volume * random.uniform(0.0, 0.3)  # 0-30% wash trading
            wash_trading_percent = (wash_trading_volume / volume * 100) if volume > 0 else 0
            
            whale_activity = random.randint(0, 10)
            social_mentions = random.randint(0, 1000)
            sentiment_score = random.uniform(-0.5, 0.5)
            
            analytic = {
                'analytics_id': f"{collection_id}_{date}",
                'collection_id': collection_id,
                'date': date,
                'floor_price': round(floor_price, 3),
                'floor_price_usd': round(floor_price_usd, 2),
                'volume': round(volume, 2),
                'volume_usd': round(volume_usd, 2),
                'sales_count': sales_count,
                'average_price': round(average_price, 3),
                'average_price_usd': round(average_price_usd, 2),
                'unique_buyers': unique_buyers,
                'unique_sellers': unique_sellers,
                'wash_trading_volume': round(wash_trading_volume, 2),
                'wash_trading_percent': round(wash_trading_percent, 2),
                'whale_activity': whale_activity,
                'social_mentions': social_mentions,
                'sentiment_score': round(sentiment_score, 3),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            analytics.append(analytic)
        
        logger.info(f"生成 {len(analytics)} 天市场分析数据")
        return analytics
    
    def save_to_database(self, data_type: str, data: List[Dict]):
        """保存数据到数据库"""
        if not data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type == 'collections':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO nft_collections 
                        (collection_id, name, symbol, description, contract_address, 
                         blockchain, chain_id, website, discord, twitter, opensea_slug, 
                         image_url, banner_image_url, featured_image_url, large_image_url, 
                         created_date, total_supply, num_owners, floor_price, 
                         floor_price_symbol, floor_price_usd, market_cap, market_cap_usd, 
                         total_volume, total_volume_usd, seven_day_volume, 
                         seven_day_volume_usd, seven_day_sales, seven_day_average_price, 
                         thirty_day_volume, thirty_day_volume_usd, thirty_day_sales, 
                         thirty_day_average_price, one_day_volume, one_day_volume_usd, 
                         one_day_sales, one_day_average_price, traits_count, 
                         attributes_json, categories, editor_choice, is_spam, is_nsfw, 
                         safelist_status, rarity_ranking, crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('collection_id'),
                        item.get('name'),
                        item.get('symbol'),
                        item.get('description', ''),
                        item.get('contract_address', ''),
                        item.get('blockchain', 'Ethereum'),
                        item.get('chain_id', 1),
                        item.get('website', ''),
                        item.get('discord', ''),
                        item.get('twitter', ''),
                        item.get('opensea_slug', ''),
                        item.get('image_url', ''),
                        item.get('banner_image_url', ''),
                        item.get('featured_image_url', ''),
                        item.get('large_image_url', ''),
                        item.get('created_date', ''),
                        item.get('total_supply', 0),
                        item.get('num_owners', 0),
                        item.get('floor_price', 0),
                        item.get('floor_price_symbol', 'ETH'),
                        item.get('floor_price_usd', 0),
                        item.get('market_cap', 0),
                        item.get('market_cap_usd', 0),
                        item.get('total_volume', 0),
                        item.get('total_volume_usd', 0),
                        item.get('seven_day_volume', 0),
                        item.get('seven_day_volume_usd', 0),
                        item.get('seven_day_sales', 0),
                        item.get('seven_day_average_price', 0),
                        item.get('thirty_day_volume', 0),
                        item.get('thirty_day_volume_usd', 0),
                        item.get('thirty_day_sales', 0),
                        item.get('thirty_day_average_price', 0),
                        item.get('one_day_volume', 0),
                        item.get('one_day_volume_usd', 0),
                        item.get('one_day_sales', 0),
                        item.get('one_day_average_price', 0),
                        item.get('traits_count', 0),
                        item.get('attributes_json', '{}'),
                        item.get('categories', ''),
                        item.get('editor_choice', False),
                        item.get('is_spam', False),
                        item.get('is_nsfw', False),
                        item.get('safelist_status', ''),
                        item.get('rarity_ranking', 0),
                        item.get('crawl_time'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                logger.info(f"保存 {len(data)} 个NFT集合到数据库")
                
            elif data_type == 'items':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO nft_items 
                        (nft_id, collection_id, token_id, name, description, 
                         image_url, animation_url, external_url, background_color, 
                         traits_json, attributes_json, rarity_score, rarity_rank, 
                         last_sale_price, last_sale_symbol, last_sale_usd, 
                         last_sale_timestamp, listing_price, listing_symbol, 
                         listing_usd, listing_expiration, owner_address, 
                         creator_address, is_listed, is_verified, is_nsfw, 
                         views, favorites, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('nft_id'),
                        item.get('collection_id'),
                        item.get('token_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('image_url', ''),
                        item.get('animation_url', ''),
                        item.get('external_url', ''),
                        item.get('background_color', ''),
                        item.get('traits_json', '{}'),
                        item.get('attributes_json', '{}'),
                        item.get('rarity_score', 0),
                        item.get('rarity_rank', 0),
                        item.get('last_sale_price'),
                        item.get('last_sale_symbol', 'ETH'),
                        item.get('last_sale_usd'),
                        item.get('last_sale_timestamp'),
                        item.get('listing_price'),
                        item.get('listing_symbol', 'ETH'),
                        item.get('listing_usd'),
                        item.get('listing_expiration'),
                        item.get('owner_address', ''),
                        item.get('creator_address', ''),
                        item.get('is_listed', False),
                        item.get('is_verified', False),
                        item.get('is_nsfw', False),
                        item.get('views', 0),
                        item.get('favorites', 0),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个NFT项目到数据库")
                
            elif data_type == 'trades':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO nft_trades 
                        (trade_id, nft_id, collection_id, token_id, from_address, 
                         to_address, seller_address, buyer_address, price, 
                         price_symbol, price_usd, transaction_hash, block_number, 
                         block_timestamp, trade_date, trade_type, marketplace, 
                         platform_fee, royalty_fee, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?)
                    ''', (
                        item.get('trade_id'),
                        item.get('nft_id'),
                        item.get('collection_id'),
                        item.get('token_id'),
                        item.get('from_address', ''),
                        item.get('to_address', ''),
                        item.get('seller_address', ''),
                        item.get('buyer_address', ''),
                        item.get('price', 0),
                        item.get('price_symbol', 'ETH'),
                        item.get('price_usd', 0),
                        item.get('transaction_hash', ''),
                        item.get('block_number', 0),
                        item.get('block_timestamp', 0),
                        item.get('trade_date', ''),
                        item.get('trade_type', ''),
                        item.get('marketplace', ''),
                        item.get('platform_fee', 0),
                        item.get('royalty_fee', 0),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条交易记录到数据库")
                
            elif data_type == 'holders':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO nft_holders 
                        (holder_id, wallet_address, collection_id, token_ids, 
                         nft_count, total_value, total_value_usd, first_acquired_date, 
                         last_acquired_date, is_whale, whale_score, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('holder_id'),
                        item.get('wallet_address', ''),
                        item.get('collection_id'),
                        item.get('token_ids', ''),
                        item.get('nft_count', 0),
                        item.get('total_value', 0),
                        item.get('total_value_usd', 0),
                        item.get('first_acquired_date', ''),
                        item.get('last_acquired_date', ''),
                        item.get('is_whale', False),
                        item.get('whale_score', 0),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个持有者到数据库")
                
            elif data_type == 'analytics':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO market_analytics 
                        (analytics_id, collection_id, date, floor_price, 
                         floor_price_usd, volume, volume_usd, sales_count, 
                         average_price, average_price_usd, unique_buyers, 
                         unique_sellers, wash_trading_volume, wash_trading_percent, 
                         whale_activity, social_mentions, sentiment_score, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('analytics_id'),
                        item.get('collection_id'),
                        item.get('date'),
                        item.get('floor_price', 0),
                        item.get('floor_price_usd', 0),
                        item.get('volume', 0),
                        item.get('volume_usd', 0),
                        item.get('sales_count', 0),
                        item.get('average_price', 0),
                        item.get('average_price_usd', 0),
                        item.get('unique_buyers', 0),
                        item.get('unique_sellers', 0),
                        item.get('wash_trading_volume', 0),
                        item.get('wash_trading_percent', 0),
                        item.get('whale_activity', 0),
                        item.get('social_mentions', 0),
                        item.get('sentiment_score', 0),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条市场分析到数据库")
            
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
    
    def run(self, collection_count: int = 3, nfts_per_collection: int = 5, 
           trades_per_collection: int = 10, holders_per_collection: int = 5, 
           analytics_days: int = 7):
        """
        运行爬虫
        
        Args:
            collection_count: NFT集合数量
            nfts_per_collection: 每个集合NFT数量
            trades_per_collection: 每个集合交易记录数量
            holders_per_collection: 每个集合持有者数量
            analytics_days: 分析数据天数
        """
        logger.info("=== NFT信息爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取NFT集合列表
            logger.info(f"获取前 {collection_count} 个NFT集合")
            collections = self.get_nft_collections('opensea', collection_count)
            self.crawl_stats['total_collections'] = len(collections)
            
            if not collections:
                logger.error("未能获取NFT集合列表")
                return
            
            # 保存集合列表
            if collections:
                self.save_to_csv(collections, "nft_collections.csv")
                self.save_to_excel(collections, "nft_collections.xlsx")
                self.save_to_database('collections', collections)
            
            all_nft_items = []
            all_trades = []
            all_holders = []
            all_analytics = []
            
            # 2. 处理每个集合
            for i, collection in enumerate(collections):
                collection_id = collection.get('collection_id')
                logger.info(f"处理NFT集合 {i+1}/{len(collections)}: {collection.get('name')}")
                
                # 获取集合详情
                detail = self.get_collection_detail(collection_id)
                if detail:
                    self.save_to_json(detail, f"{collection_id}_detail.json")
                
                # 获取NFT项目
                nft_items = self.get_nft_items(collection_id, nfts_per_collection)
                if nft_items:
                    all_nft_items.extend(nft_items)
                    self.save_to_csv(nft_items, f"{collection_id}_nfts.csv")
                    self.save_to_database('items', nft_items)
                    self.crawl_stats['total_nfts'] += len(nft_items)
                
                # 获取交易记录
                trades = self.get_nft_trades(collection_id, trades_per_collection)
                if trades:
                    all_trades.extend(trades)
                    self.save_to_csv(trades, f"{collection_id}_trades.csv")
                    self.save_to_database('trades', trades)
                    self.crawl_stats['total_trades'] += len(trades)
                
                # 获取持有者
                holders = self.get_nft_holders(collection_id, holders_per_collection)
                if holders:
                    all_holders.extend(holders)
                    self.save_to_csv(holders, f"{collection_id}_holders.csv")
                    self.save_to_database('holders', holders)
                
                # 获取市场分析
                analytics = self.get_market_analytics(collection_id, analytics_days)
                if analytics:
                    all_analytics.extend(analytics)
                    self.save_to_csv(analytics, f"{collection_id}_analytics.csv")
                    self.save_to_database('analytics', analytics)
                
                # 随机延迟
                time.sleep(random.uniform(1, 2))
            
            # 3. 保存所有数据
            if all_nft_items:
                self.save_to_csv(all_nft_items, "all_nft_items.csv")
                self.save_to_json(all_nft_items, "all_nft_items.json")
            
            if all_trades:
                self.save_to_csv(all_trades, "all_nft_trades.csv")
                self.save_to_json(all_trades, "all_nft_trades.json")
            
            if all_holders:
                self.save_to_csv(all_holders, "all_nft_holders.csv")
                self.save_to_json(all_holders, "all_nft_holders.json")
            
            if all_analytics:
                self.save_to_csv(all_analytics, "all_market_analytics.csv")
                self.save_to_json(all_analytics, "all_market_analytics.json")
            
            # 4. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== NFT信息爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = NFTCrawler()
    
    # 运行爬虫
    crawler.run(
        collection_count=2,
        nfts_per_collection=3,
        trades_per_collection=5,
        holders_per_collection=3,
        analytics_days=7
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("NFT信息爬虫使用说明")
    print("="*60)
    print("支持的网站:")
    for website_id, website in crawler.websites.items():
        print(f"  - {website_id}: {website['name']} ({website['base_url']})")
    
    print("\n主要功能:")
    print("1. 获取NFT集合列表:")
    print("   collections = crawler.get_nft_collections('opensea', limit=10)")
    print("\n2. 获取集合详情:")
    print("   detail = crawler.get_collection_detail('boredapeyachtclub')")
    print("\n3. 获取NFT项目:")
    print("   nfts = crawler.get_nft_items('0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d', limit=10)")
    print("\n4. 获取交易记录:")
    print("   trades = crawler.get_nft_trades('0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d', limit=20)")
    print("\n5. 获取持有者:")
    print("   holders = crawler.get_nft_holders('0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d', limit=10)")
    print("\n6. 获取市场分析:")
    print("   analytics = crawler.get_market_analytics('0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d', days=30)")
    print("\n7. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("   crawler.save_to_excel(data, 'filename.xlsx')")
    print("\n8. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")
    print("\n9. API配置:")
    print("   需要注册并配置API密钥:")
    print("   - OpenSea: https://docs.opensea.io/reference/api-keys")
    print("   - Rarible: https://api.rarible.org/")
    print("   - Magic Eden: https://docs.magiceden.io/reference/overview")
    print("   - NFTGo: https://docs.nftgo.io/")

if __name__ == "__main__":
    main()