#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时汇率爬虫 - 获取全球货币汇率数据
网站：多个汇率数据源（央行、交易所、金融数据平台）
功能：获取实时汇率、历史汇率、汇率换算、汇率趋势分析
"""

import requests
import json
import time
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote, urlparse
import xml.etree.ElementTree as ET
import csv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExchangeRateCrawler:
    """实时汇率爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        
        # 设置请求头
        self.headers = {
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json,application/xml,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        self.session.headers.update(self.headers)
        
        # 汇率数据源配置
        self.data_sources = {
            'ecb': {
                'name': '欧洲央行',
                'base_url': 'https://www.ecb.europa.eu',
                'daily_url': 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
                'historical_url': 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml',
                'base_currency': 'EUR',
                'format': 'xml',
            },
            'exchangerate_api': {
                'name': 'ExchangeRate-API',
                'base_url': 'https://api.exchangerate-api.com',
                'latest_url': 'https://api.exchangerate-api.com/v4/latest/{base_currency}',
                'historical_url': 'https://api.exchangerate-api.com/v4/history/{base_currency}/{year}/{month}/{day}',
                'base_currency': 'USD',
                'format': 'json',
                'free_limit': 1500,  # 每月免费请求限制
            },
            'openexchangerates': {
                'name': 'Open Exchange Rates',
                'base_url': 'https://openexchangerates.org',
                'latest_url': 'https://openexchangerates.org/api/latest.json',
                'historical_url': 'https://openexchangerates.org/api/historical/{date}.json',
                'base_currency': 'USD',
                'format': 'json',
                'requires_app_id': True,  # 需要API key
            },
            'bank_of_china': {
                'name': '中国银行',
                'base_url': 'https://www.boc.cn',
                'rate_url': 'https://www.boc.cn/sourcedb/whpj/',
                'format': 'html',
                'base_currency': 'CNY',
            },
            'xe': {
                'name': 'XE.com',
                'base_url': 'https://www.xe.com',
                'rate_url': 'https://www.xe.com/currencyconverter/convert',
                'format': 'html',
            }
        }
        
        # 常用货币代码和名称
        self.currency_codes = {
            'USD': '美元',
            'EUR': '欧元',
            'GBP': '英镑',
            'JPY': '日元',
            'CNY': '人民币',
            'HKD': '港元',
            'CAD': '加元',
            'AUD': '澳元',
            'CHF': '瑞士法郎',
            'SGD': '新加坡元',
            'KRW': '韩元',
            'INR': '印度卢比',
            'RUB': '俄罗斯卢布',
            'BRL': '巴西雷亚尔',
            'MXN': '墨西哥比索',
        }
        
        # 汇率缓存
        self.rate_cache = {}
        self.cache_expiry = 300  # 缓存过期时间（秒）
        
        # API密钥（如果有）
        self.api_keys = {}
    
    def set_api_key(self, source: str, api_key: str) -> None:
        """
        设置API密钥
        
        Args:
            source: 数据源名称
            api_key: API密钥
        """
        self.api_keys[source] = api_key
        logger.info(f"已设置 {source} 的API密钥")
    
    def get_latest_rates(self, base_currency: str = 'USD', source: str = 'exchangerate_api') -> Optional[Dict]:
        """
        获取最新汇率
        
        Args:
            base_currency: 基准货币代码
            source: 数据源名称
            
        Returns:
            汇率数据字典，失败则返回None
        """
        try:
            # 检查缓存
            cache_key = f"{source}_{base_currency}_latest"
            if cache_key in self.rate_cache:
                cached_data, timestamp = self.rate_cache[cache_key]
                if time.time() - timestamp < self.cache_expiry:
                    logger.info(f"使用缓存的汇率数据: {source}")
                    return cached_data
            
            if source not in self.data_sources:
                logger.error(f"不支持的汇率数据源: {source}")
                return None
            
            source_config = self.data_sources[source]
            
            # 根据数据源调用不同的方法
            if source == 'ecb':
                rates_data = self._get_ecb_rates(base_currency)
            elif source == 'exchangerate_api':
                rates_data = self._get_exchangerate_api_rates(base_currency)
            elif source == 'openexchangerates':
                rates_data = self._get_openexchangerates_rates(base_currency)
            elif source == 'bank_of_china':
                rates_data = self._get_bank_of_china_rates()
            elif source == 'xe':
                rates_data = self._get_xe_rates(base_currency)
            else:
                logger.error(f"未实现的数据源: {source}")
                return None
            
            if rates_data:
                # 更新缓存
                self.rate_cache[cache_key] = (rates_data, time.time())
                logger.info(f"成功获取最新汇率: {source}")
                return rates_data
            else:
                logger.warning(f"获取汇率失败: {source}")
                return None
                
        except Exception as e:
            logger.error(f"获取最新汇率时发生错误: {str(e)}")
            return None
    
    def _get_ecb_rates(self, base_currency: str = 'EUR') -> Optional[Dict]:
        """获取欧洲央行汇率数据"""
        try:
            source_config = self.data_sources['ecb']
            url = source_config['daily_url']
            
            logger.debug(f"请求ECB汇率数据: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析XML
            root = ET.fromstring(response.content)
            
            # 查找汇率数据
            rates_data = {
                'source': source_config['name'],
                'base_currency': base_currency,
                'timestamp': datetime.now().isoformat(),
                'rates': {},
            }
            
            # 解析Cube元素
            namespaces = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01', '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            
            # 查找最新的汇率数据
            cube_root = root.find('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@time]')
            if cube_root is not None:
                time_str = cube_root.get('time')
                if time_str:
                    rates_data['date'] = time_str
                
                # 提取汇率
                for cube in cube_root.findall('{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube'):
                    currency = cube.get('currency')
                    rate = cube.get('rate')
                    if currency and rate:
                        rates_data['rates'][currency] = float(rate)
            
            # 添加基准货币（EUR对EUR的汇率是1）
            rates_data['rates']['EUR'] = 1.0
            
            # 如果基准货币不是EUR，需要转换
            if base_currency != 'EUR' and base_currency in rates_data['rates']:
                base_rate = rates_data['rates'][base_currency]
                # 转换所有汇率
                converted_rates = {}
                for currency, rate in rates_data['rates'].items():
                    if currency != base_currency:
                        converted_rates[currency] = rate / base_rate
                converted_rates[base_currency] = 1.0
                rates_data['rates'] = converted_rates
                rates_data['base_currency'] = base_currency
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取ECB汇率时发生错误: {str(e)}")
            return None
    
    def _get_exchangerate_api_rates(self, base_currency: str = 'USD') -> Optional[Dict]:
        """获取ExchangeRate-API汇率数据"""
        try:
            source_config = self.data_sources['exchangerate_api']
            url = source_config['latest_url'].format(base_currency=base_currency)
            
            logger.debug(f"请求ExchangeRate-API数据: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            rates_data = {
                'source': source_config['name'],
                'base_currency': data.get('base', base_currency),
                'timestamp': datetime.fromtimestamp(data.get('time_last_updated', 0)).isoformat() if data.get('time_last_updated') else datetime.now().isoformat(),
                'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'rates': data.get('rates', {}),
            }
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取ExchangeRate-API汇率时发生错误: {str(e)}")
            return None
    
    def _get_openexchangerates_rates(self, base_currency: str = 'USD') -> Optional[Dict]:
        """获取Open Exchange Rates汇率数据"""
        try:
            source_config = self.data_sources['openexchangerates']
            
            # 检查API密钥
            app_id = self.api_keys.get('openexchangerates')
            if not app_id:
                logger.warning("Open Exchange Rates需要API密钥，使用免费源替代")
                return self._get_exchangerate_api_rates(base_currency)
            
            url = source_config['latest_url']
            params = {
                'app_id': app_id,
                'base': base_currency,
            }
            
            logger.debug(f"请求Open Exchange Rates数据: {url}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            rates_data = {
                'source': source_config['name'],
                'base_currency': data.get('base', base_currency),
                'timestamp': datetime.fromtimestamp(data.get('timestamp', 0)).isoformat() if data.get('timestamp') else datetime.now().isoformat(),
                'rates': data.get('rates', {}),
            }
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取Open Exchange Rates时发生错误: {str(e)}")
            # 失败时尝试其他源
            return self._get_exchangerate_api_rates(base_currency)
    
    def _get_bank_of_china_rates(self) -> Optional[Dict]:
        """获取中国银行汇率数据"""
        try:
            source_config = self.data_sources['bank_of_china']
            url = source_config['rate_url']
            
            logger.debug(f"请求中国银行汇率数据: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析HTML
            import re
            html_content = response.text
            
            rates_data = {
                'source': source_config['name'],
                'base_currency': 'CNY',
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'rates': {},
            }
            
            # 使用正则表达式查找汇率表格
            # 注意：实际解析需要根据中国银行网站的具体结构调整
            pattern = r'<tr>.*?<td[^>]*>([A-Z]{3})</td>.*?<td[^>]*>([\d\.]+)</td>.*?<td[^>]*>([\d\.]+)</td>.*?</tr>'
            matches = re.findall(pattern, html_content, re.DOTNAME)
            
            for match in matches:
                currency = match[0]
                buying_rate = float(match[1])  # 现汇买入价
                # 这里简化处理，使用现汇买入价作为汇率
                # 实际应用中可能需要更复杂的换算
                if currency and buying_rate > 0:
                    # 转换为1单位外币对应多少CNY
                    rates_data['rates'][currency] = buying_rate / 100  # 假设数据是100外币对应多少CNY
            
            # 添加CNY对CNY的汇率
            rates_data['rates']['CNY'] = 1.0
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取中国银行汇率时发生错误: {str(e)}")
            return None
    
    def _get_xe_rates(self, base_currency: str = 'USD') -> Optional[Dict]:
        """获取XE.com汇率数据"""
        try:
            source_config = self.data_sources['xe']
            
            # XE.com需要为每对货币单独请求，这里简化处理
            # 实际应用中可能需要多次请求或使用XE的API
            logger.warning("XE.com汇率获取需要更复杂的处理，使用其他数据源替代")
            return self._get_exchangerate_api_rates(base_currency)
            
        except Exception as e:
            logger.error(f"获取XE.com汇率时发生错误: {str(e)}")
            return None
    
    def get_historical_rates(self, date_str: str, base_currency: str = 'USD', 
                            source: str = 'exchangerate_api') -> Optional[Dict]:
        """
        获取历史汇率
        
        Args:
            date_str: 日期字符串（格式：YYYY-MM-DD）
            base_currency: 基准货币代码
            source: 数据源名称
            
        Returns:
            历史汇率数据字典，失败则返回None
        """
        try:
            # 验证日期格式
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                # 不能查询未来日期
                if date_obj > datetime.now():
                    logger.warning(f"不能查询未来日期: {date_str}")
                    return None
            except ValueError:
                logger.error(f"无效的日期格式: {date_str}，应为YYYY-MM-DD")
                return None
            
            if source not in self.data_sources:
                logger.error(f"不支持的汇率数据源: {source}")
                return None
            
            source_config = self.data_sources[source]
            
            # 检查缓存
            cache_key = f"{source}_{base_currency}_{date_str}"
            if cache_key in self.rate_cache:
                cached_data, timestamp = self.rate_cache[cache_key]
                if time.time() - timestamp < self.cache_expiry * 24:  # 历史数据缓存时间更长
                    logger.info(f"使用缓存的历史汇率数据: {source} {date_str}")
                    return cached_data
            
            if source == 'ecb':
                rates_data = self._get_ecb_historical_rates(date_str, base_currency)
            elif source == 'exchangerate_api':
                rates_data = self._get_exchangerate_api_historical_rates(date_str, base_currency)
            elif source == 'openexchangerates':
                rates_data = self._get_openexchangerates_historical_rates(date_str, base_currency)
            else:
                logger.error(f"历史汇率功能不支持的数据源: {source}")
                return None
            
            if rates_data:
                # 更新缓存
                self.rate_cache[cache_key] = (rates_data, time.time())
                logger.info(f"成功获取历史汇率: {source} {date_str}")
                return rates_data
            else:
                logger.warning(f"获取历史汇率失败: {source} {date_str}")
                return None
                
        except Exception as e:
            logger.error(f"获取历史汇率时发生错误: {str(e)}")
            return None
    
    def _get_ecb_historical_rates(self, date_str: str, base_currency: str = 'EUR') -> Optional[Dict]:
        """获取欧洲央行历史汇率数据"""
        try:
            source_config = self.data_sources['ecb']
            url = source_config['historical_url']
            
            logger.debug(f"请求ECB历史汇率数据: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析XML
            root = ET.fromstring(response.content)
            
            # 查找指定日期的汇率数据
            rates_data = {
                'source': source_config['name'],
                'base_currency': base_currency,
                'date': date_str,
                'timestamp': datetime.now().isoformat(),
                'rates': {},
            }
            
            # 解析Cube元素
            namespaces = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01', '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            
            # 查找指定日期的汇率
            date_cube = root.find(f'.//{{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}}Cube[@time="{date_str}"]')
            if date_cube is not None:
                # 提取汇率
                for cube in date_cube.findall('{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube'):
                    currency = cube.get('currency')
                    rate = cube.get('rate')
                    if currency and rate:
                        rates_data['rates'][currency] = float(rate)
                
                # 添加基准货币（EUR对EUR的汇率是1）
                rates_data['rates']['EUR'] = 1.0
                
                # 如果基准货币不是EUR，需要转换
                if base_currency != 'EUR' and base_currency in rates_data['rates']:
                    base_rate = rates_data['rates'][base_currency]
                    # 转换所有汇率
                    converted_rates = {}
                    for currency, rate in rates_data['rates'].items():
                        if currency != base_currency:
                            converted_rates[currency] = rate / base_rate
                    converted_rates[base_currency] = 1.0
                    rates_data['rates'] = converted_rates
                    rates_data['base_currency'] = base_currency
                
                return rates_data
            else:
                logger.warning(f"ECB没有找到 {date_str} 的汇率数据")
                return None
            
        except Exception as e:
            logger.error(f"获取ECB历史汇率时发生错误: {str(e)}")
            return None
    
    def _get_exchangerate_api_historical_rates(self, date_str: str, base_currency: str = 'USD') -> Optional[Dict]:
        """获取ExchangeRate-API历史汇率数据"""
        try:
            source_config = self.data_sources['exchangerate_api']
            
            # 解析日期
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            url = source_config['historical_url'].format(
                base_currency=base_currency,
                year=year,
                month=month,
                day=day
            )
            
            logger.debug(f"请求ExchangeRate-API历史数据: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            rates_data = {
                'source': source_config['name'],
                'base_currency': data.get('base', base_currency),
                'date': data.get('date', date_str),
                'timestamp': datetime.now().isoformat(),
                'rates': data.get('rates', {}),
            }
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取ExchangeRate-API历史汇率时发生错误: {str(e)}")
            return None
    
    def _get_openexchangerates_historical_rates(self, date_str: str, base_currency: str = 'USD') -> Optional[Dict]:
        """获取Open Exchange Rates历史汇率数据"""
        try:
            source_config = self.data_sources['openexchangerates']
            
            # 检查API密钥
            app_id = self.api_keys.get('openexchangerates')
            if not app_id:
                logger.warning("Open Exchange Rates需要API密钥，使用其他源替代")
                return self._get_exchangerate_api_historical_rates(date_str, base_currency)
            
            url = source_config['historical_url'].format(date=date_str)
            params = {
                'app_id': app_id,
                'base': base_currency,
            }
            
            logger.debug(f"请求Open Exchange Rates历史数据: {url}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            rates_data = {
                'source': source_config['name'],
                'base_currency': data.get('base', base_currency),
                'date': date_str,
                'timestamp': datetime.fromtimestamp(data.get('timestamp', 0)).isoformat() if data.get('timestamp') else datetime.now().isoformat(),
                'rates': data.get('rates', {}),
            }
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取Open Exchange Rates历史汇率时发生错误: {str(e)}")
            # 失败时尝试其他源
            return self._get_exchangerate_api_historical_rates(date_str, base_currency)
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str, 
                        source: str = 'exchangerate_api') -> Optional[Dict]:
        """
        货币换算
        
        Args:
            amount: 金额
            from_currency: 源货币代码
            to_currency: 目标货币代码
            source: 数据源名称
            
        Returns:
            换算结果字典，失败则返回None
        """
        try:
            # 获取最新汇率
            rates_data = self.get_latest_rates(from_currency, source)
            
            if not rates_data or 'rates' not in rates_data:
                logger.error("无法获取汇率数据")
                return None
            
            rates = rates_data['rates']
            
            if to_currency not in rates:
                logger.error(f"不支持的目标货币: {to_currency}")
                return None
            
            # 计算换算结果
            rate = rates[to_currency]
            converted_amount = amount * rate
            
            result = {
                'amount': amount,
                'from_currency': from_currency,
                'to_currency': to_currency,
                'exchange_rate': rate,
                'converted_amount': converted_amount,
                'source': rates_data.get('source', '未知'),
                'timestamp': rates_data.get('timestamp', datetime.now().isoformat()),
                'date': rates_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            }
            
            logger.info(f"货币换算完成: {amount} {from_currency} = {converted_amount:.4f} {to_currency}")
            return result
            
        except Exception as e:
            logger.error(f"货币换算时发生错误: {str(e)}")
            return None
    
    def get_rate_trend(self, from_currency: str, to_currency: str, days: int = 30, 
                      source: str = 'exchangerate_api') -> Optional[Dict]:
        """
        获取汇率趋势
        
        Args:
            from_currency: 源货币代码
            to_currency: 目标货币代码
            days: 天数
            source: 数据源名称
            
        Returns:
            汇率趋势数据字典，失败则返回None
        """
        try:
            if days <= 0 or days > 365:
                logger.error(f"天数范围无效: {days}，应在1-365之间")
                return None
            
            trend_data = {
                'from_currency': from_currency,
                'to_currency': to_currency,
                'days': days,
                'source': source,
                'start_date': None,
                'end_date': None,
                'rates': [],
                'timestamp': datetime.now().isoformat(),
            }
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            trend_data['start_date'] = start_date.strftime('%Y-%m-%d')
            trend_data['end_date'] = end_date.strftime('%Y-%m-%d')
            
            # 获取每天的汇率
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # 获取历史汇率
                historical_data = self.get_historical_rates(date_str, from_currency, source)
                
                if historical_data and 'rates' in historical_data:
                    rates = historical_data['rates']
                    if to_currency in rates:
                        rate = rates[to_currency]
                        trend_data['rates'].append({
                            'date': date_str,
                            'rate': rate,
                        })
                
                current_date += timedelta(days=1)
                
                # 避免请求过快
                time.sleep(0.1)
            
            if not trend_data['rates']:
                logger.warning("未获取到汇率趋势数据")
                return None
            
            # 计算统计信息
            rates_list = [item['rate'] for item in trend_data['rates']]
            
            if rates_list:
                trend_data['statistics'] = {
                    'min_rate': min(rates_list),
                    'max_rate': max(rates_list),
                    'avg_rate': sum(rates_list) / len(rates_list),
                    'first_rate': rates_list[0],
                    'last_rate': rates_list[-1],
                    'rate_change': rates_list[-1] - rates_list[0],
                    'rate_change_percent': ((rates_list[-1] - rates_list[0]) / rates_list[0] * 100) if rates_list[0] != 0 else 0,
                }
            
            logger.info(f"汇率趋势分析完成: {from_currency}->{to_currency} ({days}天)")
            return trend_data
            
        except Exception as e:
            logger.error(f"获取汇率趋势时发生错误: {str(e)}")
            return None
    
    def get_multiple_rates(self, base_currency: str = 'USD', target_currencies: List[str] = None, 
                          source: str = 'exchangerate_api') -> Optional[Dict]:
        """
        获取多种货币汇率
        
        Args:
            base_currency: 基准货币代码
            target_currencies: 目标货币代码列表，如果为None则获取所有可用货币
            source: 数据源名称
            
        Returns:
            多种货币汇率数据字典，失败则返回None
        """
        try:
            rates_data = self.get_latest_rates(base_currency, source)
            
            if not rates_data or 'rates' not in rates_data:
                return None
            
            if target_currencies:
                # 只返回指定的货币
                filtered_rates = {}
                for currency in target_currencies:
                    if currency in rates_data['rates']:
                        filtered_rates[currency] = rates_data['rates'][currency]
                
                rates_data['rates'] = filtered_rates
                rates_data['target_currencies'] = target_currencies
            
            return rates_data
            
        except Exception as e:
            logger.error(f"获取多种货币汇率时发生错误: {str(e)}")
            return None
    
    def save_to_json(self, data: Dict, filename: str = None) -> bool:
        """
        将数据保存为JSON文件
        
        Args:
            data: 数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not data:
                logger.warning("没有数据可保存")
                return False
            
            if filename is None:
                # 根据数据类型生成文件名
                if 'rates' in data and 'base_currency' in data:  # 汇率数据
                    base_currency = data['base_currency']
                    date = data.get('date', datetime.now().strftime('%Y%m%d'))
                    source = data.get('source', 'exchange').replace(' ', '_')
                    timestamp = datetime.now().strftime('%H%M%S')
                    filename = f"exchange_{source}_{base_currency}_{date}_{timestamp}.json"
                elif 'from_currency' in data and 'to_currency' in data:  # 换算结果
                    from_curr = data['from_currency']
                    to_curr = data['to_currency']
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"conversion_{from_curr}_to_{to_curr}_{timestamp}.json"
                elif 'trend' in data:  # 趋势数据
                    from_curr = data.get('from_currency', 'XXX')
                    to_curr = data.get('to_currency', 'XXX')
                    days = data.get('days', 0)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"trend_{from_curr}_{to_curr}_{days}d_{timestamp}.json"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"exchange_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def export_to_csv(self, data: Dict, filename: str = None) -> bool:
        """
        将汇率数据导出为CSV文件
        
        Args:
            data: 汇率数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            导出成功返回True，失败返回False
        """
        try:
            if not data or 'rates' not in data:
                logger.warning("没有汇率数据可导出")
                return False
            
            if filename is None:
                base_currency = data.get('base_currency', 'USD')
                date = data.get('date', datetime.now().strftime('%Y%m%d'))
                source = data.get('source', 'exchange').replace(' ', '_')
                filename = f"exchange_{source}_{base_currency}_{date}.csv"
            
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(['货币代码', '货币名称', '汇率', '数据源', '基准货币', '日期'])
                
                # 写入数据
                for currency_code, rate in data['rates'].items():
                    currency_name = self.currency_codes.get(currency_code, currency_code)
                    writer.writerow([
                        currency_code,
                        currency_name,
                        rate,
                        data.get('source', '未知'),
                        data.get('base_currency', '未知'),
                        data.get('date', '未知'),
                    ])
            
            logger.info(f"汇率数据已导出到CSV: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"导出CSV文件时发生错误: {str(e)}")
            return False


def main():
    """主函数，演示爬虫的使用"""
    print("实时汇率爬虫演示")
    print("=" * 50)
    print("支持数据源: 欧洲央行、ExchangeRate-API、Open Exchange Rates、中国银行、XE.com")
    print("功能: 实时汇率、历史汇率、货币换算、汇率趋势分析")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = ExchangeRateCrawler(timeout=15)
    
    # 演示获取最新汇率
    print("\n获取最新汇率（基准货币: USD）...")
    
    base_currency = "USD"
    source = "exchangerate_api"
    
    latest_rates = crawler.get_latest_rates(base_currency, source)
    
    if latest_rates:
        print(f"数据源: {latest_rates['source']}")
        print(f"基准货币: {latest_rates['base_currency']}")
        print(f"更新时间: {latest_rates.get('timestamp', '未知')}")
        print(f"日期: {latest_rates.get('date', '未知')}")
        
        # 显示几种主要货币的汇率
        major_currencies = ['EUR', 'GBP', 'JPY', 'CNY', 'CAD', 'AUD']
        
        print("\n主要货币汇率:")
        for currency in major_currencies:
            if currency in latest_rates['rates']:
                rate = latest_rates['rates'][currency]
                currency_name = crawler.currency_codes.get(currency, currency)
                print(f"  {currency} ({currency_name}): 1 {base_currency} = {rate:.4f} {currency}")
        
        # 保存数据
        crawler.save_to_json(latest_rates)
        print(f"\n汇率数据已保存到JSON文件")
        
        # 导出为CSV
        crawler.export_to_csv(latest_rates)
        print(f"汇率数据已导出到CSV文件")
    else:
        print("无法获取最新汇率")
    
    # 演示货币换算
    print("\n" + "=" * 50)
    print("货币换算演示...")
    
    amount = 100
    from_currency = "USD"
    to_currency = "CNY"
    
    conversion = crawler.convert_currency(amount, from_currency, to_currency, source)
    
    if conversion:
        print(f"换算金额: {conversion['amount']} {conversion['from_currency']}")
        print(f"汇率: 1 {conversion['from_currency']} = {conversion['exchange_rate']:.4f} {conversion['to_currency']}")
        print(f"换算结果: {conversion['converted_amount']:.2f} {conversion['to_currency']}")
        print(f"数据源: {conversion['source']}")
        print(f"时间: {conversion['timestamp']}")
        
        # 保存换算结果
        crawler.save_to_json(conversion)
        print(f"\n换算结果已保存到JSON文件")
    else:
        print("货币换算失败")
    
    # 演示获取历史汇率
    print("\n" + "=" * 50)
    print("获取历史汇率演示...")
    
    # 获取昨天的汇率
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"获取 {yesterday} 的历史汇率...")
    historical_rates = crawler.get_historical_rates(yesterday, base_currency, source)
    
    if historical_rates:
        print(f"历史汇率获取成功!")
        print(f"日期: {historical_rates['date']}")
        print(f"基准货币: {historical_rates['base_currency']}")
        
        # 显示几种货币的历史汇率
        for currency in major_currencies[:3]:  # 只显示前3种
            if currency in historical_rates['rates']:
                rate = historical_rates['rates'][currency]
                currency_name = crawler.currency_codes.get(currency, currency)
                print(f"  {currency} ({currency_name}): {rate:.4f}")
    else:
        print(f"无法获取 {yesterday} 的历史汇率")
    
    # 演示汇率趋势分析
    print("\n" + "=" * 50)
    print("汇率趋势分析演示...")
    
    from_currency = "USD"
    to_currency = "CNY"
    days = 7  # 分析最近7天的趋势
    
    print(f"分析 {from_currency} 对 {to_currency} 的 {days} 天汇率趋势...")
    trend_data = crawler.get_rate_trend(from_currency, to_currency, days, source)
    
    if trend_data:
        print(f"趋势分析完成!")
        print(f"分析期间: {trend_data['start_date']} 到 {trend_data['end_date']}")
        print(f"数据点数: {len(trend_data['rates'])}")
        
        if 'statistics' in trend_data:
            stats = trend_data['statistics']
            print(f"\n统计信息:")
            print(f"  最低汇率: {stats['min_rate']:.4f}")
            print(f"  最高汇率: {stats['max_rate']:.4f}")
            print(f"  平均汇率: {stats['avg_rate']:.4f}")
            print(f"  期初汇率: {stats['first_rate']:.4f}")
            print(f"  期末汇率: {stats['last_rate']:.4f}")
            print(f"  汇率变化: {stats['rate_change']:.4f}")
            print(f"  变化率: {stats['rate_change_percent']:.2f}%")
        
        # 显示最近几天的汇率
        print(f"\n最近几天汇率:")
        for rate_item in trend_data['rates'][-5:]:  # 只显示最后5天
            print(f"  {rate_item['date']}: {rate_item['rate']:.4f}")
        
        # 保存趋势数据
        crawler.save_to_json(trend_data)
        print(f"\n趋势数据已保存到JSON文件")
    else:
        print("汇率趋势分析失败")
    
    # 演示从不同数据源获取汇率
    print("\n" + "=" * 50)
    print("不同数据源比较演示...")
    
    sources_to_test = ['exchangerate_api']  # 可以添加更多数据源
    test_currencies = ['EUR', 'JPY', 'GBP']
    
    for test_source in sources_to_test:
        print(f"\n{test_source} 数据源:")
        rates = crawler.get_multiple_rates('USD', test_currencies, test_source)
        
        if rates:
            print(f"  基准货币: {rates['base_currency']}")
            for currency in test_currencies:
                if currency in rates['rates']:
                    print(f"  {currency}: {rates['rates'][currency]:.4f}")
        else:
            print(f"  无法获取数据")
    
    # 演示多货币换算
    print("\n" + "=" * 50)
    print("多货币换算演示...")
    
    amounts = [1, 10, 100, 1000]
    from_currency = "USD"
    to_currencies = ['EUR', 'CNY', 'JPY']
    
    print(f"将 {from_currency} 换算为多种货币:")
    for amount in amounts:
        print(f"\n{amount} {from_currency}:")
        for to_currency in to_currencies:
            conversion = crawler.convert_currency(amount, from_currency, to_currency, source)
            if conversion:
                print(f"  = {conversion['converted_amount']:.2f} {to_currency}")
    
    print("\n爬虫演示完成！")
    print("\n高级功能:")
    print("1. 多数据源汇率比较")
    print("2. 汇率波动预警")
    print("3. 汇率预测模型")
    print("4. 批量货币换算")
    print("5. 汇率数据可视化")
    print("\n注意事项:")
    print("1. 遵守各数据源的API使用政策")
    print("2. 注意API调用频率限制")
    print("3. 部分高级功能需要API key")
    print("4. 实时汇率数据可能有延迟")
    print("5. 历史汇率数据可能不完整")


if __name__ == "__main__":
    main()