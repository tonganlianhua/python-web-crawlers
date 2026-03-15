#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫02: 电商价格监控爬虫 - 京东商品价格爬取
功能: 爬取京东商品信息，监控价格变化，支持多商品同时监控
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import csv
from datetime import datetime
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import quote

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_02.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JDPriceCrawler:
    """京东商品价格爬虫"""
    
    def __init__(self):
        self.base_url = "https://search.jd.com/Search"
        self.product_url = "https://item.jd.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.jd.com/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def search_products(self, keyword: str, page: int = 1, page_size: int = 30) -> List[Dict]:
        """
        搜索商品
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            list: 商品列表
        """
        products = []
        
        try:
            logger.info(f"搜索商品: {keyword}, 第{page}页")
            
            params = {
                'keyword': keyword,
                'page': page,
                's': (page - 1) * page_size + 1,
                'click': 0
            }
            
            response = self.session.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找商品列表
            product_items = soup.select('.gl-item')
            
            for item in product_items:
                try:
                    product = {}
                    
                    # 获取商品ID
                    product_id = item.get('data-sku')
                    if product_id:
                        product['product_id'] = product_id
                        product['url'] = f"{self.product_url}{product_id}.html"
                    
                    # 获取商品名称
                    name_elem = item.select_one('.p-name a em')
                    if name_elem:
                        product['name'] = name_elem.get_text(strip=True)
                    
                    # 获取价格
                    price_elem = item.select_one('.p-price i')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # 清理价格文本
                        price_text = re.sub(r'[^\d.]', '', price_text)
                        try:
                            product['price'] = float(price_text)
                        except:
                            product['price'] = price_text
                    
                    # 获取店铺名称
                    shop_elem = item.select_one('.p-shop a')
                    if shop_elem:
                        product['shop'] = shop_elem.get_text(strip=True)
                    
                    # 获取评论数
                    comment_elem = item.select_one('.p-commit a')
                    if comment_elem:
                        comment_text = comment_elem.get_text(strip=True)
                        # 提取数字
                        nums = re.findall(r'\d+', comment_text)
                        if nums:
                            product['comments'] = int(''.join(nums))
                    
                    # 获取商品图片
                    img_elem = item.select_one('.p-img img')
                    if img_elem and img_elem.get('data-lazy-img'):
                        product['image'] = 'https:' + img_elem.get('data-lazy-img')
                    
                    if product.get('name') and product.get('price'):
                        product['crawled_at'] = datetime.now().isoformat()
                        product['keyword'] = keyword
                        products.append(product)
                        
                except Exception as e:
                    logger.warning(f"处理商品条目时出错: {e}")
                    continue
            
            logger.info(f"搜索到 {len(products)} 个商品")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {e}")
        except Exception as e:
            logger.error(f"搜索过程中出错: {e}")
        
        return products
    
    def get_product_details(self, product_url: str) -> Optional[Dict]:
        """
        获取商品详细信息
        
        Args:
            product_url: 商品详情页URL
            
        Returns:
            dict: 商品详细信息
        """
        try:
            logger.info(f"获取商品详情: {product_url}")
            
            response = self.session.get(product_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {}
            
            # 获取商品标题
            title_elem = soup.select_one('.sku-name')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # 获取价格（从详情页）
            price_elem = soup.select_one('.p-price .price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_text = re.sub(r'[^\d.]', '', price_text)
                try:
                    details['price'] = float(price_text)
                except:
                    details['price'] = price_text
            
            # 获取促销信息
            promos = []
            promo_elems = soup.select('.promise-dt')
            for elem in promo_elems:
                promos.append(elem.get_text(strip=True))
            if promos:
                details['promotions'] = promos
            
            # 获取规格参数
            params = {}
            param_elems = soup.select('.Ptable-item')
            for elem in param_elems:
                param_name = elem.select_one('h3')
                if param_name:
                    param_name = param_name.get_text(strip=True)
                    param_items = elem.select('dl')
                    for item in param_items:
                        dt = item.select_one('dt')
                        dd = item.select_one('dd')
                        if dt and dd:
                            params[dt.get_text(strip=True)] = dd.get_text(strip=True)
            
            if params:
                details['parameters'] = params
            
            # 获取商品图片
            images = []
            img_elems = soup.select('.spec-items img')
            for elem in img_elems:
                img_url = elem.get('src') or elem.get('data-url')
                if img_url:
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url
                    images.append(img_url)
            
            if images:
                details['images'] = images
            
            details['crawled_at'] = datetime.now().isoformat()
            details['url'] = product_url
            
            logger.debug(f"获取到商品详情: {details.get('title', '未知商品')}")
            return details
            
        except Exception as e:
            logger.error(f"获取商品详情时出错: {e}")
            return None
    
    def monitor_price(self, product_url: str, interval_minutes: int = 60, duration_hours: int = 24):
        """
        监控商品价格变化
        
        Args:
            product_url: 商品URL
            interval_minutes: 监控间隔（分钟）
            duration_hours: 监控时长（小时）
        """
        monitor_data = []
        end_time = time.time() + duration_hours * 3600
        
        print(f"开始监控商品价格: {product_url}")
        print(f"监控时长: {duration_hours}小时, 间隔: {interval_minutes}分钟")
        print("-" * 50)
        
        try:
            while time.time() < end_time:
                details = self.get_product_details(product_url)
                
                if details:
                    record = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'price': details.get('price'),
                        'title': details.get('title', '未知商品'),
                        'url': product_url
                    }
                    
                    monitor_data.append(record)
                    
                    print(f"[{record['timestamp']}] 价格: ¥{record['price']} - {record['title']}")
                    
                    # 如果有历史数据，显示价格变化
                    if len(monitor_data) > 1:
                        prev_price = monitor_data[-2]['price']
                        curr_price = record['price']
                        if isinstance(prev_price, (int, float)) and isinstance(curr_price, (int, float)):
                            change = curr_price - prev_price
                            change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
                            print(f"    价格变化: {change:+.2f} ({change_percent:+.2f}%)")
                
                # 等待下一次监控
                if time.time() + interval_minutes * 60 < end_time:
                    print(f"等待 {interval_minutes} 分钟...")
                    time.sleep(interval_minutes * 60)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n监控被用户中断")
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        
        # 保存监控数据
        if monitor_data:
            self.save_monitor_data(monitor_data, product_url)
        
        return monitor_data
    
    def save_monitor_data(self, data: List[Dict], product_url: str):
        """保存监控数据"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            product_id = re.search(r'/(\d+)\.html', product_url)
            if product_id:
                filename = f'jd_monitor_{product_id.group(1)}_{timestamp}.json'
            else:
                filename = f'jd_monitor_{timestamp}.json'
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"监控数据已保存到: {filename}")
            
            # 同时保存为CSV
            csv_file = filename.replace('.json', '.csv')
            if data:
                keys = data[0].keys()
                with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(data)
                
                logger.info(f"监控数据CSV已保存到: {csv_file}")
                
        except Exception as e:
            logger.error(f"保存监控数据时出错: {e}")

def main():
    """主函数"""
    try:
        crawler = JDPriceCrawler()
        
        print("=== 京东商品价格爬虫 ===")
        print("1. 搜索商品")
        print("2. 监控商品价格")
        print("3. 退出")
        
        choice = input("\n请选择功能 (1-3): ").strip()
        
        if choice == '1':
            keyword = input("请输入搜索关键词: ").strip()
            if keyword:
                products = crawler.search_products(keyword, page=1)
                
                if products:
                    print(f"\n找到 {len(products)} 个商品:")
                    for i, product in enumerate(products[:10], 1):
                        print(f"{i}. {product.get('name', '未知商品')}")
                        print(f"   价格: ¥{product.get('price', '未知')}")
                        print(f"   店铺: {product.get('shop', '未知')}")
                        print(f"   评论: {product.get('comments', 0)}")
                        print()
                    
                    # 保存搜索结果
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'jd_search_{keyword}_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(products, f, ensure_ascii=False, indent=2)
                    print(f"搜索结果已保存到: {filename}")
                else:
                    print("未找到相关商品")
                    
        elif choice == '2':
            url = input("请输入京东商品URL: ").strip()
            if url and 'item.jd.com' in url:
                try:
                    interval = int(input("监控间隔(分钟，默认60): ") or 60)
                    duration = int(input("监控时长(小时，默认24): ") or 24)
                    
                    crawler.monitor_price(url, interval, duration)
                except ValueError:
                    print("请输入有效的数字")
            else:
                print("请输入有效的京东商品URL")
                
        elif choice == '3':
            print("退出程序")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()