#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫使用示例
演示如何使用新创建的爬虫程序
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

def demo_weather_crawler():
    """演示天气预报爬虫"""
    print("=" * 60)
    print("天气预报爬虫演示")
    print("=" * 60)
    
    try:
        # 动态导入
        from crawler_11 import WeatherCrawler
        
        # 创建爬虫实例
        crawler = WeatherCrawler(timeout=15)
        
        # 获取单个城市的天气
        print("获取北京天气预报...")
        weather_data = crawler.fetch_weather("北京")
        
        if weather_data:
            print(f"城市: {weather_data['city']}")
            print(f"更新时间: {weather_data['timestamp']}")
            print(f"数据来源: {weather_data['source']}")
            
            if weather_data['today']:
                print("今日天气:")
                for key, value in weather_data['today'].items():
                    print(f"  {key}: {value}")
            
            # 保存数据
            crawler.save_to_json(weather_data, "weather_beijing.json")
            print("数据已保存到 weather_beijing.json")
        else:
            print("无法获取天气数据")
    
    except Exception as e:
        print(f"天气预报爬虫演示失败: {e}")

def demo_exchange_rate_crawler():
    """演示汇率爬虫"""
    print("\n" + "=" * 60)
    print("实时汇率爬虫演示")
    print("=" * 60)
    
    try:
        from crawler_20 import ExchangeRateCrawler
        
        # 创建爬虫实例
        crawler = ExchangeRateCrawler(timeout=15)
        
        # 获取最新汇率
        print("获取美元(USD)最新汇率...")
        rates_data = crawler.get_latest_rates('USD', 'exchangerate_api')
        
        if rates_data:
            print(f"数据源: {rates_data['source']}")
            print(f"基准货币: {rates_data['base_currency']}")
            print(f"更新时间: {rates_data.get('timestamp', '未知')}")
            
            # 显示几种主要货币的汇率
            major_currencies = ['EUR', 'GBP', 'JPY', 'CNY']
            print("\n主要货币汇率:")
            for currency in major_currencies:
                if currency in rates_data['rates']:
                    rate = rates_data['rates'][currency]
                    print(f"  {currency}: 1 USD = {rate:.4f}")
            
            # 货币换算
            print("\n货币换算演示:")
            conversion = crawler.convert_currency(100, 'USD', 'CNY', 'exchangerate_api')
            if conversion:
                print(f"100 USD = {conversion['converted_amount']:.2f} CNY")
                print(f"汇率: 1 USD = {conversion['exchange_rate']:.4f} CNY")
            
            # 保存数据
            crawler.save_to_json(rates_data, "exchange_rates.json")
            print("\n汇率数据已保存到 exchange_rates.json")
        else:
            print("无法获取汇率数据")
    
    except Exception as e:
        print(f"汇率爬虫演示失败: {e}")

def demo_stock_crawler():
    """演示股票数据爬虫"""
    print("\n" + "=" * 60)
    print("股票数据爬虫演示")
    print("=" * 60)
    
    try:
        from crawler_12 import StockCrawler
        
        # 创建爬虫实例
        crawler = StockCrawler(timeout=15)
        
        # 获取股票数据
        print("获取贵州茅台股票数据...")
        stock_data = crawler.fetch_single_stock("贵州茅台")
        
        if stock_data:
            print(f"股票名称: {stock_data['name']}")
            print(f"股票代码: {stock_data['code']}")
            print(f"更新时间: {stock_data['timestamp']}")
            
            data = stock_data['data']
            print("\n关键指标:")
            if 'current_price' in data:
                print(f"  当前价格: {data['current_price']} 元")
            if 'change_percent' in data:
                print(f"  涨跌幅: {data['change_percent']}%")
            if 'volume' in data:
                volume_wan = data['volume'] / 10000  # 转换为万手
                print(f"  成交量: {volume_wan:.2f} 万手")
            
            # 保存数据
            crawler.save_to_json(stock_data, "stock_moutai.json")
            print("\n股票数据已保存到 stock_moutai.json")
        else:
            print("无法获取股票数据")
    
    except Exception as e:
        print(f"股票爬虫演示失败: {e}")

def main():
    """主函数"""
    print("Python爬虫程序使用示例")
    print("=" * 60)
    
    # 演示几个爬虫
    demo_weather_crawler()
    demo_exchange_rate_crawler()
    demo_stock_crawler()
    
    print("\n" + "=" * 60)
    print("其他可用爬虫:")
    print("- crawler_13.py: 电影信息爬虫（豆瓣电影）")
    print("- crawler_14.py: GitHub数据爬虫")
    print("- crawler_15.py: Reddit帖子爬虫")
    print("- crawler_16.py: 技术博客爬虫")
    print("- crawler_17.py: 商品价格监控爬虫")
    print("- crawler_18.py: 招聘信息爬虫")
    print("- crawler_19.py: 学术论文爬虫")
    print("\n详细使用说明请查看各爬虫文件的main()函数")
    print("或查看 README_NEW_CRAWLERS.md 文档")

if __name__ == "__main__":
    # 检查基本依赖
    try:
        import requests
        import bs4
        print("基本依赖检查通过")
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请运行: pip install requests beautifulsoup4")
        sys.exit(1)
    
    main()