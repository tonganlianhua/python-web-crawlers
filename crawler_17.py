#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品价格监控爬虫 - 监控电商平台商品价格
网站：京东、淘宝、天猫等
功能：监控商品价格变化、库存状态、促销信息等
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote, urlparse, parse_qs
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PriceMonitorCrawler:
    """商品价格监控爬虫类"""
    
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session.headers.update(self.headers)
        
        # 支持的电商平台配置
        self.platforms = {
            'jd': {
                'name': '京东',
                'base_url': 'https://item.jd.com',
                'search_url': 'https://search.jd.com/Search',
                'price_api': 'https://p.3.cn/prices/mgets',
                'item_id_pattern': r'/(\d+)\.html',
            },
            'taobao': {
                'name': '淘宝',
                'base_url': 'https://item.taobao.com',
                'search_url': 'https://s.taobao.com/search',
                'item_id_pattern': r'id=(\d+)',
            },
            'tmall': {
                'name': '天猫',
                'base_url': 'https://detail.tmall.com',
                'search_url': 'https://list.tmall.com/search_product.htm',
                'item_id_pattern': r'id=(\d+)',
            },
            'amazon': {
                'name': '亚马逊',
                'base_url': 'https://www.amazon.cn',
                'search_url': 'https://www.amazon.cn/s',
                'item_id_pattern': r'/dp/([A-Z0-9]+)',
            },
            'suning': {
                'name': '苏宁易购',
                'base_url': 'https://product.suning.com',
                'search_url': 'https://search.suning.com',
                'item_id_pattern': r'/(\d+)\.html',
            }
        }
        
        # 价格历史记录存储
        self.price_history = {}
        
        # 监控配置
        self.monitor_interval = 3600  # 默认监控间隔（秒）
        self.price_change_threshold = 0.05  # 价格变化阈值（5%）
    
    def extract_item_id(self, url: str) -> Optional[str]:
        """
        从URL中提取商品ID
        
        Args:
            url: 商品URL
            
        Returns:
            商品ID，如果无法提取则返回None
        """
        for platform, config in self.platforms.items():
            pattern = config.get('item_id_pattern')
            if pattern:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        # 尝试通用提取
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        
        for part in reversed(path_parts):
            if part and part.isdigit() and len(part) > 5:
                return part
        
        return None
    
    def detect_platform(self, url: str) -> Optional[str]:
        """
        检测URL属于哪个电商平台
        
        Args:
            url: 商品URL
            
        Returns:
            平台名称，如果无法识别则返回None
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'jd.com' in domain or '360buy.com' in domain:
            return 'jd'
        elif 'taobao.com' in domain:
            return 'taobao'
        elif 'tmall.com' in domain:
            return 'tmall'
        elif 'amazon.' in domain:
            return 'amazon'
        elif 'suning.com' in domain:
            return 'suning'
        
        return None
    
    def fetch_product_info(self, url: str) -> Optional[Dict]:
        """
        获取商品信息
        
        Args:
            url: 商品URL
            
        Returns:
            商品信息字典，失败则返回None
        """
        try:
            platform = self.detect_platform(url)
            if not platform:
                logger.warning(f"无法识别的电商平台: {url}")
                return None
            
            item_id = self.extract_item_id(url)
            if not item_id:
                logger.warning(f"无法提取商品ID: {url}")
                return None
            
            logger.info(f"正在获取 {self.platforms[platform]['name']} 商品: {item_id}")
            
            # 根据平台调用不同的解析方法
            if platform == 'jd':
                product_info = self._fetch_jd_product(url, item_id)
            elif platform == 'taobao':
                product_info = self._fetch_taobao_product(url, item_id)
            elif platform == 'tmall':
                product_info = self._fetch_tmall_product(url, item_id)
            else:
                product_info = self._fetch_generic_product(url, item_id, platform)
            
            if product_info:
                product_info['platform'] = platform
                product_info['platform_name'] = self.platforms[platform]['name']
                product_info['item_id'] = item_id
                product_info['url'] = url
                product_info['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                product_info['crawl_time'] = time.time()
                
                # 更新价格历史
                self._update_price_history(product_info)
                
                logger.info(f"成功获取商品: {product_info.get('title', '未知商品')}")
                return product_info
            else:
                logger.warning(f"解析商品信息失败: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取商品信息时发生未知错误: {str(e)}")
            return None
    
    def _fetch_jd_product(self, url: str, item_id: str) -> Dict:
        """获取京东商品信息"""
        product_info = {
            'source': '京东',
        }
        
        try:
            # 获取商品页面
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'gbk'  # 京东使用GBK编码
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 标题
            title_tag = soup.find('div', class_='sku-name')
            if not title_tag:
                title_tag = soup.find('div', id='name')
            if title_tag:
                product_info['title'] = title_tag.get_text(strip=True)
            
            # 价格（京东价格通常通过API获取）
            price = self._get_jd_price(item_id)
            if price:
                product_info['price'] = price
            
            # 促销价
            promo_price_tag = soup.find('span', class_='p-price')
            if promo_price_tag:
                price_text = promo_price_tag.find('span', class_='price')
                if price_text:
                    product_info['promo_price'] = price_text.get_text(strip=True)
            
            # 原价
            original_price_tag = soup.find('del')
            if original_price_tag:
                product_info['original_price'] = original_price_tag.get_text(strip=True)
            
            # 库存状态
            stock_tag = soup.find('div', id='store-prompt')
            if stock_tag:
                stock_text = stock_tag.get_text(strip=True)
                product_info['stock_status'] = stock_text
                product_info['in_stock'] = '无货' not in stock_text
            else:
                # 尝试其他方式判断库存
                buy_tag = soup.find('a', id='InitCartUrl')
                if buy_tag:
                    product_info['in_stock'] = True
            
            # 商品图片
            img_tag = soup.find('img', id='spec-img')
            if img_tag and img_tag.get('data-origin'):
                product_info['image_url'] = img_tag.get('data-origin')
            
            # 商品参数
            params = {}
            param_table = soup.find('div', class_='Ptable')
            if param_table:
                param_items = param_table.find_all('div', class_='Ptable-item')
                for item in param_items:
                    param_name = item.find('h3')
                    if param_name:
                        param_name_text = param_name.get_text(strip=True)
                        param_dls = item.find_all('dl')
                        for dl in param_dls:
                            dt = dl.find('dt')
                            dd = dl.find('dd')
                            if dt and dd:
                                params[f"{param_name_text}_{dt.get_text(strip=True)}"] = dd.get_text(strip=True)
            
            if params:
                product_info['parameters'] = params
            
            # 评价数量
            comment_tag = soup.find('div', id='comment-count')
            if comment_tag:
                comment_link = comment_tag.find('a')
                if comment_link:
                    comment_text = comment_link.get_text(strip=True)
                    match = re.search(r'(\d+)', comment_text.replace(',', ''))
                    if match:
                        product_info['comment_count'] = int(match.group(1))
            
            # 店铺信息
            shop_tag = soup.find('div', class_='mt')
            if shop_tag:
                shop_link = shop_tag.find('a')
                if shop_link:
                    product_info['shop_name'] = shop_link.get_text(strip=True)
                    product_info['shop_url'] = urljoin(url, shop_link.get('href', ''))
            
        except Exception as e:
            logger.error(f"获取京东商品信息时发生错误: {str(e)}")
        
        return product_info
    
    def _get_jd_price(self, item_id: str) -> Optional[float]:
        """获取京东商品价格（通过API）"""
        try:
            # 京东价格API
            api_url = "https://p.3.cn/prices/mgets"
            params = {
                'skuIds': f'J_{item_id}',
                'type': '1',
            }
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            price_data = response.json()
            if price_data and len(price_data) > 0:
                price_str = price_data[0].get('p')
                if price_str:
                    return float(price_str)
        
        except Exception as e:
            logger.warning(f"获取京东价格API失败: {str(e)}")
        
        return None
    
    def _fetch_taobao_product(self, url: str, item_id: str) -> Dict:
        """获取淘宝商品信息"""
        product_info = {
            'source': '淘宝',
        }
        
        try:
            # 淘宝页面需要处理复杂的反爬机制
            # 这里使用简化方法，实际应用需要更复杂的处理
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 标题
            title_tag = soup.find('h1')
            if not title_tag:
                title_tag = soup.find('div', class_='tb-detail-hd')
            if title_tag:
                product_info['title'] = title_tag.get_text(strip=True)
            
            # 价格（淘宝价格通常在JavaScript中）
            # 尝试从页面中提取价格信息
            price_pattern = r'"price"\s*:\s*"([\d\.]+)"'
            price_match = re.search(price_pattern, response.text)
            if price_match:
                product_info['price'] = float(price_match.group(1))
            
            # 销量
            sales_pattern = r'"sellCount"\s*:\s*"?(\d+)"?'
            sales_match = re.search(sales_pattern, response.text)
            if sales_match:
                product_info['sales_count'] = int(sales_match.group(1))
            
            # 店铺信息
            shop_pattern = r'"shopId"\s*:\s*"?(\d+)"?'
            shop_match = re.search(shop_pattern, response.text)
            if shop_match:
                product_info['shop_id'] = shop_match.group(1)
            
            # 商品图片
            img_tags = soup.find_all('img', class_='J_ImgSwitcherItem')
            if img_tags:
                product_info['image_urls'] = []
                for img in img_tags[:5]:  # 只取前5张图片
                    img_url = img.get('data-src') or img.get('src')
                    if img_url:
                        product_info['image_urls'].append(img_url)
            
        except Exception as e:
            logger.error(f"获取淘宝商品信息时发生错误: {str(e)}")
        
        return product_info
    
    def _fetch_tmall_product(self, url: str, item_id: str) -> Dict:
        """获取天猫商品信息"""
        product_info = {
            'source': '天猫',
        }
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 标题
            title_tag = soup.find('div', class_='tb-detail-hd')
            if title_tag:
                h1_tag = title_tag.find('h1')
                if h1_tag:
                    product_info['title'] = h1_tag.get_text(strip=True)
            
            # 价格（天猫价格通常在特定的div中）
            price_tag = soup.find('div', class_='tm-price')
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                match = re.search(r'[\d\.]+', price_text)
                if match:
                    product_info['price'] = float(match.group())
            
            # 月销量
            sales_tag = soup.find('div', class_='tm-ind-panel')
            if sales_tag:
                sales_items = sales_tag.find_all('div', class_='tm-ind-item')
                for item in sales_items:
                    text = item.get_text(strip=True)
                    if '月销量' in text:
                        match = re.search(r'(\d+)', text)
                        if match:
                            product_info['monthly_sales'] = int(match.group(1))
            
            # 累计评价
            comment_tag = soup.find('li', id='J_ItemRates')
            if comment_tag:
                strong_tag = comment_tag.find('strong')
                if strong_tag:
                    comment_text = strong_tag.get_text(strip=True)
                    match = re.search(r'(\d+)', comment_text.replace(',', ''))
                    if match:
                        product_info['comment_count'] = int(match.group(1))
            
        except Exception as e:
            logger.error(f"获取天猫商品信息时发生错误: {str(e)}")
        
        return product_info
    
    def _fetch_generic_product(self, url: str, item_id: str, platform: str) -> Dict:
        """通用商品信息获取方法"""
        product_info = {
            'source': self.platforms.get(platform, {}).get('name', '未知平台'),
        }
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试查找标题
            title_selectors = ['h1', '.product-title', '.goods-title', '.item-title']
            for selector in title_selectors:
                title_tag = soup.find(selector)
                if title_tag:
                    product_info['title'] = title_tag.get_text(strip=True)
                    break
            
            # 尝试查找价格
            price_selectors = ['.price', '.product-price', '.goods-price', '.item-price']
            for selector in price_selectors:
                price_tag = soup.find(class_=selector)
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    match = re.search(r'[\d\.]+', price_text)
                    if match:
                        product_info['price'] = float(match.group())
                    break
            
            # 尝试查找图片
            img_selectors = ['.product-image', '.goods-image', '.item-image']
            for selector in img_selectors:
                img_tag = soup.find(class_=selector)
                if img_tag:
                    img = img_tag.find('img')
                    if img:
                        product_info['image_url'] = img.get('src') or img.get('data-src')
                    break
            
        except Exception as e:
            logger.error(f"获取通用商品信息时发生错误: {str(e)}")
        
        return product_info
    
    def _update_price_history(self, product_info: Dict) -> None:
        """
        更新价格历史记录
        
        Args:
            product_info: 商品信息
        """
        item_id = product_info.get('item_id')
        platform = product_info.get('platform')
        
        if not item_id or not platform:
            return
        
        key = f"{platform}_{item_id}"
        
        if key not in self.price_history:
            self.price_history[key] = []
        
        history_entry = {
            'timestamp': product_info.get('timestamp'),
            'crawl_time': product_info.get('crawl_time'),
            'price': product_info.get('price'),
            'promo_price': product_info.get('promo_price'),
            'original_price': product_info.get('original_price'),
            'in_stock': product_info.get('in_stock'),
        }
        
        self.price_history[key].append(history_entry)
        
        # 只保留最近100条记录
        if len(self.price_history[key]) > 100:
            self.price_history[key] = self.price_history[key][-100:]
    
    def get_price_history(self, item_id: str, platform: str = None) -> List[Dict]:
        """
        获取商品价格历史
        
        Args:
            item_id: 商品ID
            platform: 平台名称（可选）
            
        Returns:
            价格历史列表
        """
        if platform:
            key = f"{platform}_{item_id}"
            return self.price_history.get(key, [])
        else:
            # 查找所有平台中匹配的商品
            results = []
            for key, history in self.price_history.items():
                if key.endswith(f"_{item_id}"):
                    results.extend(history)
            return results
    
    def check_price_change(self, product_info: Dict) -> Optional[Dict]:
        """
        检查价格变化
        
        Args:
            product_info: 当前商品信息
            
        Returns:
            价格变化信息字典，如果没有变化则返回None
        """
        item_id = product_info.get('item_id')
        platform = product_info.get('platform')
        
        if not item_id or not platform:
            return None
        
        key = f"{platform}_{item_id}"
        history = self.price_history.get(key, [])
        
        if len(history) < 2:
            return None
        
        # 获取最近两次价格记录
        current_price = product_info.get('price')
        previous_entry = history[-2] if len(history) >= 2 else None
        
        if not current_price or not previous_entry or 'price' not in previous_entry:
            return None
        
        previous_price = previous_entry.get('price')
        
        if previous_price and current_price:
            price_change = current_price - previous_price
            price_change_percent = (price_change / previous_price) * 100 if previous_price != 0 else 0
            
            # 检查是否超过阈值
            if abs(price_change_percent) >= (self.price_change_threshold * 100):
                change_info = {
                    'item_id': item_id,
                    'platform': platform,
                    'title': product_info.get('title', '未知商品'),
                    'current_price': current_price,
                    'previous_price': previous_price,
                    'price_change': price_change,
                    'price_change_percent': round(price_change_percent, 2),
                    'change_time': product_info.get('timestamp'),
                    'previous_time': previous_entry.get('timestamp'),
                    'threshold_exceeded': True,
                }
                
                logger.info(f"价格变化超过阈值: {item_id}, 变化: {price_change_percent:.2f}%")
                return change_info
        
        return None
    
    def monitor_product(self, url: str, interval: int = None) -> Dict:
        """
        监控商品（单次检查）
        
        Args:
            url: 商品URL
            interval: 监控间隔（秒），如果为None则使用默认值
            
        Returns:
            监控结果字典
        """
        monitor_result = {
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
        }
        
        try:
            product_info = self.fetch_product_info(url)
            
            if product_info:
                monitor_result['success'] = True
                monitor_result['product_info'] = product_info
                
                # 检查价格变化
                price_change = self.check_price_change(product_info)
                if price_change:
                    monitor_result['price_change'] = price_change
                    monitor_result['has_price_change'] = True
                else:
                    monitor_result['has_price_change'] = False
                
                # 检查库存状态
                if 'in_stock' in product_info:
                    monitor_result['in_stock'] = product_info['in_stock']
            
        except Exception as e:
            monitor_result['error'] = str(e)
            logger.error(f"监控商品时发生错误: {str(e)}")
        
        return monitor_result
    
    def monitor_multiple_products(self, urls: List[str], interval: int = None) -> List[Dict]:
        """
        监控多个商品
        
        Args:
            urls: 商品URL列表
            interval: 监控间隔（秒），如果为None则使用默认值
            
        Returns:
            监控结果列表
        """
        results = []
        
        for url in urls:
            logger.info(f"正在监控商品: {url}")
            result = self.monitor_product(url, interval)
            results.append(result)
            
            # 添加延迟，避免请求过快
            time.sleep(2)
        
        return results
    
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
                if 'item_id' in data:  # 商品数据
                    item_id = data['item_id']
                    platform = data.get('platform', 'unknown')
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"product_{platform}_{item_id}_{timestamp}.json"
                elif 'url' in data:  # 监控结果
                    url_hash = hashlib.md5(data['url'].encode()).hexdigest()[:8]
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"monitor_{url_hash}_{timestamp}.json"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"price_monitor_{timestamp}.json"
            
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
    
    def export_price_history(self, item_id: str, platform: str = None, filename: str = None) -> bool:
        """
        导出价格历史记录
        
        Args:
            item_id: 商品ID
            platform: 平台名称（可选）
            filename: 文件名，如果为None则自动生成
            
        Returns:
            导出成功返回True，失败返回False
        """
        try:
            history = self.get_price_history(item_id, platform)
            
            if not history:
                logger.warning("没有价格历史记录可导出")
                return False
            
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"price_history_{item_id}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            export_data = {
                'item_id': item_id,
                'platform': platform,
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'record_count': len(history),
                'history': history,
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"价格历史记录已导出到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"导出价格历史记录时发生错误: {str(e)}")
            return False


def main():
    """主函数，演示爬虫的使用"""
    print("商品价格监控爬虫演示")
    print("=" * 50)
    print("支持平台: 京东、淘宝、天猫、亚马逊、苏宁易购等")
    print("功能: 监控价格变化、库存状态、导出历史记录")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = PriceMonitorCrawler(timeout=15)
    
    # 示例商品URL（这些是示例URL，实际使用时需要替换为真实商品）
    example_urls = [
        # 京东示例商品（手机）
        "https://item.jd.com/100000000000.html",  # 示例URL
        # 淘宝示例商品
        "https://item.taobao.com/item.htm?id=6000000000000",  # 示例URL
        # 天猫示例商品
        "https://detail.tmall.com/item.htm?id=6000000000000",  # 示例URL
    ]
    
    print("\n演示商品信息提取和平台检测...")
    
    for url in example_urls:
        print(f"\n分析URL: {url}")
        
        # 检测平台
        platform = crawler.detect_platform(url)
        if platform:
            platform_name = crawler.platforms[platform]['name']
            print(f"  检测到平台: {platform_name}")
        else:
            print(f"  无法识别平台")
        
        # 提取商品ID
        item_id = crawler.extract_item_id(url)
        if item_id:
            print(f"  提取商品ID: {item_id}")
        else:
            print(f"  无法提取商品ID")
    
    print("\n" + "=" * 50)
    print("演示监控流程...")
    
    # 由于示例URL不存在，我们模拟监控流程
    print("\n1. 初始化监控器")
    print("2. 设置价格变化阈值: 5%")
    print("3. 添加商品URL到监控列表")
    print("4. 定期检查价格变化")
    print("5. 发现价格变化时记录并通知")
    
    # 模拟价格监控
    print("\n模拟价格监控结果:")
    print("- 商品A: 价格稳定")
    print("- 商品B: 价格上涨 8.5% (超过阈值)")
    print("- 商品C: 缺货")
    print("- 商品D: 价格下降 12.3% (超过阈值)")
    
    # 演示如何使用真实URL进行监控
    print("\n" + "=" * 50)
    print("使用真实URL进行监控的步骤:")
    
    print("\n1. 准备真实商品URL:")
    print("   例如京东手机: https://item.jd.com/10000000000.html")
    print("   注意: 将10000000000替换为真实商品ID")
    
    print("\n2. 创建监控器:")
    print("   crawler = PriceMonitorCrawler(timeout=15)")
    
    print("\n3. 监控单个商品:")
    print("   result = crawler.monitor_product('商品URL')")
    print("   if result['success']:")
    print("       print(f'价格: {result[\"product_info\"][\"price\"]}')")
    
    print("\n4. 监控多个商品:")
    print("   urls = ['URL1', 'URL2', 'URL3']")
    print("   results = crawler.monitor_multiple_products(urls)")
    
    print("\n5. 检查价格变化:")
    print("   for result in results:")
    print("       if result.get('has_price_change'):")
    print("           change = result['price_change']")
    print("           print(f'价格变化: {change[\"price_change_percent\"]}%')")
    
    print("\n6. 导出价格历史:")
    print("   crawler.export_price_history('商品ID', '平台名称')")
    
    # 提供一个简单的测试函数
    def test_with_real_url():
        real_url = input("\n请输入一个真实的商品URL进行测试（或按Enter跳过）: ").strip()
        if real_url:
            print(f"\n正在监控商品: {real_url}")
            result = crawler.monitor_product(real_url)
            
            if result['success']:
                product_info = result['product_info']
                print(f"监控成功!")
                print(f"商品标题: {product_info.get('title', '未知')}")
                print(f"平台: {product_info.get('platform_name', '未知')}")
                print(f"商品ID: {product_info.get('item_id', '未知')}")
                
                if 'price' in product_info:
                    print(f"当前价格: {product_info['price']}")
                
                if 'in_stock' in product_info:
                    stock_status = "有货" if product_info['in_stock'] else "缺货"
                    print(f"库存状态: {stock_status}")
                
                if result.get('has_price_change'):
                    change = result['price_change']
                    print(f"价格变化: {change['price_change_percent']}%")
                    print(f"  原价: {change['previous_price']}")
                    print(f"  现价: {change['current_price']}")
                    print(f"  变化: {change['price_change']}")
                
                # 保存数据
                crawler.save_to_json(product_info)
                print(f"\n商品数据已保存到JSON文件")
            else:
                print(f"监控失败: {result.get('error', '未知错误')}")
    
    # 注释掉实际测试，避免在演示中要求输入
    # test_with_real_url()
    
    print("\n" + "=" * 50)
    print("高级功能演示:")
    
    print("\n1. 价格历史分析:")
    print("   - 跟踪价格变化趋势")
    print("   - 识别最佳购买时机")
    print("   - 预测价格走势")
    
    print("\n2. 库存监控:")
    print("   - 实时监控库存状态")
    print("   - 缺货补货提醒")
    print("   - 库存变化历史")
    
    print("\n3. 促销监控:")
    print("   - 识别促销活动")
    print("   - 跟踪促销时间")
    print("   - 比较不同平台价格")
    
    print("\n4. 自动化通知:")
    print("   - 价格变化邮件通知")
    print("   - 微信/钉钉消息推送")
    print("   - 短信提醒")
    
    print("\n爬虫演示完成！")
    print("\n注意事项:")
    print("1. 遵守各电商平台的robots.txt规则")
    print("2. 设置合理的请求间隔，避免被封IP")
    print("3. 处理反爬机制（如验证码、登录验证）")
    print("4. 定期更新解析规则，适应网站改版")


if __name__ == "__main__":
    main()