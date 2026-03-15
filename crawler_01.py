#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫01: 新闻网站爬虫 - 爬取头条新闻
功能: 爬取今日头条新闻热榜，包括标题、热度、链接
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import logging
import os
from urllib.parse import urljoin

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_01.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ToutiaoNewsCrawler:
    """今日头条新闻爬虫"""
    
    def __init__(self):
        self.base_url = "https://www.toutiao.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_hot_news(self, max_items=20):
        """
        获取热点新闻
        
        Args:
            max_items: 最大获取新闻数量
            
        Returns:
            list: 新闻列表，每个元素是包含标题、热度、链接的字典
        """
        news_list = []
        
        try:
            logger.info("开始爬取今日头条热点新闻...")
            
            # 尝试访问头条热榜页面
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找热点新闻元素（根据实际页面结构调整选择器）
            # 这里使用通用的选择器，实际使用时可能需要根据页面结构调整
            hot_items = []
            
            # 尝试多种选择器模式
            selectors = [
                '.feed-card',
                '.title-box',
                '[data-cell-index]',
                'a[href*="/article/"]',
                'a[href*="/i/"]'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if len(items) > 5:
                    hot_items = items[:max_items]
                    break
            
            if not hot_items:
                # 如果没有找到特定选择器，尝试查找所有新闻链接
                all_links = soup.find_all('a', href=True)
                hot_items = [
                    link for link in all_links 
                    if '/article/' in link['href'] or '/i/' in link['href']
                ][:max_items]
            
            for item in hot_items:
                try:
                    news = {}
                    
                    # 获取标题
                    title_elem = item.find(['div', 'span', 'h3', 'h4'], class_=['title', 'title-box'])
                    if title_elem:
                        news['title'] = title_elem.get_text(strip=True)
                    else:
                        # 尝试获取a标签内的文本
                        link_elem = item if item.name == 'a' else item.find('a')
                        if link_elem:
                            news['title'] = link_elem.get_text(strip=True)
                    
                    # 获取链接
                    link = item.get('href') if item.name == 'a' else None
                    if not link:
                        link_elem = item.find('a')
                        if link_elem:
                            link = link_elem.get('href')
                    
                    if link:
                        # 补全相对链接
                        news['url'] = urljoin(self.base_url, link)
                    
                    # 尝试获取热度
                    hot_elem = item.find(['span', 'div'], class_=['hot', 'heat', 'view'])
                    if hot_elem:
                        news['hot'] = hot_elem.get_text(strip=True)
                    
                    # 验证必要字段
                    if 'title' in news and news['title'] and 'url' in news:
                        news['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        news_list.append(news)
                        logger.debug(f"找到新闻: {news.get('title', '无标题')}")
                        
                except Exception as e:
                    logger.warning(f"处理新闻条目时出错: {e}")
                    continue
            
            logger.info(f"成功爬取到 {len(news_list)} 条新闻")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {e}")
        except Exception as e:
            logger.error(f"爬取过程中出错: {e}")
        
        return news_list
    
    def save_to_file(self, news_list, filename=None):
        """
        保存新闻数据到文件
        
        Args:
            news_list: 新闻列表
            filename: 保存文件名
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'toutiao_news_{timestamp}.json'
        
        try:
            data = {
                'source': '今日头条',
                'crawled_at': datetime.now().isoformat(),
                'count': len(news_list),
                'news': news_list
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件时出错: {e}")
            return False

def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = ToutiaoNewsCrawler()
        
        # 爬取热点新闻
        news_list = crawler.fetch_hot_news(max_items=15)
        
        if news_list:
            # 打印前5条新闻
            print("\n=== 今日头条热点新闻 ===")
            for i, news in enumerate(news_list[:5], 1):
                print(f"{i}. {news.get('title', '无标题')}")
                if 'hot' in news:
                    print(f"   热度: {news['hot']}")
                print(f"   链接: {news.get('url', '无链接')}")
                print()
            
            # 保存数据
            crawler.save_to_file(news_list)
            
            print(f"\n共爬取 {len(news_list)} 条新闻，详细信息已保存到JSON文件")
        else:
            print("未爬取到新闻数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()