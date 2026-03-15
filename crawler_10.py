#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫10: 综合数据爬虫框架
功能: 提供可配置的通用爬虫框架，支持多种网站、数据提取、数据清洗和导出
注意: 请遵守目标网站的robots.txt和法律法规
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
import logging
import os
import csv
import sqlite3
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urljoin, urlparse, parse_qs
import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_10.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrawlMethod(Enum):
    """爬取方法枚举"""
    HTML = "html"          # 普通HTML页面
    API = "api"            # REST API
    JSON = "json"          # JSON数据
    SITEMAP = "sitemap"    # 网站地图

class DataType(Enum):
    """数据类型枚举"""
    TEXT = "text"          # 文本
    NUMBER = "number"      # 数字
    DATE = "date"          # 日期
    URL = "url"            # URL
    IMAGE = "image"        # 图片
    HTML = "html"          # HTML片段

@dataclass
class FieldConfig:
    """字段配置"""
    name: str
    selector: str
    data_type: DataType = DataType.TEXT
    required: bool = False
    default: Any = None
    transform: Optional[Callable] = None
    regex: Optional[str] = None
    attributes: List[str] = field(default_factory=list)

@dataclass
class SiteConfig:
    """网站配置"""
    name: str
    base_url: str
    crawl_method: CrawlMethod
    search_url: Optional[str] = None
    detail_url_template: Optional[str] = None
    pagination_param: str = "page"
    items_per_page: int = 20
    request_delay: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    fields: List[FieldConfig] = field(default_factory=list)

class AdvancedCrawler:
    """高级通用爬虫框架"""
    
    def __init__(self, config_file: str = None):
        """
        初始化爬虫框架
        
        Args:
            config_file: 配置文件路径（YAML格式）
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        # 加载配置
        self.configs = {}
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        
        # 数据库连接
        self.db_conn = None
        self.init_database()
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_items': 0,
            'start_time': datetime.now()
        }
        
        logger.info("高级爬虫框架初始化完成")
    
    def load_config(self, config_file: str):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            for site_name, site_data in config_data.get('sites', {}).items():
                fields = []
                for field_data in site_data.get('fields', []):
                    field_config = FieldConfig(
                        name=field_data['name'],
                        selector=field_data['selector'],
                        data_type=DataType(field_data.get('data_type', 'text')),
                        required=field_data.get('required', False),
                        default=field_data.get('default'),
                        regex=field_data.get('regex'),
                        attributes=field_data.get('attributes', [])
                    )
                    fields.append(field_config)
                
                config = SiteConfig(
                    name=site_name,
                    base_url=site_data['base_url'],
                    crawl_method=CrawlMethod(site_data.get('crawl_method', 'html')),
                    search_url=site_data.get('search_url'),
                    detail_url_template=site_data.get('detail_url_template'),
                    pagination_param=site_data.get('pagination_param', 'page'),
                    items_per_page=site_data.get('items_per_page', 20),
                    request_delay=site_data.get('request_delay', 1.0),
                    headers=site_data.get('headers', {}),
                    fields=fields
                )
                
                self.configs[site_name] = config
            
            logger.info(f"成功加载 {len(self.configs)} 个网站配置")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def init_database(self):
        """初始化数据库"""
        try:
            self.db_conn = sqlite3.connect('crawler_data.db')
            cursor = self.db_conn.cursor()
            
            # 创建通用数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawled_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    item_id TEXT,
                    item_url TEXT,
                    data_json TEXT NOT NULL,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(site_name, item_id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_site_name ON crawled_data(site_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_type ON crawled_data(data_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawled_at ON crawled_data(crawled_at)')
            
            self.db_conn.commit()
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def crawl_site(self, site_name: str, query: str = None, pages: int = 1, 
                  max_items: int = 100) -> List[Dict]:
        """
        爬取指定网站
        
        Args:
            site_name: 网站名称
            query: 搜索查询（可选）
            pages: 爬取页数
            max_items: 最大爬取项目数
            
        Returns:
            爬取的数据列表
        """
        if site_name not in self.configs:
            logger.error(f"未找到网站配置: {site_name}")
            return []
        
        config = self.configs[site_name]
        all_items = []
        
        try:
            logger.info(f"开始爬取网站: {site_name}, 查询: {query}, 页数: {pages}")
            
            for page in range(1, pages + 1):
                if len(all_items) >= max_items:
                    break
                
                # 构建请求URL
                if query and config.search_url:
                    url = self._build_search_url(config, query, page)
                else:
                    url = self._build_list_url(config, page)
                
                logger.info(f"爬取第 {page} 页: {url}")
                
                # 发送请求
                response = self._make_request(url, config)
                if not response:
                    continue
                
                # 解析响应
                items = self._parse_response(response, config, url)
                
                if items:
                    all_items.extend(items)
                    logger.info(f"第 {page} 页获取到 {len(items)} 个项目")
                    
                    # 保存到数据库
                    self._save_to_database(site_name, 'list', items)
                
                # 延迟请求
                if page < pages:
                    time.sleep(config.request_delay)
            
            self.stats['total_items'] += len(all_items)
            logger.info(f"爬取完成，共获取 {len(all_items)} 个项目")
            
            return all_items
            
        except Exception as e:
            logger.error(f"爬取网站失败: {e}")
            return []
    
    def crawl_item_details(self, site_name: str, item_urls: List[str]) -> List[Dict]:
        """
        爬取项目详情
        
        Args:
            site_name: 网站名称
            item_urls: 项目URL列表
            
        Returns:
            详情数据列表
        """
        if site_name not in self.configs:
            logger.error(f"未找到网站配置: {site_name}")
            return []
        
        config = self.configs[site_name]
        all_details = []
        
        try:
            logger.info(f"开始爬取 {len(item_urls)} 个项目详情")
            
            for i, item_url in enumerate(item_urls):
                logger.info(f"爬取详情 {i+1}/{len(item_urls)}: {item_url}")
                
                # 发送请求
                response = self._make_request(item_url, config)
                if not response:
                    continue
                
                # 解析详情
                detail = self._parse_detail_response(response, config, item_url)
                
                if detail:
                    detail['source_url'] = item_url
                    all_details.append(detail)
                    
                    # 保存到数据库
                    self._save_to_database(site_name, 'detail', [detail])
                
                # 延迟请求
                if i < len(item_urls) - 1:
                    time.sleep(config.request_delay)
            
            logger.info(f"详情爬取完成，共获取 {len(all_details)} 个项目详情")
            
            return all_details
            
        except Exception as e:
            logger.error(f"爬取详情失败: {e}")
            return []
    
    def _build_search_url(self, config: SiteConfig, query: str, page: int) -> str:
        """构建搜索URL"""
        if config.crawl_method == CrawlMethod.API:
            # API格式
            url = config.search_url.format(query=quote(query), page=page)
        else:
            # HTML格式
            params = {
                'q': query,
                config.pagination_param: page
            }
            url = f"{config.base_url}{config.search_url}"
            if '?' in url:
                url += '&' + '&'.join(f"{k}={v}" for k, v in params.items())
            else:
                url += '?' + '&'.join(f"{k}={v}" for k, v in params.items())
        
        return url
    
    def _build_list_url(self, config: SiteConfig, page: int) -> str:
        """构建列表URL"""
        if config.crawl_method == CrawlMethod.API:
            url = config.base_url.format(page=page)
        else:
            url = f"{config.base_url}{config.search_url or ''}"
            if config.pagination_param:
                if '?' in url:
                    url += f"&{config.pagination_param}={page}"
                else:
                    url += f"?{config.pagination_param}={page}"
        
        return url
    
    def _make_request(self, url: str, config: SiteConfig) -> Optional[requests.Response]:
        """发送HTTP请求"""
        try:
            self.stats['total_requests'] += 1
            
            headers = {**self.session.headers, **config.headers}
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            self.stats['successful_requests'] += 1
            return response
            
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            logger.error(f"请求失败: {url} - {e}")
            return None
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"请求异常: {url} - {e}")
            return None
    
    def _parse_response(self, response: requests.Response, config: SiteConfig, 
                       source_url: str) -> List[Dict]:
        """解析响应数据"""
        try:
            if config.crawl_method == CrawlMethod.API:
                return self._parse_api_response(response.json(), config)
            elif config.crawl_method == CrawlMethod.JSON:
                return self._parse_json_response(response.json(), config)
            else:
                return self._parse_html_response(response.content, config, source_url)
                
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return []
    
    def _parse_html_response(self, html_content: bytes, config: SiteConfig, 
                            source_url: str) -> List[Dict]:
        """解析HTML响应"""
        items = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找项目容器（根据配置或自动检测）
            item_selectors = [
                '.item', '.product', '.article', '.list-item',
                'div[class*="item"]', 'li[class*="item"]',
                'article', 'section'
            ]
            
            item_containers = None
            for selector in item_selectors:
                containers = soup.select(selector)
                if len(containers) >= 3:  # 至少找到3个项目
                    item_containers = containers
                    break
            
            if not item_containers:
                # 如果没有找到特定选择器，尝试查找所有链接容器
                link_containers = soup.find_all(['div', 'li', 'article'], 
                                               recursive=True)[:50]
                item_containers = link_containers
            
            for container in item_containers:
                try:
                    item = {
                        '_source_url': source_url,
                        '_crawled_at': datetime.now().isoformat(),
                        '_site': config.name
                    }
                    
                    # 提取字段
                    for field_config in config.fields:
                        value = self._extract_field(container, field_config)
                        if value is not None or field_config.required:
                            item[field_config.name] = value or field_config.default
                    
                    # 提取链接（如果未在字段中定义）
                    if 'url' not in item:
                        link_elem = container.find('a', href=True)
                        if link_elem:
                            item['url'] = urljoin(config.base_url, link_elem['href'])
                    
                    # 生成项目ID
                    if 'url' in item:
                        item['id'] = hashlib.md5(item['url'].encode()).hexdigest()[:12]
                    
                    # 验证必要字段
                    if self._validate_item(item, config):
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"处理项目容器时出错: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"解析HTML失败: {e}")
            return []
    
    def _parse_api_response(self, data: Dict, config: SiteConfig) -> List[Dict]:
        """解析API响应"""
        items = []
        
        try:
            # 尝试从常见API结构中提取数据
            data_items = []
            
            # 尝试不同可能的键
            possible_keys = ['items', 'data', 'results', 'list', 'products']
            for key in possible_keys:
                if key in data and isinstance(data[key], list):
                    data_items = data[key]
                    break
            
            if not data_items and isinstance(data, list):
                data_items = data
            
            for item_data in data_items:
                try:
                    item = {
                        '_crawled_at': datetime.now().isoformat(),
                        '_site': config.name
                    }
                    
                    # 提取字段
                    for field_config in config.fields:
                        value = self._extract_from_dict(item_data, field_config.selector)
                        if field_config.transform:
                            value = field_config.transform(value)
                        if value is not None or field_config.required:
                            item[field_config.name] = value or field_config.default
                    
                    # 生成项目ID
                    if 'id' not in item and 'url' in item:
                        item['id'] = hashlib.md5(item['url'].encode()).hexdigest()[:12]
                    
                    if self._validate_item(item, config):
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"处理API项目时出错: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"解析API响应失败: {e}")
            return []
    
    def _parse_json_response(self, data: Dict, config: SiteConfig) -> List[Dict]:
        """解析JSON响应（与API类似，但可能结构不同）"""
        # 这里使用与API相同的方法
        return self._parse_api_response(data, config)
    
    def _parse_detail_response(self, response: requests.Response, config: SiteConfig, 
                              source_url: str) -> Dict:
        """解析详情响应"""
        try:
            if config.crawl_method == CrawlMethod.API:
                data = response.json()
                detail = {}
                
                for field_config in config.fields:
                    value = self._extract_from_dict(data, field_config.selector)
                    if field_config.transform:
                        value = field_config.transform(value)
                    if value is not None or field_config.required:
                        detail[field_config.name] = value or field_config.default
                
                return detail
                
            else:
                # HTML详情页
                soup = BeautifulSoup(response.content, 'html.parser')
                detail = {
                    '_source_url': source_url,
                    '_crawled_at': datetime.now().isoformat(),
                    '_site': config.name
                }
                
                for field_config in config.fields:
                    value = self._extract_field(soup, field_config)
                    if value is not None or field_config.required:
                        detail[field_config.name] = value or field_config.default
                
                return detail
                
        except Exception as e:
            logger.error(f"解析详情响应失败: {e}")
            return {}
    
    def _extract_field(self, element, field_config: FieldConfig) -> Any:
        """从HTML元素中提取字段"""
        try:
            # 使用CSS选择器查找元素
            selected = element.select(field_config.selector)
            if not selected:
                return None
            
            target = selected[0]
            
            # 提取文本或属性
            if field_config.attributes:
                for attr in field_config.attributes:
                    if target.has_attr(attr):
                        value = target[attr]
                        break
                else:
                    value = target.get_text(strip=True)
            else:
                value = target.get_text(strip=True)
            
            # 应用正则表达式
            if field_config.regex and value:
                match = re.search(field_config.regex, value)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
            
            # 数据类型转换
            if field_config.data_type == DataType.NUMBER:
                try:
                    # 提取数字
                    numbers = re.findall(r'[-+]?\d*\.?\d+', str(value))
                    if numbers:
                        return float(numbers[0])
                    return None
                except:
                    return None
            
            elif field_config.data_type == DataType.DATE:
                # 简单的日期解析
                date_patterns = [
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{2}/\d{2}/\d{4})',
                    r'(\d{4}年\d{2}月\d{2}日)'
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, str(value))
                    if match:
                        return match.group(1)
                return value
            
            elif field_config.data_type == DataType.URL:
                if value and not value.startswith(('http://', 'https://')):
                    # 尝试构建完整URL
                    base = getattr(element, 'base_url', '')
                    if base:
                        return urljoin(base, value)
                return value
            
            else:
                return value
                
        except Exception as e:
            logger.debug(f"提取字段失败: {field_config.name} - {e}")
            return None
    
    def _extract_from_dict(self, data: Dict, selector: str) -> Any:
        """从字典中提取字段"""
        try:
            # 支持点号分隔的路径
            parts = selector.split('.')
            current = data
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None
            
            return current
            
        except Exception as e:
            logger.debug(f"从字典提取失败: {selector} - {e}")
            return None
    
    def _validate_item(self, item: Dict, config: SiteConfig) -> bool:
        """验证项目数据"""
        # 检查必要字段
        for field_config in config.fields:
            if field_config.required and field_config.name not in item:
                logger.debug(f"缺少必要字段: {field_config.name}")
                return False
        
        # 至少需要ID或URL
        if 'id' not in item and 'url' not in item:
            logger.debug("项目缺少ID和URL")
            return False
        
        return True
    
    def _save_to_database(self, site_name: str, data_type: str, items: List[Dict]):
        """保存数据到数据库"""
        try:
            cursor = self.db_conn.cursor()
            
            for item in items:
                item_id = item.get('id')
                item_url = item.get('url')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO crawled_data 
                    (site_name, data_type, item_id, item_url, data_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    site_name,
                    data_type,
                    item_id,
                    item_url,
                    json.dumps(item, ensure_ascii=False)
                ))
            
            self.db_conn.commit()
            logger.debug(f"保存 {len(items)} 个项目到数据库")
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
            self.db_conn.rollback()
    
    def export_data(self, site_name: str, data_type: str = None, 
                   format: str = 'json', filename: str = None) -> bool:
        """
        导出数据
        
        Args:
            site_name: 网站名称
            data_type: 数据类型（list/detail）
            format: 导出格式（json/csv）
            filename: 输出文件名
            
        Returns:
            是否导出成功
        """
        try:
            cursor = self.db_conn.cursor()
            
            query = 'SELECT data_json FROM crawled_data WHERE site_name = ?'
            params = [site_name]
            
            if data_type:
                query += ' AND data_type = ?'
                params.append(data_type)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                logger.warning(f"无数据可导出: {site_name}")
                return False
            
            # 解析JSON数据
            items = []
            for row in rows:
                try:
                    item = json.loads(row[0])
                    items.append(item)
                except:
                    continue
            
            if not items:
                logger.warning(f"无有效数据可导出: {site_name}")
                return False
            
            # 生成文件名
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'crawler_export_{site_name}_{data_type or "all"}_{timestamp}.{format}'
            
            # 导出数据
            if format == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
            
            elif format == 'csv':
                if items:
                    # 提取所有可能的字段
                    all_fields = set()
                    for item in items:
                        all_fields.update(item.keys())
                    
                    # 排序字段
                    field_order = ['id', 'url', 'title', 'name', 'price', 'date']
                    remaining_fields = sorted([f for f in all_fields if f not in field_order])
                    fields = field_order + remaining_fields
                    
                    with open(filename, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fields)
                        writer.writeheader()
                        
                        for item in items:
                            # 确保所有字段都存在
                            row = {field: item.get(field, '') for field in fields}
                            writer.writerow(row)
            
            logger.info(f"数据已导出到: {filename}")
            print(f"\n导出统计:")
            print(f"  网站: {site_name}")
            print(f"  数据类型: {data_type or 'all'}")
            print(f"  项目数: {len(items)}")
            print(f"  文件: {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取爬虫统计信息"""
        current_time = datetime.now()
        elapsed = (current_time - self.stats['start_time']).total_seconds()
        
        stats = self.stats.copy()
        stats['elapsed_seconds'] = elapsed
        stats['requests_per_second'] = stats['total_requests'] / elapsed if elapsed > 0 else 0
        stats['success_rate'] = (stats['successful_requests'] / stats['total_requests'] * 100 
                                if stats['total_requests'] > 0 else 0)
        
        return stats
    
    def close(self):
        """关闭资源"""
        try:
            if self.db_conn:
                self.db_conn.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭资源失败: {e}")

def create_sample_config():
    """创建示例配置文件"""
    sample_config = {
        'sites': {
            'example_news': {
                'name': '示例新闻网站',
                'base_url': 'https://example.com',
                'crawl_method': 'html',
                'search_url': '/search',
                'pagination_param': 'page',
                'items_per_page': 20,
                'request_delay': 1.0,
                'headers': {
                    'Referer': 'https://example.com'
                },
                'fields': [
                    {
                        'name': 'title',
                        'selector': '.news-title',
                        'data_type': 'text',
                        'required': True
                    },
                    {
                        'name': 'url',
                        'selector': '.news-title a',
                        'data_type': 'url',
                        'required': True,
                        'attributes': ['href']
                    },
                    {
                        'name': 'summary',
                        'selector': '.news-summary',
                        'data_type': 'text'
                    },
                    {
                        'name': 'date',
                        'selector': '.news-date',
                        'data_type': 'date',
                        'regex': r'(\d{4}-\d{2}-\d{2})'
                    },
                    {
                        'name': 'author',
                        'selector': '.news-author',
                        'data_type': 'text'
                    }
                ]
            },
            'example_api': {
                'name': '示例API网站',
                'base_url': 'https://api.example.com/items?page={page}',
                'crawl_method': 'api',
                'items_per_page': 50,
                'request_delay': 0.5,
                'fields': [
                    {
                        'name': 'id',
                        'selector': 'id',
                        'data_type': 'text',
                        'required': True
                    },
                    {
                        'name': 'name',
                        'selector': 'name',
                        'data_type': 'text',
                        'required': True
                    },
                    {
                        'name': 'price',
                        'selector': 'price',
                        'data_type': 'number'
                    },
                    {
                        'name': 'category',
                        'selector': 'category.name',
                        'data_type': 'text'
                    }
                ]
            }
        }
    }
    
    return sample_config

def main():
    """主函数"""
    try:
        print("=== 高级通用爬虫框架 ===")
        print("功能: 可配置的多网站数据爬取框架")
        print()
        
        crawler = AdvancedCrawler()
        
        print("1. 创建示例配置文件")
        print("2. 加载配置文件")
        print("3. 爬取网站数据")
        print("4. 导出爬取数据")
        print("5. 查看爬虫统计")
        print("6. 退出")
        
        choice = input("\n请选择功能 (1-6): ").strip()
        
        if choice == '1':
            # 创建示例配置文件
            sample_config = create_sample_config()
            
            filename = input("保存文件名 (默认: crawler_config.yaml): ").strip()
            if not filename:
                filename = 'crawler_config.yaml'
            
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(sample_config, f, allow_unicode=True, default_flow_style=False)
            
            print(f"示例配置文件已保存到: {filename}")
            print("\n请编辑配置文件，然后使用功能2加载配置")
            
        elif choice == '2':
            config_file = input("请输入配置文件路径: ").strip()
            if os.path.exists(config_file):
                crawler.load_config(config_file)
                
                if crawler.configs:
                    print(f"\n已加载 {len(crawler.configs)} 个网站配置:")
                    for site_name in crawler.configs:
                        config = crawler.configs[site_name]
                        print(f"  {site_name}: {config.name}")
                        print(f"    基础URL: {config.base_url}")
                        print(f"    爬取方法: {config.crawl_method.value}")
                        print(f"    字段数: {len(config.fields)}")
                else:
                    print("配置文件加载失败或为空")
            else:
                print("配置文件不存在")
                
        elif choice == '3':
            if not crawler.configs:
                print("请先加载配置文件")
                return
            
            print("\n可用网站配置:")
            for i, site_name in enumerate(crawler.configs.keys(), 1):
                print(f"{i}. {site_name} - {crawler.configs[site_name].name}")
            
            site_choice = input("请选择网站 (输入编号或名称): ").strip()
            
            if site_choice.isdigit():
                site_index = int(site_choice) - 1
                site_names = list(crawler.configs.keys())
                if 0 <= site_index < len(site_names):
                    site_name = site_names[site_index]
                else:
                    print("无效选择")
                    return
            else:
                site_name = site_choice
            
            if site_name not in crawler.configs:
                print(f"未找到网站配置: {site_name}")
                return
            
            config = crawler.configs[site_name]
            
            # 获取爬取参数
            query = None
            if config.search_url:
                query = input("搜索查询 (留空跳过): ").strip()
                if not query:
                    query = None
            
            pages = input(f"爬取页数 (默认1, 最大10): ").strip()
            pages = int(pages) if pages.isdigit() and 1 <= int(pages) <= 10 else 1
            
            max_items = input(f"最大项目数 (默认100): ").strip()
            max_items = int(max_items) if max_items.isdigit() else 100
            
            print(f"\n开始爬取: {config.name}")
            print(f"参数: 查询='{query}', 页数={pages}, 最大项目数={max_items}")
            
            items = crawler.crawl_site(site_name, query, pages, max_items)
            
            if items:
                print(f"\n爬取完成，共获取 {len(items)} 个项目")
                
                # 显示前5个项目
                print(f"\n前5个项目:")
                for i, item in enumerate(items[:5], 1):
                    title = item.get('title') or item.get('name') or '无标题'
                    print(f"{i}. {title}")
                    
                    if 'url' in item:
                        print(f"   链接: {item['url']}")
                    
                    if 'price' in item:
                        print(f"   价格: {item['price']}")
                    
                    if 'date' in item:
                        print(f"   日期: {item['date']}")
                    
                    print()
                
                # 询问是否爬取详情
                if 'url' in items[0]:
                    get_details = input("是否爬取项目详情？ (y/n): ").strip().lower()
                    if get_details == 'y':
                        urls = [item['url'] for item in items if 'url' in item]
                        details = crawler.crawl_item_details(site_name, urls[:10])  # 只取前10个
                        
                        if details:
                            print(f"\n获取到 {len(details)} 个项目详情")
            else:
                print("未爬取到数据")
                
        elif choice == '4':
            if not crawler.configs:
                print("请先加载配置文件")
                return
            
            print("\n可用网站配置:")
            for site_name in crawler.configs:
                print(f"  {site_name} - {crawler.configs[site_name].name}")
            
            site_name = input("请输入网站名称: ").strip()
            
            if site_name not in crawler.configs:
                print(f"未找到网站配置: {site_name}")
                return
            
            print("\n导出选项:")
            print("1. 导出列表数据")
            print("2. 导出详情数据")
            print("3. 导出所有数据")
            
            data_choice = input("请选择 (1-3): ").strip()
            data_type_map = {'1': 'list', '2': 'detail', '3': None}
            data_type = data_type_map.get(data_choice)
            
            print("\n导出格式:")
            print("1. JSON")
            print("2. CSV")
            
            format_choice = input("请选择 (1-2): ").strip()
            format_map = {'1': 'json', '2': 'csv'}
            export_format = format_map.get(format_choice, 'json')
            
            filename = input("输出文件名 (留空自动生成): ").strip()
            
            if crawler.export_data(site_name, data_type, export_format, filename):
                print("导出成功")
            else:
                print("导出失败")
                
        elif choice == '5':
            stats = crawler.get_stats()
            
            print(f"\n=== 爬虫统计 ===")
            print(f"开始时间: {stats['start_time']}")
            print(f"运行时长: {stats['elapsed_seconds']:.1f}秒")
            print(f"总请求数: {stats['total_requests']}")
            print(f"成功请求: {stats['successful_requests']}")
            print(f"失败请求: {stats['failed_requests']}")
            print(f"成功率: {stats['success_rate']:.1f}%")
            print(f"请求速率: {stats['requests_per_second']:.2f}次/秒")
            print(f"总项目数: {stats['total_items']}")
            
        elif choice == '6':
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