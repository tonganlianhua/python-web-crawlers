#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫04: API数据爬虫 - 天气数据获取
功能: 通过公开API获取天气数据，支持多个城市、历史天气、天气预报
"""

import requests
import json
import time
from datetime import datetime, timedelta
import logging
import os
import csv
from typing import Dict, List, Optional, Tuple
import sqlite3
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_04.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WeatherAPI:
    """天气API枚举"""
    OPENWEATHER = "openweather"
    WEATHERAPI = "weatherapi"
    QWEATHER = "qweather"
    TIANQI = "tianqi"

@dataclass
class WeatherData:
    """天气数据结构"""
    city: str
    country: str
    temperature: float  # 温度（摄氏度）
    feels_like: float  # 体感温度
    humidity: int  # 湿度（%）
    pressure: int  # 气压（hPa）
    wind_speed: float  # 风速（m/s）
    wind_direction: int  # 风向（度）
    description: str  # 天气描述
    icon: str  # 天气图标代码
    visibility: int  # 能见度（米）
    clouds: int  # 云量（%）
    sunrise: str  # 日出时间
    sunset: str  # 日落时间
    timestamp: str  # 数据时间戳
    source: str  # 数据源

class WeatherCrawler:
    """天气数据爬虫"""
    
    def __init__(self, api_key: str = None, api_source: str = WeatherAPI.OPENWEATHER):
        """
        初始化天气爬虫
        
        Args:
            api_key: API密钥
            api_source: API数据源
        """
        self.api_key = api_key
        self.api_source = api_source
        self.base_urls = {
            WeatherAPI.OPENWEATHER: "https://api.openweathermap.org/data/2.5",
            WeatherAPI.WEATHERAPI: "https://api.weatherapi.com/v1",
            WeatherAPI.QWEATHER: "https://devapi.qweather.com/v7",
            WeatherAPI.TIANQI: "https://api.tianqi.com"
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 初始化数据库
        self.init_database()
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            self.db_conn = sqlite3.connect('weather_data.db')
            self.db_cursor = self.db_conn.cursor()
            
            # 创建天气数据表
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country TEXT,
                    temperature REAL,
                    feels_like REAL,
                    humidity INTEGER,
                    pressure INTEGER,
                    wind_speed REAL,
                    wind_direction INTEGER,
                    description TEXT,
                    icon TEXT,
                    visibility INTEGER,
                    clouds INTEGER,
                    sunrise TEXT,
                    sunset TEXT,
                    timestamp TEXT NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建城市表
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    country TEXT,
                    lat REAL,
                    lon REAL,
                    timezone TEXT,
                    last_updated TEXT
                )
            ''')
            
            self.db_conn.commit()
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def get_current_weather(self, city: str, country: str = "CN") -> Optional[WeatherData]:
        """
        获取当前天气
        
        Args:
            city: 城市名
            country: 国家代码
            
        Returns:
            WeatherData对象或None
        """
        try:
            logger.info(f"获取 {city} 的当前天气")
            
            if self.api_source == WeatherAPI.OPENWEATHER:
                return self._get_openweather_current(city, country)
            elif self.api_source == WeatherAPI.WEATHERAPI:
                return self._get_weatherapi_current(city)
            else:
                logger.warning(f"不支持的API源: {self.api_source}")
                return None
                
        except Exception as e:
            logger.error(f"获取当前天气失败: {e}")
            return None
    
    def _get_openweather_current(self, city: str, country: str) -> Optional[WeatherData]:
        """通过OpenWeather API获取当前天气"""
        if not self.api_key:
            logger.warning("需要OpenWeather API密钥")
            return None
        
        try:
            url = f"{self.base_urls[WeatherAPI.OPENWEATHER]}/weather"
            params = {
                'q': f"{city},{country}",
                'appid': self.api_key,
                'units': 'metric',  # 使用摄氏度
                'lang': 'zh_cn'  # 中文描述
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析数据
            weather_data = WeatherData(
                city=data['name'],
                country=data['sys']['country'],
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                wind_speed=data['wind']['speed'],
                wind_direction=data['wind'].get('deg', 0),
                description=data['weather'][0]['description'],
                icon=data['weather'][0]['icon'],
                visibility=data.get('visibility', 10000),
                clouds=data['clouds']['all'],
                sunrise=datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M:%S'),
                sunset=datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M:%S'),
                timestamp=datetime.fromtimestamp(data['dt']).isoformat(),
                source=WeatherAPI.OPENWEATHER
            )
            
            # 保存到数据库
            self.save_to_database(weather_data)
            
            return weather_data
            
        except Exception as e:
            logger.error(f"OpenWeather API请求失败: {e}")
            return None
    
    def _get_weatherapi_current(self, city: str) -> Optional[WeatherData]:
        """通过WeatherAPI获取当前天气"""
        if not self.api_key:
            logger.warning("需要WeatherAPI密钥")
            return None
        
        try:
            url = f"{self.base_urls[WeatherAPI.WEATHERAPI]}/current.json"
            params = {
                'key': self.api_key,
                'q': city,
                'lang': 'zh'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析数据
            weather_data = WeatherData(
                city=data['location']['name'],
                country=data['location']['country'],
                temperature=data['current']['temp_c'],
                feels_like=data['current']['feelslike_c'],
                humidity=data['current']['humidity'],
                pressure=data['current']['pressure_mb'],
                wind_speed=data['current']['wind_kph'] / 3.6,  # 转换为m/s
                wind_direction=data['current']['wind_degree'],
                description=data['current']['condition']['text'],
                icon=data['current']['condition']['icon'].split('/')[-1].split('.')[0],
                visibility=data['current']['vis_km'] * 1000,  # 转换为米
                clouds=data['current']['cloud'],
                sunrise='',  # WeatherAPI需要额外请求
                sunset='',
                timestamp=datetime.fromtimestamp(data['current']['last_updated_epoch']).isoformat(),
                source=WeatherAPI.WEATHERAPI
            )
            
            # 保存到数据库
            self.save_to_database(weather_data)
            
            return weather_data
            
        except Exception as e:
            logger.error(f"WeatherAPI请求失败: {e}")
            return None
    
    def get_forecast(self, city: str, days: int = 3) -> List[Dict]:
        """
        获取天气预报
        
        Args:
            city: 城市名
            days: 预报天数（1-7）
            
        Returns:
            天气预报列表
        """
        try:
            logger.info(f"获取 {city} 的 {days} 天天气预报")
            
            if self.api_source == WeatherAPI.OPENWEATHER:
                return self._get_openweather_forecast(city, days)
            elif self.api_source == WeatherAPI.WEATHERAPI:
                return self._get_weatherapi_forecast(city, days)
            else:
                logger.warning(f"不支持的API源: {self.api_source}")
                return []
                
        except Exception as e:
            logger.error(f"获取天气预报失败: {e}")
            return []
    
    def _get_openweather_forecast(self, city: str, days: int) -> List[Dict]:
        """通过OpenWeather获取天气预报"""
        if not self.api_key:
            logger.warning("需要OpenWeather API密钥")
            return []
        
        try:
            url = f"{self.base_urls[WeatherAPI.OPENWEATHER]}/forecast"
            params = {
                'q': city,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'zh_cn',
                'cnt': days * 8  # 每3小时一个数据点
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            forecast_list = []
            
            for item in data['list']:
                forecast = {
                    'datetime': datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M:%S'),
                    'temperature': item['main']['temp'],
                    'feels_like': item['main']['feels_like'],
                    'humidity': item['main']['humidity'],
                    'pressure': item['main']['pressure'],
                    'description': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon'],
                    'wind_speed': item['wind']['speed'],
                    'wind_direction': item['wind'].get('deg', 0),
                    'clouds': item['clouds']['all'],
                    'pop': item.get('pop', 0)  # 降水概率
                }
                forecast_list.append(forecast)
            
            return forecast_list
            
        except Exception as e:
            logger.error(f"OpenWeather预报请求失败: {e}")
            return []
    
    def _get_weatherapi_forecast(self, city: str, days: int) -> List[Dict]:
        """通过WeatherAPI获取天气预报"""
        if not self.api_key:
            logger.warning("需要WeatherAPI密钥")
            return []
        
        try:
            url = f"{self.base_urls[WeatherAPI.WEATHERAPI]}/forecast.json"
            params = {
                'key': self.api_key,
                'q': city,
                'days': days,
                'lang': 'zh'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            forecast_list = []
            
            for day in data['forecast']['forecastday']:
                forecast = {
                    'date': day['date'],
                    'max_temp': day['day']['maxtemp_c'],
                    'min_temp': day['day']['mintemp_c'],
                    'avg_temp': day['day']['avgtemp_c'],
                    'condition': day['day']['condition']['text'],
                    'icon': day['day']['condition']['icon'],
                    'max_wind': day['day']['maxwind_kph'] / 3.6,
                    'total_precip': day['day']['totalprecip_mm'],
                    'avg_humidity': day['day']['avghumidity'],
                    'sunrise': day['astro']['sunrise'],
                    'sunset': day['astro']['sunset'],
                    'moon_phase': day['astro']['moon_phase']
                }
                forecast_list.append(forecast)
            
            return forecast_list
            
        except Exception as e:
            logger.error(f"WeatherAPI预报请求失败: {e}")
            return []
    
    def save_to_database(self, weather_data: WeatherData):
        """保存天气数据到数据库"""
        try:
            self.db_cursor.execute('''
                INSERT INTO weather (
                    city, country, temperature, feels_like, humidity, pressure,
                    wind_speed, wind_direction, description, icon, visibility,
                    clouds, sunrise, sunset, timestamp, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                weather_data.city,
                weather_data.country,
                weather_data.temperature,
                weather_data.feels_like,
                weather_data.humidity,
                weather_data.pressure,
                weather_data.wind_speed,
                weather_data.wind_direction,
                weather_data.description,
                weather_data.icon,
                weather_data.visibility,
                weather_data.clouds,
                weather_data.sunrise,
                weather_data.sunset,
                weather_data.timestamp,
                weather_data.source
            ))
            
            self.db_conn.commit()
            logger.debug(f"天气数据已保存到数据库: {weather_data.city}")
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
    
    def get_historical_data(self, city: str, start_date: str, end_date: str = None) -> List[Dict]:
        """
        从数据库获取历史天气数据
        
        Args:
            city: 城市名
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天
            
        Returns:
            历史天气数据列表
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            self.db_cursor.execute('''
                SELECT * FROM weather 
                WHERE city = ? AND date(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (city, start_date, end_date))
            
            columns = [desc[0] for desc in self.db_cursor.description]
            rows = self.db_cursor.fetchall()
            
            historical_data = []
            for row in rows:
                data = dict(zip(columns, row))
                historical_data.append(data)
            
            logger.info(f"获取到 {len(historical_data)} 条历史天气数据")
            return historical_data
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return []
    
    def export_to_csv(self, city: str, filename: str = None):
        """
        导出天气数据到CSV
        
        Args:
            city: 城市名
            filename: 输出文件名
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'weather_{city}_{timestamp}.csv'
            
            # 获取所有数据
            self.db_cursor.execute('''
                SELECT * FROM weather WHERE city = ? ORDER BY timestamp
            ''', (city,))
            
            columns = [desc[0] for desc in self.db_cursor.description]
            rows = self.db_cursor.fetchall()
            
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            
            logger.info(f"天气数据已导出到: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
    
    def monitor_weather(self, city: str, interval_minutes: int = 60, duration_hours: int = 24):
        """
        监控天气变化
        
        Args:
            city: 城市名
            interval_minutes: 监控间隔（分钟）
            duration_hours: 监控时长（小时）
        """
        end_time = time.time() + duration_hours * 3600
        
        print(f"开始监控 {city} 天气")
        print(f"监控时长: {duration_hours}小时, 间隔: {interval_minutes}分钟")
        print("-" * 50)
        
        try:
            while time.time() < end_time:
                weather_data = self.get_current_weather(city)
                
                if weather_data:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {city} 天气")
                    print(f"  温度: {weather_data.temperature}°C (体感: {weather_data.feels_like}°C)")
                    print(f"  湿度: {weather_data.humidity}%")
                    print(f"  天气: {weather_data.description}")
                    print(f"  风速: {weather_data.wind_speed} m/s")
                    print(f"  气压: {weather_data.pressure} hPa")
                    print()
                
                # 等待下一次监控
                if time.time() + interval_minutes * 60 < end_time:
                    time.sleep(interval_minutes * 60)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n监控被用户中断")
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        
        print("监控结束")
    
    def close(self):
        """关闭数据库连接"""
        try:
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

def main():
    """主函数"""
    try:
        print("=== 天气数据爬虫 ===")
        print("注意: 部分功能需要API密钥")
        print()
        
        # 选择API源
        print("选择天气API源:")
        print("1. OpenWeatherMap (需要API密钥)")
        print("2. WeatherAPI (需要API密钥)")
        print("3. 使用模拟数据（无需API）")
        
        api_choice = input("请选择 (1-3, 默认3): ").strip()
        
        api_source = WeatherAPI.OPENWEATHER if api_choice == '1' else WeatherAPI.WEATHERAPI if api_choice == '2' else None
        api_key = None
        
        if api_choice in ['1', '2']:
            api_key = input("请输入API密钥: ").strip()
            if not api_key:
                print("未提供API密钥，将使用模拟数据")
                api_source = None
        
        crawler = WeatherCrawler(api_key=api_key, api_source=api_source) if api_source else WeatherCrawler()
        
        print("\n可用功能:")
        print("1. 获取当前天气")
        print("2. 获取天气预报")
        print("3. 查看历史天气")
        print("4. 导出数据到CSV")
        print("5. 监控天气变化")
        print("6. 退出")
        
        choice = input("\n请选择功能 (1-6): ").strip()
        
        if choice == '1':
            city = input("请输入城市名 (例如: Beijing, Shanghai): ").strip()
            if city:
                weather_data = crawler.get_current_weather(city)
                
                if weather_data:
                    print(f"\n=== {weather_data.city} 当前天气 ===")
                    print(f"时间: {weather_data.timestamp}")
                    print(f"温度: {weather_data.temperature}°C")
                    print(f"体感温度: {weather_data.feels_like}°C")
                    print(f"天气: {weather_data.description}")
                    print(f"湿度: {weather_data.humidity}%")
                    print(f"气压: {weather_data.pressure} hPa")
                    print(f"风速: {weather_data.wind_speed} m/s")
                    print(f"风向: {weather_data.wind_direction}°")
                    print(f"能见度: {weather_data.visibility}米")
                    print(f"云量: {weather_data.clouds}%")
                    print(f"日出: {weather_data.sunrise}")
                    print(f"日落: {weather_data.sunset}")
                else:
                    print("获取天气数据失败")
                    
        elif choice == '2':
            city = input("请输入城市名: ").strip()
            if city:
                days = input("预报天数 (1-7, 默认3): ").strip()
                days = int(days) if days.isdigit() and 1 <= int(days) <= 7 else 3
                
                forecast = crawler.get_forecast(city, days)
                
                if forecast:
                    print(f"\n=== {city} {days}天天气预报 ===")
                    for i, day in enumerate(forecast):
                        if i >= days:
                            break
                        date = day.get('date', day.get('datetime', '未知'))
                        print(f"\n{date}:")
                        if 'max_temp' in day:  # WeatherAPI格式
                            print(f"  最高温: {day['max_temp']}°C")
                            print(f"  最低温: {day['min_temp']}°C")
                            print(f"  平均温: {day['avg_temp']}°C")
                            print(f"  天气: {day['condition']}")
                            print(f"  降水量: {day['total_precip']}mm")
                        else:  # OpenWeather格式
                            print(f"  温度: {day['temperature']}°C")
                            print(f"  体感: {day['feels_like']}°C")
                            print(f"  天气: {day['description']}")
                            print(f"  湿度: {day['humidity']}%")
                else:
                    print("获取天气预报失败")
                    
        elif choice == '3':
            city = input("请输入城市名: ").strip()
            if city:
                start_date = input("开始日期 (YYYY-MM-DD, 默认30天前): ").strip()
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                end_date = input("结束日期 (YYYY-MM-DD, 默认今天): ").strip()
                
                historical = crawler.get_historical_data(city, start_date, end_date)
                
                if historical:
                    print(f"\n=== {city} 历史天气 ({start_date} 到 {end_date if end_date else '今天'}) ===")
                    print(f"共 {len(historical)} 条记录")
                    
                    # 显示摘要统计
                    if historical:
                        temps = [d['temperature'] for d in historical if d['temperature']]
                        if temps:
                            print(f"平均温度: {sum(temps)/len(temps):.1f}°C")
                            print(f"最高温度: {max(temps):.1f}°C")
                            print(f"最低温度: {min(temps):.1f}°C")
                        
                        # 显示最近5条记录
                        print(f"\n最近5条记录:")
                        for data in historical[-5:]:
                            dt = data.get('timestamp', '')
                            temp = data.get('temperature', '')
                            desc = data.get('description', '')
                            print(f"  {dt}: {temp}°C, {desc}")
                else:
                    print("无历史数据")
                    
        elif choice == '4':
            city = input("请输入城市名: ").strip()
            if city:
                if crawler.export_to_csv(city):
                    print("数据导出成功")
                else:
                    print("数据导出失败")
                    
        elif choice == '5':
            city = input("请输入城市名: ").strip()
            if city:
                interval = input("监控间隔(分钟，默认60): ").strip()
                interval = int(interval) if interval.isdigit() else 60
                
                duration = input("监控时长(小时，默认24): ").strip()
                duration = int(duration) if duration.isdigit() else 24
                
                crawler.monitor_weather(city, interval, duration)
                
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