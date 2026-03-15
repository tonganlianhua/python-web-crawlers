#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汽车信息爬虫 - 汽车之家车型数据
爬取汽车之家网站的车型信息：价格、配置、参数、评测等
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
class CarModel:
    """汽车车型数据结构"""
    name: str
    url: str
    brand: str  # 品牌
    series: str  # 车系
    price_range: str  # 价格范围
    min_price: float  # 最低价（万元）
    max_price: float  # 最高价（万元）
    car_type: str  # 车型（SUV、轿车、MPV等）
    fuel_type: str  # 燃料类型（汽油、电动、混动等）
    transmission: str  # 变速箱（手动、自动等）
    engine: str  # 发动机
    horsepower: int  # 马力（匹）
    torque: float  # 扭矩（牛米）
    length: float  # 车长（mm）
    width: float  # 车宽（mm）
    height: float  # 车高（mm）
    wheelbase: float  # 轴距（mm）
    fuel_consumption: float  # 油耗（L/100km）
    seating_capacity: int  # 座位数
    release_year: int  # 上市年份
    image_url: str  # 车型图片
    rating: float  # 评分（0-5）


class AutohomeCrawler:
    """汽车之家爬虫类"""
    
    def __init__(self):
        self.base_url = "https://www.autohome.com.cn"
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
        
        # 汽车品牌映射
        self.car_brands = {
            'audi': '奥迪',
            'bmw': '宝马',
            'benz': '奔驰',
            'vw': '大众',
            'toyota': '丰田',
            'honda': '本田',
            'nissan': '日产',
            'hyundai': '现代',
            'ford': '福特',
            'chevrolet': '雪佛兰',
            'buick': '别克',
            'changan': '长安',
            'geely': '吉利',
            'byd': '比亚迪',
            'greatwall': '长城'
        }
        
        # 车型分类
        self.car_types = {
            'suv': 'SUV',
            'sedan': '轿车',
            'mpv': 'MPV',
            'sports': '跑车',
            'ev': '新能源',
            'pickup': '皮卡'
        }
    
    def get_popular_cars(self, car_type: str = None, limit: int = 30) -> List[CarModel]:
        """
        获取热门车型
        
        Args:
            car_type: 车型分类（可选）
            limit: 获取数量
            
        Returns:
            车型对象列表
        """
        cars = []
        page = 1
        
        try:
            type_name = self.car_types.get(car_type, '全部') if car_type else '全部'
            logger.info(f"正在获取 {type_name} 车型，数量: {limit}")
            
            while len(cars) < limit:
                # 构建URL
                if car_type and car_type in self.car_types:
                    url = f"{self.base_url}/{car_type}/"
                else:
                    url = f"{self.base_url}/car/"
                
                params = {'page': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找车型列表
                car_elements = soup.select('.cartab, .list-item, .car-card')
                
                if not car_elements:
                    # 尝试其他选择器
                    car_elements = soup.select('.uibox, .row .col')
                
                if not car_elements:
                    logger.warning("未找到车型元素，可能页面结构已变化")
                    break
                
                # 解析每个车型
                new_cars = 0
                for element in car_elements:
                    if len(cars) >= limit:
                        break
                    
                    car = self._parse_car_element(element)
                    if car:
                        cars.append(car)
                        new_cars += 1
                
                if new_cars == 0:
                    logger.info(f"第 {page} 页没有新车型，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_cars} 个车型，总计 {len(cars)} 个")
                page += 1
                
                # 避免请求过快
                time.sleep(2)
            
            logger.info(f"成功获取 {len(cars)} 个车型信息")
            return cars
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析车型失败: {e}")
            return []
    
    def _parse_car_element(self, element) -> Optional[CarModel]:
        """解析车型HTML元素"""
        try:
            # 提取车型名称
            name_element = element.select_one('.title, h3, .cartab-title')
            name = name_element.get_text(strip=True) if name_element else ''
            
            if not name:
                return None
            
            # 提取链接
            link_element = element.select_one('a')
            if not link_element or not link_element.get('href'):
                return None
            
            car_url = link_element['href']
            if not car_url.startswith('http'):
                car_url = self.base_url + car_url
            
            # 提取品牌和车系
            brand, series = self._extract_brand_series(name)
            
            # 提取价格信息
            price_element = element.select_one('.price, .price-range, .cost')
            price_range = price_element.get_text(strip=True) if price_element else '未知'
            
            # 解析价格范围
            min_price, max_price = self._parse_price_range(price_range)
            
            # 提取车型图片
            image_element = element.select_one('img')
            image_url = image_element['src'] if image_element and image_element.get('src') else ''
            
            # 提取基本参数
            param_elements = element.select('.param, .info-item, .spec')
            engine = ''
            transmission = ''
            car_type_name = '未知'
            fuel_type = '未知'
            
            for param in param_elements:
                param_text = param.get_text(strip=True)
                if '发动机' in param_text:
                    engine = param_text.replace('发动机', '').strip()
                elif '变速箱' in param_text:
                    transmission = param_text.replace('变速箱', '').strip()
                elif '车型' in param_text:
                    car_type_name = param_text.replace('车型', '').strip()
                elif '燃料' in param_text or '能源' in param_text:
                    fuel_type = param_text
            
            # 获取车型详细信息
            horsepower, torque, dimensions, fuel_consumption, seating_capacity, release_year, rating = self._get_car_details(car_url)
            
            # 解析尺寸
            length, width, height, wheelbase = dimensions
            
            car = CarModel(
                name=html.unescape(name),
                url=car_url,
                brand=brand,
                series=series,
                price_range=price_range,
                min_price=min_price,
                max_price=max_price,
                car_type=car_type_name,
                fuel_type=fuel_type,
                transmission=transmission,
                engine=engine,
                horsepower=horsepower,
                torque=torque,
                length=length,
                width=width,
                height=height,
                wheelbase=wheelbase,
                fuel_consumption=fuel_consumption,
                seating_capacity=seating_capacity,
                release_year=release_year,
                image_url=image_url,
                rating=rating
            )
            
            return car
            
        except Exception as e:
            logger.warning(f"解析车型元素失败: {e}")
            return None
    
    def _extract_brand_series(self, name: str) -> Tuple[str, str]:
        """从车型名称中提取品牌和车系"""
        brand = '未知'
        series = name
        
        # 检查常见品牌
        for brand_en, brand_cn in self.car_brands.items():
            if brand_cn in name:
                brand = brand_cn
                # 尝试提取车系（通常是品牌后的部分）
                parts = name.split(brand_cn)
                if len(parts) > 1 and parts[1].strip():
                    series = parts[1].strip()
                break
        
        return brand, series
    
    def _parse_price_range(self, price_range: str) -> Tuple[float, float]:
        """解析价格范围字符串"""
        min_price = 0.0
        max_price = 0.0
        
        try:
            # 处理各种价格格式
            if '万' in price_range:
                # 去除"万"和"起"等字符
                clean_text = price_range.replace('万', '').replace('起', '').replace('售价', '').strip()
                
                if '-' in clean_text:
                    parts = clean_text.split('-')
                    if len(parts) == 2:
                        min_price = float(parts[0])
                        max_price = float(parts[1])
                else:
                    # 单一价格
                    match = re.search(r'[\d.]+', clean_text)
                    if match:
                        price = float(match.group())
                        min_price = price
                        max_price = price
            elif price_range == '未知':
                min_price = 0.0
                max_price = 0.0
            else:
                # 尝试直接提取数字
                numbers = re.findall(r'[\d.]+', price_range)
                if len(numbers) >= 2:
                    min_price = float(numbers[0])
                    max_price = float(numbers[1])
                elif len(numbers) == 1:
                    min_price = max_price = float(numbers[0])
        
        except Exception as e:
            logger.warning(f"解析价格范围失败 {price_range}: {e}")
        
        return min_price, max_price
    
    def _get_car_details(self, url: str) -> Tuple[int, float, Tuple[float, float, float, float], float, int, int, float]:
        """获取车型详细信息"""
        horsepower = 0
        torque = 0.0
        dimensions = (0.0, 0.0, 0.0, 0.0)  # 长, 宽, 高, 轴距
        fuel_consumption = 0.0
        seating_capacity = 5
        release_year = datetime.now().year
        rating = 0.0
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取动力参数
            power_section = soup.select_one('.power, .engine-info')
            if power_section:
                # 查找马力和扭矩
                power_text = power_section.get_text()
                
                # 马力
                hp_match = re.search(r'(\d+)\s*匹|马力\s*(\d+)', power_text)
                if hp_match:
                    for group in hp_match.groups():
                        if group:
                            horsepower = int(group)
                            break
                
                # 扭矩
                torque_match = re.search(r'(\d+)\s*牛米|扭矩\s*(\d+)', power_text)
                if torque_match:
                    for group in torque_match.groups():
                        if group:
                            torque = float(group)
                            break
            
            # 提取尺寸参数
            size_section = soup.select_one('.size, .dimensions')
            if size_section:
                size_text = size_section.get_text()
                
                # 长宽高轴距
                numbers = re.findall(r'[\d.]+', size_text)
                if len(numbers) >= 4:
                    try:
                        dimensions = (
                            float(numbers[0]),  # 长
                            float(numbers[1]),  # 宽
                            float(numbers[2]),  # 高
                            float(numbers[3])   # 轴距
                        )
                    except:
                        pass
            
            # 提取油耗
            fuel_section = soup.select_one('.fuel, .consumption')
            if fuel_section:
                fuel_text = fuel_section.get_text()
                match = re.search(r'([\d.]+)\s*L/100km|油耗\s*([\d.]+)', fuel_text)
                if match:
                    for group in match.groups():
                        if group:
                            fuel_consumption = float(group)
                            break
            
            # 提取座位数
            seat_section = soup.select_one('.seats, .capacity')
            if seat_section:
                seat_text = seat_section.get_text()
                match = re.search(r'(\d+)\s*座|座位数\s*(\d+)', seat_text)
                if match:
                    for group in match.groups():
                        if group:
                            seating_capacity = int(group)
                            break
            
            # 提取上市年份
            year_section = soup.select_one('.year, .release')
            if year_section:
                year_text = year_section.get_text()
                match = re.search(r'(\d{4})年', year_text)
                if match:
                    release_year = int(match.group(1))
            
            # 提取评分
            rating_section = soup.select_one('.rating, .score')
            if rating_section:
                rating_text = rating_section.get_text()
                match = re.search(r'[\d.]+', rating_text)
                if match:
                    rating = float(match.group())
        
        except Exception as e:
            logger.warning(f"获取车型详情失败 {url}: {e}")
        
        return horsepower, torque, dimensions, fuel_consumption, seating_capacity, release_year, rating
    
    def search_cars(self, **filters) -> List[CarModel]:
        """
        搜索车型
        
        Args:
            filters: 筛选条件（品牌、价格、车型等）
            
        Returns:
            车型对象列表
        """
        search_url = f"{self.base_url}/car/"
        
        # 构建查询参数
        params = {}
        
        # 品牌筛选
        if 'brand' in filters:
            brand_en = ''
            for en, cn in self.car_brands.items():
                if cn == filters['brand']:
                    brand_en = en
                    break
            
            if brand_en:
                search_url = f"{self.base_url}/{brand_en}/"
        
        # 车型筛选
        if 'car_type' in filters and filters['car_type'] in self.car_types:
            car_type_en = filters['car_type']
            search_url = f"{self.base_url}/{car_type_en}/"
        
        # 价格筛选
        if 'price_min' in filters and 'price_max' in filters:
            price_min = filters['price_min']
            price_max = filters['price_max']
            # 汽车之家价格参数（简化处理）
            params['price'] = f'{price_min}-{price_max}'
        
        try:
            logger.info(f"正在搜索车型，条件: {filters}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cars = []
            car_elements = soup.select('.cartab, .list-item')
            
            for element in car_elements[:30]:  # 最多30个结果
                car = self._parse_car_element(element)
                if car:
                    # 进一步筛选
                    if self._match_filters(car, filters):
                        cars.append(car)
            
            logger.info(f"搜索到 {len(cars)} 个符合条件的车型")
            return cars
            
        except Exception as e:
            logger.error(f"搜索车型失败: {e}")
            return []
    
    def _match_filters(self, car: CarModel, filters: Dict) -> bool:
        """检查车型是否匹配筛选条件"""
        # 品牌筛选
        if 'brand' in filters and filters['brand'] != car.brand:
            return False
        
        # 车型筛选
        if 'car_type' in filters and filters['car_type'] != car.car_type.lower():
            return False
        
        # 价格筛选
        if 'price_min' in filters and 'price_max' in filters:
            price_min = filters['price_min']
            price_max = filters['price_max']
            
            # 检查车型价格是否在范围内
            if car.min_price > price_max or car.max_price < price_min:
                return False
        
        # 燃料类型筛选
        if 'fuel_type' in filters:
            filter_fuel = filters['fuel_type']
            if filter_fuel == 'electric' and '电动' not in car.fuel_type and '新能源' not in car.fuel_type:
                return False
            elif filter_fuel == 'gasoline' and '汽油' not in car.fuel_type:
                return False
            elif filter_fuel == 'hybrid' and '混动' not in car.fuel_type:
                return False
        
        return True
    
    def compare_cars(self, car_urls: List[str]) -> List[Dict]:
        """
        对比多款车型
        
        Args:
            car_urls: 车型URL列表
            
        Returns:
            对比结果列表
        """
        comparison = []
        
        try:
            for url in car_urls[:5]:  # 最多对比5款车型
                # 获取车型详细信息
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取关键对比信息
                name_element = soup.select_one('.cartitle, h1')
                name = name_element.get_text(strip=True) if name_element else '未知'
                
                price_element = soup.select_one('.price, .price-range')
                price = price_element.get_text(strip=True) if price_element else '未知'
                
                # 提取关键参数
                params = {}
                param_sections = soup.select('.param-list, .spec-list')
                
                for section in param_sections:
                    rows = section.select('li, .row')
                    for row in rows:
                        label = row.select_one('.label, dt')
                        value = row.select_one('.value, dd')
                        
                        if label and value:
                            label_text = label.get_text(strip=True)
                            value_text = value.get_text(strip=True)
                            params[label_text] = value_text
                
                comparison.append({
                    'name': name,
                    'url': url,
                    'price': price,
                    'key_params': params
                })
            
            logger.info(f"成功对比 {len(comparison)} 款车型")
            return comparison
            
        except Exception as e:
            logger.error(f"对比车型失败: {e}")
            return []
    
    def analyze_cars(self, cars: List[CarModel]) -> Dict:
        """
        分析车型数据
        
        Args:
            cars: 车型对象列表
            
        Returns:
            分析结果字典
        """
        if not cars:
            return {}
        
        try:
            # 统计信息
            total_cars = len(cars)
            
            # 品牌统计
            brand_counts = {}
            for car in cars:
                brand_counts[car.brand] = brand_counts.get(car.brand, 0) + 1
            
            top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 车型分类统计
            type_counts = {}
            for car in cars:
                type_counts[car.car_type] = type_counts.get(car.car_type, 0) + 1
            
            top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 价格统计
            total_prices = [car.min_price for car in cars if car.min_price > 0]
            avg_min_price = sum(total_prices) / len(total_prices) if total_prices else 0
            
            # 马力统计
            horsepowers = [car.horsepower for car in cars if car.horsepower > 0]
            avg_horsepower = sum(horsepowers) / len(horsepowers) if horsepowers else 0
            
            # 油耗统计
            fuel_consumptions = [car.fuel_consumption for car in cars if car.fuel_consumption > 0]
            avg_fuel_consumption = sum(fuel_consumptions) / len(fuel_consumptions) if fuel_consumptions else 0
            
            # 评分统计
            ratings = [car.rating for car in cars if car.rating > 0]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            # 最贵和最便宜的车型
            if cars:
                sorted_by_price = sorted(cars, key=lambda x: x.min_price, reverse=True)
                most_expensive = sorted_by_price[0] if sorted_by_price else None
                cheapest = sorted_by_price[-1] if sorted_by_price else None
                
                sorted_by_horsepower = sorted(cars, key=lambda x: x.horsepower, reverse=True)
                most_powerful = sorted_by_horsepower[0] if sorted_by_horsepower else None
                least_powerful = sorted_by_horsepower[-1] if sorted_by_horsepower else None
            else:
                most_expensive = cheapest = most_powerful = least_powerful = None
            
            # 燃料类型分布
            fuel_type_counts = {}
            for car in cars:
                fuel_type = car.fuel_type
                if fuel_type not in fuel_type_counts:
                    fuel_type_counts[fuel_type] = 0
                fuel_type_counts[fuel_type] += 1
            
            return {
                'total_cars': total_cars,
                'top_brands': top_brands,
                'top_types': top_types,
                'avg_min_price': avg_min_price,
                'avg_horsepower': avg_horsepower,
                'avg_fuel_consumption': avg_fuel_consumption,
                'avg_rating': avg_rating,
                'fuel_type_distribution': fuel_type_counts,
                'most_expensive': (most_expensive.name[:30], most_expensive.min_price) if most_expensive else None,
                'cheapest': (cheapest.name[:30], cheapest.min_price) if cheapest else None,
                'most_powerful': (most_powerful.name[:30], most_powerful.horsepower) if most_powerful else None,
                'least_powerful': (least_powerful.name[:30], least_powerful.horsepower) if least_powerful else None
            }
            
        except Exception as e:
            logger.error(f"分析车型数据失败: {e}")
            return {}
    
    def save_to_csv(self, cars: List[CarModel], filename: str = "car_models.csv"):
        """
        保存车型数据到CSV文件
        
        Args:
            cars: 车型对象列表
            filename: 输出文件名
        """
        if not cars:
            logger.warning("没有车型数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'name', 'url', 'brand', 'series', 'price_range', 'min_price', 'max_price',
                    'car_type', 'fuel_type', 'transmission', 'engine', 'horsepower', 'torque',
                    'length', 'width', 'height', 'wheelbase', 'fuel_consumption',
                    'seating_capacity', 'release_year', 'image_url', 'rating'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for car in cars:
                    row = car.__dict__.copy()
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(cars)} 个车型数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("汽车之家车型数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = AutohomeCrawler()
    
    try:
        # 1. 显示汽车品牌
        print("支持的汽车品牌:")
        print("-" * 30)
        for i, (code, name) in enumerate(crawler.car_brands.items(), 1):
            print(f"  {code}: {name}", end='  ')
            if i % 3 == 0:
                print()
        print()
        
        # 2. 显示车型分类
        print("车型分类:")
        print("-" * 30)
        for code, name in crawler.car_types.items():
            print(f"  {code}: {name}")
        print()
        
        # 3. 获取车型数据（可选择分类）
        type_choice = input("请输入车型分类代码（直接回车获取全部）: ").strip().lower()
        
        if type_choice and type_choice not in crawler.car_types:
            print(f"无效分类代码，将获取全部车型")
            type_choice = None
        
        print(f"\n正在爬取车型数据...")
        cars = crawler.get_popular_cars(car_type=type_choice, limit=25)
        
        if not cars:
            print("未获取到车型数据，程序退出")
            return
        
        # 4. 显示统计信息
        print(f"\n成功获取 {len(cars)} 个车型:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_cars(cars)
        
        if analysis:
            print(f"总计车型: {analysis['total_cars']}")
            print(f"平均最低价: {analysis['avg_min_price']:.1f} 万元")
            print(f"平均马力: {analysis['avg_horsepower']:.0f} 匹")
            print(f"平均油耗: {analysis['avg_fuel_consumption']:.1f} L/100km")
            print(f"平均评分: {analysis['avg_rating']:.1f}")
            
            if analysis['top_brands']:
                print("\n热门品牌:")
                for brand, count in analysis['top_brands']:
                    print(f"  {brand}: {count} 款")
            
            if analysis['top_types']:
                print("\n车型分布:")
                for type_name, count in analysis['top_types']:
                    print(f"  {type_name}: {count} 款")
            
            if analysis['fuel_type_distribution']:
                print("\n燃料类型分布:")
                for fuel_type, count in analysis['fuel_type_distribution'].items():
                    print(f"  {fuel_type}: {count} 款")
        
        # 5. 显示前5个车型详情
        print("\n热门车型 TOP 5:")
        print("-" * 30)
        for i, car in enumerate(cars[:5], 1):
            print(f"{i}. {car.name}")
            print(f"   品牌: {car.brand}, 车系: {car.series}")
            print(f"   价格: {car.price_range}")
            print(f"   车型: {car.car_type}, 燃料: {car.fuel_type}")
            print(f"   发动机: {car.engine}")
            print(f"   马力: {car.horsepower}匹, 扭矩: {car.torque:.0f}牛米")
            print(f"   尺寸: {car.length}×{car.width}×{car.height}mm")
            print(f"   轴距: {car.wheelbase}mm, 油耗: {car.fuel_consumption:.1f}L/100km")
            print(f"   座位: {car.seating_capacity}座, 上市: {car.release_year}年")
            print(f"   评分: {car.rating:.1f}")
            print()
        
        # 6. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_name = crawler.car_types.get(type_choice, 'all') if type_choice else 'all'
        csv_file = f"car_models_{type_name}_{timestamp}.csv"
        
        crawler.save_to_csv(cars, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 7. 展示一个车型的详细内容
        if cars:
            sample_car = cars[0]
            print(f"\n车型 '{sample_car.name[:20]}...' 的详细参数:")
            print("-" * 30)
            
            print(f"基本信息:")
            print(f"  品牌: {sample_car.brand}")
            print(f"  车系: {sample_car.series}")
            print(f"  车型: {sample_car.car_type}")
            print(f"  燃料类型: {sample_car.fuel_type}")
            print(f"  变速箱: {sample_car.transmission}")
            
            print(f"\n价格信息:")
            print(f"  价格范围: {sample_car.price_range}")
            print(f"  最低价: {sample_car.min_price:.1f} 万元")
            print(f"  最高价: {sample_car.max_price:.1f} 万元")
            
            print(f"\n动力参数:")
            print(f"  发动机: {sample_car.engine}")
            print(f"  马力: {sample_car.horsepower} 匹")
            print(f"  扭矩: {sample_car.torque:.0f} 牛米")
            print(f"  油耗: {sample_car.fuel_consumption:.1f} L/100km")
            
            print(f"\n尺寸参数:")
            print(f"  车长: {sample_car.length} mm")
            print(f"  车宽: {sample_car.width} mm")
            print(f"  车高: {sample_car.height} mm")
            print(f"  轴距: {sample_car.wheelbase} mm")
            print(f"  座位数: {sample_car.seating_capacity} 座")
            
            print(f"\n其他信息:")
            print(f"  上市年份: {sample_car.release_year}")
            print(f"  综合评分: {sample_car.rating:.1f}")
        
        # 8. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示筛选搜索功能:")
        
        print("可选筛选条件:")
        print("  1. 品牌 (例如: 奥迪)")
        print("  2. 车型 (例如: suv)")
        print("  3. 价格范围 (例如: 20-40)")
        print("  4. 燃料类型 (例如: electric)")
        
        filters = {}
        
        # 品牌筛选
        brand_input = input("请输入品牌（直接回车跳过）: ").strip()
        if brand_input and brand_input in crawler.car_brands.values():
            filters['brand'] = brand_input
        
        # 车型筛选
        type_input = input("请输入车型（直接回车跳过）: ").strip().lower()
        if type_input and type_input in crawler.car_types:
            filters['car_type'] = type_input
        
        # 价格筛选
        price_input = input("请输入价格范围 (如: 20-40，直接回车跳过): ").strip()
        if price_input and '-' in price_input:
            try:
                price_min, price_max = price_input.split('-')
                filters['price_min'] = float(price_min)
                filters['price_max'] = float(price_max)
            except:
                print("价格格式错误，跳过价格筛选")
        
        # 燃料类型筛选
        fuel_input = input("请输入燃料类型 (gasoline/electric/hybrid，直接回车跳过): ").strip().lower()
        if fuel_input and fuel_input in ['gasoline', 'electric', 'hybrid']:
            filters['fuel_type'] = fuel_input
        
        if filters:
            print(f"\n正在根据条件搜索: {filters}")
            search_results = crawler.search_cars(**filters)
            
            if search_results:
                print(f"找到 {len(search_results)} 个符合条件的车型:")
                for i, car in enumerate(search_results[:5], 1):
                    print(f"{i}. {car.name}")
                    print(f"   品牌: {car.brand}, 价格: {car.price_range}")
                    print(f"   车型: {car.car_type}, 燃料: {car.fuel_type}")
            else:
                print("未找到符合条件的车型")
        
        # 9. 演示对比功能
        print("\n" + "=" * 50)
        print("演示车型对比功能:")
        
        if len(cars) >= 2:
            print("随机选择2款车型进行对比:")
            compare_urls = [cars[0].url, cars[1].url]
            comparison = crawler.compare_cars(compare_urls)
            
            if comparison:
                print("\n车型对比:")
                print("-" * 60)
                
                # 打印表头
                headers = ["参数"] + [car['name'][:15] for car in comparison]
                print(" | ".join(headers))
                print("-" * 60)
                
                # 收集所有参数
                all_params = set()
                for car in comparison:
                    all_params.update(car['key_params'].keys())
                
                # 打印参数对比
                for param in sorted(all_params)[:10]:  # 最多显示10个参数
                    row = [param]
                    for car in comparison:
                        value = car['key_params'].get(param, '-')
                        row.append(str(value)[:15])
                    
                    print(" | ".join(row))
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()