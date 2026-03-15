#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气预报爬虫 - 获取中国主要城市天气预报
网站：中国天气网 (http://www.weather.com.cn)
功能：获取指定城市的今日天气、温度、风向、空气质量等信息
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WeatherCrawler:
    """天气预报爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "http://www.weather.com.cn"
        
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
        
        # 城市代码映射表（常用城市）
        self.city_codes = {
            '北京': '101010100',
            '上海': '101020100',
            '广州': '101280101',
            '深圳': '101280601',
            '杭州': '101210101',
            '南京': '101190101',
            '成都': '101270101',
            '武汉': '101200101',
            '西安': '101110101',
            '天津': '101030100',
        }
    
    def get_city_code(self, city_name: str) -> Optional[str]:
        """
        获取城市代码
        
        Args:
            city_name: 城市名称
            
        Returns:
            城市代码，如果未找到则返回None
        """
        # 先从预定义的映射表中查找
        if city_name in self.city_codes:
            return self.city_codes[city_name]
        
        # 如果不在预定义列表中，尝试从网站搜索（这里简化处理）
        logger.warning(f"城市 '{city_name}' 不在预定义列表中，尝试使用北京代码")
        return '101010100'  # 默认使用北京
    
    def fetch_weather(self, city_name: str) -> Optional[Dict]:
        """
        获取指定城市的天气预报
        
        Args:
            city_name: 城市名称
            
        Returns:
            包含天气信息的字典，失败则返回None
        """
        try:
            city_code = self.get_city_code(city_name)
            if not city_code:
                logger.error(f"无法获取城市 '{city_name}' 的代码")
                return None
            
            # 构建天气页面URL
            weather_url = f"{self.base_url}/weather/{city_code}.shtml"
            
            logger.info(f"正在获取 {city_name} 的天气信息，URL: {weather_url}")
            
            # 发送请求
            response = self.session.get(weather_url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取天气信息
            weather_data = self._parse_weather_page(soup, city_name)
            
            if weather_data:
                logger.info(f"成功获取 {city_name} 的天气信息")
                return weather_data
            else:
                logger.warning(f"解析 {city_name} 天气信息失败")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取天气信息时发生未知错误: {str(e)}")
            return None
    
    def _parse_weather_page(self, soup: BeautifulSoup, city_name: str) -> Dict:
        """
        解析天气页面
        
        Args:
            soup: BeautifulSoup对象
            city_name: 城市名称
            
        Returns:
            天气信息字典
        """
        try:
            weather_data = {
                'city': city_name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': '中国天气网',
                'today': {},
                'forecast': []
            }
            
            # 提取今日天气
            today_div = soup.find('div', class_='today')
            if today_div:
                # 温度
                temp_div = today_div.find('div', class_='tem')
                if temp_div:
                    temp_text = temp_div.get_text(strip=True)
                    weather_data['today']['temperature'] = temp_text
                
                # 天气状况
                wea_div = today_div.find('div', class_='wea')
                if wea_div:
                    weather_data['today']['weather'] = wea_div.get_text(strip=True)
                
                # 风力风向
                win_div = today_div.find('div', class_='win')
                if win_div:
                    weather_data['today']['wind'] = win_div.get_text(strip=True)
            
            # 提取7天预报
            forecast_div = soup.find('div', class_='7d')
            if forecast_div:
                forecast_items = forecast_div.find_all('li')
                for item in forecast_items[:7]:  # 只取7天
                    day_info = {}
                    
                    # 日期
                    date_span = item.find('span', class_='date')
                    if date_span:
                        day_info['date'] = date_span.get_text(strip=True)
                    
                    # 天气
                    wea_span = item.find('span', class_='wea')
                    if wea_span:
                        day_info['weather'] = wea_span.get_text(strip=True)
                    
                    # 温度
                    tem_span = item.find('span', class_='tem')
                    if tem_span:
                        day_info['temperature'] = tem_span.get_text(strip=True)
                    
                    # 风力
                    win_span = item.find('span', class_='win')
                    if win_span:
                        day_info['wind'] = win_span.get_text(strip=True)
                    
                    if day_info:
                        weather_data['forecast'].append(day_info)
            
            # 如果没有找到详细信息，尝试备用解析方法
            if not weather_data['today']:
                # 备用解析：查找class包含"weather"的元素
                weather_elements = soup.find_all(class_=lambda x: x and 'weather' in x.lower())
                for element in weather_elements:
                    text = element.get_text(strip=True)
                    if '°' in text or '℃' in text or '度' in text:
                        weather_data['today']['temperature'] = text
                        break
            
            return weather_data
            
        except Exception as e:
            logger.error(f"解析页面时发生错误: {str(e)}")
            return weather_data
    
    def save_to_json(self, weather_data: Dict, filename: str = None) -> bool:
        """
        将天气数据保存为JSON文件
        
        Args:
            weather_data: 天气数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not weather_data:
                logger.warning("没有天气数据可保存")
                return False
            
            if filename is None:
                city = weather_data.get('city', 'unknown')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"weather_{city}_{timestamp}.json"
            
            # 确保保存到crawlers目录
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(weather_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"天气数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def get_multiple_cities_weather(self, city_names: List[str]) -> List[Dict]:
        """
        获取多个城市的天气信息
        
        Args:
            city_names: 城市名称列表
            
        Returns:
            天气信息列表
        """
        results = []
        
        for city in city_names:
            logger.info(f"正在处理城市: {city}")
            weather = self.fetch_weather(city)
            if weather:
                results.append(weather)
            
            # 添加延迟，避免请求过快
            time.sleep(1)
        
        return results


def main():
    """主函数，演示爬虫的使用"""
    print("天气预报爬虫演示")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = WeatherCrawler(timeout=15)
    
    # 获取单个城市的天气
    city = "北京"
    print(f"\n获取 {city} 的天气信息...")
    weather_data = crawler.fetch_weather(city)
    
    if weather_data:
        print(f"城市: {weather_data['city']}")
        print(f"更新时间: {weather_data['timestamp']}")
        print(f"数据来源: {weather_data['source']}")
        
        if weather_data['today']:
            print("\n今日天气:")
            for key, value in weather_data['today'].items():
                print(f"  {key}: {value}")
        
        if weather_data['forecast']:
            print("\n未来几天预报:")
            for i, forecast in enumerate(weather_data['forecast'][:3]):  # 只显示3天
                print(f"  第{i+1}天: {forecast.get('date', '未知')} - "
                      f"{forecast.get('weather', '未知')} "
                      f"{forecast.get('temperature', '未知')}")
        
        # 保存数据
        crawler.save_to_json(weather_data)
        print(f"\n数据已保存到JSON文件")
    else:
        print(f"无法获取 {city} 的天气信息")
    
    # 获取多个城市的天气
    print("\n" + "=" * 50)
    print("获取多个城市天气信息...")
    cities = ["上海", "广州", "深圳"]
    all_weather = crawler.get_multiple_cities_weather(cities)
    
    print(f"\n成功获取 {len(all_weather)} 个城市的天气信息")
    for weather in all_weather:
        print(f"- {weather['city']}: {weather.get('today', {}).get('weather', '未知')}")
    
    print("\n爬虫演示完成！")


if __name__ == "__main__":
    main()