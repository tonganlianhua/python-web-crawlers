"""
爬虫 50: V2EX技术社区爬虫
功能: 爬取V2EX技术社区热门话题、回复和用户信息
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import csv
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup


class V2EXCrawler:
    """V2EX技术社区爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # V2EX相关URL
        self.base_url = "https://www.v2ex.com"
        self.latest_url = f"{self.base_url}/recent"
        self.hot_url = f"{self.base_url}/?tab=hot"
        self.node_url = f"{self.base_url}/go"
        self.topic_url = f"{self.base_url}/t"
        self.member_url = f"{self.base_url}/member"
        self.api_url = f"{self.base_url}/api/v2"  # V2EX API v2
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.v2ex.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # V2EX节点分类
        self.node_categories = {
            'tech': ['programming', 'python', 'java', 'javascript', 'go', 'rust', 'linux', 'apple', 'android'],
            'creative': ['design', 'share', 'create', 'ideas', 'qna'],
            'play': ['games', 'anime', 'comic', 'music', 'movie'],
            'apple': ['macos', 'ios', 'iphone', 'ipad', 'apple'],
            'jobs': ['jobs', 'career', 'freelance'],
            'deals': ['deals', 'buy', 'sell'],
            'city': ['beijing', 'shanghai', 'shenzhen', 'guangzhou', 'hangzhou'],
            'qna': ['qna', 'ask', 'help'],
        }
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.topic_cache = {}
        self.member_cache = {}
        self.node_cache = {}
        
    def get_hot_topics(self, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取热门话题
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 热门话题列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取V2EX热门话题")
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.hot_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取热门话题失败，状态码: {response.status_code}")
                return self._retry_get_hot_topics(limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            topics = []
            
            # 查找话题项
            topic_items = soup.select('.cell.item')
            
            for idx, item in enumerate(topic_items[:limit]):
                try:
                    topic = self._parse_topic_item(item, idx + 1)
                    if topic:
                        topics.append(topic)
                except Exception as e:
                    print(f"解析话题项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(topics)} 个热门话题")
            return topics
            
        except requests.exceptions.Timeout:
            print("获取热门话题请求超时")
            return self._retry_get_hot_topics(limit)
        except requests.exceptions.ConnectionError:
            print("获取热门话题连接错误")
            return self._retry_get_hot_topics(limit)
        except Exception as e:
            print(f"获取热门话题时发生未知错误: {str(e)}")
            return None
    
    def _parse_topic_item(self, item, rank: int) -> Optional[Dict]:
        """
        解析话题项
        
        Args:
            item: BeautifulSoup元素
            rank: 排名
            
        Returns:
            Dict: 话题信息
        """
        try:
            # 提取话题标题和链接
            title_elem = item.select_one('.item_title a')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            topic_url = title_elem.get('href', '')
            
            # 提取话题ID
            topic_id = None
            if '/t/' in topic_url:
                match = re.search(r'/t/(\d+)', topic_url)
                if match:
                    topic_id = match.group(1)
            
            # 提取节点信息
            node_elem = item.select_one('.node')
            node_name = node_elem.get_text(strip=True) if node_elem else ''
            node_url = node_elem.get('href') if node_elem else ''
            
            # 提取作者信息
            author_elem = item.select_one('.topic_info strong a')
            author_name = author_elem.get_text(strip=True) if author_elem else ''
            author_url = author_elem.get('href') if author_elem else ''
            
            # 提取回复数
            count_elem = item.select_one('.count_livid')
            if count_elem:
                reply_count = int(count_elem.get_text(strip=True))
            else:
                # 尝试其他选择器
                count_alt = item.select_one('.count_orange')
                reply_count = int(count_alt.get_text(strip=True)) if count_alt else 0
            
            # 提取最后回复时间
            time_elem = item.select_one('.topic_info')
            last_reply_time = ''
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 提取时间部分
                time_match = re.search(r'\d+[分钟小时天前]', time_text)
                last_reply_time = time_match.group(0) if time_match else ''
            
            topic_info = {
                'topic_id': topic_id,
                'title': title,
                'node_name': node_name,
                'node_url': node_url if node_url.startswith('http') else f"{self.base_url}{node_url}",
                'author_name': author_name,
                'author_url': author_url if author_url.startswith('http') else f"{self.base_url}{author_url}",
                'reply_count': reply_count,
                'last_reply_time': last_reply_time,
                'rank': rank,
                'url': topic_url if topic_url.startswith('http') else f"{self.base_url}{topic_url}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return topic_info
            
        except Exception as e:
            print(f"解析话题项时出错: {str(e)}")
            return None
    
    def _retry_get_hot_topics(self, limit: int) -> Optional[List[Dict]]:
        """
        重试获取热门话题
        
        Returns:
            List[Dict]: 热门话题列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_hot_topics(limit)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_latest_topics(self, page: int = 1, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取最新话题
        
        Args:
            page: 页码
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 最新话题列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取V2EX最新话题 (第{page}页)")
            
            # V2EX最近话题页面
            params = {'p': page} if page > 1 else {}
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.latest_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取最新话题失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            topics = []
            
            # 查找话题项
            topic_items = soup.select('.cell.item')
            
            for idx, item in enumerate(topic_items[:limit]):
                try:
                    topic = self._parse_topic_item(item, idx + 1)
                    if topic:
                        topic['source'] = 'latest'
                        topics.append(topic)
                except Exception as e:
                    print(f"解析最新话题项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(topics)} 个最新话题")
            return topics
            
        except Exception as e:
            print(f"获取最新话题时出错: {str(e)}")
            return None
    
    def get_node_topics(self, node_name: str, page: int = 1, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取节点话题
        
        Args:
            node_name: 节点名称
            page: 页码
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 节点话题列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取V2EX节点话题: {node_name} (第{page}页)")
            
            node_url = f"{self.base_url}/go/{node_name}"
            params = {'p': page} if page > 1 else {}
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                node_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取节点话题失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            topics = []
            
            # 查找话题项
            topic_items = soup.select('.cell.item')
            
            for idx, item in enumerate(topic_items[:limit]):
                try:
                    topic = self._parse_topic_item(item, idx + 1)
                    if topic:
                        topic['node'] = node_name
                        topic['source'] = f'node_{node_name}'
                        topics.append(topic)
                except Exception as e:
                    print(f"解析节点话题项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(topics)} 个节点话题")
            return topics
            
        except Exception as e:
            print(f"获取节点话题时出错: {str(e)}")
            return None
    
    def get_topic_detail(self, topic_id: str) -> Optional[Dict]:
        """
        获取话题详细信息
        
        Args:
            topic_id: 话题ID
            
        Returns:
            Dict: 话题详细信息
        """
        # 检查缓存
        if topic_id in self.topic_cache:
            print(f"从缓存获取话题 {topic_id} 的详细信息")
            return self.topic_cache[topic_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取话题详细信息: {topic_id}")
            
            url = f"{self.base_url}/t/{topic_id}"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取话题详情失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取话题信息
            info = {}
            
            # 标题
            title_elem = soup.select_one('#Main .header h1')
            info['title'] = title_elem.get_text(strip=True) if title_elem else ''
            
            # 节点信息
            node_elem = soup.select_one('.header a[href*="/go/"]')
            if node_elem:
                info['node_name'] = node_elem.get_text(strip=True)
                info['node_url'] = node_elem.get('href')
            
            # 作者信息
            author_elem = soup.select_one('.header .gray a')
            if author_elem:
                info['author_name'] = author_elem.get_text(strip=True)
                info['author_url'] = author_elem.get('href')
            
            # 发布时间
            time_elem = soup.select_one('.header .gray')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 提取时间
                time_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', time_text)
                info['created_time'] = time_match.group(0) if time_match else ''
            
            # 话题内容
            content_elem = soup.select_one('.topic_content')
            if content_elem:
                info['content'] = content_elem.get_text(strip=True)
                info['content_html'] = str(content_elem)
            
            # 查看次数
            views_elem = soup.select_one('.topic_stats .gray')
            if views_elem:
                views_text = views_elem.get_text(strip=True)
                views_match = re.search(r'(\d+) 次查看', views_text)
                info['view_count'] = int(views_match.group(1)) if views_match else 0
            
            # 收藏数
            favorite_elem = soup.select_one('.topic_stats a[onclick*="favorite"]')
            if favorite_elem:
                favorite_text = favorite_elem.get_text(strip=True)
                favorite_match = re.search(r'(\d+) 人收藏', favorite_text)
                info['favorite_count'] = int(favorite_match.group(1)) if favorite_match else 0
            
            # 感谢数
            thank_elem = soup.select_one('.topic_stats a[onclick*="thank"]')
            if thank_elem:
                thank_text = thank_elem.get_text(strip=True)
                thank_match = re.search(r'(\d+) 人感谢', thank_text)
                info['thank_count'] = int(thank_match.group(1)) if thank_match else 0
            
            # 完整信息
            detail = {
                'topic_id': topic_id,
                **info,
                'url': url,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.topic_cache[topic_id] = detail
            
            print(f"[{datetime.now()}] 成功获取话题详细信息")
            return detail
            
        except Exception as e:
            print(f"获取话题详细信息时出错: {str(e)}")
            return None
    
    def get_topic_replies(self, topic_id: str, limit: int = 50) -> Optional[List[Dict]]:
        """
        获取话题回复
        
        Args:
            topic_id: 话题ID
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 回复列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取话题回复: {topic_id}")
            
            url = f"{self.base_url}/t/{topic_id}"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取回复失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            replies = []
            
            # 查找回复项
            reply_items = soup.select('.cell[id^="r_"]')
            
            for idx, item in enumerate(reply_items[:limit]):
                try:
                    reply = self._parse_reply_item(item, idx + 1)
                    if reply:
                        replies.append(reply)
                except Exception as e:
                    print(f"解析回复项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(replies)} 个回复")
            return replies
            
        except Exception as e:
            print(f"获取话题回复时出错: {str(e)}")
            return None
    
    def _parse_reply_item(self, item, reply_no: int) -> Optional[Dict]:
        """
        解析回复项
        
        Args:
            item: BeautifulSoup元素
            reply_no: 回复编号
            
        Returns:
            Dict: 回复信息
        """
        try:
            # 回复ID
            reply_id = item.get('id', '').replace('r_', '')
            
            # 作者信息
            author_elem = item.select_one('.dark')
            author_name = author_elem.get_text(strip=True) if author_elem else ''
            author_url = author_elem.get('href') if author_elem else ''
            
            # 回复时间
            time_elem = item.select_one('.ago')
            reply_time = time_elem.get_text(strip=True) if time_elem else ''
            
            # 回复内容
            content_elem = item.select_one('.reply_content')
            content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 感谢数
            thank_elem = item.select_one('.small.fade')
            thank_count = 0
            if thank_elem:
                thank_text = thank_elem.get_text(strip=True)
                thank_match = re.search(r'(\d+) 人感谢', thank_text)
                thank_count = int(thank_match.group(1)) if thank_match else 0
            
            # 楼层
            floor_elem = item.select_one('.no')
            floor_text = floor_elem.get_text(strip=True) if floor_elem else ''
            floor_match = re.search(r'#(\d+)', floor_text)
            floor = int(floor_match.group(1)) if floor_match else reply_no
            
            reply_info = {
                'reply_id': reply_id,
                'reply_no': reply_no,
                'floor': floor,
                'author_name': author_name,
                'author_url': author_url if author_url.startswith('http') else f"{self.base_url}{author_url}",
                'reply_time': reply_time,
                'content': content,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'thank_count': thank_count,
                'url': f"{self.base_url}/t/{reply_id}" if reply_id else '',
            }
            
            return reply_info
            
        except Exception as e:
            print(f"解析回复项时出错: {str(e)}")
            return None
    
    def get_member_info(self, username: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            Dict: 用户信息
        """
        # 检查缓存
        if username in self.member_cache:
            print(f"从缓存获取用户 {username} 的信息")
            return self.member_cache[username]
        
        try:
            print(f"[{datetime.now()}] 开始获取用户信息: {username}")
            
            url = f"{self.base_url}/member/{username}"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取用户信息失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取用户信息
            user_info = {
                'username': username,
                'url': url,
            }
            
            # 基本信息
            profile_elem = soup.select_one('#Main .box')
            if profile_elem:
                # 头像
                avatar_elem = profile_elem.select_one('.avatar')
                if avatar_elem and avatar_elem.get('src'):
                    user_info['avatar_url'] = avatar_elem.get('src')
                
                # 用户名
                name_elem = profile_elem.select_one('h1')
                if name_elem:
                    user_info['display_name'] = name_elem.get_text(strip=True)
                
                # 其他信息
                info_elems = profile_elem.select('.gray')
                for elem in info_elems:
                    text = elem.get_text(strip=True)
                    
                    # 提取创建时间
                    if 'V2EX 第' in text and '号会员' in text:
                        match = re.search(r'V2EX 第 (\d+) 号会员', text)
                        if match:
                            user_info['member_id'] = int(match.group(1))
                    
                    # 提取加入时间
                    if '加入于' in text:
                        match = re.search(r'加入于 (\d{4}-\d{2}-\d{2})', text)
                        if match:
                            user_info['join_date'] = match.group(1)
                    
                    # 提取主题数
                    if '主题数' in text:
                        match = re.search(r'主题数 (\d+)', text)
                        if match:
                            user_info['topic_count'] = int(match.group(1))
                    
                    # 提取回复数
                    if '回复数' in text:
                        match = re.search(r'回复数 (\d+)', text)
                        if match:
                            user_info['reply_count'] = int(match.group(1))
                    
                    # 获取网站
                    website_elem = profile_elem.select_one('a[rel="nofollow external"]')
                    if website_elem:
                        user_info['website'] = website_elem.get('href', '')
            
            # 最近创建的主题
            recent_topics = []
            topic_elems = soup.select('.cell.item')
            for elem in topic_elems[:5]:
                try:
                    title_elem = elem.select_one('.item_title a')
                    if title_elem:
                        topic = {
                            'title': title_elem.get_text(strip=True),
                            'url': title_elem.get('href'),
                        }
                        recent_topics.append(topic)
                except:
                    continue
            
            if recent_topics:
                user_info['recent_topics'] = recent_topics
            
            user_info['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 缓存数据
            self.member_cache[username] = user_info
            
            print(f"[{datetime.now()}] 成功获取用户信息")
            return user_info
            
        except Exception as e:
            print(f"获取用户信息时出错: {str(e)}")
            return None
    
    def get_node_info(self, node_name: str) -> Optional[Dict]:
        """
        获取节点信息
        
        Args:
            node_name: 节点名称
            
        Returns:
            Dict: 节点信息
        """
        try:
            print(f"[{datetime.now()}] 开始获取节点信息: {node_name}")
            
            url = f"{self.base_url}/go/{node_name}"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取节点信息失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取节点信息
            node_info = {
                'node_name': node_name,
                'url': url,
            }
            
            # 节点标题
            title_elem = soup.select_one('#Main h1')
            if title_elem:
                node_info['title'] = title_elem.get_text(strip=True)
            
            # 节点描述
            desc_elem = soup.select_one('.topic_content')
            if desc_elem:
                node_info['description'] = desc_elem.get_text(strip=True)
            
            # 节点统计
            stats_elem = soup.select_one('.inner')
            if stats_elem:
                stats_text = stats_elem.get_text(strip=True)
                
                # 提取主题数
                topic_match = re.search(r'(\d+) 个主题', stats_text)
                if topic_match:
                    node_info['topic_count'] = int(topic_match.group(1))
                
                # 提取今日主题数
                today_match = re.search(r'今日: (\d+)', stats_text)
                if today_match:
                    node_info['today_topic_count'] = int(today_match.group(1))
            
            node_info['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"[{datetime.now()}] 成功获取节点信息")
            return node_info
            
        except Exception as e:
            print(f"获取节点信息时出错: {str(e)}")
            return None
    
    def analyze_topic_metrics(self, topic_detail: Dict, replies: List[Dict]) -> Dict:
        """
        分析话题指标
        
        Args:
            topic_detail: 话题详细信息
            replies: 回复列表
            
        Returns:
            Dict: 分析指标
        """
        try:
            metrics = {
                'view_count': topic_detail.get('view_count', 0),
                'favorite_count': topic_detail.get('favorite_count', 0),
                'thank_count': topic_detail.get('thank_count', 0),
                'reply_count': len(replies) if replies else 0,
            }
            
            # 分析回复数据
            if replies:
                total_replies = len(replies)
                total_thanks = sum(r.get('thank_count', 0) for r in replies)
                avg_thanks = total_thanks / total_replies if total_replies > 0 else 0
                
                # 高质量回复比例（感谢数>0）
                high_quality_replies = sum(1 for r in replies if r.get('thank_count', 0) > 0)
                high_quality_rate = (high_quality_replies / total_replies) * 100 if total_replies > 0 else 0
                
                # 回复长度分析
                reply_lengths = [len(r.get('content', '')) for r in replies]
                avg_reply_length = sum(reply_lengths) / total_replies if total_replies > 0 else 0
                max_reply_length = max(reply_lengths) if reply_lengths else 0
                
                metrics.update({
                    'total_replies_analyzed': total_replies,
                    'total_thanks': total_thanks,
                    'avg_thanks_per_reply': round(avg_thanks, 2),
                    'high_quality_reply_rate': round(high_quality_rate, 2),
                    'avg_reply_length': round(avg_reply_length, 2),
                    'max_reply_length': max_reply_length,
                })
            
            # 计算热度评分
            metrics['hot_score'] = self._calculate_hot_score(topic_detail, replies)
            
            # 计算质量评分
            metrics['quality_score'] = self._calculate_quality_score(topic_detail, replies)
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析话题指标时出错: {str(e)}")
            return {}
    
    def _calculate_hot_score(self, topic_detail: Dict, replies: List[Dict]) -> float:
        """
        计算热度评分
        
        Args:
            topic_detail: 话题详细信息
            replies: 回复列表
            
        Returns:
            float: 热度评分
        """
        try:
            score = 0
            
            # 浏览量权重
            view_count = topic_detail.get('view_count', 0)
            score += min(view_count / 1000 * 30, 30)
            
            # 回复数权重
            reply_count = len(replies) if replies else 0
            score += min(reply_count / 10 * 30, 30)
            
            # 收藏数权重
            favorite_count = topic_detail.get('favorite_count', 0)
            score += min(favorite_count * 10, 20)
            
            # 感谢数权重
            thank_count = topic_detail.get('thank_count', 0)
            score += min(thank_count * 5, 20)
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def _calculate_quality_score(self, topic_detail: Dict, replies: List[Dict]) -> float:
        """
        计算质量评分
        
        Args:
            topic_detail: 话题详细信息
            replies: 回复列表
            
        Returns:
            float: 质量评分
        """
        try:
            score = 0
            
            # 内容长度权重
            content = topic_detail.get('content', '')
            content_length = len(content)
            score += min(content_length / 500 * 20, 20)
            
            # 收藏数权重
            favorite_count = topic_detail.get('favorite_count', 0)
            score += min(favorite_count * 10, 20)
            
            # 回复质量权重
            if replies:
                high_quality_replies = sum(1 for r in replies if r.get('thank_count', 0) > 0)
                high_quality_rate = (high_quality_replies / len(replies)) * 100 if replies else 0
                score += min(high_quality_rate * 0.6, 60)
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def get_popular_nodes(self, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取热门节点
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 热门节点列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取热门节点")
            
            # 从首页获取节点信息
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.base_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取热门节点失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            nodes = []
            
            # 查找节点
            node_elems = soup.select('.box a[href^="/go/"]')
            
            for elem in node_elems[:limit]:
                try:
                    node_url = elem.get('href', '')
                    node_name = node_url.replace('/go/', '')
                    node_title = elem.get_text(strip=True)
                    
                    node_info = {
                        'node_name': node_name,
                        'title': node_title,
                        'url': f"{self.base_url}{node_url}",
                    }
                    nodes.append(node_info)
                except Exception as e:
                    print(f"解析节点时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(nodes)} 个热门节点")
            return nodes
            
        except Exception as e:
            print(f"获取热门节点时出错: {str(e)}")
            return None
    
    def save_to_json(self, data: List[Dict], filename: Optional[str] = None):
        """
        保存数据到JSON文件
        
        Args:
            data: 要保存的数据列表
            filename: 文件名，默认为当前时间戳
        """
        if not data:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"v2ex_topics_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            print(f"保存数据到JSON时出错: {str(e)}")
    
    def run(self, get_hot_topics: bool = True, get_node_topics: bool = True, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            get_hot_topics: 是否获取热门话题
            get_node_topics: 是否获取节点话题
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("V2EX技术社区爬虫开始运行")
        print("=" * 50)
        
        all_topics = []
        
        # 获取热门话题
        if get_hot_topics:
            print("\n获取V2EX热门话题...")
            hot_topics = self.get_hot_topics(limit=15)
            
            if hot_topics:
                for topic in hot_topics[:10]:  # 只处理前10个
                    try:
                        topic_id = topic.get('topic_id')
                        if not topic_id:
                            continue
                        
                        # 获取详细信息
                        detail = self.get_topic_detail(topic_id)
                        if not detail:
                            continue
                        
                        # 获取回复
                        replies = self.get_topic_replies(topic_id, limit=20)
                        
                        # 获取作者信息
                        author_name = topic.get('author_name')
                        author_info = None
                        if author_name:
                            author_info = self.get_member_info(author_name)
                        
                        # 获取节点信息
                        node_name = topic.get('node_name')
                        node_info = None
                        if node_name:
                            node_info = self.get_node_info(node_name)
                        
                        # 分析指标
                        metrics = self.analyze_topic_metrics(detail, replies or [])
                        
                        # 合并数据
                        complete_data = {
                            **topic,
                            **detail,
                            'replies_count': len(replies) if replies else 0,
                            'sample_replies': replies[:5] if replies else [],  # 保存5条样本回复
                            'author_info': author_info,
                            'node_info': node_info,
                            **metrics,
                            'source': 'hot',
                        }
                        
                        all_topics.append(complete_data)
                        
                        print(f"  已处理: {topic.get('title')} (回复: {topic.get('reply_count', 0)})")
                        
                        # 避免请求过快
                        time.sleep(random.uniform(3, 4))
                        
                    except Exception as e:
                        print(f"处理话题 {topic.get('title')} 时出错: {str(e)}")
                        continue
        
        # 获取节点话题
        if get_node_topics:
            popular_nodes = ['python', 'programming', 'share']
            for node in popular_nodes:
                print(f"\n获取节点 {node} 的话题...")
                node_topics = self.get_node_topics(node, page=1, limit=5)
                
                if node_topics:
                    for topic in node_topics[:3]:  # 每个节点只处理前3个
                        try:
                            topic_id = topic.get('topic_id')
                            if not topic_id or any(t.get('topic_id') == topic_id for t in all_topics):
                                continue  # 避免重复
                            
                            # 获取详细信息
                            detail = self.get_topic_detail(topic_id)
                            if not detail:
                                continue
                            
                            # 分析指标
                            metrics = self.analyze_topic_metrics(detail, [])
                            
                            # 合并数据
                            complete_data = {
                                **topic,
                                **detail,
                                **metrics,
                                'source': f'node_{node}',
                            }
                            
                            all_topics.append(complete_data)
                            
                            print(f"  已处理: {topic.get('title')}")
                            
                            time.sleep(random.uniform(2, 3))
                            
                        except Exception as e:
                            print(f"处理节点话题时出错: {str(e)}")
                            continue
        
        # 获取热门节点
        print("\n获取热门节点...")
        popular_nodes = self.get_popular_nodes(limit=10)
        if popular_nodes:
            print(f"热门节点TOP5: {', '.join([n['title'] for n in popular_nodes[:5]])}")
        
        # 保存到文件
        if save_to_file and all_topics:
            self.save_to_json(all_topics)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_topics)} 个话题数据")
        print("=" * 50)
        
        return all_topics


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = V2EXCrawler()
        
        # 运行爬虫
        topics = crawler.run(
            get_hot_topics=True,
            get_node_topics=True,
            save_to_file=True
        )
        
        if topics:
            print(f"\n数据统计:")
            print(f"总话题数: {len(topics)}")
            
            # 按回复数排序
            sorted_topics = sorted(topics, key=lambda x: x.get('reply_count', 0), reverse=True)
            
            print(f"\n回复最多的前5个话题:")
            for idx, topic in enumerate(sorted_topics[:5], 1):
                title = topic.get('title', '')[:50]
                if len(topic.get('title', '')) > 50:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     回复: {topic.get('reply_count', 0)} | "
                      f"浏览: {topic.get('view_count', 0):,} | "
                      f"节点: {topic.get('node_name', '')}")
                print(f"     热度评分: {topic.get('hot_score', 0):.2f} | "
                      f"质量评分: {topic.get('quality_score', 0):.2f}")
                
                if topic.get('author_name'):
                    print(f"     作者: {topic.get('author_name')}")
        else:
            print("未能获取话题数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()