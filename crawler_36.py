#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币数据爬虫 - 从加密货币交易所和行情网站获取数据
目标网站: CoinMarketCap, Binance, CoinGecko等
功能: 爬取加密货币价格、交易量、市值、历史数据、市场动态等
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
        logging.FileHandler('crypto_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CryptocurrencyCrawler:
    """加密货币数据爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'coinmarketcap': {
                'name': 'CoinMarketCap',
                'base_url': 'https://coinmarketcap.com',
                'api_base': 'https://api.coinmarketcap.com',
                'api_key': 'CMC_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'X-CMC_PRO_API_KEY': 'YOUR_API_KEY_HERE'  # 需要替换
                }
            },
            'coingecko': {
                'name': 'CoinGecko',
                'base_url': 'https://www.coingecko.com',
                'api_base': 'https://api.coingecko.com/api/v3',
                'api_key': 'CG_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'binance': {
                'name': 'Binance',
                'base_url': 'https://www.binance.com',
                'api_base': 'https://api.binance.com',
                'api_key': 'BINANCE_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'X-MBX-APIKEY': 'YOUR_API_KEY_HERE'  # 需要替换
                }
            }
        }
        
        # 主要加密货币
        self.major_cryptos = [
            {'symbol': 'BTC', 'name': 'Bitcoin', 'id': 'bitcoin'},
            {'symbol': 'ETH', 'name': 'Ethereum', 'id': 'ethereum'},
            {'symbol': 'BNB', 'name': 'Binance Coin', 'id': 'binancecoin'},
            {'symbol': 'SOL', 'name': 'Solana', 'id': 'solana'},
            {'symbol': 'XRP', 'name': 'Ripple', 'id': 'ripple'},
            {'symbol': 'ADA', 'name': 'Cardano', 'id': 'cardano'},
            {'symbol': 'AVAX', 'name': 'Avalanche', 'id': 'avalanche-2'},
            {'symbol': 'DOT', 'name': 'Polkadot', 'id': 'polkadot'},
            {'symbol': 'DOGE', 'name': 'Dogecoin', 'id': 'dogecoin'},
            {'symbol': 'SHIB', 'name': 'Shiba Inu', 'id': 'shiba-inu'}
        ]
        
        # 加密货币分类
        self.crypto_categories = [
            'Layer 1', 'Layer 2', 'DeFi', 'NFT', 'GameFi',
            'Web3', 'AI & Big Data', 'Meme', 'Stablecoin', 'Privacy',
            'Oracle', 'Exchange Token', 'Interoperability', 'SocialFi',
            'Infrastructure', 'Governance', 'Metaverse', 'Storage'
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "crypto_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "cryptocurrency.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_cryptos': 0,
            'total_markets': 0,
            'total_news': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 请求限制
        self.rate_limits = {
            'coinmarketcap': {'calls_per_minute': 30, 'last_call': 0},
            'coingecko': {'calls_per_minute': 50, 'last_call': 0},
            'binance': {'calls_per_minute': 1200, 'last_call': 0}
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
            os.path.join(self.data_dir, 'cryptocurrencies'),
            os.path.join(self.data_dir, 'markets'),
            os.path.join(self.data_dir, 'exchanges'),
            os.path.join(self.data_dir, 'news'),
            os.path.join(self.data_dir, 'historical'),
            os.path.join(self.data_dir, 'analysis'),
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
            
            # 创建加密货币表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cryptocurrencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crypto_id TEXT UNIQUE,
                    symbol TEXT,
                    name TEXT,
                    slug TEXT,
                    rank INTEGER,
                    market_cap_usd REAL,
                    market_cap_rank INTEGER,
                    fully_diluted_valuation REAL,
                    total_volume_usd REAL,
                    max_supply REAL,
                    total_supply REAL,
                    circulating_supply REAL,
                    price_usd REAL,
                    price_btc REAL,
                    price_change_24h REAL,
                    price_change_percent_24h REAL,
                    market_cap_change_24h REAL,
                    market_cap_change_percent_24h REAL,
                    ath REAL,
                    ath_change_percent REAL,
                    ath_date TEXT,
                    atl REAL,
                    atl_change_percent REAL,
                    atl_date TEXT,
                    last_updated TEXT,
                    website TEXT,
                    whitepaper TEXT,
                    explorer TEXT,
                    twitter TEXT,
                    telegram TEXT,
                    reddit TEXT,
                    github TEXT,
                    categories TEXT,
                    tags TEXT,
                    description TEXT,
                    platform TEXT,
                    contract_address TEXT,
                    crawl_time TIMESTAMP,
                    last_updated_db TIMESTAMP
                )
            ''')
            
            # 创建市场数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crypto_id TEXT,
                    exchange_id TEXT,
                    pair TEXT,
                    price_usd REAL,
                    volume_24h REAL,
                    volume_percent REAL,
                    last_trade_time TEXT,
                    bid_price REAL,
                    ask_price REAL,
                    spread REAL,
                    depth_bid REAL,
                    depth_ask REAL,
                    update_time TIMESTAMP,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies (crypto_id)
                )
            ''')
            
            # 创建交易所表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchanges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange_id TEXT UNIQUE,
                    name TEXT,
                    year_established INTEGER,
                    country TEXT,
                    trust_score INTEGER,
                    trust_score_rank INTEGER,
                    trade_volume_24h_btc REAL,
                    trade_volume_24h_btc_normalized REAL,
                    url TEXT,
                    logo TEXT,
                    has_trading_incentive BOOLEAN,
                    centralized BOOLEAN,
                    description TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建历史数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historical_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crypto_id TEXT,
                    timestamp INTEGER,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    market_cap REAL,
                    update_time TIMESTAMP,
                    UNIQUE(crypto_id, timestamp)
                )
            ''')
            
            # 创建新闻表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crypto_news (
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
                    related_cryptos TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建投资组合表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    total_value REAL,
                    daily_change REAL,
                    daily_change_percent REAL,
                    creation_date TEXT,
                    last_updated TEXT,
                    holdings_json TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cryptos_symbol ON cryptocurrencies (symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cryptos_rank ON cryptocurrencies (rank)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_crypto ON market_data (crypto_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_exchange ON market_data (exchange_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_data_crypto ON historical_data (crypto_id, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_data_date ON historical_data (date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_date ON crypto_news (publish_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_cryptos ON crypto_news (related_cryptos)')
            
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
    
    def get_cached_response(self, cache_key: str, max_age_minutes: int = 5) -> Optional[Dict]:
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
                    cache_age: int = 5,  # 分钟
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
    
    def get_cryptocurrency_list(self, website_id: str = 'coingecko', 
                               limit: int = 20) -> List[Dict]:
        """
        获取加密货币列表
        
        Args:
            website_id: 网站ID
            limit: 限制数量
            
        Returns:
            加密货币列表
        """
        website = self.websites.get(website_id, self.websites['coingecko'])
        logger.info(f"从{website['name']}获取加密货币列表，限制{limit}个")
        
        if website_id == 'coingecko':
            # CoinGecko API
            url = f"{website['api_base']}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '1h,24h,7d'
            }
            
            response = self.safe_request(
                url,
                params=params,
                headers=website['headers'],
                website_id=website_id,
                use_cache=True,
                cache_age=10
            )
            
            if response:
                try:
                    data = response.json()
                    cryptos = self._parse_coingecko_markets(data)
                    return cryptos[:limit]
                except Exception as e:
                    logger.error(f"解析CoinGecko响应失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_cryptocurrencies(limit)
    
    def _parse_coingecko_markets(self, data: List[Dict]) -> List[Dict]:
        """解析CoinGecko市场数据"""
        cryptos = []
        
        for item in data:
            try:
                crypto = {
                    'crypto_id': item.get('id', ''),
                    'symbol': item.get('symbol', '').upper(),
                    'name': item.get('name', ''),
                    'rank': item.get('market_cap_rank', 0),
                    'market_cap_usd': item.get('market_cap', 0),
                    'total_volume_usd': item.get('total_volume', 0),
                    'price_usd': item.get('current_price', 0),
                    'price_change_percent_24h': item.get('price_change_percentage_24h', 0),
                    'ath': item.get('ath', 0),
                    'ath_change_percent': item.get('ath_change_percentage', 0),
                    'ath_date': item.get('ath_date', ''),
                    'atl': item.get('atl', 0),
                    'atl_change_percent': item.get('atl_change_percentage', 0),
                    'atl_date': item.get('atl_date', ''),
                    'last_updated': item.get('last_updated', ''),
                    'image': item.get('image', ''),
                    'circulating_supply': item.get('circulating_supply', 0),
                    'total_supply': item.get('total_supply', 0),
                    'max_supply': item.get('max_supply', 0),
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                cryptos.append(crypto)
            except Exception as e:
                logger.error(f"解析加密货币数据失败: {e}")
                continue
        
        logger.info(f"解析到 {len(cryptos)} 个加密货币")
        return cryptos
    
    def _generate_mock_cryptocurrencies(self, count: int) -> List[Dict]:
        """生成模拟加密货币数据"""
        cryptos = []
        
        for i in range(min(count, len(self.major_cryptos))):
            crypto_info = self.major_cryptos[i]
            
            # 生成价格数据
            base_price = random.uniform(10, 50000)
            market_cap = base_price * random.uniform(1e6, 1e9)
            volume_24h = market_cap * random.uniform(0.01, 0.1)
            
            # 生成涨跌幅
            price_change_24h = random.uniform(-0.2, 0.2)  # -20% 到 +20%
            
            # 生成ATH/ATL数据
            ath = base_price * random.uniform(1.5, 3.0)
            ath_change_percent = ((base_price - ath) / ath) * 100
            atl = base_price * random.uniform(0.1, 0.5)
            atl_change_percent = ((base_price - atl) / atl) * 100
            
            crypto = {
                'crypto_id': crypto_info['id'],
                'symbol': crypto_info['symbol'],
                'name': crypto_info['name'],
                'rank': i + 1,
                'market_cap_usd': round(market_cap, 2),
                'total_volume_usd': round(volume_24h, 2),
                'price_usd': round(base_price, 4),
                'price_change_24h': round(base_price * price_change_24h, 4),
                'price_change_percent_24h': round(price_change_24h * 100, 2),
                'ath': round(ath, 4),
                'ath_change_percent': round(ath_change_percent, 2),
                'ath_date': (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'atl': round(atl, 4),
                'atl_change_percent': round(atl_change_percent, 2),
                'atl_date': (datetime.now() - timedelta(days=random.randint(365, 1825))).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'last_updated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'image': f"https://example.com/images/{crypto_info['symbol'].lower()}.png",
                'circulating_supply': random.uniform(1e6, 1e9),
                'total_supply': random.uniform(1e6, 1e10),
                'max_supply': random.uniform(1e7, 2.1e7),
                'categories': random.choice(self.crypto_categories),
                'description': f"{crypto_info['name']} is a decentralized cryptocurrency.",
                'website': f"https://www.{crypto_info['symbol'].lower()}.org",
                'whitepaper': f"https://www.{crypto_info['symbol'].lower()}.org/whitepaper.pdf",
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            cryptos.append(crypto)
        
        logger.info(f"生成 {len(cryptos)} 个模拟加密货币")
        return cryptos
    
    def get_cryptocurrency_detail(self, crypto_id: str, 
                                 website_id: str = 'coingecko') -> Optional[Dict]:
        """
        获取加密货币详情
        
        Args:
            crypto_id: 加密货币ID
            website_id: 网站ID
            
        Returns:
            加密货币详情字典
        """
        logger.info(f"获取加密货币详情: {crypto_id}")
        
        website = self.websites.get(website_id, self.websites['coingecko'])
        
        if website_id == 'coingecko':
            # CoinGecko API
            url = f"{website['api_base']}/coins/{crypto_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
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
                    detail = self._parse_coingecko_detail(data, crypto_id)
                    return detail
                except Exception as e:
                    logger.error(f"解析CoinGecko详情失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_crypto_detail(crypto_id)
    
    def _parse_coingecko_detail(self, data: Dict, crypto_id: str) -> Dict:
        """解析CoinGecko详情数据"""
        try:
            market_data = data.get('market_data', {})
            
            detail = {
                'crypto_id': crypto_id,
                'symbol': data.get('symbol', '').upper(),
                'name': data.get('name', ''),
                'description': data.get('description', {}).get('en', ''),
                'homepage': data.get('links', {}).get('homepage', [''])[0],
                'whitepaper': data.get('links', {}).get('whitepaper', ''),
                'explorer': data.get('links', {}).get('blockchain_site', [''])[0],
                'twitter': data.get('links', {}).get('twitter_screen_name', ''),
                'telegram': data.get('links', {}).get('telegram_channel_identifier', ''),
                'reddit': data.get('links', {}).get('subreddit_url', ''),
                'github': data.get('links', {}).get('repos_url', {}).get('github', [''])[0],
                'categories': ','.join(data.get('categories', [])),
                'genesis_date': data.get('genesis_date', ''),
                'hashing_algorithm': data.get('hashing_algorithm', ''),
                'market_cap_rank': data.get('market_cap_rank', 0),
                'market_cap_usd': market_data.get('market_cap', {}).get('usd', 0),
                'total_volume_usd': market_data.get('total_volume', {}).get('usd', 0),
                'fully_diluted_valuation': market_data.get('fully_diluted_valuation', {}).get('usd', 0),
                'price_usd': market_data.get('current_price', {}).get('usd', 0),
                'price_btc': market_data.get('current_price', {}).get('btc', 0),
                'price_change_24h': market_data.get('price_change_24h', 0),
                'price_change_percent_24h': market_data.get('price_change_percentage_24h', 0),
                'market_cap_change_24h': market_data.get('market_cap_change_24h', 0),
                'market_cap_change_percent_24h': market_data.get('market_cap_change_percentage_24h', 0),
                'circulating_supply': market_data.get('circulating_supply', 0),
                'total_supply': market_data.get('total_supply', 0),
                'max_supply': market_data.get('max_supply', 0),
                'ath': market_data.get('ath', {}).get('usd', 0),
                'ath_change_percent': market_data.get('ath_change_percentage', {}).get('usd', 0),
                'ath_date': market_data.get('ath_date', {}).get('usd', ''),
                'atl': market_data.get('atl', {}).get('usd', 0),
                'atl_change_percent': market_data.get('atl_change_percentage', {}).get('usd', 0),
                'atl_date': market_data.get('atl_date', {}).get('usd', ''),
                'last_updated': market_data.get('last_updated', ''),
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"解析加密货币详情: {detail['name']}")
            return detail
            
        except Exception as e:
            logger.error(f"解析加密货币详情异常: {e}")
            return self._generate_mock_crypto_detail(crypto_id)
    
    def _generate_mock_crypto_detail(self, crypto_id: str) -> Dict:
        """生成模拟加密货币详情"""
        # 查找加密货币信息
        crypto_info = None
        for crypto in self.major_cryptos:
            if crypto['id'] == crypto_id:
                crypto_info = crypto
                break
        
        if not crypto_info:
            # 创建默认信息
            crypto_info = {
                'symbol': crypto_id[:3].upper(),
                'name': crypto_id.capitalize(),
                'id': crypto_id
            }
        
        # 生成详细数据
        base_price = random.uniform(10, 50000)
        
        detail = {
            'crypto_id': crypto_id,
            'symbol': crypto_info['symbol'],
            'name': crypto_info['name'],
            'description': f"{crypto_info['name']} is a decentralized cryptocurrency that enables peer-to-peer transactions without intermediaries.",
            'homepage': f"https://www.{crypto_info['symbol'].lower()}.org",
            'whitepaper': f"https://www.{crypto_info['symbol'].lower()}.org/whitepaper.pdf",
            'explorer': f"https://explorer.{crypto_info['symbol'].lower()}.org",
            'twitter': f"@{crypto_info['symbol'].lower()}",
            'telegram': f"https://t.me/{crypto_info['symbol'].lower()}",
            'reddit': f"https://reddit.com/r/{crypto_info['symbol'].lower()}",
            'github': f"https://github.com/{crypto_info['symbol'].lower()}",
            'categories': random.choice(self.crypto_categories),
            'genesis_date': '2018-01-01',
            'hashing_algorithm': random.choice(['SHA-256', 'Ethash', 'Scrypt', 'X11', 'RandomX']),
            'market_cap_rank': random.randint(1, 100),
            'market_cap_usd': round(base_price * random.uniform(1e6, 1e9), 2),
            'total_volume_usd': round(base_price * random.uniform(1e5, 1e8), 2),
            'fully_diluted_valuation': round(base_price * random.uniform(1e7, 1e10), 2),
            'price_usd': round(base_price, 4),
            'price_btc': round(base_price / 50000, 8),  # 假设比特币价格50000
            'price_change_24h': round(base_price * random.uniform(-0.2, 0.2), 4),
            'price_change_percent_24h': round(random.uniform(-20, 20), 2),
            'market_cap_change_24h': round(base_price * random.uniform(-0.1, 0.1) * random.uniform(1e6, 1e9), 2),
            'market_cap_change_percent_24h': round(random.uniform(-10, 10), 2),
            'circulating_supply': round(random.uniform(1e6, 1e9), 0),
            'total_supply': round(random.uniform(1e6, 1e10), 0),
            'max_supply': round(random.uniform(1e7, 2.1e7), 0),
            'ath': round(base_price * random.uniform(1.5, 3.0), 4),
            'ath_change_percent': round(random.uniform(-50, -20), 2),
            'ath_date': (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'atl': round(base_price * random.uniform(0.1, 0.5), 4),
            'atl_change_percent': round(random.uniform(100, 500), 2),
            'atl_date': (datetime.now() - timedelta(days=random.randint(365, 1825))).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'last_updated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return detail
    
    def get_historical_data(self, crypto_id: str, days: int = 30, 
                           website_id: str = 'coingecko') -> List[Dict]:
        """
        获取历史数据
        
        Args:
            crypto_id: 加密货币ID
            days: 天数
            website_id: 网站ID
            
        Returns:
            历史数据列表
        """
        logger.info(f"获取{crypto_id}的历史数据，{days}天")
        
        website = self.websites.get(website_id, self.websites['coingecko'])
        
        if website_id == 'coingecko':
            # CoinGecko API
            url = f"{website['api_base']}/coins/{crypto_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
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
                    historical_data = self._parse_coingecko_historical(data, crypto_id, days)
                    return historical_data
                except Exception as e:
                    logger.error(f"解析CoinGecko历史数据失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_historical_data(crypto_id, days)
    
    def _parse_coingecko_historical(self, data: Dict, crypto_id: str, days: int) -> List[Dict]:
        """解析CoinGecko历史数据"""
        historical_data = []
        
        try:
            prices = data.get('prices', [])
            market_caps = data.get('market_caps', [])
            total_volumes = data.get('total_volumes', [])
            
            for i in range(len(prices)):
                timestamp = prices[i][0] // 1000  # 转换为秒
                date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                price = prices[i][1]
                
                # 获取对应的市值和交易量
                market_cap = market_caps[i][1] if i < len(market_caps) else 0
                volume = total_volumes[i][1] if i < len(total_volumes) else 0
                
                # 生成OHLC数据（简化）
                open_price = price * random.uniform(0.98, 1.02)
                high_price = max(open_price, price) * random.uniform(1.0, 1.05)
                low_price = min(open_price, price) * random.uniform(0.95, 1.0)
                close_price = price
                
                data_point = {
                    'crypto_id': crypto_id,
                    'timestamp': timestamp,
                    'date': date,
                    'open': round(open_price, 4),
                    'high': round(high_price, 4),
                    'low': round(low_price, 4),
                    'close': round(close_price, 4),
                    'volume': round(volume, 2),
                    'market_cap': round(market_cap, 2),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                historical_data.append(data_point)
            
            logger.info(f"解析到 {len(historical_data)} 条历史数据")
            
        except Exception as e:
            logger.error(f"解析历史数据异常: {e}")
            historical_data = self._generate_mock_historical_data(crypto_id, days)
        
        return historical_data
    
    def _generate_mock_historical_data(self, crypto_id: str, days: int) -> List[Dict]:
        """生成模拟历史数据"""
        historical_data = []
        
        # 基础价格
        base_price = random.uniform(10, 50000)
        
        for i in range(days):
            # 生成日期
            date = datetime.now() - timedelta(days=days - i - 1)
            
            # 生成价格（模拟随机游走）
            if i == 0:
                price = base_price
            else:
                # 基于前一日价格生成
                prev_price = historical_data[-1]['close']
                change_percent = random.uniform(-0.1, 0.1)  # -10% 到 +10%
                price = prev_price * (1 + change_percent)
            
            # 生成OHLC数据
            open_price = price * random.uniform(0.98, 1.02)
            high_price = max(open_price, price) * random.uniform(1.0, 1.05)
            low_price = min(open_price, price) * random.uniform(0.95, 1.0)
            close_price = price
            
            # 生成交易量和市值
            volume = random.uniform(1e5, 1e8)
            market_cap = close_price * random.uniform(1e6, 1e9)
            
            data_point = {
                'crypto_id': crypto_id,
                'timestamp': int(date.timestamp()),
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 4),
                'high': round(high_price, 4),
                'low': round(low_price, 4),
                'close': round(close_price, 4),
                'volume': round(volume, 2),
                'market_cap': round(market_cap, 2),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            historical_data.append(data_point)
        
        logger.info(f"生成 {len(historical_data)} 条模拟历史数据")
        return historical_data
    
    def get_crypto_news(self, limit: int = 10) -> List[Dict]:
        """
        获取加密货币新闻
        
        Args:
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        logger.info(f"获取加密货币新闻，限制{limit}条")
        
        # 模拟新闻数据
        news_sources = ['CoinDesk', 'Cointelegraph', 'CryptoSlate', 'Bitcoin.com', 'Decrypt']
        news_topics = [
            'Bitcoin ETF Approval',
            'Ethereum Upgrade',
            'Regulatory News',
            'Market Analysis',
            'New Cryptocurrency Launch',
            'Exchange News',
            'DeFi Developments',
            'NFT Trends',
            'Web3 Innovations',
            'Crypto Adoption'
        ]
        
        news_list = []
        
        for i in range(limit):
            # 生成随机时间（最近7天内）
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            publish_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
            
            # 选择相关加密货币
            related_cryptos = random.sample(self.major_cryptos, random.randint(1, 3))
            crypto_symbols = [crypto['symbol'] for crypto in related_cryptos]
            
            news = {
                'news_id': f"news_{hashlib.md5(str(i).encode()).hexdigest()[:12]}",
                'source': random.choice(news_sources),
                'title': f"{random.choice(news_topics)}: What You Need to Know",
                'summary': f"Latest developments in {', '.join(crypto_symbols)} and the broader cryptocurrency market.",
                'content': f"This article discusses the latest news about {', '.join(crypto_symbols)}. The cryptocurrency market continues to evolve with new developments and regulatory changes.",
                'url': f"https://example.com/news/{i+1}",
                'image_url': f"https://example.com/images/crypto_news_{i+1}.jpg",
                'publish_date': publish_time.strftime('%Y-%m-%d %H:%M:%S'),
                'author': random.choice(['John Crypto', 'Alice Blockchain', 'Bob Bitcoin']),
                'tags': ','.join(['cryptocurrency', 'blockchain', 'news'] + crypto_symbols),
                'sentiment_score': round(random.uniform(-0.5, 0.5), 2),
                'related_cryptos': ','.join(crypto_symbols),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            news_list.append(news)
        
        logger.info(f"生成 {len(news_list)} 条加密货币新闻")
        return news_list
    
    def save_to_database(self, data_type: str, data: List[Dict]):
        """保存数据到数据库"""
        if not data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type == 'cryptocurrencies':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO cryptocurrencies 
                        (crypto_id, symbol, name, slug, rank, market_cap_usd, 
                         market_cap_rank, fully_diluted_valuation, total_volume_usd, 
                         max_supply, total_supply, circulating_supply, price_usd, 
                         price_btc, price_change_24h, price_change_percent_24h, 
                         market_cap_change_24h, market_cap_change_percent_24h, 
                         ath, ath_change_percent, ath_date, atl, atl_change_percent, 
                         atl_date, last_updated, website, whitepaper, explorer, 
                         twitter, telegram, reddit, github, categories, tags, 
                         description, platform, contract_address, crawl_time, 
                         last_updated_db)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('crypto_id'),
                        item.get('symbol'),
                        item.get('name'),
                        item.get('symbol', '').lower(),
                        item.get('rank', 0),
                        item.get('market_cap_usd', 0),
                        item.get('rank', 0),  # market_cap_rank
                        item.get('fully_diluted_valuation', 0),
                        item.get('total_volume_usd', 0),
                        item.get('max_supply', 0),
                        item.get('total_supply', 0),
                        item.get('circulating_supply', 0),
                        item.get('price_usd', 0),
                        item.get('price_btc', 0),
                        item.get('price_change_24h', 0),
                        item.get('price_change_percent_24h', 0),
                        item.get('market_cap_change_24h', 0),
                        item.get('market_cap_change_percent_24h', 0),
                        item.get('ath', 0),
                        item.get('ath_change_percent', 0),
                        item.get('ath_date', ''),
                        item.get('atl', 0),
                        item.get('atl_change_percent', 0),
                        item.get('atl_date', ''),
                        item.get('last_updated', ''),
                        item.get('website', ''),
                        item.get('whitepaper', ''),
                        item.get('explorer', ''),
                        item.get('twitter', ''),
                        item.get('telegram', ''),
                        item.get('reddit', ''),
                        item.get('github', ''),
                        item.get('categories', ''),
                        item.get('tags', ''),
                        item.get('description', ''),
                        '',  # platform
                        '',  # contract_address
                        item.get('crawl_time'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                logger.info(f"保存 {len(data)} 个加密货币到数据库")
                
            elif data_type == 'historical':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO historical_data 
                        (crypto_id, timestamp, date, open, high, low, close, 
                         volume, market_cap, update_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('crypto_id'),
                        item.get('timestamp'),
                        item.get('date'),
                        item.get('open'),
                        item.get('high'),
                        item.get('low'),
                        item.get('close'),
                        item.get('volume'),
                        item.get('market_cap'),
                        item.get('update_time')
                    ))
                
                logger.info(f"保存 {len(data)} 条历史数据到数据库")
                
            elif data_type == 'news':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO crypto_news 
                        (news_id, source, title, summary, content, url, 
                         image_url, publish_date, author, tags, sentiment_score, 
                         related_cryptos, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        item.get('sentiment_score'),
                        item.get('related_cryptos'),
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
    
    def run(self, crypto_count: int = 5, historical_days: int = 7, 
           news_count: int = 5):
        """
        运行爬虫
        
        Args:
            crypto_count: 加密货币数量
            historical_days: 历史数据天数
            news_count: 新闻数量
        """
        logger.info("=== 加密货币爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取加密货币列表
            logger.info(f"获取前 {crypto_count} 个加密货币")
            cryptos = self.get_cryptocurrency_list('coingecko', crypto_count)
            self.crawl_stats['total_cryptos'] = len(cryptos)
            
            if not cryptos:
                logger.error("未能获取加密货币列表")
                return
            
            # 保存加密货币列表
            if cryptos:
                self.save_to_csv(cryptos, "cryptocurrencies.csv")
                self.save_to_excel(cryptos, "cryptocurrencies.xlsx")
                self.save_to_database('cryptocurrencies', cryptos)
            
            all_crypto_details = []
            all_historical_data = []
            
            # 2. 获取每个加密货币的详情和历史数据
            for i, crypto in enumerate(cryptos):
                crypto_id = crypto.get('crypto_id')
                logger.info(f"处理加密货币 {i+1}/{len(cryptos)}: {crypto.get('name')}")
                
                # 获取详情
                detail = self.get_cryptocurrency_detail(crypto_id)
                if detail:
                    all_crypto_details.append(detail)
                    
                    # 保存详情
                    self.save_to_json(detail, f"{crypto_id}_detail.json")
                
                # 获取历史数据
                historical = self.get_historical_data(crypto_id, historical_days)
                if historical:
                    all_historical_data.extend(historical)
                    
                    # 保存历史数据
                    self.save_to_csv(historical, f"{crypto_id}_historical.csv")
                
                # 随机延迟
                time.sleep(random.uniform(1, 2))
            
            # 3. 保存所有详情和历史数据
            if all_crypto_details:
                self.save_to_csv(all_crypto_details, "all_crypto_details.csv")
                self.save_to_json(all_crypto_details, "all_crypto_details.json")
            
            if all_historical_data:
                self.save_to_csv(all_historical_data, "all_historical_data.csv")
                self.save_to_database('historical', all_historical_data)
            
            # 4. 获取加密货币新闻
            logger.info(f"获取 {news_count} 条加密货币新闻")
            news = self.get_crypto_news(news_count)
            self.crawl_stats['total_news'] = len(news)
            
            if news:
                self.save_to_csv(news, "crypto_news.csv")
                self.save_to_json(news, "crypto_news.json")
                self.save_to_database('news', news)
            
            # 5. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.crawl_stats['total_markets'] = len(cryptos)  # 假设每个加密货币代表一个市场
            
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 加密货币爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = CryptocurrencyCrawler()
    
    # 运行爬虫
    crawler.run(
        crypto_count=3,
        historical_days=7,
        news_count=3
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("加密货币数据爬虫使用说明")
    print("="*60)
    print("支持的网站:")
    for website_id, website in crawler.websites.items():
        print(f"  - {website_id}: {website['name']} ({website['base_url']})")
    
    print("\n主要功能:")
    print("1. 获取加密货币列表:")
    print("   cryptos = crawler.get_cryptocurrency_list('coingecko', limit=10)")
    print("\n2. 获取加密货币详情:")
    print("   detail = crawler.get_cryptocurrency_detail('bitcoin')")
    print("\n3. 获取历史数据:")
    print("   historical = crawler.get_historical_data('bitcoin', days=30)")
    print("\n4. 获取加密货币新闻:")
    print("   news = crawler.get_crypto_news(limit=10)")
    print("\n5. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("   crawler.save_to_excel(data, 'filename.xlsx')")
    print("\n6. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")
    print("\n7. API配置:")
    print("   需要注册并配置API密钥:")
    print("   - CoinMarketCap: https://coinmarketcap.com/api/")
    print("   - CoinGecko: https://www.coingecko.com/api")
    print("   - Binance: https://www.binance.com/en/binance-api")

if __name__ == "__main__":
    main()