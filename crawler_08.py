#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫08: 房产信息爬虫 - 二手房/租房信息获取
功能: 爬取链家、贝壳等房产网站的二手房和租房信息
注意: 本爬虫仅用于学习研究，请遵守网站robots.txt和法律法规
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
import logging
import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote
import hashlib
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_08.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealEstateCrawler:
    """房产信息爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alike',
            'Referer': 'https://www.lianjia.com/',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 网站配置
        self.site_config = {
            'lianjia': {
                'base_url': 'https://www.lianjia.com',
                'ershoufang': '/ershoufang/',      # 二手房
                'zufang': '/zufang/',              # 租房
                'city': 'bj'                       # 默认城市（北京）
            },
            'ke': {
                'base_url': 'https://bj.ke.com',
                'ershoufang': '/ershoufang/',
                'zufang': '/zufang/',
                'city': 'bj'
            }
        }
        
        # 城市代码映射
        self.city_codes = {
            '北京': 'bj',
            '上海': 'sh',
            '广州': 'gz',
            '深圳': 'sz',
            '杭州': 'hz',
            '成都': 'cd',
            '武汉': 'wh',
            '南京': 'nj',
            '天津': 'tj',
            '西安': 'xa',
            '重庆': 'cq',
            '郑州': 'zz',
            '长沙': 'cs',
            '沈阳': 'sy',
            '青岛': 'qd',
            '大连': 'dl',
            '厦门': 'xm',
            '苏州': 'su',
            '宁波': 'nb',
            '无锡': 'wx'
        }
        
        logger.info("房产信息爬虫初始化完成")
    
    def search_houses(self, site: str, city: str = '北京', house_type: str = 'ershoufang', 
                     page: int = 1, max_results: int = 30) -> List[Dict]:
        """
        搜索房产信息
        
        Args:
            site: 网站 (lianjia, ke)
            city: 城市名称
            house_type: 类型 (ershoufang, zufang)
            page: 页码
            max_results: 最大结果数
            
        Returns:
            房产信息列表
        """
        try:
            logger.info(f"在 {site} 搜索{self._get_house_type_name(house_type)}: {city}")
            
            if site == 'lianjia':
                return self._search_lianjia(city, house_type, page, max_results)
            elif site == 'ke':
                return self._search_ke(city, house_type, page, max_results)
            else:
                logger.warning(f"不支持的网站: {site}")
                return []
                
        except Exception as e:
            logger.error(f"搜索房产信息失败: {e}")
            return []
    
    def _search_lianjia(self, city: str, house_type: str, page: int, max_results: int) -> List[Dict]:
        """搜索链家房产信息"""
        houses = []
        
        try:
            config = self.site_config['lianjia']
            
            # 获取城市代码
            city_code = self.city_codes.get(city, config['city'])
            
            # 构建URL
            base_path = config['ershoufang'] if house_type == 'ershoufang' else config['zufang']
            url = f"{config['base_url']}{city_code}{base_path}pg{page}/"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找房产列表
            house_items = soup.select('.sellListContent li')
            
            for item in house_items[:max_results]:
                try:
                    house = {
                        'site': 'lianjia',
                        'city': city,
                        'type': house_type,
                        'crawled_at': datetime.now().isoformat()
                    }
                    
                    # 获取标题和链接
                    title_elem = item.select_one('.title a')
                    if title_elem:
                        house['title'] = title_elem.get_text(strip=True)
                        house['url'] = urljoin(config['base_url'], title_elem.get('href', ''))
                    
                    # 获取房源ID
                    if house.get('url'):
                        match = re.search(r'/(\d+)\.html', house['url'])
                        if match:
                            house['house_id'] = match.group(1)
                    
                    # 获取基本信息
                    info_elem = item.select_one('.houseInfo')
                    if info_elem:
                        info_text = info_elem.get_text(strip=True)
                        house['info'] = info_text
                        
                        # 解析户型、面积、朝向等信息
                        parts = info_text.split('|')
                        if len(parts) >= 3:
                            house['layout'] = parts[0].strip()  # 户型
                            house['area'] = parts[1].strip()    # 面积
                            house['direction'] = parts[2].strip() if len(parts) > 2 else ''  # 朝向
                    
                    # 获取位置信息
                    position_elem = item.select_one('.positionInfo')
                    if position_elem:
                        position_text = position_elem.get_text(strip=True)
                        house['position'] = position_text
                        
                        # 解析小区和地区
                        parts = position_text.split('-')
                        if len(parts) >= 2:
                            house['community'] = parts[0].strip()  # 小区
                            house['district'] = parts[1].strip()   # 地区
                    
                    # 获取价格信息
                    price_elem = item.select_one('.totalPrice')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # 提取数字
                        nums = re.findall(r'[\d.]+', price_text)
                        if nums:
                            house['price'] = float(''.join(nums))
                            house['price_unit'] = '万' if house_type == 'ershoufang' else '元/月'
                    
                    # 获取单价（二手房）
                    if house_type == 'ershoufang':
                        unit_price_elem = item.select_one('.unitPrice')
                        if unit_price_elem:
                            unit_price_text = unit_price_elem.get_text(strip=True)
                            house['unit_price'] = unit_price_text
                    
                    # 获取标签
                    tags = []
                    tag_elems = item.select('.tag span')
                    for tag in tag_elems:
                        tags.append(tag.get_text(strip=True))
                    
                    if tags:
                        house['tags'] = tags
                    
                    # 获取关注度
                    follow_elem = item.select_one('.starIcon')
                    if follow_elem:
                        follow_text = follow_elem.next_sibling
                        if follow_text:
                            house['follow'] = follow_text.strip()
                    
                    if house.get('house_id'):
                        houses.append(house)
                        
                except Exception as e:
                    logger.debug(f"处理房产条目时出错: {e}")
                    continue
            
            logger.info(f"从链家找到 {len(houses)} 个房源")
            return houses
            
        except Exception as e:
            logger.error(f"搜索链家失败: {e}")
            return []
    
    def _search_ke(self, city: str, house_type: str, page: int, max_results: int) -> List[Dict]:
        """搜索贝壳房产信息"""
        houses = []
        
        try:
            config = self.site_config['ke']
            
            # 获取城市代码
            city_code = self.city_codes.get(city, config['city'])
            
            # 贝壳使用不同的域名格式
            base_url = f"https://{city_code}.ke.com"
            
            # 构建URL
            base_path = config['ershoufang'] if house_type == 'ershoufang' else config['zufang']
            url = f"{base_url}{base_path}pg{page}/"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找房产列表
            house_items = soup.select('.sellListContent li') or soup.select('.content__list--item')
            
            for item in house_items[:max_results]:
                try:
                    house = {
                        'site': 'ke',
                        'city': city,
                        'type': house_type,
                        'crawled_at': datetime.now().isoformat()
                    }
                    
                    # 根据不同类型解析
                    if house_type == 'ershoufang':
                        # 二手房解析
                        title_elem = item.select_one('a[data-el="ershoufang"]')
                        if title_elem:
                            house['title'] = title_elem.get('title', '').strip()
                            house['url'] = urljoin(base_url, title_elem.get('href', ''))
                        
                        # 获取房源ID
                        if house.get('url'):
                            match = re.search(r'/(\d+)\.html', house['url'])
                            if match:
                                house['house_id'] = match.group(1)
                        
                        # 获取基本信息
                        info_elem = item.select_one('.houseInfo')
                        if info_elem:
                            info_text = info_elem.get_text(strip=True)
                            house['info'] = info_text
                    
                    else:
                        # 租房解析
                        title_elem = item.select_one('.content__list--item--title a')
                        if title_elem:
                            house['title'] = title_elem.get_text(strip=True)
                            house['url'] = urljoin(base_url, title_elem.get('href', ''))
                        
                        # 获取房源ID
                        if house.get('url'):
                            match = re.search(r'/(\d+)\.html', house['url'])
                            if match:
                                house['house_id'] = match.group(1)
                        
                        # 获取租房信息
                        desc_elem = item.select_one('.content__list--item--des')
                        if desc_elem:
                            house['info'] = desc_elem.get_text(strip=True)
                    
                    # 获取价格信息
                    price_elem = item.select_one('.price')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        nums = re.findall(r'[\d.]+', price_text)
                        if nums:
                            house['price'] = float(''.join(nums))
                            house['price_unit'] = '万' if house_type == 'ershoufang' else '元/月'
                    
                    if house.get('house_id'):
                        houses.append(house)
                        
                except Exception as e:
                    logger.debug(f"处理贝壳房产条目时出错: {e}")
                    continue
            
            logger.info(f"从贝壳找到 {len(houses)} 个房源")
            return houses
            
        except Exception as e:
            logger.error(f"搜索贝壳失败: {e}")
            return []
    
    def get_house_details(self, house_url: str) -> Optional[Dict]:
        """
        获取房产详细信息
        
        Args:
            house_url: 房产详情页URL
            
        Returns:
            房产详细信息
        """
        try:
            logger.info(f"获取房产详情: {house_url}")
            
            if 'lianjia.com' in house_url:
                return self._get_lianjia_details(house_url)
            elif 'ke.com' in house_url:
                return self._get_ke_details(house_url)
            else:
                logger.warning(f"不支持的房产URL: {house_url}")
                return None
                
        except Exception as e:
            logger.error(f"获取房产详情失败: {e}")
            return None
    
    def _get_lianjia_details(self, house_url: str) -> Optional[Dict]:
        """获取链家房产详情"""
        try:
            response = self.session.get(house_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': house_url,
                'site': 'lianjia',
                'crawled_at': datetime.now().isoformat()
            }
            
            # 获取房源ID
            match = re.search(r'/(\d+)\.html', house_url)
            if match:
                details['house_id'] = match.group(1)
            
            # 获取标题
            title_elem = soup.select_one('.title .main')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # 获取总价
            total_price_elem = soup.select_one('.total')
            if total_price_elem:
                total_text = total_price_elem.get_text(strip=True)
                nums = re.findall(r'[\d.]+', total_text)
                if nums:
                    details['total_price'] = float(''.join(nums))
                    details['total_price_unit'] = '万'
            
            # 获取单价
            unit_price_elem = soup.select_one('.unitPriceValue')
            if unit_price_elem:
                unit_text = unit_price_elem.get_text(strip=True)
                nums = re.findall(r'[\d.]+', unit_text)
                if nums:
                    details['unit_price'] = float(''.join(nums))
                    details['unit_price_unit'] = '元/平米'
            
            # 获取基本信息
            base_info = {}
            base_items = soup.select('.base .content li')
            for item in base_items:
                text = item.get_text(strip=True)
                if '：' in text:
                    key, value = text.split('：', 1)
                    base_info[key.strip()] = value.strip()
            
            if base_info:
                details['base_info'] = base_info
            
            # 获取交易属性
            transaction_info = {}
            transaction_items = soup.select('.transaction .content li')
            for item in transaction_items:
                text = item.get_text(strip=True)
                if '：' in text:
                    key, value = text.split('：', 1)
                    transaction_info[key.strip()] = value.strip()
            
            if transaction_info:
                details['transaction_info'] = transaction_info
            
            # 获取房源特色
            feature_elem = soup.select_one('.introContent')
            if feature_elem:
                details['features'] = feature_elem.get_text(strip=True)[:500]  # 限制长度
            
            # 获取小区信息
            community_elem = soup.select_one('.communityName a')
            if community_elem:
                details['community_name'] = community_elem.get_text(strip=True)
            
            # 获取地理位置
            area_elem = soup.select_one('.areaName .info a')
            if area_elem:
                details['district'] = area_elem.get_text(strip=True)
            
            # 获取图片数量
            img_count_elem = soup.select_one('.smallpic li')
            if img_count_elem:
                img_items = soup.select('.smallpic li')
                details['image_count'] = len(img_items)
            
            logger.debug(f"获取到链家房产详情: {details.get('title', '未知标题')}")
            return details
            
        except Exception as e:
            logger.error(f"获取链家详情失败: {e}")
            return None
    
    def _get_ke_details(self, house_url: str) -> Optional[Dict]:
        """获取贝壳房产详情"""
        try:
            response = self.session.get(house_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': house_url,
                'site': 'ke',
                'crawled_at': datetime.now().isoformat()
            }
            
            # 获取房源ID
            match = re.search(r'/(\d+)\.html', house_url)
            if match:
                details['house_id'] = match.group(1)
            
            # 获取标题
            title_elem = soup.select_one('.title .main')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # 获取价格信息
            price_elem = soup.select_one('.price .total')
            if price_elem:
                total_text = price_elem.get_text(strip=True)
                nums = re.findall(r'[\d.]+', total_text)
                if nums:
                    details['total_price'] = float(''.join(nums))
                    details['total_price_unit'] = '万'
            
            # 获取基本信息
            base_info = {}
            base_items = soup.select('.base .content li')
            for item in base_items:
                text = item.get_text(strip=True)
                if '：' in text:
                    key, value = text.split('：', 1)
                    base_info[key.strip()] = value.strip()
            
            if base_info:
                details['base_info'] = base_info
            
            # 获取房源描述
            desc_elem = soup.select_one('.content__article')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)[:500]
            
            # 获取配套设施
            facility_items = soup.select('.content__item')
            if facility_items:
                facilities = []
                for item in facility_items:
                    facilities.append(item.get_text(strip=True))
                details['facilities'] = facilities
            
            logger.debug(f"获取到贝壳房产详情: {details.get('title', '未知标题')}")
            return details
            
        except Exception as e:
            logger.error(f"获取贝壳详情失败: {e}")
            return None
    
    def _get_house_type_name(self, house_type: str) -> str:
        """获取房产类型名称"""
        return {
            'ershoufang': '二手房',
            'zufang': '租房'
        }.get(house_type, '房产')
    
    def analyze_housing_data(self, houses: List[Dict]) -> Dict:
        """
        分析房产数据
        
        Args:
            houses: 房产列表
            
        Returns:
            分析结果
        """
        analysis = {
            'total_houses': len(houses),
            'sites': {},
            'types': {},
            'price_stats': {},
            'city_stats': {}
        }
        
        if not houses:
            return analysis
        
        # 统计网站和类型
        for house in houses:
            site = house.get('site', 'unknown')
            house_type = house.get('type', 'unknown')
            city = house.get('city', 'unknown')
            
            analysis['sites'][site] = analysis['sites'].get(site, 0) + 1
            analysis['types'][house_type] = analysis['types'].get(house_type, 0) + 1
            analysis['city_stats'][city] = analysis['city_stats'].get(city, 0) + 1
        
        # 价格分析
        prices = []
        for house in houses:
            price = house.get('price')
            if price and isinstance(price, (int, float)):
                prices.append(price)
        
        if prices:
            analysis['price_stats']['average'] = sum(prices) / len(prices)
            analysis['price_stats']['max'] = max(prices)
            analysis['price_stats']['min'] = min(prices)
            analysis['price_stats']['median'] = sorted(prices)[len(prices) // 2]
        
        return analysis

def main():
    """主函数"""
    try:
        crawler = RealEstateCrawler()
        
        print("=== 房产信息爬虫 ===")
        print("支持网站: 链家(lianjia), 贝壳(ke)")
        print("支持类型: 二手房(ershoufang), 租房(zufang)")
        print()
        
        print("选择功能:")
        print("1. 搜索房产信息")
        print("2. 获取房产详情")
        print("3. 分析房产数据")
        print("4. 退出")
        
        choice = input("\n请选择功能 (1-4): ").strip()
        
        if choice == '1':
            print("\n选择网站:")
            print("1. 链家 (lianjia)")
            print("2. 贝壳 (ke)")
            
            site_choice = input("请选择 (1-2): ").strip()
            sites = ['lianjia', 'ke']
            
            if site_choice.isdigit() and 1 <= int(site_choice) <= 2:
                site = sites[int(site_choice) - 1]
            else:
                print("无效选择，使用默认: 链家")
                site = 'lianjia'
            
            print("\n选择房产类型:")
            print("1. 二手房")
            print("2. 租房")
            
            type_choice = input("请选择 (1-2): ").strip()
            types = ['ershoufang', 'zufang']
            
            if type_choice.isdigit() and 1 <= int(type_choice) <= 2:
                house_type = types[int(type_choice) - 1]
            else:
                print("无效选择，使用默认: 二手房")
                house_type = 'ershoufang'
            
            city = input("请输入城市名称 (例如: 北京, 上海): ").strip()
            if not city:
                print("城市不能为空")
                return
            
            page = input("页码 (默认1): ").strip()
            page = int(page) if page.isdigit() else 1
            
            max_results = input("最大结果数 (默认20): ").strip()
            max_results = int(max_results) if max_results.isdigit() else 20
            
            print(f"\n正在搜索 {site} 的{crawler._get_house_type_name(house_type)}信息...")
            houses = crawler.search_houses(site, city, house_type, page, max_results)
            
            if houses:
                type_name = crawler._get_house_type_name(house_type)
                print(f"\n找到 {len(houses)} 个{type_name}房源:")
                
                for i, house in enumerate(houses[:10], 1):
                    title = house.get('title', '无标题')
                    price = house.get('price', 0)
                    unit = house.get('price_unit', '')
                    
                    print(f"{i}. {title[:40]}...")
                    print(f"   价格: {price} {unit}")
                    
                    if 'position' in house:
                        print(f"   位置: {house['position']}")
                    elif 'district' in house:
                        print(f"   地区: {house.get('district', '未知')}")
                    
                    if 'info' in house:
                        print(f"   信息: {house['info'][:50]}...")
                    print()
                
                # 保存搜索结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'realestate_{site}_{house_type}_{city}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(houses, f, ensure_ascii=False, indent=2)
                print(f"搜索结果已保存到: {filename}")
            else:
                print("未找到相关房源")
                
        elif choice == '2':
            url = input("请输入房产详情页URL: ").strip()
            if url:
                details = crawler.get_house_details(url)
                
                if details:
                    print(f"\n=== 房产详情 ===")
                    print(f"网站: {details.get('site', '未知')}")
                    print(f"标题: {details.get('title', '无标题')}")
                    
                    if 'total_price' in details:
                        print(f"总价: {details['total_price']} {details.get('total_price_unit', '')}")
                    
                    if 'unit_price' in details:
                        print(f"单价: {details['unit_price']} {details.get('unit_price_unit', '')}")
                    
                    # 显示基本信息
                    if 'base_info' in details:
                        print(f"\n基本信息:")
                        for key, value in details['base_info'].items():
                            print(f"  {key}: {value}")
                    
                    # 显示交易信息
                    if 'transaction_info' in details:
                        print(f"\n交易信息:")
                        for key, value in details['transaction_info'].items():
                            print(f"  {key}: {value}")
                    
                    # 显示其他信息
                    if 'district' in details:
                        print(f"地区: {details['district']}")
                    
                    if 'community_name' in details:
                        print(f"小区: {details['community_name']}")
                    
                    if 'image_count' in details:
                        print(f"图片数量: {details['image_count']}")
                    
                    # 保存详情
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    house_id = details.get('house_id', 'unknown')
                    filename = f'house_details_{house_id}_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(details, f, ensure_ascii=False, indent=2)
                    print(f"\n详情已保存到: {filename}")
                else:
                    print("获取房产详情失败")
            else:
                print("URL不能为空")
                
        elif choice == '3':
            # 先搜索一些数据进行分析
            city = input("请输入城市名称 (默认北京): ").strip() or '北京'
            house_type = input("请输入房产类型 (ershoufang/zufang, 默认ershoufang): ").strip() or 'ershoufang'
            
            print(f"\n正在获取 {city} 的{house_type}数据进行分析...")
            houses = crawler.search_houses('lianjia', city, house_type, max_results=50)
            
            if houses:
                analysis = crawler.analyze_housing_data(houses)
                
                print(f"\n=== 房产数据分析 ===")
                print(f"总房源数: {analysis['total_houses']}")
                
                if 'sites' in analysis:
                    print(f"网站分布: {analysis['sites']}")
                
                if 'types' in analysis:
                    type_names = {
                        'ershoufang': '二手房',
                        'zufang': '租房'
                    }
                    types_data = {}
                    for key, value in analysis['types'].items():
                        types_data[type_names.get(key, key)] = value
                    print(f"类型分布: {types_data}")
                
                if 'city_stats' in analysis:
                    print(f"城市分布: {analysis['city_stats']}")
                
                if 'price_stats' in analysis:
                    print(f"\n价格统计:")
                    for key, value in analysis['price_stats'].items():
                        if key == 'average':
                            print(f"  平均价格: {value:,.2f} 万")
                        elif key == 'median':
                            print(f"  中位数价格: {value:,.2f} 万")
                        elif key == 'max':
                            print(f"  最高价格: {value:,.2f} 万")
                        elif key == 'min':
                            print(f"  最低价格: {value:,.2f} 万")
                
                # 保存分析结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'realestate_analysis_{city}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                print(f"\n分析结果已保存到: {filename}")
            else:
                print("无房产数据可分析")
                
        elif choice == '4':
            print("退出程序")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()