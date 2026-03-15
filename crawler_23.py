#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏数据爬虫 - Steam热门游戏信息
爬取Steam平台热门游戏：游戏名、价格、评分、发行日期、标签等
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
import urllib.parse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SteamGame:
    """Steam游戏数据结构"""
    name: str
    appid: int
    price: str  # 价格（包含货币符号）
    price_original: str  # 原价（如果有折扣）
    discount_percent: int  # 折扣百分比
    release_date: str  # 发行日期
    review_summary: str  # 评价摘要
    review_score: int  # 评价分数（0-100）
    review_count: int  # 评价数量
    developers: List[str]  # 开发商
    publishers: List[str]  # 发行商
    tags: List[str]  # 游戏标签
    description: str  # 游戏描述（简短）
    header_image: str  # 封面图片URL
    store_url: str  # Steam商店链接


class SteamCrawler:
    """Steam游戏爬虫类"""
    
    def __init__(self):
        self.base_url = "https://store.steampowered.com"
        self.api_url = "https://store.steampowered.com/api"
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
        
    def get_featured_games(self, count: int = 50) -> List[SteamGame]:
        """
        获取特色游戏列表
        
        Args:
            count: 获取数量
            
        Returns:
            游戏对象列表
        """
        url = f"{self.base_url}/api/featured"
        
        try:
            logger.info(f"正在获取Steam特色游戏，数量: {count}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            games = []
            # 从多个部分获取游戏
            sections = [
                data.get('featured_win', []),
                data.get('top_sellers', {}).get('items', []),
                data.get('new_releases', {}).get('items', [])
            ]
            
            seen_appids = set()
            
            for section in sections:
                for item in section:
                    if len(games) >= count:
                        break
                    
                    try:
                        appid = item.get('id')
                        if not appid or appid in seen_appids:
                            continue
                        
                        # 获取游戏详情
                        game_detail = self._parse_game_item(item)
                        if game_detail:
                            games.append(game_detail)
                            seen_appids.add(appid)
                            
                    except Exception as e:
                        logger.warning(f"解析游戏数据失败: {e}")
                        continue
            
            logger.info(f"成功获取 {len(games)} 个游戏")
            return games
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return []
    
    def _parse_game_item(self, item: Dict) -> Optional[SteamGame]:
        """解析游戏数据项"""
        try:
            appid = item.get('id')
            if not appid:
                return None
            
            # 价格信息
            price_data = item.get('final_price', 0)
            original_price = item.get('original_price', 0)
            discount_percent = item.get('discount_percent', 0)
            
            # 格式化价格
            price_str = f"¥{price_data/100:.2f}" if price_data > 0 else "免费"
            original_price_str = f"¥{original_price/100:.2f}" if original_price > 0 else ""
            
            # 评价信息
            review_summary = item.get('review_desc', '')
            review_score = 0
            
            # 尝试从摘要中提取评分
            if review_summary:
                if '压倒性好评' in review_summary:
                    review_score = 95
                elif '特别好评' in review_summary:
                    review_score = 85
                elif '多半好评' in review_summary:
                    review_score = 75
                elif '褒贬不一' in review_summary:
                    review_score = 50
                elif '多半差评' in review_summary:
                    review_score = 30
                elif '差评如潮' in review_summary:
                    review_score = 10
            
            game = SteamGame(
                name=item.get('name', ''),
                appid=appid,
                price=price_str,
                price_original=original_price_str,
                discount_percent=discount_percent,
                release_date=item.get('released', '即将推出'),
                review_summary=review_summary,
                review_score=review_score,
                review_count=item.get('reviews_total', 0),
                developers=item.get('developers', []),
                publishers=item.get('publishers', []),
                tags=self._extract_tags(item),
                description=item.get('short_description', '')[:200],
                header_image=item.get('header_image', ''),
                store_url=f"https://store.steampowered.com/app/{appid}/"
            )
            
            return game
            
        except Exception as e:
            logger.warning(f"解析游戏项失败: {e}")
            return None
    
    def _extract_tags(self, item: Dict) -> List[str]:
        """提取游戏标签"""
        tags = []
        
        # 从类型字段提取
        genres = item.get('genres', [])
        for genre in genres:
            if isinstance(genre, dict):
                tags.append(genre.get('description', ''))
            elif isinstance(genre, str):
                tags.append(genre)
        
        # 从类别字段提取
        categories = item.get('categories', [])
        for category in categories:
            if isinstance(category, dict):
                tags.append(category.get('description', ''))
        
        # 去重并过滤空值
        tags = list(set([tag for tag in tags if tag]))
        
        return tags[:10]  # 限制最多10个标签
    
    def get_game_details(self, appid: int) -> Optional[Dict]:
        """
        获取游戏详细信息
        
        Args:
            appid: 游戏ID
            
        Returns:
            游戏详细信息字典
        """
        url = f"{self.api_url}/appdetails"
        params = {
            'appids': appid,
            'l': 'schinese'  # 中文语言
        }
        
        try:
            logger.info(f"正在获取游戏详情: {appid}")
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            game_data = data.get(str(appid), {})
            
            if not game_data.get('success'):
                logger.error(f"获取游戏详情失败: {appid}")
                return None
            
            return game_data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
    
    def search_games(self, query: str, count: int = 20) -> List[SteamGame]:
        """
        搜索游戏
        
        Args:
            query: 搜索关键词
            count: 返回数量
            
        Returns:
            游戏对象列表
        """
        url = f"{self.base_url}/search/results"
        params = {
            'term': query,
            'count': count,
            'l': 'schinese',
            'json': 1
        }
        
        try:
            logger.info(f"正在搜索游戏: {query}")
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            games = []
            for item in data.get('items', []):
                try:
                    # 解析搜索结果
                    game = self._parse_search_result(item)
                    if game:
                        games.append(game)
                        
                except Exception as e:
                    logger.warning(f"解析搜索结果失败: {e}")
                    continue
            
            logger.info(f"搜索到 {len(games)} 个相关游戏")
            return games
            
        except Exception as e:
            logger.error(f"搜索游戏失败: {e}")
            return []
    
    def _parse_search_result(self, item: Dict) -> Optional[SteamGame]:
        """解析搜索结果"""
        try:
            # 从搜索结果中提取基本信息
            name = item.get('name', '')
            appid = item.get('id', 0)
            price = item.get('price', {}).get('final', '免费')
            discount_percent = item.get('discount_percent', 0)
            
            game = SteamGame(
                name=name,
                appid=appid,
                price=price,
                price_original=item.get('price', {}).get('initial', ''),
                discount_percent=discount_percent,
                release_date='',
                review_summary=item.get('review_summary', ''),
                review_score=0,
                review_count=0,
                developers=[],
                publishers=[],
                tags=[],
                description='',
                header_image=item.get('tiny_image', ''),
                store_url=f"https://store.steampowered.com/app/{appid}/"
            )
            
            return game
            
        except Exception as e:
            logger.warning(f"解析搜索结果项失败: {e}")
            return None
    
    def analyze_games(self, games: List[SteamGame]) -> Dict:
        """
        分析游戏数据
        
        Args:
            games: 游戏对象列表
            
        Returns:
            分析结果字典
        """
        if not games:
            return {}
        
        try:
            # 统计信息
            total_games = len(games)
            free_games = sum(1 for game in games if game.price == "免费" or game.price == "0")
            discounted_games = sum(1 for game in games if game.discount_percent > 0)
            
            # 价格统计（排除免费游戏）
            prices = []
            for game in games:
                if game.price != "免费" and game.price != "0":
                    # 提取数字价格
                    match = re.search(r'[\d.]+', game.price)
                    if match:
                        prices.append(float(match.group()))
            
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # 标签频率
            tag_counts = {}
            for game in games:
                for tag in game.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # 评价统计
            positive_games = sum(1 for game in games if game.review_score >= 70)
            mixed_games = sum(1 for game in games if 40 <= game.review_score < 70)
            negative_games = sum(1 for game in games if game.review_score < 40)
            
            return {
                'total_games': total_games,
                'free_games': free_games,
                'free_percentage': (free_games / total_games * 100) if total_games else 0,
                'discounted_games': discounted_games,
                'discounted_percentage': (discounted_games / total_games * 100) if total_games else 0,
                'avg_price': avg_price,
                'top_tags': top_tags,
                'positive_games': positive_games,
                'mixed_games': mixed_games,
                'negative_games': negative_games,
                'positive_percentage': (positive_games / total_games * 100) if total_games else 0
            }
            
        except Exception as e:
            logger.error(f"分析游戏数据失败: {e}")
            return {}
    
    def save_to_csv(self, games: List[SteamGame], filename: str = "steam_games.csv"):
        """
        保存游戏数据到CSV文件
        
        Args:
            games: 游戏对象列表
            filename: 输出文件名
        """
        if not games:
            logger.warning("没有游戏数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'name', 'appid', 'price', 'price_original', 'discount_percent', 
                    'release_date', 'review_summary', 'review_score', 'review_count',
                    'developers', 'publishers', 'tags', 'description', 'header_image', 'store_url'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for game in games:
                    row = game.__dict__.copy()
                    # 转换列表为字符串
                    row['developers'] = ', '.join(row['developers'])
                    row['publishers'] = ', '.join(row['publishers'])
                    row['tags'] = ', '.join(row['tags'])
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(games)} 个游戏数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("Steam游戏数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = SteamCrawler()
    
    try:
        # 1. 获取特色游戏
        print("正在爬取Steam特色游戏...")
        games = crawler.get_featured_games(count=30)
        
        if not games:
            print("未获取到游戏数据，程序退出")
            return
        
        # 2. 显示统计信息
        print(f"\n成功获取 {len(games)} 个游戏:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_games(games)
        
        if analysis:
            print(f"总计游戏: {analysis['total_games']}")
            print(f"免费游戏: {analysis['free_games']} ({analysis['free_percentage']:.1f}%)")
            print(f"折扣游戏: {analysis['discounted_games']} ({analysis['discounted_percentage']:.1f}%)")
            print(f"平均价格: ¥{analysis['avg_price']:.2f}")
            print(f"好评游戏: {analysis['positive_games']} ({analysis['positive_percentage']:.1f}%)")
            
            print("\n最流行的游戏标签:")
            for tag, count in analysis['top_tags'][:5]:
                print(f"  {tag}: {count} 个游戏")
        
        # 3. 显示前5个游戏详情
        print("\n热门游戏 TOP 5:")
        print("-" * 30)
        for i, game in enumerate(games[:5], 1):
            print(f"{i}. {game.name}")
            print(f"   价格: {game.price}", end="")
            if game.price_original:
                print(f" (-{game.discount_percent}%)", end="")
            print()
            print(f"   评价: {game.review_summary} ({game.review_score}/100)")
            print(f"   发行: {game.release_date}")
            
            if game.tags:
                print(f"   标签: {', '.join(game.tags[:3])}")
            
            print()
        
        # 4. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"steam_games_{timestamp}.csv"
        
        crawler.save_to_csv(games, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 5. 获取并展示一个游戏的详细信息
        if games:
            sample_game = games[0]
            print(f"\n获取游戏 '{sample_game.name[:20]}...' 的详细信息:")
            details = crawler.get_game_details(sample_game.appid)
            
            if details:
                print(f"完整名称: {details.get('name')}")
                print(f"详细描述: {details.get('short_description', '')[:100]}...")
                
                # 系统要求
                pc_requirements = details.get('pc_requirements', {})
                if isinstance(pc_requirements, dict):
                    requirements = pc_requirements.get('minimum', '')
                    if requirements:
                        # 清理HTML标签
                        requirements = re.sub('<[^<]+?>', '', requirements)[:200]
                        print(f"最低配置: {requirements}...")
        
        # 6. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示搜索功能:")
        search_query = input("请输入要搜索的游戏名称（直接回车跳过）: ").strip()
        
        if search_query:
            print(f"\n正在搜索 '{search_query}'...")
            search_results = crawler.search_games(search_query, count=10)
            
            if search_results:
                print(f"找到 {len(search_results)} 个相关结果:")
                for i, game in enumerate(search_results[:5], 1):
                    print(f"{i}. {game.name} - {game.price}")
            else:
                print("未找到相关游戏")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()