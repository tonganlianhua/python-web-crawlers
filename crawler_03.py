#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫03: 社交媒体数据爬虫 - 微博热搜爬取
功能: 爬取微博热搜榜，包括热搜词、热度、分类等
注意: 本爬虫仅用于学习研究，请遵守网站robots.txt和法律法规
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
import logging
import os
from typing import Dict, List, Optional
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_03.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WeiboTrendingCrawler:
    """微博热搜爬虫"""
    
    def __init__(self):
        self.base_url = "https://s.weibo.com"
        self.trending_url = f"{self.base_url}/top/summary"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://weibo.com/',
            'Cookie': 'SUB=_2AkMSpYJSf8NxqwJRmP0QyW7kZYt2zgrEieKlc2V3JRMxHRl-yT9jqlEStRB6P_d3eK6JbP7SdYwGpOcJxwTpDvB4s9V5'  # 示例cookie，实际需要更新
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_trending_list(self, category: str = "realtime") -> List[Dict]:
        """
        获取热搜列表
        
        Args:
            category: 热搜分类
                - realtime: 实时热搜
                - hot: 热门热搜
                - news: 新闻热搜
                - entertainment: 娱乐热搜
                
        Returns:
            list: 热搜列表
        """
        trending_list = []
        
        try:
            logger.info(f"开始爬取微博热搜榜，分类: {category}")
            
            params = {
                'cate': category
            }
            
            response = self.session.get(self.trending_url, params=params, timeout=15)
            response.raise_for_status()
            
            # 检查是否被重定向到登录页
            if 'passport.weibo.com' in response.url:
                logger.warning("需要登录，尝试使用备用方法")
                return self._fetch_trending_backup()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找热搜表格
            table = soup.find('table')
            if not table:
                logger.warning("未找到热搜表格，尝试备用选择器")
                return self._fetch_trending_backup()
            
            # 解析热搜行
            rows = table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                try:
                    trend = {}
                    
                    # 获取排名
                    rank_elem = row.find('td', class_='td-01')
                    if rank_elem:
                        rank_text = rank_elem.get_text(strip=True)
                        if rank_text.isdigit():
                            trend['rank'] = int(rank_text)
                    
                    # 获取热搜词和链接
                    keyword_elem = row.find('td', class_='td-02')
                    if keyword_elem:
                        link_elem = keyword_elem.find('a')
                        if link_elem:
                            trend['keyword'] = link_elem.get_text(strip=True)
                            trend['url'] = self.base_url + link_elem.get('href', '')
                            
                            # 获取热度标签
                            tag_elem = keyword_elem.find('span')
                            if tag_elem:
                                tag_text = tag_elem.get_text(strip=True)
                                trend['tag'] = tag_text
                    
                    # 获取热度值
                    hot_elem = row.find('td', class_='td-03')
                    if hot_elem:
                        hot_text = hot_elem.get_text(strip=True)
                        # 提取数字
                        nums = re.findall(r'\d+', hot_text)
                        if nums:
                            trend['hot_value'] = int(''.join(nums))
                    
                    # 验证必要字段
                    if trend.get('keyword') and trend.get('rank'):
                        trend['category'] = category
                        trend['crawled_at'] = datetime.now().isoformat()
                        trend['trend_id'] = hashlib.md5(
                            f"{trend['keyword']}_{trend['rank']}".encode()
                        ).hexdigest()[:8]
                        
                        trending_list.append(trend)
                        
                except Exception as e:
                    logger.warning(f"处理热搜条目时出错: {e}")
                    continue
            
            logger.info(f"成功爬取到 {len(trending_list)} 条热搜")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {e}")
        except Exception as e:
            logger.error(f"爬取过程中出错: {e}")
        
        return trending_list
    
    def _fetch_trending_backup(self) -> List[Dict]:
        """备用方法获取热搜（通过API或备用页面）"""
        trending_list = []
        
        try:
            # 尝试使用微博API（可能需要更新token）
            api_url = "https://weibo.com/ajax/side/hotSearch"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://weibo.com/'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 解析API返回的数据结构
                if 'data' in data and 'realtime' in data['data']:
                    for i, item in enumerate(data['data']['realtime'], 1):
                        trend = {
                            'rank': i,
                            'keyword': item.get('word', ''),
                            'hot_value': item.get('num', 0),
                            'category': 'realtime',
                            'crawled_at': datetime.now().isoformat(),
                            'trend_id': hashlib.md5(
                                f"{item.get('word', '')}_{i}".encode()
                            ).hexdigest()[:8]
                        }
                        
                        # 获取链接
                        if 'word_scheme' in item:
                            trend['url'] = f"https://s.weibo.com/weibo?q={item['word_scheme']}"
                        
                        trending_list.append(trend)
                    
                    logger.info(f"通过API获取到 {len(trending_list)} 条热搜")
                else:
                    logger.warning("API返回数据格式异常")
            else:
                logger.warning(f"API请求失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"备用方法获取热搜时出错: {e}")
        
        return trending_list
    
    def get_trend_details(self, trend_url: str) -> Optional[Dict]:
        """
        获取热搜详情（相关微博）
        
        Args:
            trend_url: 热搜链接
            
        Returns:
            dict: 热搜详情
        """
        try:
            logger.info(f"获取热搜详情: {trend_url}")
            
            response = self.session.get(trend_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'trend_url': trend_url,
                'crawled_at': datetime.now().isoformat(),
                'weibos': []
            }
            
            # 查找相关微博
            weibo_items = soup.select('.card-wrap')
            
            for item in weibo_items[:10]:  # 只取前10条
                try:
                    weibo = {}
                    
                    # 获取用户信息
                    user_elem = item.select_one('.name')
                    if user_elem:
                        weibo['user'] = user_elem.get_text(strip=True)
                    
                    # 获取微博内容
                    content_elem = item.select_one('.txt')
                    if content_elem:
                        weibo['content'] = content_elem.get_text(strip=True)
                    
                    # 获取发布时间
                    time_elem = item.select_one('.from a')
                    if time_elem:
                        weibo['publish_time'] = time_elem.get_text(strip=True)
                    
                    # 获取转发、评论、点赞数
                    stats = item.select('.act .line')
                    if len(stats) >= 3:
                        weibo['repost'] = stats[0].get_text(strip=True)
                        weibo['comment'] = stats[1].get_text(strip=True)
                        weibo['like'] = stats[2].get_text(strip=True)
                    
                    if weibo.get('content'):
                        weibo['weibo_id'] = hashlib.md5(
                            f"{weibo.get('content', '')[:20]}".encode()
                        ).hexdigest()[:8]
                        details['weibos'].append(weibo)
                        
                except Exception as e:
                    logger.debug(f"处理微博条目时出错: {e}")
                    continue
            
            logger.info(f"获取到 {len(details['weibos'])} 条相关微博")
            return details
            
        except Exception as e:
            logger.error(f"获取热搜详情时出错: {e}")
            return None
    
    def analyze_trending_data(self, trending_list: List[Dict]) -> Dict:
        """
        分析热搜数据
        
        Args:
            trending_list: 热搜列表
            
        Returns:
            dict: 分析结果
        """
        analysis = {
            'total_count': len(trending_list),
            'average_hot': 0,
            'max_hot': 0,
            'min_hot': float('inf'),
            'hot_keywords': [],
            'categories': {}
        }
        
        if not trending_list:
            return analysis
        
        total_hot = 0
        hot_count = 0
        
        for trend in trending_list:
            # 统计热度
            hot_value = trend.get('hot_value')
            if isinstance(hot_value, (int, float)):
                total_hot += hot_value
                hot_count += 1
                
                if hot_value > analysis['max_hot']:
                    analysis['max_hot'] = hot_value
                    analysis['hottest_keyword'] = trend.get('keyword')
                
                if hot_value < analysis['min_hot']:
                    analysis['min_hot'] = hot_value
            
            # 按分类统计
            category = trend.get('category', 'unknown')
            if category not in analysis['categories']:
                analysis['categories'][category] = 0
            analysis['categories'][category] += 1
            
            # 收集高热关键词
            if hot_value and hot_value > 1000000:  # 热度超过100万
                analysis['hot_keywords'].append({
                    'keyword': trend.get('keyword'),
                    'hot': hot_value,
                    'rank': trend.get('rank')
                })
        
        if hot_count > 0:
            analysis['average_hot'] = total_hot / hot_count
        
        # 按热度排序
        analysis['hot_keywords'].sort(key=lambda x: x.get('hot', 0), reverse=True)
        
        return analysis
    
    def save_trending_data(self, trending_list: List[Dict], filename: str = None):
        """
        保存热搜数据
        
        Args:
            trending_list: 热搜列表
            filename: 保存文件名
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'weibo_trending_{timestamp}.json'
        
        try:
            data = {
                'source': '微博热搜',
                'crawled_at': datetime.now().isoformat(),
                'count': len(trending_list),
                'trends': trending_list,
                'analysis': self.analyze_trending_data(trending_list)
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"热搜数据已保存到: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据时出错: {e}")
            return False

def main():
    """主函数"""
    try:
        crawler = WeiboTrendingCrawler()
        
        print("=== 微博热搜爬虫 ===")
        print("1. 获取实时热搜")
        print("2. 获取热搜详情")
        print("3. 分析热搜数据")
        print("4. 退出")
        
        choice = input("\n请选择功能 (1-4): ").strip()
        
        if choice == '1':
            print("\n热搜分类:")
            print("1. 实时热搜")
            print("2. 热门热搜")
            print("3. 新闻热搜")
            print("4. 娱乐热搜")
            
            cat_choice = input("请选择分类 (1-4, 默认1): ").strip()
            categories = ['realtime', 'hot', 'news', 'entertainment']
            category = categories[int(cat_choice) - 1] if cat_choice.isdigit() and 1 <= int(cat_choice) <= 4 else 'realtime'
            
            trending_list = crawler.fetch_trending_list(category)
            
            if trending_list:
                print(f"\n=== 微博{category}热搜榜 ===")
                for trend in trending_list[:20]:  # 显示前20条
                    rank = trend.get('rank', 0)
                    keyword = trend.get('keyword', '未知')
                    hot = trend.get('hot_value', 0)
                    tag = trend.get('tag', '')
                    
                    print(f"{rank:2d}. {keyword}")
                    if hot:
                        print(f"    热度: {hot:,}")
                    if tag:
                        print(f"    标签: {tag}")
                    print()
                
                # 保存数据
                crawler.save_trending_data(trending_list)
                
                # 显示分析结果
                analysis = crawler.analyze_trending_data(trending_list)
                print(f"\n数据分析:")
                print(f"总热搜数: {analysis['total_count']}")
                print(f"平均热度: {analysis['average_hot']:,.0f}")
                print(f"最高热度: {analysis['max_hot']:,} ({analysis.get('hottest_keyword', '无')})")
                
            else:
                print("未获取到热搜数据")
                
        elif choice == '2':
            keyword = input("请输入热搜关键词或URL: ").strip()
            
            if 's.weibo.com' in keyword:
                url = keyword
            else:
                url = f"https://s.weibo.com/weibo?q={keyword}"
            
            details = crawler.get_trend_details(url)
            
            if details and details.get('weibos'):
                print(f"\n=== 热搜详情: {keyword} ===")
                for i, weibo in enumerate(details['weibos'][:5], 1):
                    print(f"\n{i}. 用户: {weibo.get('user', '未知')}")
                    print(f"   内容: {weibo.get('content', '')[:100]}...")
                    print(f"   时间: {weibo.get('publish_time', '未知')}")
                    print(f"   转发: {weibo.get('repost', '0')} | "
                          f"评论: {weibo.get('comment', '0')} | "
                          f"点赞: {weibo.get('like', '0')}")
                
                # 保存详情
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'weibo_details_{hashlib.md5(keyword.encode()).hexdigest()[:8]}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(details, f, ensure_ascii=False, indent=2)
                print(f"\n详情已保存到: {filename}")
            else:
                print("未获取到热搜详情")
                
        elif choice == '3':
            # 获取数据并分析
            trending_list = crawler.fetch_trending_list()
            
            if trending_list:
                analysis = crawler.analyze_trending_data(trending_list)
                
                print(f"\n=== 热搜数据分析 ===")
                print(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"总热搜数: {analysis['total_count']}")
                print(f"平均热度: {analysis['average_hot']:,.0f}")
                print(f"最高热度: {analysis['max_hot']:,}")
                print(f"最低热度: {analysis['min_hot']:,}")
                
                print(f"\n分类分布:")
                for cat, count in analysis['categories'].items():
                    print(f"  {cat}: {count}条")
                
                if analysis['hot_keywords']:
                    print(f"\n高热关键词 (热度>100万):")
                    for item in analysis['hot_keywords'][:10]:
                        print(f"  {item['keyword']}: {item['hot']:,} (排名: {item['rank']})")
            else:
                print("无数据可分析")
                
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