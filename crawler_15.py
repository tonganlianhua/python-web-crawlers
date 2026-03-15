#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit帖子爬虫 - 获取Reddit热门帖子和评论
网站：Reddit (https://www.reddit.com)
功能：获取热门帖子、评论、用户信息等
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditCrawler:
    """Reddit数据爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None, client_id: str = None, client_secret: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent（必须设置）
            client_id: Reddit API客户端ID（可选）
            client_secret: Reddit API客户端密钥（可选）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "https://www.reddit.com"
        self.api_url = "https://oauth.reddit.com" if client_id else "https://www.reddit.com"
        
        # Reddit要求设置唯一的User-Agent
        self.user_agent = user_agent or (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 设置请求头
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        self.session.headers.update(headers)
        
        # API认证信息
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        
        # 如果提供了客户端ID和密钥，获取访问令牌
        if client_id and client_secret:
            self._authenticate()
        
        # 速率限制跟踪
        self.request_count = 0
        self.last_request_time = time.time()
    
    def _authenticate(self) -> bool:
        """
        使用OAuth2认证获取访问令牌
        
        Returns:
            认证成功返回True，失败返回False
        """
        try:
            auth_url = "https://www.reddit.com/api/v1/access_token"
            auth_data = {
                'grant_type': 'client_credentials',
                'duration': 'temporary',
            }
            
            auth_headers = {
                'User-Agent': self.user_agent,
            }
            
            # 使用基本认证
            response = requests.post(
                auth_url,
                data=auth_data,
                auth=(self.client_id, self.client_secret),
                headers=auth_headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            auth_response = response.json()
            
            if 'access_token' in auth_response:
                self.access_token = auth_response['access_token']
                # 更新会话头
                self.session.headers.update({
                    'Authorization': f'bearer {self.access_token}'
                })
                logger.info("Reddit API认证成功")
                return True
            else:
                logger.warning("Reddit API认证失败")
                return False
                
        except Exception as e:
            logger.error(f"Reddit认证时发生错误: {str(e)}")
            return False
    
    def _rate_limit_delay(self) -> None:
        """
        实施速率限制延迟
        Reddit要求每分钟最多60个请求
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 确保每分钟不超过60个请求
        if time_since_last < 1.0:  # 每秒最多1个请求
            sleep_time = 1.0 - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每60个请求后重置计数
        if self.request_count >= 60:
            self.request_count = 0
    
    def _make_request(self, endpoint: str, params: Dict = None, use_api: bool = False) -> Optional[Dict]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 查询参数
            use_api: 是否使用API端点（需要认证）
            
        Returns:
            JSON响应数据，失败则返回None
        """
        try:
            # 应用速率限制
            self._rate_limit_delay()
            
            base_url = self.api_url if (use_api and self.access_token) else self.base_url
            url = urljoin(base_url, endpoint)
            
            # 确保URL以.json结尾（Reddit API约定）
            if not url.endswith('.json'):
                url += '.json'
            
            logger.debug(f"发送请求: {url}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"API请求时发生未知错误: {str(e)}")
            return None
    
    def get_hot_posts(self, subreddit: str = 'all', limit: int = 10) -> List[Dict]:
        """
        获取热门帖子
        
        Args:
            subreddit: 子版块名称（默认为'all'）
            limit: 返回帖子数量限制
            
        Returns:
            帖子列表
        """
        try:
            endpoint = f"/r/{subreddit}/hot"
            params = {
                'limit': min(limit, 100),
            }
            
            logger.info(f"正在获取热门帖子: r/{subreddit}")
            
            data = self._make_request(endpoint, params)
            
            if data and 'data' in data and 'children' in data['data']:
                posts = []
                for post_data in data['data']['children'][:limit]:
                    post = post_data.get('data', {})
                    
                    # 提取帖子信息
                    post_info = {
                        'id': post.get('id'),
                        'title': post.get('title'),
                        'author': post.get('author'),
                        'subreddit': post.get('subreddit'),
                        'score': post.get('score'),
                        'upvote_ratio': post.get('upvote_ratio'),
                        'num_comments': post.get('num_comments'),
                        'created_utc': post.get('created_utc'),
                        'permalink': post.get('permalink'),
                        'url': post.get('url'),
                        'selftext': post.get('selftext', '')[:500],  # 限制文本长度
                        'selftext_html': post.get('selftext_html'),
                        'is_self': post.get('is_self'),  # 是否是自帖子
                        'is_video': post.get('is_video'),
                        'media': post.get('media'),
                        'thumbnail': post.get('thumbnail'),
                        'preview': post.get('preview'),
                        'spoiler': post.get('spoiler'),
                        'over_18': post.get('over_18'),  # NSFW标记
                        'stickied': post.get('stickied'),  # 置顶帖子
                        'locked': post.get('locked'),
                        'distinguished': post.get('distinguished'),
                        'award_count': len(post.get('all_awardings', [])),
                        'timestamp': datetime.now().isoformat(),
                        'source': 'Reddit',
                    }
                    
                    # 清理HTML标签
                    if post_info['selftext_html']:
                        import re
                        post_info['selftext_clean'] = re.sub(r'<[^>]+>', '', post_info['selftext_html'])
                    
                    posts.append(post_info)
                
                logger.info(f"成功获取 {len(posts)} 个热门帖子")
                return posts
            else:
                logger.warning(f"无法获取热门帖子: r/{subreddit}")
                return []
                
        except Exception as e:
            logger.error(f"获取热门帖子时发生错误: {str(e)}")
            return []
    
    def get_new_posts(self, subreddit: str = 'all', limit: int = 10) -> List[Dict]:
        """
        获取最新帖子
        
        Args:
            subreddit: 子版块名称
            limit: 返回帖子数量限制
            
        Returns:
            帖子列表
        """
        try:
            endpoint = f"/r/{subreddit}/new"
            params = {
                'limit': min(limit, 100),
            }
            
            logger.info(f"正在获取最新帖子: r/{subreddit}")
            
            data = self._make_request(endpoint, params)
            
            if data and 'data' in data and 'children' in data['data']:
                posts = []
                for post_data in data['data']['children'][:limit]:
                    post = post_data.get('data', {})
                    
                    post_info = {
                        'id': post.get('id'),
                        'title': post.get('title'),
                        'author': post.get('author'),
                        'subreddit': post.get('subreddit'),
                        'score': post.get('score'),
                        'num_comments': post.get('num_comments'),
                        'created_utc': post.get('created_utc'),
                        'permalink': post.get('permalink'),
                        'url': post.get('url'),
                        'selftext': post.get('selftext', '')[:500],
                        'timestamp': datetime.now().isoformat(),
                        'source': 'Reddit',
                    }
                    
                    posts.append(post_info)
                
                logger.info(f"成功获取 {len(posts)} 个最新帖子")
                return posts
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取最新帖子时发生错误: {str(e)}")
            return []
    
    def get_top_posts(self, subreddit: str = 'all', time_filter: str = 'day', limit: int = 10) -> List[Dict]:
        """
        获取顶部帖子
        
        Args:
            subreddit: 子版块名称
            time_filter: 时间过滤（hour, day, week, month, year, all）
            limit: 返回帖子数量限制
            
        Returns:
            帖子列表
        """
        try:
            endpoint = f"/r/{subreddit}/top"
            params = {
                'limit': min(limit, 100),
                't': time_filter,
            }
            
            logger.info(f"正在获取顶部帖子: r/{subreddit} ({time_filter})")
            
            data = self._make_request(endpoint, params)
            
            if data and 'data' in data and 'children' in data['data']:
                posts = []
                for post_data in data['data']['children'][:limit]:
                    post = post_data.get('data', {})
                    
                    post_info = {
                        'id': post.get('id'),
                        'title': post.get('title'),
                        'author': post.get('author'),
                        'subreddit': post.get('subreddit'),
                        'score': post.get('score'),
                        'num_comments': post.get('num_comments'),
                        'created_utc': post.get('created_utc'),
                        'permalink': post.get('permalink'),
                        'url': post.get('url'),
                        'selftext': post.get('selftext', '')[:500],
                        'timestamp': datetime.now().isoformat(),
                        'source': 'Reddit',
                    }
                    
                    posts.append(post_info)
                
                logger.info(f"成功获取 {len(posts)} 个顶部帖子")
                return posts
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取顶部帖子时发生错误: {str(e)}")
            return []
    
    def get_post_comments(self, post_id: str, subreddit: str = None, limit: int = 20, depth: int = 1) -> List[Dict]:
        """
        获取帖子评论
        
        Args:
            post_id: 帖子ID
            subreddit: 子版块名称（可选）
            limit: 返回评论数量限制
            depth: 评论深度（1=仅顶级评论）
            
        Returns:
            评论列表
        """
        try:
            # 构建帖子URL
            if subreddit:
                endpoint = f"/r/{subreddit}/comments/{post_id}"
            else:
                # 如果没有提供subreddit，尝试直接访问
                endpoint = f"/comments/{post_id}"
            
            params = {
                'limit': min(limit, 100),
                'depth': depth,
            }
            
            logger.info(f"正在获取帖子评论: {post_id}")
            
            data = self._make_request(endpoint, params)
            
            if data and len(data) > 0:
                # 第一个元素是帖子，第二个元素是评论
                if len(data) > 1 and 'data' in data[1] and 'children' in data[1]['data']:
                    comments_data = data[1]['data']['children']
                    comments = self._parse_comments(comments_data, limit)
                    
                    logger.info(f"成功获取 {len(comments)} 条评论")
                    return comments
                else:
                    logger.warning("评论数据格式异常")
                    return []
            else:
                logger.warning(f"无法获取帖子评论: {post_id}")
                return []
                
        except Exception as e:
            logger.error(f"获取帖子评论时发生错误: {str(e)}")
            return []
    
    def _parse_comments(self, comments_data: List, limit: int, current_depth: int = 0, max_depth: int = 3) -> List[Dict]:
        """
        递归解析评论
        
        Args:
            comments_data: 原始评论数据
            limit: 数量限制
            current_depth: 当前深度
            max_depth: 最大递归深度
            
        Returns:
            解析后的评论列表
        """
        comments = []
        
        for comment_item in comments_data:
            if len(comments) >= limit:
                break
            
            # 跳过被删除的评论
            if comment_item.get('kind') == 'more':
                continue
            
            comment = comment_item.get('data', {})
            
            # 检查评论是否被删除或移除
            if comment.get('body') in ['[deleted]', '[removed]']:
                continue
            
            comment_info = {
                'id': comment.get('id'),
                'author': comment.get('author'),
                'body': comment.get('body'),
                'body_html': comment.get('body_html'),
                'score': comment.get('score'),
                'created_utc': comment.get('created_utc'),
                'depth': current_depth,
                'permalink': comment.get('permalink'),
                'is_submitter': comment.get('is_submitter'),  # 是否是发帖人
                'stickied': comment.get('stickied'),  # 是否置顶
                'award_count': len(comment.get('all_awardings', [])),
                'replies': [],
            }
            
            # 清理HTML标签
            if comment_info['body_html']:
                import re
                comment_info['body_clean'] = re.sub(r'<[^>]+>', '', comment_info['body_html'])
            
            # 递归解析回复
            if (current_depth < max_depth and 'replies' in comment and 
                comment['replies'] and comment['replies'] != ''):
                replies_data = comment['replies'].get('data', {}).get('children', [])
                if replies_data:
                    comment_info['replies'] = self._parse_comments(
                        replies_data, 
                        limit - len(comments), 
                        current_depth + 1, 
                        max_depth
                    )
            
            comments.append(comment_info)
        
        return comments
    
    def get_subreddit_info(self, subreddit: str) -> Optional[Dict]:
        """
        获取子版块信息
        
        Args:
            subreddit: 子版块名称
            
        Returns:
            子版块信息字典，失败则返回None
        """
        try:
            endpoint = f"/r/{subreddit}/about"
            logger.info(f"正在获取子版块信息: r/{subreddit}")
            
            data = self._make_request(endpoint)
            
            if data and 'data' in data:
                subreddit_data = data['data']
                
                subreddit_info = {
                    'id': subreddit_data.get('id'),
                    'display_name': subreddit_data.get('display_name'),
                    'title': subreddit_data.get('title'),
                    'description': subreddit_data.get('public_description', '')[:500],
                    'description_html': subreddit_data.get('description_html'),
                    'subscribers': subreddit_data.get('subscribers'),
                    'active_user_count': subreddit_data.get('active_user_count'),
                    'created_utc': subreddit_data.get('created_utc'),
                    'over18': subreddit_data.get('over18'),
                    'url': subreddit_data.get('url'),
                    'header_img': subreddit_data.get('header_img'),
                    'banner_img': subreddit_data.get('banner_img'),
                    'icon_img': subreddit_data.get('icon_img'),
                    'primary_color': subreddit_data.get('primary_color'),
                    'key_color': subreddit_data.get('key_color'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Reddit',
                }
                
                logger.info(f"成功获取子版块信息: r/{subreddit}")
                return subreddit_info
            else:
                logger.warning(f"无法获取子版块信息: r/{subreddit}")
                return None
                
        except Exception as e:
            logger.error(f"获取子版块信息时发生错误: {str(e)}")
            return None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            用户信息字典，失败则返回None
        """
        try:
            endpoint = f"/user/{username}/about"
            logger.info(f"正在获取用户信息: u/{username}")
            
            data = self._make_request(endpoint)
            
            if data and 'data' in data:
                user_data = data['data']
                
                user_info = {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'created_utc': user_data.get('created_utc'),
                    'link_karma': user_data.get('link_karma'),
                    'comment_karma': user_data.get('comment_karma'),
                    'total_karma': user_data.get('total_karma'),
                    'awarder_karma': user_data.get('awarder_karma'),
                    'awardee_karma': user_data.get('awardee_karma'),
                    'is_gold': user_data.get('is_gold'),
                    'is_mod': user_data.get('is_mod'),
                    'verified': user_data.get('verified'),
                    'has_verified_email': user_data.get('has_verified_email'),
                    'icon_img': user_data.get('icon_img'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Reddit',
                }
                
                logger.info(f"成功获取用户信息: u/{username}")
                return user_info
            else:
                logger.warning(f"无法获取用户信息: u/{username}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息时发生错误: {str(e)}")
            return None
    
    def search_posts(self, query: str, subreddit: str = 'all', sort: str = 'relevance', limit: int = 10) -> List[Dict]:
        """
        搜索帖子
        
        Args:
            query: 搜索查询
            subreddit: 子版块名称（默认为'all'）
            sort: 排序方式（relevance, hot, top, new, comments）
            limit: 返回帖子数量限制
            
        Returns:
            帖子列表
        """
        try:
            endpoint = f"/r/{subreddit}/search"
            params = {
                'q': query,
                'sort': sort,
                'limit': min(limit, 100),
                'restrict_sr': 'on' if subreddit != 'all' else 'off',
                'type': 'link',
            }
            
            logger.info(f"正在搜索帖子: '{query}' in r/{subreddit}")
            
            data = self._make_request(endpoint, params)
            
            if data and 'data' in data and 'children' in data['data']:
                posts = []
                for post_data in data['data']['children'][:limit]:
                    post = post_data.get('data', {})
                    
                    post_info = {
                        'id': post.get('id'),
                        'title': post.get('title'),
                        'author': post.get('author'),
                        'subreddit': post.get('subreddit'),
                        'score': post.get('score'),
                        'num_comments': post.get('num_comments'),
                        'created_utc': post.get('created_utc'),
                        'permalink': post.get('permalink'),
                        'url': post.get('url'),
                        'selftext': post.get('selftext', '')[:500],
                        'timestamp': datetime.now().isoformat(),
                        'source': 'Reddit',
                    }
                    
                    posts.append(post_info)
                
                logger.info(f"搜索到 {len(posts)} 个帖子")
                return posts
            else:
                logger.warning(f"搜索帖子失败: '{query}'")
                return []
                
        except Exception as e:
            logger.error(f"搜索帖子时发生错误: {str(e)}")
            return []
    
    def save_to_json(self, data: Dict, filename: str = None) -> bool:
        """
        将数据保存为JSON文件
        
        Args:
            data: 数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not data:
                logger.warning("没有数据可保存")
                return False
            
            if filename is None:
                # 根据数据类型生成文件名
                if 'subreddit' in data:  # 子版块数据
                    name = data['display_name']
                    prefix = 'subreddit'
                elif 'name' in data:  # 用户数据
                    name = data['name']
                    prefix = 'user'
                elif isinstance(data, list) and len(data) > 0 and 'subreddit' in data[0]:  # 帖子列表
                    subreddit = data[0]['subreddit']
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"posts_{subreddit}_{timestamp}.json"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"reddit_{timestamp}.json"
                
                if 'filename' not in locals():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{prefix}_{name}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False


def main():
    """主函数，演示爬虫的使用"""
    print("Reddit帖子爬虫演示")
    print("=" * 50)
    print("注意: Reddit要求设置唯一的User-Agent并遵守速率限制")
    print("建议: 使用client_id和client_secret获取更好的API访问权限")
    print("=" * 50)
    
    # 创建爬虫实例
    # 可以传入client_id和client_secret以使用OAuth2认证
    crawler = RedditCrawler(
        timeout=15,
        user_agent="MyRedditCrawler/1.0 (by /u/your_username)",
        # client_id="your_client_id",
        # client_secret="your_client_secret"
    )
    
    # 获取热门子版块的热门帖子
    print("\n获取r/programming热门帖子...")
    hot_posts = crawler.get_hot_posts('programming', limit=5)
    
    if hot_posts:
        print(f"找到 {len(hot_posts)} 个热门帖子:")
        for i, post in enumerate(hot_posts, 1):
            print(f"{i}. [{post['subreddit']}] {post['title'][:80]}...")
            print(f"   作者: u/{post['author']} | 分数: {post['score']} | 评论: {post['num_comments']}")
            print(f"   链接: https://reddit.com{post['permalink']}")
            
            # 获取第一个帖子的评论
            if i == 1:
                print(f"\n获取第一个帖子的评论...")
                comments = crawler.get_post_comments(post['id'], 'programming', limit=5)
                if comments:
                    print(f"  找到 {len(comments)} 条评论:")
                    for j, comment in enumerate(comments[:3], 1):  # 只显示前3条
                        print(f"  {j}. u/{comment['author']}: {comment['body'][:100]}...")
    
    # 获取子版块信息
    print("\n" + "=" * 50)
    print("获取r/technology子版块信息...")
    subreddit_info = crawler.get_subreddit_info('technology')
    
    if subreddit_info:
        print(f"子版块: r/{subreddit_info['display_name']}")
        print(f"标题: {subreddit_info['title']}")
        print(f"订阅者: {subreddit_info['subscribers']:,}")
        print(f"描述: {subreddit_info['description'][:200]}...")
        print(f"创建时间: {datetime.fromtimestamp(subreddit_info['created_utc'])}")
        
        # 保存子版块信息
        crawler.save_to_json(subreddit_info)
        print(f"\n子版块信息已保存到JSON文件")
    
    # 获取多个子版块的热门帖子
    print("\n" + "=" * 50)
    print("获取多个子版块的顶部帖子...")
    subreddits = ['science', 'worldnews', 'funny']
    
    for subreddit in subreddits:
        print(f"\nr/{subreddit} 的顶部帖子:")
        top_posts = crawler.get_top_posts(subreddit, time_filter='day', limit=3)
        
        if top_posts:
            for post in top_posts:
                print(f"  - {post['title'][:60]}... (分: {post['score']})")
        else:
            print(f"  无法获取帖子")
    
    # 搜索帖子
    print("\n" + "=" * 50)
    print("搜索关于'AI'的帖子...")
    search_results = crawler.search_posts('artificial intelligence', 'all', 'relevance', 5)
    
    if search_results:
        print(f"找到 {len(search_results)} 个相关帖子:")
        for i, post in enumerate(search_results, 1):
            print(f"{i}. [{post['subreddit']}] {post['title'][:80]}...")
    
    # 获取用户信息（示例用户）
    print("\n" + "=" * 50)
    print("获取用户信息...")
    # 注意: 这里使用一个已知的活跃用户作为示例
    user_info = crawler.get_user_info('spez')  # Reddit CEO
    
    if user_info:
        print(f"用户名: u/{user_info['name']}")
        print(f"创建时间: {datetime.fromtimestamp(user_info['created_utc'])}")
        print(f"帖子Karma: {user_info['link_karma']:,}")
        print(f"评论Karma: {user_info['comment_karma']:,}")
        print(f"总Karma: {user_info['total_karma']:,}")
    
    print("\n爬虫演示完成！")
    print("注意: 请遵守Reddit的API使用政策和速率限制")


if __name__ == "__main__":
    main()