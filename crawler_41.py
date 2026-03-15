"""
爬虫 41: 微博热搜爬虫
功能: 爬取微博实时热搜榜数据
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import random
import re
from bs4 import BeautifulSoup


class WeiboTrendingCrawler:
    """微博热搜爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        self.base_url = "https://weibo.com/ajax/side/hotSearch"
        self.hotband_url = "https://weibo.com/ajax/statuses/hot_band"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://weibo.com/',
            'Origin': 'https://weibo.com',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 错误计数器
        self.error_count = 0
        self.max_retries = 3
        
    def get_hot_search(self) -> Optional[Dict]:
        """
        获取微博热搜数据
        
        Returns:
            Dict: 热搜数据字典，包含热搜列表和统计信息
        """
        try:
            print(f"[{datetime.now()}] 开始获取微博热搜数据...")
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(1, 2))
            
            # 发送请求
            response = self.session.get(
                self.hotband_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                return self._retry_get_hot_search()
            
            # 解析JSON数据
            data = response.json()
            
            if not data.get('ok'):
                print("数据获取失败，返回状态异常")
                return None
            
            # 提取热搜数据
            hot_searches = []
            band_list = data.get('data', {}).get('band_list', [])
            
            for idx, item in enumerate(band_list[:50], 1):
                try:
                    hot_item = {
                        'rank': idx,
                        'keyword': item.get('word', ''),
                        'hot_value': item.get('num', 0),
                        'label_name': item.get('label_name', ''),
                        'category': item.get('category', ''),
                        'url': f"https://s.weibo.com/weibo?q={item.get('word', '')}"
                    }
                    hot_searches.append(hot_item)
                except Exception as e:
                    print(f"处理热搜项 {idx} 时出错: {str(e)}")
                    continue
            
            result = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total': len(hot_searches),
                'hot_searches': hot_searches,
                'source': 'weibo_hotband',
                'status': 'success'
            }
            
            print(f"[{datetime.now()}] 成功获取 {len(hot_searches)} 条热搜数据")
            return result
            
        except requests.exceptions.Timeout:
            print("请求超时")
            return self._retry_get_hot_search()
        except requests.exceptions.ConnectionError:
            print("连接错误")
            return self._retry_get_hot_search()
        except json.JSONDecodeError:
            print("JSON解析错误")
            return None
        except Exception as e:
            print(f"获取热搜数据时发生未知错误: {str(e)}")
            return None
    
    def _retry_get_hot_search(self) -> Optional[Dict]:
        """
        重试获取热搜数据
        
        Returns:
            Dict: 热搜数据字典，重试失败返回None
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            print(f"第 {self.error_count} 次重试...")
            time.sleep(2 ** self.error_count)  # 指数退避
            return self.get_hot_search()
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_hot_search_detail(self, keyword: str) -> Optional[List[Dict]]:
        """
        获取热搜关键词的详细微博内容
        
        Args:
            keyword: 热搜关键词
            
        Returns:
            List[Dict]: 相关微博内容列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取热搜 '{keyword}' 的详细内容...")
            
            # 构造搜索URL
            search_url = f"https://weibo.com/ajax/statuses/search"
            params = {
                'q': keyword,
                'count': 20,
                'page': 1
            }
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取详细内容失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            tweets = data.get('data', {}).get('list', [])
            
            detailed_tweets = []
            for tweet in tweets[:10]:  # 只取前10条
                try:
                    tweet_info = {
                        'user_name': tweet.get('user', {}).get('screen_name', ''),
                        'user_followers': tweet.get('user', {}).get('followers_count', 0),
                        'text': self._clean_text(tweet.get('text', '')),
                        'created_at': tweet.get('created_at', ''),
                        'reposts_count': tweet.get('reposts_count', 0),
                        'comments_count': tweet.get('comments_count', 0),
                        'attitudes_count': tweet.get('attitudes_count', 0),
                        'url': f"https://weibo.com/{tweet.get('user', {}).get('id', '')}/{tweet.get('id', '')}"
                    }
                    detailed_tweets.append(tweet_info)
                except Exception as e:
                    print(f"处理微博内容时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(detailed_tweets)} 条相关微博")
            return detailed_tweets
            
        except Exception as e:
            print(f"获取热搜详细内容时出错: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """
        清理微博文本，移除HTML标签和多余空格
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', text)
        # 移除多余空格
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        # 移除表情符号
        clean_text = re.sub(r'\[.*?\]', '', clean_text)
        
        return clean_text[:200]  # 限制长度
    
    def save_to_json(self, data: Dict, filename: Optional[str] = None):
        """
        保存数据到JSON文件
        
        Args:
            data: 要保存的数据
            filename: 文件名，默认为当前时间戳
        """
        if not data:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"weibo_hotsearch_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            # 确保目录存在
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到: {filepath}")
        except Exception as e:
            print(f"保存数据到文件时出错: {str(e)}")
    
    def run(self, save_to_file: bool = True) -> Optional[Dict]:
        """
        运行爬虫主程序
        
        Args:
            save_to_file: 是否保存到文件
            
        Returns:
            Dict: 爬取的数据
        """
        print("=" * 50)
        print("微博热搜爬虫开始运行")
        print("=" * 50)
        
        # 重置错误计数器
        self.error_count = 0
        
        # 获取热搜数据
        hot_search_data = self.get_hot_search()
        
        if not hot_search_data:
            print("未能获取热搜数据")
            return None
        
        # 如果需要，获取热搜详细内容
        if hot_search_data.get('hot_searches'):
            for idx, item in enumerate(hot_search_data['hot_searches'][:3]):  # 只处理前3个热搜
                keyword = item.get('keyword')
                if keyword:
                    details = self.get_hot_search_detail(keyword)
                    if details:
                        hot_search_data['hot_searches'][idx]['details'] = details
        
        # 保存到文件
        if save_to_file and hot_search_data:
            self.save_to_json(hot_search_data)
        
        print("=" * 50)
        print("微博热搜爬虫运行完成")
        print("=" * 50)
        
        return hot_search_data


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = WeiboTrendingCrawler()
        
        # 运行爬虫
        data = crawler.run(save_to_file=True)
        
        if data:
            # 打印简要结果
            print(f"\n热搜统计:")
            print(f"时间: {data.get('timestamp')}")
            print(f"总数: {data.get('total')} 条")
            print(f"\n热搜前5名:")
            for item in data.get('hot_searches', [])[:5]:
                print(f"  {item['rank']}. {item['keyword']} (热度: {item['hot_value']})")
        else:
            print("未能获取数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()