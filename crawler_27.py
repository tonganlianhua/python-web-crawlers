#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游信息爬虫 - 携程旅游景点数据
爬取携程网站的旅游景点信息：景点名称、评分、门票价格、开放时间、地址等
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
class TouristAttraction:
    """旅游景点数据结构"""
    name: str
    url: str
    city: str  # 所在城市
    rating: float  # 评分（0-5）
    rating_count: int  # 评分人数
    ticket_price: str  # 门票价格
    opening_hours: str  # 开放时间
    address: str  # 详细地址
    description: str  # 景点描述
    best_season: str  # 最佳季节
    visit_duration: str  # 建议游玩时间
    attractions_type: str  # 景点类型（自然风光、历史古迹等）
    tags: List[str]  # 标签
    image_url: str  # 景点图片
    latitude: float  # 纬度
    longitude: float  # 经度


class CtripCrawler:
    """携程旅游爬虫类"""
    
    def __init__(self):
        self.base_url = "https://you.ctrip.com"
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
        
        # 热门城市映射
        self.popular_cities = {
            'beijing': '北京',
            'shanghai': '上海',
            'guangzhou': '广州',
            'shenzhen': '深圳',
            'hangzhou': '杭州',
            'chengdu': '成都',
            'xian': '西安',
            'suzhou': '苏州',
            'nanjing': '南京',
            'chongqing': '重庆',
            'wuhan': '武汉',
            'tianjin': '天津',
            'sanya': '三亚',
            'lijiang': '丽江',
            'xiamen': '厦门'
        }
    
    def get_attractions_by_city(self, city: str, limit: int = 30) -> List[TouristAttraction]:
        """
        获取城市旅游景点
        
        Args:
            city: 城市名称或代码
            limit: 获取数量
            
        Returns:
            景点对象列表
        """
        attractions = []
        page = 1
        
        try:
            # 确定城市URL
            city_url = self._get_city_url(city)
            if not city_url:
                logger.error(f"找不到城市: {city}")
                return []
            
            logger.info(f"正在获取 {city} 的旅游景点，数量: {limit}")
            
            while len(attractions) < limit:
                # 构建景点列表URL
                url = f"{self.base_url}{city_url}/sight"
                params = {'pageno': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找景点列表
                attraction_elements = soup.select('.sight_item, .list_item, .attraction-item')
                
                if not attraction_elements:
                    # 尝试其他选择器
                    attraction_elements = soup.select('.rdetailbox, .sightlist .item')
                
                if not attraction_elements:
                    logger.warning("未找到景点元素，可能页面结构已变化")
                    break
                
                # 解析每个景点
                new_attractions = 0
                for element in attraction_elements:
                    if len(attractions) >= limit:
                        break
                    
                    attraction = self._parse_attraction_element(element, city)
                    if attraction:
                        attractions.append(attraction)
                        new_attractions += 1
                
                if new_attractions == 0:
                    logger.info(f"第 {page} 页没有新景点，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_attractions} 个景点，总计 {len(attractions)} 个")
                page += 1
                
                # 避免请求过快
                time.sleep(2)
            
            logger.info(f"成功获取 {len(attractions)} 个旅游景点")
            return attractions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析景点失败: {e}")
            return []
    
    def _get_city_url(self, city: str) -> Optional[str]:
        """获取城市URL路径"""
        # 如果是中文城市名，转换为拼音
        if city in self.popular_cities.values():
            # 找到对应的拼音
            for pinyin, name in self.popular_cities.items():
                if name == city:
                    return f"/place/{pinyin}.html"
        
        # 如果是拼音
        if city in self.popular_cities:
            return f"/place/{city}.html"
        
        # 尝试其他格式
        city_lower = city.lower().replace(' ', '')
        if city_lower in self.popular_cities:
            return f"/place/{city_lower}.html"
        
        # 默认返回北京
        logger.warning(f"未找到城市 {city}，使用北京作为默认")
        return "/place/beijing.html"
    
    def _parse_attraction_element(self, element, city: str) -> Optional[TouristAttraction]:
        """解析景点HTML元素"""
        try:
            # 提取景点名称
            name_element = element.select_one('.sight_item_caption, .title, h3, .rdetailbox_title')
            name = name_element.get_text(strip=True) if name_element else ''
            
            if not name:
                return None
            
            # 提取链接
            link_element = element.select_one('a')
            if not link_element or not link_element.get('href'):
                return None
            
            attraction_url = link_element['href']
            if not attraction_url.startswith('http'):
                attraction_url = self.base_url + attraction_url
            
            # 提取评分
            rating_element = element.select_one('.score, .rating, .stars')
            rating = 0.0
            rating_count = 0
            
            if rating_element:
                rating_text = rating_element.get_text(strip=True)
                # 尝试提取数字评分
                match = re.search(r'[\d.]+', rating_text)
                if match:
                    rating = float(match.group())
                
                # 尝试提取评分人数
                count_match = re.search(r'[\(（](\d+)[\)）]', rating_text)
                if count_match:
                    rating_count = int(count_match.group(1))
            
            # 提取地址
            address_element = element.select_one('.address, .location, .addr')
            address = address_element.get_text(strip=True) if address_element else ''
            
            # 提取门票价格
            price_element = element.select_one('.price, .ticket-price, .cost')
            ticket_price = price_element.get_text(strip=True) if price_element else '免费或未知'
            
            # 提取开放时间
            time_element = element.select_one('.opening, .time, .hours')
            opening_hours = time_element.get_text(strip=True) if time_element else '未知'
            
            # 提取图片
            image_element = element.select_one('img')
            image_url = image_element['src'] if image_element and image_element.get('src') else ''
            
            # 提取描述
            desc_element = element.select_one('.desc, .summary, .intro')
            description = desc_element.get_text(strip=True)[:150] if desc_element else ''
            
            # 提取标签
            tags = []
            tag_elements = element.select('.tag, .label, .keyword')
            for tag_element in tag_elements:
                tag_text = tag_element.get_text(strip=True)
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
            
            # 获取景点详细信息
            best_season, visit_duration, attractions_type, lat, lng = self._get_attraction_details(attraction_url)
            
            attraction = TouristAttraction(
                name=html.unescape(name),
                url=attraction_url,
                city=city if city in self.popular_cities.values() else self.popular_cities.get(city, city),
                rating=rating,
                rating_count=rating_count,
                ticket_price=html.unescape(ticket_price),
                opening_hours=html.unescape(opening_hours),
                address=html.unescape(address),
                description=html.unescape(description),
                best_season=best_season,
                visit_duration=visit_duration,
                attractions_type=attractions_type,
                tags=[html.unescape(tag) for tag in tags],
                image_url=image_url,
                latitude=lat,
                longitude=lng
            )
            
            return attraction
            
        except Exception as e:
            logger.warning(f"解析景点元素失败: {e}")
            return None
    
    def _get_attraction_details(self, url: str) -> Tuple[str, str, str, float, float]:
        """获取景点详细内容"""
        best_season = '四季皆宜'
        visit_duration = '2-3小时'
        attractions_type = '旅游景点'
        latitude = 0.0
        longitude = 0.0
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找最佳季节
            season_section = soup.select_one('.best-season, .season, .recommend-season')
            if season_section:
                season_text = season_section.get_text(strip=True)
                if '最佳季节' in season_text:
                    best_season = season_text.replace('最佳季节', '').strip()
                elif '适宜游玩季节' in season_text:
                    best_season = season_text.replace('适宜游玩季节', '').strip()
            
            # 查找建议游玩时间
            duration_section = soup.select_one('.duration, .suggest-time, .visit-time')
            if duration_section:
                duration_text = duration_section.get_text(strip=True)
                if '建议游玩时间' in duration_text:
                    visit_duration = duration_text.replace('建议游玩时间', '').strip()
                elif '游玩时长' in duration_text:
                    visit_duration = duration_text.replace('游玩时长', '').strip()
            
            # 查找景点类型
            type_section = soup.select_one('.attraction-type, .category, .type')
            if type_section:
                type_text = type_section.get_text(strip=True)
                if '景点类型' in type_text:
                    attractions_type = type_text.replace('景点类型', '').strip()
                elif '分类' in type_text:
                    attractions_type = type_text.replace('分类', '').strip()
            
            # 尝试从页面中提取经纬度
            # 通常在JavaScript数据中
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # 查找经纬度
                    lat_match = re.search(r'"lat":\s*([\d.]+)', script.string)
                    lng_match = re.search(r'"lng":\s*([\d.]+)', script.string)
                    
                    if lat_match and lng_match:
                        try:
                            latitude = float(lat_match.group(1))
                            longitude = float(lng_match.group(1))
                            break
                        except:
                            continue
                    
                    # 另一种格式
                    lat_match = re.search(r'latitude["\']?\s*:\s*([\d.]+)', script.string)
                    lng_match = re.search(r'longitude["\']?\s*:\s*([\d.]+)', script.string)
                    
                    if lat_match and lng_match:
                        try:
                            latitude = float(lat_match.group(1))
                            longitude = float(lng_match.group(1))
                            break
                        except:
                            continue
            
        except Exception as e:
            logger.warning(f"获取景点详情失败 {url}: {e}")
        
        return best_season, visit_duration, attractions_type, latitude, longitude
    
    def search_attractions(self, query: str, limit: int = 20) -> List[TouristAttraction]:
        """
        搜索旅游景点
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            景点对象列表
        """
        search_url = f"{self.base_url}/searchsite"
        params = {
            'query': query,
            'isSearch': 'true'
        }
        
        try:
            logger.info(f"正在搜索旅游景点: {query}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            attractions = []
            search_results = soup.select('.search-result, .result-item, .sight_item')
            
            for result in search_results[:limit]:
                # 尝试确定城市
                city_match = re.search(r'【(.+?)】', result.get_text())
                city = city_match.group(1) if city_match else '未知'
                
                attraction = self._parse_search_result(result, city)
                if attraction:
                    attractions.append(attraction)
            
            logger.info(f"搜索到 {len(attractions)} 个相关景点")
            return attractions
            
        except Exception as e:
            logger.error(f"搜索景点失败: {e}")
            return []
    
    def _parse_search_result(self, element, city: str) -> Optional[TouristAttraction]:
        """解析搜索结果元素"""
        try:
            # 搜索结果的解析逻辑与普通列表类似
            return self._parse_attraction_element(element, city)
            
        except Exception as e:
            logger.warning(f"解析搜索结果失败: {e}")
            return None
    
    def get_recommended_itineraries(self, city: str, days: int = 3) -> List[Dict]:
        """
        获取推荐旅游路线
        
        Args:
            city: 城市名称
            days: 行程天数
            
        Returns:
            路线列表
        """
        # 这里使用模拟数据，实际应用中需要调用相关API
        logger.info(f"生成 {city} {days}天推荐路线")
        
        # 模拟推荐路线
        itineraries = []
        
        # 1日游路线
        if days >= 1:
            itineraries.append({
                'day': 1,
                'title': f'{city}经典一日游',
                'description': f'游览{city}最著名的景点，体验城市精华',
                'attractions': ['市中心地标', '历史博物馆', '特色美食街'],
                'time_allocation': '上午: 参观地标建筑; 下午: 游览博物馆; 晚上: 品尝当地美食',
                'estimated_cost': '中等'
            })
        
        # 2-3日游路线
        if days >= 2:
            itineraries.append({
                'day': 2,
                'title': f'{city}深度文化游',
                'description': f'深入体验{city}的文化和历史',
                'attractions': ['古镇/古街', '艺术区', '传统表演'],
                'time_allocation': '上午: 游览古镇; 下午: 参观艺术区; 晚上: 观看传统表演',
                'estimated_cost': '中等'
            })
        
        if days >= 3:
            itineraries.append({
                'day': 3,
                'title': f'{city}自然风光游',
                'description': f'欣赏{city}周边的自然美景',
                'attractions': ['国家公园', '湖泊/山区', '观景台'],
                'time_allocation': '全天: 游览自然景区，享受户外活动',
                'estimated_cost': '较低'
            })
        
        return itineraries
    
    def analyze_attractions(self, attractions: List[TouristAttraction]) -> Dict:
        """
        分析景点数据
        
        Args:
            attractions: 景点对象列表
            
        Returns:
            分析结果字典
        """
        if not attractions:
            return {}
        
        try:
            # 统计信息
            total_attractions = len(attractions)
            
            # 分类统计
            city_counts = {}
            type_counts = {}
            tag_counts = {}
            price_range_counts = {'免费': 0, '低价': 0, '中等': 0, '高价': 0}
            
            total_rating = 0
            high_rated_attractions = 0
            
            for attraction in attractions:
                # 城市统计
                city_counts[attraction.city] = city_counts.get(attraction.city, 0) + 1
                
                # 类型统计
                type_counts[attraction.attractions_type] = type_counts.get(attraction.attractions_type, 0) + 1
                
                # 标签统计
                for tag in attraction.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # 价格区间统计
                price_text = attraction.ticket_price.lower()
                if '免费' in price_text or '0元' in price_text:
                    price_range_counts['免费'] += 1
                elif '元以下' in price_text or '10元' in price_text:
                    price_range_counts['低价'] += 1
                elif '50元' in price_text or '100元' in price_text:
                    price_range_counts['中等'] += 1
                else:
                    price_range_counts['高价'] += 1
                
                # 评分统计
                total_rating += attraction.rating
                if attraction.rating >= 4.0:
                    high_rated_attractions += 1
            
            # 最常见的城市、类型、标签
            top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # 平均评分
            avg_rating = total_rating / total_attractions if total_attractions > 0 else 0
            
            # 最佳季节分布
            season_counts = {}
            for attraction in attractions:
                season = attraction.best_season
                if '春' in season:
                    season_counts['春季'] = season_counts.get('春季', 0) + 1
                if '夏' in season:
                    season_counts['夏季'] = season_counts.get('夏季', 0) + 1
                if '秋' in season:
                    season_counts['秋季'] = season_counts.get('秋季', 0) + 1
                if '冬' in season:
                    season_counts['冬季'] = season_counts.get('冬季', 0) + 1
                if '四季' in season or '全年' in season:
                    season_counts['四季皆宜'] = season_counts.get('四季皆宜', 0) + 1
            
            # 最受欢迎的景点（按评分）
            top_rated_attractions = sorted(attractions, key=lambda x: x.rating, reverse=True)[:5]
            
            return {
                'total_attractions': total_attractions,
                'total_cities': len(city_counts),
                'avg_rating': avg_rating,
                'high_rated_percentage': (high_rated_attractions / total_attractions * 100) if total_attractions > 0 else 0,
                'top_cities': top_cities,
                'top_types': top_types,
                'top_tags': top_tags,
                'price_distribution': price_range_counts,
                'season_distribution': season_counts,
                'top_rated_attractions': [(a.name[:30], a.rating) for a in top_rated_attractions]
            }
            
        except Exception as e:
            logger.error(f"分析景点数据失败: {e}")
            return {}
    
    def save_to_csv(self, attractions: List[TouristAttraction], filename: str = "tourist_attractions.csv"):
        """
        保存景点数据到CSV文件
        
        Args:
            attractions: 景点对象列表
            filename: 输出文件名
        """
        if not attractions:
            logger.warning("没有景点数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'name', 'url', 'city', 'rating', 'rating_count', 'ticket_price',
                    'opening_hours', 'address', 'description', 'best_season',
                    'visit_duration', 'attractions_type', 'tags', 'image_url',
                    'latitude', 'longitude'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for attraction in attractions:
                    row = attraction.__dict__.copy()
                    # 转换标签列表为字符串
                    row['tags'] = ', '.join(row['tags'])
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(attractions)} 个景点数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("携程旅游景点爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = CtripCrawler()
    
    try:
        # 1. 显示热门城市
        print("热门旅游城市:")
        print("-" * 30)
        for i, (pinyin, name) in enumerate(crawler.popular_cities.items(), 1):
            print(f"  {pinyin}: {name}", end='  ')
            if i % 3 == 0:
                print()
        print()
        
        # 2. 获取景点（可选择城市）
        city_choice = input("请输入城市名称或拼音（直接回车使用北京）: ").strip()
        
        if not city_choice:
            city_choice = '北京'
        
        print(f"\n正在爬取 {city_choice} 的旅游景点...")
        attractions = crawler.get_attractions_by_city(city_choice, limit=20)
        
        if not attractions:
            print("未获取到景点数据，程序退出")
            return
        
        # 3. 显示统计信息
        print(f"\n成功获取 {len(attractions)} 个旅游景点:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_attractions(attractions)
        
        if analysis:
            print(f"总计景点: {analysis['total_attractions']}")
            print(f"涉及城市: {analysis['total_cities']}")
            print(f"平均评分: {analysis['avg_rating']:.2f}")
            print(f"高评分景点: {analysis['high_rated_percentage']:.1f}%")
            
            if analysis['top_types']:
                print("\n景点类型分布:")
                for type_name, count in analysis['top_types']:
                    print(f"  {type_name}: {count} 个")
            
            if analysis['price_distribution']:
                print("\n门票价格分布:")
                for price_range, count in analysis['price_distribution'].items():
                    if count > 0:
                        print(f"  {price_range}: {count} 个")
        
        # 4. 显示前5个景点详情
        print("\n热门景点 TOP 5:")
        print("-" * 30)
        for i, attraction in enumerate(attractions[:5], 1):
            print(f"{i}. {attraction.name}")
            print(f"   城市: {attraction.city}, 评分: {attraction.rating:.1f} ({attraction.rating_count}人)")
            print(f"   门票: {attraction.ticket_price}, 开放: {attraction.opening_hours}")
            print(f"   地址: {attraction.address[:50]}...")
            
            if attraction.tags:
                print(f"   标签: {', '.join(attraction.tags[:3])}")
            
            print()
        
        # 5. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"tourist_attractions_{timestamp}.csv"
        
        crawler.save_to_csv(attractions, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 6. 展示一个景点的详细内容
        if attractions:
            sample_attraction = attractions[0]
            print(f"\n景点 '{sample_attraction.name[:20]}...' 的详细内容:")
            print("-" * 30)
            
            print(f"城市: {sample_attraction.city}")
            print(f"评分: {sample_attraction.rating:.1f} ({sample_attraction.rating_count}人评价)")
            print(f"门票价格: {sample_attraction.ticket_price}")
            print(f"开放时间: {sample_attraction.opening_hours}")
            print(f"详细地址: {sample_attraction.address}")
            print(f"最佳季节: {sample_attraction.best_season}")
            print(f"建议游玩时间: {sample_attraction.visit_duration}")
            print(f"景点类型: {sample_attraction.attractions_type}")
            
            if sample_attraction.description:
                print(f"\n景点描述: {sample_attraction.description}")
            
            if sample_attraction.tags:
                print(f"标签: {', '.join(sample_attraction.tags)}")
            
            if sample_attraction.latitude != 0 and sample_attraction.longitude != 0:
                print(f"地理位置: 纬度 {sample_attraction.latitude}, 经度 {sample_attraction.longitude}")
        
        # 7. 演示推荐路线功能
        print("\n" + "=" * 50)
        print("演示推荐旅游路线功能:")
        days_input = input("请输入行程天数（1-7，直接回车跳过）: ").strip()
        
        if days_input and days_input.isdigit():
            days = int(days_input)
            if 1 <= days <= 7:
                print(f"\n{city_choice} {days}天推荐路线:")
                print("-" * 30)
                
                itineraries = crawler.get_recommended_itineraries(city_choice, days)
                
                for itinerary in itineraries:
                    print(f"\n第{itinerary['day']}天: {itinerary['title']}")
                    print(f"描述: {itinerary['description']}")
                    print(f"主要景点: {', '.join(itinerary['attractions'])}")
                    print(f"时间安排: {itinerary['time_allocation']}")
                    print(f"预计花费: {itinerary['estimated_cost']}")
        
        # 8. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示搜索功能:")
        search_query = input("请输入要搜索的景点或关键词（直接回车跳过）: ").strip()
        
        if search_query:
            print(f"\n正在搜索 '{search_query}'...")
            search_results = crawler.search_attractions(search_query, limit=10)
            
            if search_results:
                print(f"找到 {len(search_results)} 个相关景点:")
                for i, attraction in enumerate(search_results[:5], 1):
                    print(f"{i}. {attraction.name}")
                    print(f"   城市: {attraction.city}, 评分: {attraction.rating:.1f}")
                    print(f"   门票: {attraction.ticket_price}")
            else:
                print("未找到相关景点")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()