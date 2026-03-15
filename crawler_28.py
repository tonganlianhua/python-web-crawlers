#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房地产数据爬虫 - 链家二手房数据
爬取链家网站的二手房信息：价格、面积、户型、楼层、朝向、小区等
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import csv
import os
from bs4 import BeautifulSoup
import html

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SecondHandHouse:
    """二手房数据结构"""
    title: str
    url: str
    total_price: float  # 总价（万元）
    unit_price: float  # 单价（元/平米）
    area: float  # 面积（平米）
    room_type: str  # 户型（如：3室2厅1卫）
    floor: str  # 楼层（如：中楼层/18层）
    orientation: str  # 朝向（如：南向）
    decoration: str  # 装修（精装/简装/毛坯）
    age: int  # 建筑年代（年）
    community: str  # 小区名称
    district: str  # 行政区
    subdistrict: str  # 街道/板块
    publish_date: str  # 发布时间
    house_type: str  # 房屋类型（住宅/公寓/别墅等）
    has_elevator: bool  # 是否有电梯
    property_right: str  # 产权性质
    subway_info: str  # 地铁信息
    school_info: str  # 学校信息
    image_url: str  # 房屋图片


class LianjiaCrawler:
    """链家二手房爬虫类"""
    
    def __init__(self):
        self.base_url = "https://bj.lianjia.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 城市映射（链家支持的城市）
        self.cities = {
            'bj': '北京',
            'sh': '上海',
            'sz': '深圳',
            'gz': '广州',
            'cd': '成都',
            'cq': '重庆',
            'hz': '杭州',
            'nj': '南京',
            'tj': '天津',
            'wh': '武汉',
            'xa': '西安',
            'cs': '长沙',
            'su': '苏州',
            'qd': '青岛',
            'xm': '厦门'
        }
        
        # 北京行政区划
        self.beijing_districts = {
            'dongcheng': '东城',
            'xicheng': '西城',
            'chaoyang': '朝阳',
            'haidian': '海淀',
            'fengtai': '丰台',
            'shijingshan': '石景山',
            'tongzhou': '通州',
            'changping': '昌平',
            'daxing': '大兴',
            'yizhuangkaifaqu': '亦庄开发区',
            'shunyi': '顺义',
            'fangshan': '房山',
            'mentougou': '门头沟',
            'pinggu': '平谷',
            'huairou': '怀柔',
            'miyun': '密云',
            'yanqing': '延庆'
        }
    
    def get_houses_by_city(self, city: str = 'bj', limit: int = 30) -> List[SecondHandHouse]:
        """
        获取城市二手房列表
        
        Args:
            city: 城市代码（默认北京）
            limit: 获取数量
            
        Returns:
            房屋对象列表
        """
        houses = []
        page = 1
        
        try:
            city_name = self.cities.get(city, '北京')
            logger.info(f"正在获取 {city_name} 二手房，数量: {limit}")
            
            while len(houses) < limit:
                # 构建URL
                url = f"{self.base_url.replace('bj', city)}/ershoufang"
                params = {'pg': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找房屋列表
                house_elements = soup.select('.sellListContent li')
                
                if not house_elements:
                    # 尝试其他选择器
                    house_elements = soup.select('.listContent .info, .house-list .item')
                
                if not house_elements:
                    logger.warning("未找到房屋元素，可能页面结构已变化")
                    break
                
                # 解析每个房屋
                new_houses = 0
                for element in house_elements:
                    if len(houses) >= limit:
                        break
                    
                    house = self._parse_house_element(element, city)
                    if house:
                        houses.append(house)
                        new_houses += 1
                
                if new_houses == 0:
                    logger.info(f"第 {page} 页没有新房屋，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_houses} 个房屋，总计 {len(houses)} 个")
                page += 1
                
                # 避免请求过快
                time.sleep(2)
            
            logger.info(f"成功获取 {len(houses)} 个二手房信息")
            return houses
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析房屋失败: {e}")
            return []
    
    def _parse_house_element(self, element, city: str) -> Optional[SecondHandHouse]:
        """解析房屋HTML元素"""
        try:
            # 提取标题和链接
            title_element = element.select_one('.title a')
            if not title_element:
                return None
            
            title = title_element.get_text(strip=True)
            house_url = title_element['href']
            
            if not title or not house_url:
                return None
            
            # 提取价格信息
            price_element = element.select_one('.totalPrice')
            total_price = 0.0
            if price_element:
                price_text = price_element.get_text(strip=True)
                match = re.search(r'[\d.]+', price_text)
                if match:
                    total_price = float(match.group())
            
            # 提取单价
            unit_price_element = element.select_one('.unitPrice')
            unit_price = 0.0
            if unit_price_element:
                unit_price_text = unit_price_element.get_text(strip=True)
                match = re.search(r'[\d,]+', unit_price_text)
                if match:
                    unit_price = float(match.group(0).replace(',', ''))
            
            # 提取房屋信息（户型、面积、楼层、朝向等）
            house_info_element = element.select_one('.houseInfo')
            house_info = house_info_element.get_text(strip=True) if house_info_element else ''
            
            # 解析房屋信息字符串
            room_type, area, orientation, floor, decoration, age = self._parse_house_info(house_info)
            
            # 提取小区信息
            community_element = element.select_one('.positionInfo a')
            community = community_element.get_text(strip=True) if community_element else ''
            
            # 提取位置信息
            position_element = element.select_one('.positionInfo')
            position_info = position_element.get_text(strip=True) if position_element else ''
            
            # 解析位置信息
            district, subdistrict = self._parse_position_info(position_info, community)
            
            # 提取发布时间
            follow_element = element.select_one('.followInfo')
            publish_date = ''
            if follow_element:
                follow_text = follow_element.get_text(strip=True)
                # 尝试提取日期
                date_match = re.search(r'(\d+天前|\d+个月前|今天|昨天|\d{4}-\d{2}-\d{2})', follow_text)
                if date_match:
                    publish_date = date_match.group(1)
            
            # 提取图片
            image_element = element.select_one('img')
            image_url = image_element['src'] if image_element and image_element.get('src') else ''
            
            # 获取房屋详细信息
            house_type, has_elevator, property_right, subway_info, school_info = self._get_house_details(house_url)
            
            house = SecondHandHouse(
                title=html.unescape(title),
                url=house_url,
                total_price=total_price,
                unit_price=unit_price,
                area=area,
                room_type=room_type,
                floor=floor,
                orientation=orientation,
                decoration=decoration,
                age=age,
                community=html.unescape(community),
                district=html.unescape(district),
                subdistrict=html.unescape(subdistrict),
                publish_date=publish_date,
                house_type=house_type,
                has_elevator=has_elevator,
                property_right=property_right,
                subway_info=subway_info,
                school_info=school_info,
                image_url=image_url
            )
            
            return house
            
        except Exception as e:
            logger.warning(f"解析房屋元素失败: {e}")
            return None
    
    def _parse_house_info(self, house_info: str) -> Tuple[str, float, str, str, str, int]:
        """解析房屋信息字符串"""
        room_type = '未知'
        area = 0.0
        orientation = '未知'
        floor = '未知'
        decoration = '未知'
        age = 0
        
        try:
            # 链家房屋信息格式通常为："3室2厅 | 89平米 | 南向 | 中楼层/18层 | 精装 | 2015年建"
            parts = [p.strip() for p in house_info.split('|') if p.strip()]
            
            for part in parts:
                if '室' in part and '厅' in part:
                    room_type = part.strip()
                elif '平米' in part:
                    match = re.search(r'([\d.]+)平米', part)
                    if match:
                        area = float(match.group(1))
                elif '向' in part:
                    orientation = part.strip()
                elif '层' in part:
                    floor = part.strip()
                elif '装' in part:
                    decoration = part.strip()
                elif '年建' in part or '年' in part:
                    match = re.search(r'(\d{4})年', part)
                    if match:
                        age = int(match.group(1))
                    else:
                        # 计算建筑年代
                        current_year = datetime.now().year
                        match = re.search(r'(\d+)年', part)
                        if match:
                            age = current_year - int(match.group(1))
        
        except Exception as e:
            logger.warning(f"解析房屋信息失败: {e}")
        
        return room_type, area, orientation, floor, decoration, age
    
    def _parse_position_info(self, position_info: str, community: str) -> Tuple[str, str]:
        """解析位置信息"""
        district = '未知'
        subdistrict = '未知'
        
        try:
            # 链家位置信息格式通常为："小区名 - 板块 - 行政区"
            # 或者："板块 - 行政区"
            
            # 先尝试按分隔符分割
            if ' - ' in position_info:
                parts = [p.strip() for p in position_info.split(' - ') if p.strip()]
                if len(parts) >= 2:
                    # 最后一部分通常是行政区
                    district = parts[-1]
                    # 倒数第二部分通常是板块
                    if len(parts) >= 3:
                        subdistrict = parts[-2]
                    else:
                        subdistrict = parts[-1]  # 如果没有板块信息，使用行政区
            
            # 如果分割失败，尝试从社区名中提取
            if district == '未知' and community:
                # 检查是否包含行政区信息
                for dname in self.beijing_districts.values():
                    if dname in community:
                        district = dname
                        break
        
        except Exception as e:
            logger.warning(f"解析位置信息失败: {e}")
        
        return district, subdistrict
    
    def _get_house_details(self, url: str) -> Tuple[str, bool, str, str, str]:
        """获取房屋详细信息"""
        house_type = '住宅'
        has_elevator = False
        property_right = '商品房'
        subway_info = ''
        school_info = ''
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取基本信息
            base_info_section = soup.select_one('.base, .introContent .base')
            if base_info_section:
                rows = base_info_section.select('.row')
                for row in rows:
                    label = row.select_one('.label')
                    content = row.select_one('.content')
                    
                    if label and content:
                        label_text = label.get_text(strip=True)
                        content_text = content.get_text(strip=True)
                        
                        if label_text == '房屋用途':
                            house_type = content_text
                        elif label_text == '产权所属':
                            property_right = content_text
                        elif label_text == '电梯':
                            has_elevator = '有' in content_text
            
            # 提取交通信息
            subway_section = soup.select_one('.aroundInfo, .transport')
            if subway_section:
                subway_items = subway_section.select('.item')
                subway_lines = []
                for item in subway_items:
                    item_text = item.get_text(strip=True)
                    if '地铁' in item_text:
                        subway_lines.append(item_text)
                
                if subway_lines:
                    subway_info = '; '.join(subway_lines[:3])
            
            # 提取学校信息
            school_section = soup.select_one('.schoolInfo, .education')
            if school_section:
                school_items = school_section.select('.item')
                schools = []
                for item in school_items:
                    item_text = item.get_text(strip=True)
                    if '小学' in item_text or '中学' in item_text or '幼儿园' in item_text:
                        schools.append(item_text)
                
                if schools:
                    school_info = '; '.join(schools[:3])
        
        except Exception as e:
            logger.warning(f"获取房屋详情失败 {url}: {e}")
        
        return house_type, has_elevator, property_right, subway_info, school_info
    
    def search_houses(self, city: str = 'bj', **filters) -> List[SecondHandHouse]:
        """
        搜索二手房
        
        Args:
            city: 城市代码
            filters: 筛选条件（价格、面积、户型等）
            
        Returns:
            房屋对象列表
        """
        url = f"{self.base_url.replace('bj', city)}/ershoufang"
        
        # 构建查询参数
        params = {}
        
        # 价格筛选
        if 'price_min' in filters and 'price_max' in filters:
            price_min = filters['price_min']
            price_max = filters['price_max']
            # 链家价格区间参数
            params['bp'] = f'{price_min}ep{price_max}'
        
        # 面积筛选
        if 'area_min' in filters and 'area_max' in filters:
            area_min = filters['area_min']
            area_max = filters['area_max']
            params['ba'] = f'{area_min}ea{area_max}'
        
        # 户型筛选
        if 'room_type' in filters:
            # 链家户型参数：l1=1室，l2=2室，l3=3室，l4=4室，l5=5室+
            room_type = filters['room_type']
            if room_type == '1':
                params['l1'] = 'on'
            elif room_type == '2':
                params['l2'] = 'on'
            elif room_type == '3':
                params['l3'] = 'on'
            elif room_type == '4':
                params['l4'] = 'on'
            elif room_type == '5':
                params['l5'] = 'on'
        
        # 行政区筛选
        if 'district' in filters:
            district_en = ''
            for en, cn in self.beijing_districts.items():
                if cn == filters['district']:
                    district_en = en
                    break
            
            if district_en:
                params['g'] = district_en
        
        try:
            logger.info(f"正在搜索二手房，条件: {filters}")
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            houses = []
            house_elements = soup.select('.sellListContent li')
            
            for element in house_elements[:30]:  # 最多30个结果
                house = self._parse_house_element(element, city)
                if house:
                    houses.append(house)
            
            logger.info(f"搜索到 {len(houses)} 个符合条件的房屋")
            return houses
            
        except Exception as e:
            logger.error(f"搜索房屋失败: {e}")
            return []
    
    def analyze_houses(self, houses: List[SecondHandHouse]) -> Dict:
        """
        分析房屋数据
        
        Args:
            houses: 房屋对象列表
            
        Returns:
            分析结果字典
        """
        if not houses:
            return {}
        
        try:
            # 统计信息
            total_houses = len(houses)
            
            # 价格统计
            total_prices = [h.total_price for h in houses if h.total_price > 0]
            unit_prices = [h.unit_price for h in houses if h.unit_price > 0]
            areas = [h.area for h in houses if h.area > 0]
            
            avg_total_price = sum(total_prices) / len(total_prices) if total_prices else 0
            avg_unit_price = sum(unit_prices) / len(unit_prices) if unit_prices else 0
            avg_area = sum(areas) / len(areas) if areas else 0
            
            # 价格区间统计
            price_ranges = {
                '100万以下': 0,
                '100-200万': 0,
                '200-300万': 0,
                '300-500万': 0,
                '500-800万': 0,
                '800-1000万': 0,
                '1000万以上': 0
            }
            
            for house in houses:
                price = house.total_price
                if price < 100:
                    price_ranges['100万以下'] += 1
                elif price < 200:
                    price_ranges['100-200万'] += 1
                elif price < 300:
                    price_ranges['200-300万'] += 1
                elif price < 500:
                    price_ranges['300-500万'] += 1
                elif price < 800:
                    price_ranges['500-800万'] += 1
                elif price < 1000:
                    price_ranges['800-1000万'] += 1
                else:
                    price_ranges['1000万以上'] += 1
            
            # 户型统计
            room_type_counts = {}
            for house in houses:
                room_type = house.room_type
                if room_type != '未知':
                    room_type_counts[room_type] = room_type_counts.get(room_type, 0) + 1
            
            top_room_types = sorted(room_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 行政区统计
            district_counts = {}
            for house in houses:
                district = house.district
                if district != '未知':
                    district_counts[district] = district_counts.get(district, 0) + 1
            
            top_districts = sorted(district_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 朝向统计
            orientation_counts = {}
            for house in houses:
                orientation = house.orientation
                if orientation != '未知':
                    orientation_counts[orientation] = orientation_counts.get(orientation, 0) + 1
            
            top_orientations = sorted(orientation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 楼龄统计
            age_ranges = {
                '5年以内': 0,
                '5-10年': 0,
                '10-15年': 0,
                '15-20年': 0,
                '20年以上': 0
            }
            
            for house in houses:
                age = house.age
                if age == 0:
                    continue
                
                if age <= 5:
                    age_ranges['5年以内'] += 1
                elif age <= 10:
                    age_ranges['5-10年'] += 1
                elif age <= 15:
                    age_ranges['10-15年'] += 1
                elif age <= 20:
                    age_ranges['15-20年'] += 1
                else:
                    age_ranges['20年以上'] += 1
            
            # 最贵和最便宜的房屋
            if houses:
                sorted_by_price = sorted(houses, key=lambda x: x.total_price, reverse=True)
                most_expensive = sorted_by_price[0] if sorted_by_price else None
                cheapest = sorted_by_price[-1] if sorted_by_price else None
                
                sorted_by_unit_price = sorted(houses, key=lambda x: x.unit_price, reverse=True)
                highest_unit_price = sorted_by_unit_price[0] if sorted_by_unit_price else None
                lowest_unit_price = sorted_by_unit_price[-1] if sorted_by_unit_price else None
            else:
                most_expensive = cheapest = highest_unit_price = lowest_unit_price = None
            
            return {
                'total_houses': total_houses,
                'avg_total_price': avg_total_price,
                'avg_unit_price': avg_unit_price,
                'avg_area': avg_area,
                'price_distribution': price_ranges,
                'top_room_types': top_room_types,
                'top_districts': top_districts,
                'top_orientations': top_orientations,
                'age_distribution': age_ranges,
                'most_expensive': (most_expensive.title[:30], most_expensive.total_price) if most_expensive else None,
                'cheapest': (cheapest.title[:30], cheapest.total_price) if cheapest else None,
                'highest_unit_price': (highest_unit_price.title[:30], highest_unit_price.unit_price) if highest_unit_price else None,
                'lowest_unit_price': (lowest_unit_price.title[:30], lowest_unit_price.unit_price) if lowest_unit_price else None
            }
            
        except Exception as e:
            logger.error(f"分析房屋数据失败: {e}")
            return {}
    
    def save_to_csv(self, houses: List[SecondHandHouse], filename: str = "secondhand_houses.csv"):
        """
        保存房屋数据到CSV文件
        
        Args:
            houses: 房屋对象列表
            filename: 输出文件名
        """
        if not houses:
            logger.warning("没有房屋数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'title', 'url', 'total_price', 'unit_price', 'area', 'room_type',
                    'floor', 'orientation', 'decoration', 'age', 'community',
                    'district', 'subdistrict', 'publish_date', 'house_type',
                    'has_elevator', 'property_right', 'subway_info', 'school_info',
                    'image_url'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for house in houses:
                    row = house.__dict__.copy()
                    # 转换布尔值为字符串
                    row['has_elevator'] = '是' if row['has_elevator'] else '否'
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(houses)} 个房屋数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("链家二手房数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = LianjiaCrawler()
    
    try:
        # 1. 显示支持的城市
        print("支持的城市:")
        print("-" * 30)
        for i, (code, name) in enumerate(crawler.cities.items(), 1):
            print(f"  {code}: {name}", end='  ')
            if i % 3 == 0:
                print()
        print()
        
        # 2. 选择城市
        city_choice = input("请输入城市代码（直接回车使用北京）: ").strip().lower()
        
        if not city_choice or city_choice not in crawler.cities:
            city_choice = 'bj'
            print(f"使用默认城市: {crawler.cities[city_choice]}")
        
        # 3. 获取二手房数据
        print(f"\n正在爬取 {crawler.cities[city_choice]} 二手房数据...")
        houses = crawler.get_houses_by_city(city_choice, limit=25)
        
        if not houses:
            print("未获取到房屋数据，程序退出")
            return
        
        # 4. 显示统计信息
        print(f"\n成功获取 {len(houses)} 套二手房:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_houses(houses)
        
        if analysis:
            print(f"总计房屋: {analysis['total_houses']}")
            print(f"平均总价: {analysis['avg_total_price']:.1f} 万元")
            print(f"平均单价: {analysis['avg_unit_price']:.0f} 元/平米")
            print(f"平均面积: {analysis['avg_area']:.1f} 平米")
            
            if analysis['top_districts']:
                print("\n热门行政区:")
                for district, count in analysis['top_districts']:
                    print(f"  {district}: {count} 套")
            
            if analysis['price_distribution']:
                print("\n价格分布:")
                for price_range, count in analysis['price_distribution'].items():
                    if count > 0:
                        print(f"  {price_range}: {count} 套")
        
        # 5. 显示前5套房屋详情
        print("\n最新房源 TOP 5:")
        print("-" * 30)
        for i, house in enumerate(houses[:5], 1):
            print(f"{i}. {house.title}")
            print(f"   总价: {house.total_price:.1f}万, 单价: {house.unit_price:.0f}元/平米")
            print(f"   面积: {house.area:.1f}平米, 户型: {house.room_type}")
            print(f"   楼层: {house.floor}, 朝向: {house.orientation}")
            print(f"   小区: {house.community}, 区域: {house.district}")
            print()
        
        # 6. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        city_name = crawler.cities[city_choice]
        csv_file = f"secondhand_houses_{city_name}_{timestamp}.csv"
        
        crawler.save_to_csv(houses, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 7. 展示一套房屋的详细内容
        if houses:
            sample_house = houses[0]
            print(f"\n房屋 '{sample_house.title[:20]}...' 的详细内容:")
            print("-" * 30)
            
            print(f"基本信息:")
            print(f"  总价: {sample_house.total_price:.1f} 万元")
            print(f"  单价: {sample_house.unit_price:.0f} 元/平米")
            print(f"  面积: {sample_house.area:.1f} 平米")
            print(f"  户型: {sample_house.room_type}")
            print(f"  楼层: {sample_house.floor}")
            print(f"  朝向: {sample_house.orientation}")
            print(f"  装修: {sample_house.decoration}")
            print(f"  楼龄: {sample_house.age} 年")
            
            print(f"\n位置信息:")
            print(f"  小区: {sample_house.community}")
            print(f"  行政区: {sample_house.district}")
            print(f"  板块: {sample_house.subdistrict}")
            
            print(f"\n其他信息:")
            print(f"  房屋类型: {sample_house.house_type}")
            print(f"  是否有电梯: {'是' if sample_house.has_elevator else '否'}")
            print(f"  产权性质: {sample_house.property_right}")
            print(f"  发布时间: {sample_house.publish_date}")
            
            if sample_house.subway_info:
                print(f"  地铁信息: {sample_house.subway_info}")
            
            if sample_house.school_info:
                print(f"  学校信息: {sample_house.school_info}")
        
        # 8. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示筛选搜索功能:")
        
        print("可选筛选条件:")
        print("  1. 价格范围 (例如: 300-500)")
        print("  2. 面积范围 (例如: 80-100)")
        print("  3. 户型 (例如: 3)")
        print("  4. 行政区 (北京地区)")
        
        filters = {}
        
        # 价格筛选
        price_input = input("请输入价格范围 (如: 300-500，直接回车跳过): ").strip()
        if price_input and '-' in price_input:
            try:
                price_min, price_max = price_input.split('-')
                filters['price_min'] = int(price_min)
                filters['price_max'] = int(price_max)
            except:
                print("价格格式错误，跳过价格筛选")
        
        # 面积筛选
        area_input = input("请输入面积范围 (如: 80-100，直接回车跳过): ").strip()
        if area_input and '-' in area_input:
            try:
                area_min, area_max = area_input.split('-')
                filters['area_min'] = int(area_min)
                filters['area_max'] = int(area_max)
            except:
                print("面积格式错误，跳过面积筛选")
        
        # 户型筛选
        room_input = input("请输入户型 (1-5，直接回车跳过): ").strip()
        if room_input and room_input in ['1', '2', '3', '4', '5']:
            filters['room_type'] = room_input
        
        # 行政区筛选（仅限北京）
        if city_choice == 'bj':
            print("北京行政区:", ', '.join(crawler.beijing_districts.values()))
            district_input = input("请输入行政区 (直接回车跳过): ").strip()
            if district_input and district_input in crawler.beijing_districts.values():
                filters['district'] = district_input
        
        if filters:
            print(f"\n正在根据条件搜索: {filters}")
            search_results = crawler.search_houses(city_choice, **filters)
            
            if search_results:
                print(f"找到 {len(search_results)} 个符合条件的房屋:")
                for i, house in enumerate(search_results[:5], 1):
                    print(f"{i}. {house.title}")
                    print(f"   总价: {house.total_price:.1f}万, 面积: {house.area:.1f}平米")
                    print(f"   户型: {house.room_type}, 区域: {house.district}")
            else:
                print("未找到符合条件的房屋")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()