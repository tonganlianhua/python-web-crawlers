#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据爬虫 - 获取A股实时行情数据
网站：东方财富网 (http://quote.eastmoney.com)
功能：获取股票实时价格、涨跌幅、成交量、市值等信息
"""

import requests
import json
import time
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockCrawler:
    """股票数据爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "http://push2.eastmoney.com"
        
        # 设置请求头
        self.headers = {
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'http://quote.eastmoney.com/',
            'Origin': 'http://quote.eastmoney.com',
        }
        
        self.session.headers.update(self.headers)
        
        # 常用股票代码映射
        self.stock_symbols = {
            '贵州茅台': '600519',
            '宁德时代': '300750',
            '招商银行': '600036',
            '中国平安': '601318',
            '五粮液': '000858',
            '比亚迪': '002594',
            '中信证券': '600030',
            '东方财富': '300059',
            '美的集团': '000333',
            '格力电器': '000651',
        }
        
        # 市场前缀映射
        self.market_prefix = {
            'sh': '1',  # 上海主板
            'sz': '0',  # 深圳主板
            'bj': '0',  # 北京交易所
        }
    
    def get_stock_code(self, stock_name: str) -> Optional[str]:
        """
        获取股票代码
        
        Args:
            stock_name: 股票名称或代码
            
        Returns:
            标准化的股票代码，如果未找到则返回None
        """
        # 如果输入的是代码，直接返回
        if stock_name.isdigit():
            return stock_name
        
        # 从映射表中查找
        if stock_name in self.stock_symbols:
            return self.stock_symbols[stock_name]
        
        logger.warning(f"股票 '{stock_name}' 不在预定义列表中")
        return None
    
    def get_market_prefix(self, stock_code: str) -> str:
        """
        根据股票代码获取市场前缀
        
        Args:
            stock_code: 股票代码
            
        Returns:
            市场前缀
        """
        if stock_code.startswith('6'):
            return 'sh'  # 上海
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return 'sz'  # 深圳
        elif stock_code.startswith('4') or stock_code.startswith('8'):
            return 'bj'  # 北京
        else:
            return 'sh'  # 默认上海
    
    def fetch_single_stock(self, stock_input: str) -> Optional[Dict]:
        """
        获取单只股票的实时数据
        
        Args:
            stock_input: 股票名称或代码
            
        Returns:
            股票数据字典，失败则返回None
        """
        try:
            stock_code = self.get_stock_code(stock_input)
            if not stock_code:
                logger.error(f"无法识别股票: {stock_input}")
                return None
            
            market = self.get_market_prefix(stock_code)
            full_code = f"{market}.{stock_code}"
            
            # 构建API URL
            api_url = f"{self.base_url}/api/qt/stock/get"
            params = {
                'invt': '2',
                'fltt': '2',
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f37,f38,f39,f46,f48,f60,f100,f102,f103,f124,f128,f136,f152',
                'secid': full_code,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'cb': 'jQuery112406995981539278674_1698901234567',
                '_': str(int(time.time() * 1000))
            }
            
            logger.info(f"正在获取股票 {stock_input} ({stock_code}) 的数据")
            
            # 发送请求
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析响应（去除JSONP包装）
            response_text = response.text
            if response_text.startswith('jQuery'):
                # 提取JSON部分
                start_idx = response_text.find('(') + 1
                end_idx = response_text.rfind(')')
                json_str = response_text[start_idx:end_idx]
            else:
                json_str = response_text
            
            data = json.loads(json_str)
            
            if data.get('rc') == 0 and data.get('data'):
                stock_data = self._parse_stock_data(data['data'], stock_input, stock_code)
                logger.info(f"成功获取股票 {stock_input} 的数据")
                return stock_data
            else:
                logger.warning(f"API返回错误: {data.get('msg', '未知错误')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取股票数据时发生未知错误: {str(e)}")
            return None
    
    def _parse_stock_data(self, raw_data: Dict, stock_name: str, stock_code: str) -> Dict:
        """
        解析原始股票数据
        
        Args:
            raw_data: 原始API数据
            stock_name: 股票名称
            stock_code: 股票代码
            
        Returns:
            格式化后的股票数据字典
        """
        try:
            # 字段映射表
            field_mapping = {
                'f2': 'current_price',      # 当前价
                'f3': 'change_percent',     # 涨跌幅
                'f4': 'change_amount',      # 涨跌额
                'f5': 'volume',             # 成交量（手）
                'f6': 'turnover',           # 成交额
                'f7': 'amplitude',          # 振幅
                'f8': 'turnover_rate',      # 换手率
                'f9': 'pe_ratio',           # 市盈率
                'f10': 'volume_ratio',      # 量比
                'f12': 'code',              # 股票代码
                'f13': 'market_code',       # 市场代码
                'f14': 'name',              # 股票名称
                'f15': 'high',              # 最高价
                'f16': 'low',               # 最低价
                'f17': 'open',              # 开盘价
                'f18': 'close',             # 昨收
                'f20': 'total_mv',          # 总市值
                'f21': 'circulating_mv',    # 流通市值
                'f23': 'pb_ratio',          # 市净率
                'f24': 'upper_limit',       # 涨停价
                'f25': 'lower_limit',       # 跌停价
                'f26': 'volume_ratio_5d',   # 5日量比
                'f37': 'roe',               # 净资产收益率
                'f38': 'total_share',       # 总股本
                'f39': 'circulating_share', # 流通股本
                'f46': '52week_high',       # 52周最高
                'f47': '52week_low',        # 52周最低
                'f48': 'eps',               # 每股收益
                'f57': 'current_year_percent',  # 年初至今涨跌幅
                'f60': 'last_60d_high',     # 60日最高
                'f61': 'last_60d_low',      # 60日最低
                'f100': 'industry',         # 所属行业
                'f102': 'area',             # 地区
                'f103': 'concept',          # 概念板块
                'f124': 'timestamp',        # 时间戳
                'f128': 'market_value',     # 市值排名
                'f136': 'dividend_yield',   # 股息率
                'f152': 'roe_weighted',     # 加权ROE
            }
            
            stock_data = {
                'name': stock_name,
                'code': stock_code,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': '东方财富网',
                'market': self.get_market_prefix(stock_code).upper(),
                'data': {}
            }
            
            # 映射字段
            for field_key, field_name in field_mapping.items():
                if field_key in raw_data:
                    value = raw_data[field_key]
                    # 处理特殊字段
                    if field_key == 'f124':  # 时间戳转换为可读格式
                        if value:
                            try:
                                value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                            except:
                                pass
                    stock_data['data'][field_name] = value
            
            # 计算一些衍生指标
            if 'current_price' in stock_data['data'] and 'close' in stock_data['data']:
                current = stock_data['data']['current_price']
                prev_close = stock_data['data']['close']
                if prev_close and prev_close != 0:
                    change_pct = ((current - prev_close) / prev_close) * 100
                    stock_data['data']['calculated_change_percent'] = round(change_pct, 2)
            
            return stock_data
            
        except Exception as e:
            logger.error(f"解析股票数据时发生错误: {str(e)}")
            # 返回基本数据
            return {
                'name': stock_name,
                'code': stock_code,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': '东方财富网',
                'market': self.get_market_prefix(stock_code).upper(),
                'data': raw_data
            }
    
    def fetch_multiple_stocks(self, stock_list: List[str]) -> List[Dict]:
        """
        获取多只股票的实时数据
        
        Args:
            stock_list: 股票名称或代码列表
            
        Returns:
            股票数据列表
        """
        results = []
        
        for stock in stock_list:
            logger.info(f"正在处理股票: {stock}")
            stock_data = self.fetch_single_stock(stock)
            if stock_data:
                results.append(stock_data)
            
            # 添加延迟，避免请求过快
            time.sleep(0.5)
        
        return results
    
    def save_to_csv(self, stock_data_list: List[Dict], filename: str = None) -> bool:
        """
        将股票数据保存为CSV文件
        
        Args:
            stock_data_list: 股票数据列表
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not stock_data_list:
                logger.warning("没有股票数据可保存")
                return False
            
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"stocks_{timestamp}.csv"
            
            # 确保保存到crawlers目录
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            # 准备CSV数据
            csv_data = []
            for stock in stock_data_list:
                row = {
                    '股票名称': stock['name'],
                    '股票代码': stock['code'],
                    '市场': stock['market'],
                    '更新时间': stock['timestamp']
                }
                
                # 添加数据字段
                for key, value in stock['data'].items():
                    if isinstance(value, (int, float)):
                        row[key] = value
                    elif isinstance(value, str):
                        row[key] = value
                    else:
                        row[key] = str(value)
                
                csv_data.append(row)
            
            # 转换为DataFrame并保存
            df = pd.DataFrame(csv_data)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            logger.info(f"股票数据已保存到CSV: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存CSV文件时发生错误: {str(e)}")
            return False
    
    def save_to_json(self, stock_data: Dict, filename: str = None) -> bool:
        """
        将单只股票数据保存为JSON文件
        
        Args:
            stock_data: 股票数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not stock_data:
                logger.warning("没有股票数据可保存")
                return False
            
            if filename is None:
                stock_name = stock_data.get('name', 'unknown').replace('/', '_')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"stock_{stock_name}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stock_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"股票数据已保存到JSON: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def get_stock_kline(self, stock_code: str, period: str = 'day', count: int = 100) -> Optional[List]:
        """
        获取股票K线数据（简化版）
        
        Args:
            stock_code: 股票代码
            period: 周期（day, week, month）
            count: 数据条数
            
        Returns:
            K线数据列表
        """
        # 注意：实际实现需要更复杂的API调用
        logger.info(f"获取 {stock_code} 的K线数据功能待实现")
        return None


def main():
    """主函数，演示爬虫的使用"""
    print("股票数据爬虫演示")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = StockCrawler(timeout=15)
    
    # 获取单只股票的实时数据
    stock = "贵州茅台"
    print(f"\n获取 {stock} 的实时数据...")
    stock_data = crawler.fetch_single_stock(stock)
    
    if stock_data:
        print(f"股票名称: {stock_data['name']}")
        print(f"股票代码: {stock_data['code']}")
        print(f"更新时间: {stock_data['timestamp']}")
        print(f"数据来源: {stock_data['source']}")
        print(f"市场: {stock_data['market']}")
        
        data = stock_data['data']
        print("\n关键指标:")
        if 'current_price' in data:
            print(f"  当前价格: {data['current_price']} 元")
        if 'change_percent' in data:
            print(f"  涨跌幅: {data['change_percent']}%")
        if 'volume' in data:
            volume_wan = data['volume'] / 10000  # 转换为万手
            print(f"  成交量: {volume_wan:.2f} 万手")
        if 'turnover' in data:
            turnover_yi = data['turnover'] / 100000000  # 转换为亿元
            print(f"  成交额: {turnover_yi:.2f} 亿元")
        if 'pe_ratio' in data:
            print(f"  市盈率: {data['pe_ratio']}")
        if 'total_mv' in data:
            mv_yi = data['total_mv'] / 100000000  # 转换为亿元
            print(f"  总市值: {mv_yi:.2f} 亿元")
        
        # 保存数据
        crawler.save_to_json(stock_data)
        print(f"\n数据已保存到JSON文件")
    else:
        print(f"无法获取 {stock} 的股票数据")
    
    # 获取多只股票的实时数据
    print("\n" + "=" * 50)
    print("获取多只股票实时数据...")
    stocks = ["宁德时代", "招商银行", "比亚迪"]
    all_stocks = crawler.fetch_multiple_stocks(stocks)
    
    print(f"\n成功获取 {len(all_stocks)} 只股票的数据")
    for stock in all_stocks:
        data = stock.get('data', {})
        price = data.get('current_price', 'N/A')
        change = data.get('change_percent', 'N/A')
        print(f"- {stock['name']}: {price} 元 ({change}%)")
    
    # 保存为CSV
    if all_stocks:
        crawler.save_to_csv(all_stocks)
        print(f"\n所有股票数据已保存到CSV文件")
    
    print("\n爬虫演示完成！")


if __name__ == "__main__":
    main()