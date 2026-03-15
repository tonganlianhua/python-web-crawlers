#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫07: 股票数据爬虫 - 实时股票信息获取
功能: 爬取股票实时行情、历史数据、财务指标，支持A股、港股、美股
注意: 本爬虫仅用于学习研究，不构成投资建议
"""

import requests
import json
import time
from datetime import datetime, timedelta
import logging
import os
import csv
import sqlite3
from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_07.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StockMarket(Enum):
    """股票市场枚举"""
    A_SHARE = "ashare"      # A股
    HK = "hk"              # 港股
    US = "us"              # 美股

@dataclass
class StockData:
    """股票数据结构"""
    symbol: str            # 股票代码
    name: str              # 股票名称
    market: StockMarket    # 市场
    current_price: float   # 当前价格
    change: float          # 涨跌额
    change_percent: float  # 涨跌幅
    open_price: float      # 开盘价
    prev_close: float      # 昨收价
    high: float            # 最高价
    low: float             # 最低价
    volume: int            # 成交量
    amount: float          # 成交额
    timestamp: str         # 时间戳

class StockCrawler:
    """股票数据爬虫"""
    
    def __init__(self, db_path: str = "stocks.db"):
        """
        初始化股票爬虫
        
        Args:
            db_path: 数据库路径
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # API配置
        self.api_config = {
            'eastmoney': 'https://push2.eastmoney.com/api',  # 东方财富
            'sina': 'https://hq.sinajs.cn',                  # 新浪财经
            'tencent': 'https://qt.gtimg.cn',                # 腾讯财经
            'yahoo': 'https://query1.finance.yahoo.com'      # Yahoo Finance
        }
        
        # 数据库连接
        self.db_path = db_path
        self.init_database()
        
        logger.info("股票数据爬虫初始化完成")
    
    def init_database(self):
        """初始化数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # 创建股票基本信息表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    market TEXT,
                    industry TEXT,
                    area TEXT,
                    list_date TEXT,
                    total_shares REAL,
                    circulating_shares REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, market)
                )
            ''')
            
            # 创建股票日线数据表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount REAL,
                    change REAL,
                    change_percent REAL,
                    turnover_rate REAL,
                    amplitude REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            ''')
            
            # 创建股票实时数据表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_realtime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    price REAL,
                    change REAL,
                    change_percent REAL,
                    volume INTEGER,
                    amount REAL,
                    bid_price REAL,
                    ask_price REAL,
                    bid_volume INTEGER,
                    ask_volume INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建指数
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON stocks(symbol)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON stock_daily(symbol, date)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_realtime_symbol ON stock_realtime(symbol)')
            
            self.conn.commit()
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def get_realtime_price(self, symbol: str, market: StockMarket = StockMarket.A_SHARE) -> Optional[StockData]:
        """
        获取股票实时价格
        
        Args:
            symbol: 股票代码
            market: 市场类型
            
        Returns:
            StockData对象或None
        """
        try:
            logger.info(f"获取股票实时价格: {symbol} ({market.value})")
            
            if market == StockMarket.A_SHARE:
                return self._get_ashare_realtime(symbol)
            elif market == StockMarket.HK:
                return self._get_hk_realtime(symbol)
            elif market == StockMarket.US:
                return self._get_us_realtime(symbol)
            else:
                logger.warning(f"不支持的股票市场: {market}")
                return None
                
        except Exception as e:
            logger.error(f"获取实时价格失败: {e}")
            return None
    
    def _get_ashare_realtime(self, symbol: str) -> Optional[StockData]:
        """获取A股实时价格"""
        try:
            # 东方财富API
            api_url = f"{self.api_config['eastmoney']}/qt/stock/get"
            
            # 转换股票代码格式
            if symbol.startswith('6'):
                market_code = '1'  # 上证
            elif symbol.startswith('0') or symbol.startswith('3'):
                market_code = '0'  # 深证
            else:
                market_code = '0'
            
            secid = f"{market_code}.{symbol}"
            
            params = {
                'fltt': '2',
                'invt': '2',
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
                'secid': secid
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('rc') == 0 and data.get('data'):
                stock_data = data['data']
                
                stock = StockData(
                    symbol=stock_data.get('f12', symbol),
                    name=stock_data.get('f14', ''),
                    market=StockMarket.A_SHARE,
                    current_price=float(stock_data.get('f2', 0)),
                    change=float(stock_data.get('f4', 0)),
                    change_percent=float(stock_data.get('f3', 0)),
                    open_price=float(stock_data.get('f17', 0)),
                    prev_close=float(stock_data.get('f18', 0)),
                    high=float(stock_data.get('f15', 0)),
                    low=float(stock_data.get('f16', 0)),
                    volume=int(stock_data.get('f5', 0)),
                    amount=float(stock_data.get('f6', 0)),
                    timestamp=datetime.now().isoformat()
                )
                
                # 保存到数据库
                self.save_realtime_data(stock)
                
                return stock
            
            logger.warning(f"API返回数据异常: {data}")
            return None
            
        except Exception as e:
            logger.error(f"获取A股实时价格失败: {e}")
            # 尝试备用方法
            return self._get_ashare_realtime_backup(symbol)
    
    def _get_ashare_realtime_backup(self, symbol: str) -> Optional[StockData]:
        """A股实时价格备用方法（新浪财经）"""
        try:
            # 新浪财经API
            api_url = f"{self.api_config['sina']}/list={self._get_sina_symbol(symbol)}"
            
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            
            # 解析返回的数据（格式特殊）
            content = response.text
            # 格式: var hq_str_sh600000="浦发银行,11.650,11.660,11.640,...";
            
            data_match = re.search(r'="(.*?)"', content)
            if data_match:
                data_str = data_match.group(1)
                data_parts = data_str.split(',')
                
                if len(data_parts) >= 30:
                    stock = StockData(
                        symbol=symbol,
                        name=data_parts[0],
                        market=StockMarket.A_SHARE,
                        current_price=float(data_parts[3]),
                        change=float(data_parts[3]) - float(data_parts[2]),
                        change_percent=(float(data_parts[3]) - float(data_parts[2])) / float(data_parts[2]) * 100,
                        open_price=float(data_parts[1]),
                        prev_close=float(data_parts[2]),
                        high=float(data_parts[4]),
                        low=float(data_parts[5]),
                        volume=int(data_parts[8]),
                        amount=float(data_parts[9]),
                        timestamp=datetime.now().isoformat()
                    )
                    
                    self.save_realtime_data(stock)
                    return stock
            
            return None
            
        except Exception as e:
            logger.error(f"备用方法获取A股实时价格失败: {e}")
            return None
    
    def _get_hk_realtime(self, symbol: str) -> Optional[StockData]:
        """获取港股实时价格"""
        try:
            # 腾讯财经API
            api_url = f"{self.api_config['tencent']}/q=hk{symbol}"
            
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            
            # 解析返回的数据
            content = response.text
            # 格式: v_hk00700="腾讯控股";v_hk00700="340.200;340.600;..."
            
            data_match = re.search(r'="(.*?)"', content)
            if data_match:
                data_str = data_match.group(1)
                data_parts = data_str.split(';')
                
                if len(data_parts) >= 10:
                    stock = StockData(
                        symbol=symbol,
                        name=data_parts[0],
                        market=StockMarket.HK,
                        current_price=float(data_parts[1]),
                        change=float(data_parts[2]),
                        change_percent=float(data_parts[3]),
                        open_price=float(data_parts[4]),
                        prev_close=float(data_parts[5]),
                        high=float(data_parts[6]),
                        low=float(data_parts[7]),
                        volume=int(data_parts[8]),
                        amount=float(data_parts[9]),
                        timestamp=datetime.now().isoformat()
                    )
                    
                    self.save_realtime_data(stock)
                    return stock
            
            return None
            
        except Exception as e:
            logger.error(f"获取港股实时价格失败: {e}")
            return None
    
    def _get_us_realtime(self, symbol: str) -> Optional[StockData]:
        """获取美股实时价格"""
        try:
            # Yahoo Finance API
            api_url = f"{self.api_config['yahoo']}/v8/finance/chart/{symbol}"
            
            params = {
                'range': '1d',
                'interval': '1m',
                'includePrePost': 'false'
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('chart') and data['chart'].get('result'):
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                
                # 获取最新价格
                quotes = result.get('indicators', {}).get('quote', [{}])[0]
                close_prices = quotes.get('close', [])
                volumes = quotes.get('volume', [])
                
                if close_prices:
                    current_price = close_prices[-1]
                    prev_close = meta.get('previousClose', current_price)
                    
                    stock = StockData(
                        symbol=symbol,
                        name=meta.get('longName', symbol),
                        market=StockMarket.US,
                        current_price=current_price,
                        change=current_price - prev_close,
                        change_percent=(current_price - prev_close) / prev_close * 100,
                        open_price=meta.get('open', current_price),
                        prev_close=prev_close,
                        high=meta.get('dayHigh', current_price),
                        low=meta.get('dayLow', current_price),
                        volume=sum(volumes) if volumes else 0,
                        amount=current_price * (sum(volumes) if volumes else 0),
                        timestamp=datetime.now().isoformat()
                    )
                    
                    self.save_realtime_data(stock)
                    return stock
            
            return None
            
        except Exception as e:
            logger.error(f"获取美股实时价格失败: {e}")
            return None
    
    def _get_sina_symbol(self, symbol: str) -> str:
        """转换为新浪财经股票代码格式"""
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"
        else:
            return symbol
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str = None, 
                           market: StockMarket = StockMarket.A_SHARE) -> List[Dict]:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天
            market: 市场类型
            
        Returns:
            历史数据列表
        """
        try:
            logger.info(f"获取股票历史数据: {symbol} ({start_date} 到 {end_date})")
            
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 先从数据库查询
            historical = self.get_historical_from_db(symbol, start_date, end_date)
            
            if historical:
                logger.info(f"从数据库获取到 {len(historical)} 条历史数据")
                return historical
            
            # 数据库没有数据，从API获取
            if market == StockMarket.A_SHARE:
                api_data = self._get_ashare_historical(symbol, start_date, end_date)
            elif market == StockMarket.US:
                api_data = self._get_us_historical(symbol, start_date, end_date)
            else:
                logger.warning(f"暂不支持的历史数据获取: {market}")
                api_data = []
            
            if api_data:
                # 保存到数据库
                self.save_historical_data(symbol, api_data)
                return api_data
            
            return []
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return []
    
    def _get_ashare_historical(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """获取A股历史数据"""
        try:
            # 使用东方财富API
            if symbol.startswith('6'):
                secid = f"1.{symbol}"
            else:
                secid = f"0.{symbol}"
            
            api_url = f"{self.api_config['eastmoney']}/qt/stock/kline/get"
            
            params = {
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101',  # 日线
                'fqt': '1',    # 前复权
                'beg': start_date.replace('-', ''),
                'end': end_date.replace('-', ''),
                'lmt': '10000'  # 最大数据量
            }
            
            response = self.session.get(api_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('rc') == 0 and data.get('data'):
                klines = data['data'].get('klines', [])
                
                historical_data = []
                for kline in klines:
                    parts = kline.split(',')
                    if len(parts) >= 11:
                        record = {
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': int(parts[5]),
                            'amount': float(parts[6]),
                            'amplitude': float(parts[7]),
                            'change_percent': float(parts[8]),
                            'change': float(parts[9]),
                            'turnover_rate': float(parts[10])
                        }
                        historical_data.append(record)
                
                logger.info(f"从API获取到 {len(historical_data)} 条A股历史数据")
                return historical_data
            
            return []
            
        except Exception as e:
            logger.error(f"获取A股历史数据失败: {e}")
            return []
    
    def _get_us_historical(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """获取美股历史数据"""
        try:
            # Yahoo Finance API
            api_url = f"{self.api_config['yahoo']}/v8/finance/chart/{symbol}"
            
            params = {
                'period1': int(datetime.strptime(start_date, '%Y-%m-%d').timestamp()),
                'period2': int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()),
                'interval': '1d',
                'includePrePost': 'false'
            }
            
            response = self.session.get(api_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('chart') and data['chart'].get('result'):
                result = data['chart']['result'][0]
                timestamps = result.get('timestamp', [])
                
                quotes = result.get('indicators', {}).get('quote', [{}])[0]
                opens = quotes.get('open', [])
                highs = quotes.get('high', [])
                lows = quotes.get('low', [])
                closes = quotes.get('close', [])
                volumes = quotes.get('volume', [])
                
                historical_data = []
                for i in range(len(timestamps)):
                    if i < len(opens) and opens[i] is not None:
                        record = {
                            'date': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d'),
                            'open': opens[i],
                            'high': highs[i] if i < len(highs) else opens[i],
                            'low': lows[i] if i < len(lows) else opens[i],
                            'close': closes[i] if i < len(closes) else opens[i],
                            'volume': volumes[i] if i < len(volumes) else 0,
                            'amount': closes[i] * volumes[i] if i < len(closes) and i < len(volumes) else 0
                        }
                        historical_data.append(record)
                
                logger.info(f"从API获取到 {len(historical_data)} 条美股历史数据")
                return historical_data
            
            return []
            
        except Exception as e:
            logger.error(f"获取美股历史数据失败: {e}")
            return []
    
    def get_historical_from_db(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """从数据库获取历史数据"""
        try:
            self.cursor.execute('''
                SELECT date, open, high, low, close, volume, amount, 
                       change, change_percent, turnover_rate, amplitude
                FROM stock_daily 
                WHERE symbol = ? AND date BETWEEN ? AND ?
                ORDER BY date
            ''', (symbol, start_date, end_date))
            
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            
            historical_data = []
            for row in rows:
                record = dict(zip(columns, row))
                historical_data.append(record)
            
            return historical_data
            
        except Exception as e:
            logger.error(f"从数据库获取历史数据失败: {e}")
            return []
    
    def save_historical_data(self, symbol: str, historical_data: List[Dict]):
        """保存历史数据到数据库"""
        try:
            for record in historical_data:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO stock_daily 
                    (symbol, date, open, high, low, close, volume, amount, 
                     change, change_percent, turnover_rate, amplitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    record['date'],
                    record.get('open'),
                    record.get('high'),
                    record.get('low'),
                    record.get('close'),
                    record.get('volume', 0),
                    record.get('amount', 0),
                    record.get('change', 0),
                    record.get('change_percent', 0),
                    record.get('turnover_rate', 0),
                    record.get('amplitude', 0)
                ))
            
            self.conn.commit()
            logger.info(f"保存 {len(historical_data)} 条历史数据到数据库")
            
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")
            self.conn.rollback()
    
    def save_realtime_data(self, stock: StockData):
        """保存实时数据到数据库"""
        try:
            self.cursor.execute('''
                INSERT INTO stock_realtime 
                (symbol, timestamp, price, change, change_percent, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                stock.symbol,
                stock.timestamp,
                stock.current_price,
                stock.change,
                stock.change_percent,
                stock.volume,
                stock.amount
            ))
            
            self.conn.commit()
            logger.debug(f"实时数据已保存到数据库: {stock.symbol}")
            
        except Exception as e:
            logger.error(f"保存实时数据失败: {e}")
            self.conn.rollback()
    
    def monitor_stock(self, symbol: str, market: StockMarket = StockMarket.A_SHARE, 
                     interval_seconds: int = 60, duration_minutes: int = 60):
        """
        监控股票价格变化
        
        Args:
            symbol: 股票代码
            market: 市场类型
            interval_seconds: 监控间隔（秒）
            duration_minutes: 监控时长（分钟）
        """
        end_time = time.time() + duration_minutes * 60
        
        print(f"开始监控股票: {symbol}")
        print(f"监控时长: {duration_minutes}分钟, 间隔: {interval_seconds}秒")
        print("-" * 50)
        
        try:
            price_history = []
            
            while time.time() < end_time:
                stock_data = self.get_realtime_price(symbol, market)
                
                if stock_data:
                    current_time = datetime.now().strftime('%H:%M:%S')
                    
                    print(f"[{current_time}] {stock_data.name} ({stock_data.symbol})")
                    print(f"  当前价: {stock_data.current_price:.2f}")
                    print(f"  涨跌幅: {stock_data.change_percent:+.2f}% ({stock_data.change:+.2f})")
                    print(f"  成交量: {stock_data.volume:,}")
                    print(f"  成交额: {stock_data.amount:,.0f}")
                    
                    # 记录价格历史
                    price_history.append({
                        'time': current_time,
                        'price': stock_data.current_price,
                        'volume': stock_data.volume
                    })
                    
                    # 显示价格变化趋势
                    if len(price_history) > 1:
                        first_price = price_history[0]['price']
                        current_price = price_history[-1]['price']
                        total_change = ((current_price - first_price) / first_price) * 100
                        print(f"  累计变化: {total_change:+.2f}%")
                    
                    print()
                
                # 等待下一次监控
                if time.time() + interval_seconds < end_time:
                    time.sleep(interval_seconds)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n监控被用户中断")
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        
        # 显示监控总结
        if price_history:
            print("\n=== 监控总结 ===")
            prices = [p['price'] for p in price_history]
            print(f"监控次数: {len(price_history)}")
            print(f"最高价: {max(prices):.2f}")
            print(f"最低价: {min(prices):.2f}")
            print(f"平均价: {sum(prices)/len(prices):.2f}")
            print(f"最终价: {prices[-1]:.2f}")
            print(f"价格波动: {(max(prices) - min(prices))/min(prices)*100:.2f}%")
        
        print("监控结束")
    
    def export_to_csv(self, symbol: str, start_date: str, end_date: str = None, 
                     filename: str = None) -> bool:
        """
        导出股票数据到CSV
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            filename: 输出文件名
            
        Returns:
            是否导出成功
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'stock_{symbol}_{start_date}_to_{end_date}_{timestamp}.csv'
            
            # 获取数据
            historical = self.get_historical_data(symbol, start_date, end_date)
            
            if historical:
                # 转换为DataFrame
                df = pd.DataFrame(historical)
                
                # 计算技术指标
                df['MA5'] = df['close'].rolling(window=5).mean()
                df['MA10'] = df['close'].rolling(window=10).mean()
                df['MA20'] = df['close'].rolling(window=20).mean()
                
                # 保存到CSV
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                
                logger.info(f"股票数据已导出到: {filename}")
                
                # 显示统计信息
                print(f"\n=== 数据统计 ===")
                print(f"数据期间: {start_date} 到 {end_date}")
                print(f"数据条数: {len(df)}")
                print(f"开盘价范围: {df['open'].min():.2f} - {df['open'].max():.2f}")
                print(f"收盘价范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
                print(f"平均成交量: {df['volume'].mean():,.0f}")
                print(f"平均成交额: {df['amount'].mean():,.0f}")
                print(f"涨跌天数: 上涨 {len(df[df['change'] > 0])}天, 下跌 {len(df[df['change'] < 0])}天")
                
                return True
            else:
                logger.warning("无数据可导出")
                return False
            
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

def main():
    """主函数"""
    try:
        crawler = StockCrawler()
        
        print("=== 股票数据爬虫 ===")
        print("注意: 本工具仅用于学习研究，不构成投资建议")
        print()
        
        print("选择功能:")
        print("1. 获取股票实时价格")
        print("2. 获取历史数据")
        print("3. 监控股票价格")
        print("4. 导出数据到CSV")
        print("5. 退出")
        
        choice = input("\n请选择功能 (1-5): ").strip()
        
        if choice == '1':
            symbol = input("请输入股票代码 (例如: 600000, AAPL, 00700): ").strip()
            if symbol:
                # 自动判断市场
                if symbol.isdigit() and len(symbol) == 6:
                    market = StockMarket.A_SHARE
                elif symbol.startswith('0') and len(symbol) == 5:
                    market = StockMarket.HK
                else:
                    market = StockMarket.US
                
                stock_data = crawler.get_realtime_price(symbol, market)
                
                if stock_data:
                    print(f"\n=== {stock_data.name} ({stock_data.symbol}) ===")
                    print(f"市场: {stock_data.market.value}")
                    print(f"当前价: {stock_data.current_price}")
                    print(f"涨跌: {stock_data.change:+.2f} ({stock_data.change_percent:+.2f}%)")
                    print(f"今开: {stock_data.open_price}")
                    print(f"昨收: {stock_data.prev_close}")
                    print(f"最高: {stock_data.high}")
                    print(f"最低: {stock_data.low}")
                    print(f"成交量: {stock_data.volume:,}")
                    print(f"成交额: {stock_data.amount:,.0f}")
                    print(f"更新时间: {stock_data.timestamp}")
                else:
                    print("获取股票数据失败")
                    
        elif choice == '2':
            symbol = input("请输入股票代码: ").strip()
            if symbol:
                start_date = input("开始日期 (YYYY-MM-DD, 默认30天前): ").strip()
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                end_date = input("结束日期 (YYYY-MM-DD, 默认今天): ").strip()
                
                historical = crawler.get_historical_data(symbol, start_date, end_date)
                
                if historical:
                    print(f"\n=== {symbol} 历史数据 ({start_date} 到 {end_date}) ===")
                    print(f"共 {len(historical)} 条记录")
                    
                    # 显示最近5条记录
                    print(f"\n最近5个交易日:")
                    for record in historical[-5:]:
                        date = record.get('date', '')
                        close = record.get('close', 0)
                        change = record.get('change', 0)
                        change_percent = record.get('change_percent', 0)
                        volume = record.get('volume', 0)
                        
                        print(f"  {date}: {close:.2f} ({change:+.2f}, {change_percent:+.2f}%), 成交量: {volume:,}")
                    
                    # 显示统计信息
                    closes = [r['close'] for r in historical if 'close' in r]
                    if closes:
                        print(f"\n统计:")
                        print(f"  最高收盘价: {max(closes):.2f}")
                        print(f"  最低收盘价: {min(closes):.2f}")
                        print(f"  平均收盘价: {sum(closes)/len(closes):.2f}")
                        print(f"  价格波动: {(max(closes)-min(closes))/min(closes)*100:.2f}%")
                else:
                    print("无历史数据")
                    
        elif choice == '3':
            symbol = input("请输入股票代码: ").strip()
            if symbol:
                interval = input("监控间隔(秒, 默认60): ").strip()
                interval = int(interval) if interval.isdigit() else 60
                
                duration = input("监控时长(分钟, 默认60): ").strip()
                duration = int(duration) if duration.isdigit() else 60
                
                crawler.monitor_stock(symbol, interval_seconds=interval, duration_minutes=duration)
                
        elif choice == '4':
            symbol = input("请输入股票代码: ").strip()
            if symbol:
                start_date = input("开始日期 (YYYY-MM-DD): ").strip()
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                end_date = input("结束日期 (YYYY-MM-DD, 默认今天): ").strip()
                
                if crawler.export_to_csv(symbol, start_date, end_date):
                    print("数据导出成功")
                else:
                    print("数据导出失败")
                    
        elif choice == '5':
            print("退出程序")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
    finally:
        if 'crawler' in locals():
            crawler.close()

if __name__ == "__main__":
    main()