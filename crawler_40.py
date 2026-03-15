#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区块链数据爬虫 - 从区块链浏览器和数据分析平台获取区块链数据
目标网站: Etherscan, BscScan, PolygonScan, DeFiLlama等
功能: 爬取区块链交易、智能合约、DeFi协议、NFT数据等
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
        logging.FileHandler('blockchain_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BlockchainCrawler:
    """区块链数据爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'etherscan': {
                'name': 'Etherscan',
                'base_url': 'https://etherscan.io',
                'api_base': 'https://api.etherscan.io/api',
                'api_key': 'ETHERSCAN_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'bscscan': {
                'name': 'BscScan',
                'base_url': 'https://bscscan.com',
                'api_base': 'https://api.bscscan.com/api',
                'api_key': 'BSCSCAN_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'polygonscan': {
                'name': 'PolygonScan',
                'base_url': 'https://polygonscan.com',
                'api_base': 'https://api.polygonscan.com/api',
                'api_key': 'POLYGONSCAN_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'defillama': {
                'name': 'DeFiLlama',
                'base_url': 'https://defillama.com',
                'api_base': 'https://api.llama.fi',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            }
        }
        
        # 区块链网络
        self.blockchain_networks = [
            {'name': 'Ethereum', 'symbol': 'ETH', 'chain_id': 1, 'scan': 'etherscan'},
            {'name': 'BNB Chain', 'symbol': 'BNB', 'chain_id': 56, 'scan': 'bscscan'},
            {'name': 'Polygon', 'symbol': 'MATIC', 'chain_id': 137, 'scan': 'polygonscan'},
            {'name': 'Arbitrum', 'symbol': 'ARB', 'chain_id': 42161, 'scan': 'arbiscan'},
            {'name': 'Optimism', 'symbol': 'OP', 'chain_id': 10, 'scan': 'optimistic.etherscan'},
            {'name': 'Avalanche', 'symbol': 'AVAX', 'chain_id': 43114, 'scan': 'snowtrace'},
            {'name': 'Fantom', 'symbol': 'FTM', 'chain_id': 250, 'scan': 'ftmscan'},
            {'name': 'Base', 'symbol': 'BASE', 'chain_id': 8453, 'scan': 'basescan'}
        ]
        
        # 主要DeFi协议
        self.defi_protocols = [
            {'name': 'Uniswap', 'category': 'DEX', 'tvl': 5000000000},
            {'name': 'Aave', 'category': 'Lending', 'tvl': 15000000000},
            {'name': 'Compound', 'category': 'Lending', 'tvl': 2000000000},
            {'name': 'MakerDAO', 'category': 'CDP', 'tvl': 8000000000},
            {'name': 'Curve', 'category': 'Stablecoin DEX', 'tvl': 2000000000},
            {'name': 'Lido', 'category': 'Liquid Staking', 'tvl': 35000000000},
            {'name': 'PancakeSwap', 'category': 'DEX', 'tvl': 1500000000},
            {'name': 'SushiSwap', 'category': 'DEX', 'tvl': 300000000},
            {'name': 'Balancer', 'category': 'DEX', 'tvl': 1000000000},
            {'name': 'Yearn Finance', 'category': 'Yield Aggregator', 'tvl': 500000000}
        ]
        
        # 主要代币
        self.major_tokens = [
            {'symbol': 'ETH', 'name': 'Ethereum', 'contract': '0x0000000000000000000000000000000000000000'},
            {'symbol': 'USDT', 'name': 'Tether', 'contract': '0xdac17f958d2ee523a2206206994597c13d831ec7'},
            {'symbol': 'USDC', 'name': 'USD Coin', 'contract': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'},
            {'symbol': 'WBTC', 'name': 'Wrapped Bitcoin', 'contract': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'},
            {'symbol': 'DAI', 'name': 'Dai Stablecoin', 'contract': '0x6b175474e89094c44da98b954eedeac495271d0f'},
            {'symbol': 'LINK', 'name': 'Chainlink', 'contract': '0x514910771af9ca656af840dff83e8264ecf986ca'},
            {'symbol': 'UNI', 'name': 'Uniswap', 'contract': '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984'},
            {'symbol': 'AAVE', 'name': 'Aave', 'contract': '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9'},
            {'symbol': 'MATIC', 'name': 'Polygon', 'contract': '0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0'},
            {'symbol': 'BNB', 'name': 'BNB', 'contract': '0xb8c77482e45f1f44de1745f52c74426c631bdd52'}
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "blockchain_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "blockchain.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_transactions': 0,
            'total_contracts': 0,
            'total_tokens': 0,
            'total_defi_protocols': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 请求限制
        self.rate_limits = {
            'etherscan': {'calls_per_second': 5, 'last_call': 0},
            'bscscan': {'calls_per_second': 5, 'last_call': 0},
            'polygonscan': {'calls_per_second': 5, 'last_call': 0},
            'defillama': {'calls_per_second': 10, 'last_call': 0}
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
            os.path.join(self.data_dir, 'transactions'),
            os.path.join(self.data_dir, 'contracts'),
            os.path.join(self.data_dir, 'tokens'),
            os.path.join(self.data_dir, 'defi'),
            os.path.join(self.data_dir, 'nfts'),
            os.path.join(self.data_dir, 'wallets'),
            os.path.join(self.data_dir, 'blocks'),
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
            
            # 创建区块链网络表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blockchain_networks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    network_id TEXT UNIQUE,
                    name TEXT,
                    symbol TEXT,
                    chain_id INTEGER,
                    rpc_url TEXT,
                    explorer_url TEXT,
                    native_token TEXT,
                    gas_token TEXT,
                    block_time INTEGER,
                    consensus_mechanism TEXT,
                    launch_date TEXT,
                    total_supply REAL,
                    circulating_supply REAL,
                    market_cap REAL,
                    market_cap_usd REAL,
                    total_transactions INTEGER,
                    total_addresses INTEGER,
                    total_contracts INTEGER,
                    active_addresses_24h INTEGER,
                    transaction_fee_avg REAL,
                    transaction_fee_usd_avg REAL,
                    tps INTEGER,
                    tps_max INTEGER,
                    security_score REAL,
                      decentralization_score REAL,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建交易表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blockchain_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT UNIQUE,
                    network_id TEXT,
                    block_number INTEGER,
                    block_hash TEXT,
                    timestamp INTEGER,
                    from_address TEXT,
                    to_address TEXT,
                    value REAL,
                    value_usd REAL,
                    gas_price REAL,
                    gas_used INTEGER,
                    gas_limit INTEGER,
                    transaction_fee REAL,
                    transaction_fee_usd REAL,
                    nonce INTEGER,
                    input_data TEXT,
                    method TEXT,
                    status TEXT,
                    contract_address TEXT,
                    token_transfers TEXT,
                    internal_transactions TEXT,
                    log_events TEXT,
                    confirmation_blocks INTEGER,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (network_id) REFERENCES blockchain_networks (network_id)
                )
            ''')
            
            # 创建智能合约表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smart_contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id