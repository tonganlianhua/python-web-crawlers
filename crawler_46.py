"""
爬虫 46: 豆瓣电影评论爬虫
功能: 爬取豆瓣电影评分、评论和用户评价
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import csv
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup


class DoubanMovieCrawler:
    """豆瓣电影爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # 豆瓣相关URL
        self.base_url = "https://movie.douban.com"
        self.search_url = f"{self.base_url}/subject_search"
        self.top250_url = f"{self.base_url}/top250"
        self.weekly_url = f"{self.base_url}/chart"
        self.comments_url = f"{self.base_url}/subject/{{}}/comments"
        self.reviews_url = f"{self.base_url}/subject/{{}}/reviews"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://movie.douban.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.movie_cache = {}
        self.comment_cache = {}
        
    def search_movies(self, keyword: str, page: int = 1) -> Optional[List[Dict]]:
        """
        搜索豆瓣电影
        
        Args:
            keyword: 搜索关键词
            page: 页码
            
        Returns:
            List[Dict]: 电影列表
        """
        try:
            print(f"[{datetime.now()}] 开始搜索豆瓣电影: {keyword} (第{page}页)")
            
            params = {
                'search_text': keyword,
                'cat': 1002,  # 电影分类
                'start': (page - 1) * 15,  # 豆瓣每页15条
            }
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.search_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"搜索电影失败，状态码: {response.status_code}")
                return self._retry_search_movies(keyword, page)
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            movies = []
            
            # 查找电影项
            movie_items = soup.select('.item-root')
            if not movie_items:
                movie_items = soup.select('.subject-item')
            
            for item in movie_items:
                try:
                    movie = self._parse_movie_item(item)
                    if movie:
                        movies.append(movie)
                except Exception as e:
                    print(f"解析电影项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功搜索到 {len(movies)} 部电影")
            return movies
            
        except requests.exceptions.Timeout:
            print("搜索电影请求超时")
            return self._retry_search_movies(keyword, page)
        except requests.exceptions.ConnectionError:
            print("搜索电影连接错误")
            return self._retry_search_movies(keyword, page)
        except Exception as e:
            print(f"搜索电影时发生未知错误: {str(e)}")
            return None
    
    def _parse_movie_item(self, item) -> Optional[Dict]:
        """
        解析电影项
        
        Args:
            item: BeautifulSoup元素
            
        Returns:
            Dict: 电影信息
        """
        try:
            # 提取电影ID
            link = item.select_one('a')
            if not link:
                return None
            
            href = link.get('href', '')
            movie_id = re.search(r'subject/(\d+)/', href)
            if not movie_id:
                return None
            
            movie_id = movie_id.group(1)
            
            # 提取标题
            title_elem = item.select_one('.title a')
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                title = item.select_one('.title').get_text(strip=True) if item.select_one('.title') else ''
            
            # 提取评分
            rating_elem = item.select_one('.rating_nums')
            rating = float(rating_elem.get_text(strip=True)) if rating_elem else 0
            
            # 提取评价人数
            votes_elem = item.select_one('.pl')
            votes_text = votes_elem.get_text(strip=True) if votes_elem else ''
            votes_match = re.search(r'(\d+)', votes_text.replace(',', ''))
            votes = int(votes_match.group(1)) if votes_match else 0
            
            # 提取导演和演员
            info_elem = item.select_one('.abstract')
            info_text = info_elem.get_text(strip=True) if info_elem else ''
            
            # 提取年份
            year_match = re.search(r'(\d{4})', info_text)
            year = int(year_match.group(1)) if year_match else 0
            
            # 提取图片
            img_elem = item.select_one('img')
            image_url = img_elem.get('src') if img_elem else ''
            
            movie_info = {
                'movie_id': movie_id,
                'title': title,
                'rating': rating,
                'votes': votes,
                'year': year,
                'image_url': image_url,
                'url': f"https://movie.douban.com/subject/{movie_id}/",
                'search_rank': None,  # 将在外部设置
            }
            
            return movie_info
            
        except Exception as e:
            print(f"解析电影项时出错: {str(e)}")
            return None
    
    def _retry_search_movies(self, keyword: str, page: int) -> Optional[List[Dict]]:
        """
        重试搜索电影
        
        Returns:
            List[Dict]: 电影列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.search_movies(keyword, page)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_top250_movies(self, start: int = 0, count: int = 25) -> Optional[List[Dict]]:
        """
        获取豆瓣Top250电影
        
        Args:
            start: 起始位置
            count: 获取数量
            
        Returns:
            List[Dict]: Top250电影列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取豆瓣Top250电影 (从{start}开始)")
            
            movies = []
            current_start = start
            
            while len(movies) < count:
                params = {
                    'start': current_start,
                }
                
                time.sleep(random.uniform(2, 3))
                
                response = self.session.get(
                    self.top250_url,
                    params=params,
                    headers=self.headers,
                    proxies=self.proxy,
                    timeout=15
                )
                
                if response.status_code != 200:
                    print(f"获取Top250失败，状态码: {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.item')
                
                if not items:
                    break
                
                for item in items:
                    try:
                        movie = self._parse_top250_item(item)
                        if movie:
                            movie['top_rank'] = current_start + len(movies) + 1
                            movies.append(movie)
                            
                            if len(movies) >= count:
                                break
                    except Exception as e:
                        print(f"解析Top250项时出错: {str(e)}")
                        continue
                
                if len(items) < 25:  # 豆瓣每页25条
                    break
                
                current_start += 25
                
                if len(movies) >= count:
                    break
            
            print(f"[{datetime.now()}] 成功获取 {len(movies)} 部Top250电影")
            return movies
            
        except Exception as e:
            print(f"获取Top250电影时出错: {str(e)}")
            return None
    
    def _parse_top250_item(self, item) -> Optional[Dict]:
        """
        解析Top250电影项
        
        Args:
            item: BeautifulSoup元素
            
        Returns:
            Dict: 电影信息
        """
        try:
            # 提取电影ID
            link = item.select_one('a')
            if not link:
                return None
            
            href = link.get('href', '')
            movie_id = re.search(r'subject/(\d+)/', href)
            if not movie_id:
                return None
            
            movie_id = movie_id.group(1)
            
            # 提取标题
            title_elem = item.select_one('.title')
            if title_elem:
                title = title_elem.get_text(strip=True).replace('\n', ' ').replace('/', ' ')
            else:
                return None
            
            # 提取评分
            rating_elem = item.select_one('.rating_num')
            rating = float(rating_elem.get_text(strip=True)) if rating_elem else 0
            
            # 提取评价人数
            votes_elem = item.select_one('.star span:last-child')
            votes_text = votes_elem.get_text(strip=True) if votes_elem else ''
            votes_match = re.search(r'(\d+)', votes_text.replace(',', ''))
            votes = int(votes_match.group(1)) if votes_match else 0
            
            # 提取简介
            quote_elem = item.select_one('.inq')
            quote = quote_elem.get_text(strip=True) if quote_elem else ''
            
            # 提取导演和演员信息
            bd_elem = item.select_one('.bd p')
            bd_text = bd_elem.get_text(strip=True) if bd_elem else ''
            
            # 提取年份和地区
            info_parts = bd_text.split('\n')
            if len(info_parts) > 1:
                year_area = info_parts[1].strip()
            else:
                year_area = ''
            
            # 提取图片
            img_elem = item.select_one('img')
            image_url = img_elem.get('src') if img_elem else ''
            
            movie_info = {
                'movie_id': movie_id,
                'title': title,
                'rating': rating,
                'votes': votes,
                'quote': quote,
                'year_area': year_area,
                'image_url': image_url,
                'url': f"https://movie.douban.com/subject/{movie_id}/",
                'top_rank': None,  # 将在外部设置
            }
            
            return movie_info
            
        except Exception as e:
            print(f"解析Top250项时出错: {str(e)}")
            return None
    
    def get_movie_detail(self, movie_id: str) -> Optional[Dict]:
        """
        获取电影详细信息
        
        Args:
            movie_id: 电影ID
            
        Returns:
            Dict: 电影详细信息
        """
        # 检查缓存
        if movie_id in self.movie_cache:
            print(f"从缓存获取电影 {movie_id} 的详细信息")
            return self.movie_cache[movie_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取电影详细信息: {movie_id}")
            
            url = f"https://movie.douban.com/subject/{movie_id}/"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取电影详情失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取基本信息
            info = {}
            
            # 标题
            title_elem = soup.select_one('#content h1 span')
            info['title'] = title_elem.get_text(strip=True) if title_elem else ''
            
            # 年份
            year_elem = soup.select_one('#content h1 .year')
            if year_elem:
                year_text = year_elem.get_text(strip=True)
                year_match = re.search(r'(\d{4})', year_text)
                info['year'] = int(year_match.group(1)) if year_match else 0
            
            # 评分
            rating_elem = soup.select_one('.rating_num')
            info['rating'] = float(rating_elem.get_text(strip=True)) if rating_elem else 0
            
            # 评分人数
            votes_elem = soup.select_one('.rating_sum span')
            if votes_elem:
                votes_text = votes_elem.get_text(strip=True)
                votes_match = re.search(r'(\d+)', votes_text.replace(',', ''))
                info['votes'] = int(votes_match.group(1)) if votes_match else 0
            
            # 评分分布
            rating_dist = {}
            rating_bars = soup.select('.ratings-on-weight .item')
            for bar in rating_bars:
                try:
                    rating_text = bar.select_one('.rating_per').get_text(strip=True)
                    rating_value = float(rating_text.replace('%', ''))
                    
                    star_text = bar.select_one('.rating_stars').get_text(strip=True)
                    star_match = re.search(r'(\d+)', star_text)
                    if star_match:
                        star = int(star_match.group(1))
                        rating_dist[star] = rating_value
                except:
                    continue
            info['rating_distribution'] = rating_dist
            
            # 电影信息
            info_elem = soup.select_one('#info')
            if info_elem:
                info_text = info_elem.get_text()
                
                # 导演
                director_match = re.search(r'导演:\s*(.*?)\n', info_text)
                info['director'] = director_match.group(1).strip() if director_match else ''
                
                # 编剧
                writer_match = re.search(r'编剧:\s*(.*?)\n', info_text)
                info['writer'] = writer_match.group(1).strip() if writer_match else ''
                
                # 主演
                actor_match = re.search(r'主演:\s*(.*?)\n', info_text)
                info['actor'] = actor_match.group(1).strip() if actor_match else ''
                
                # 类型
                genre_match = re.search(r'类型:\s*(.*?)\n', info_text)
                info['genre'] = genre_match.group(1).strip() if genre_match else ''
                
                # 地区
                country_match = re.search(r'制片国家/地区:\s*(.*?)\n', info_text)
                info['country'] = country_match.group(1).strip() if country_match else ''
                
                # 语言
                language_match = re.search(r'语言:\s*(.*?)\n', info_text)
                info['language'] = language_match.group(1).strip() if language_match else ''
                
                # 上映日期
                release_match = re.search(r'上映日期:\s*(.*?)\n', info_text)
                info['release_date'] = release_match.group(1).strip() if release_match else ''
                
                # 片长
                duration_match = re.search(r'片长:\s*(.*?)\n', info_text)
                info['duration'] = duration_match.group(1).strip() if duration_match else ''
            
            # 简介
            summary_elem = soup.select_one('.related-info .indent span')
            if summary_elem:
                info['summary'] = summary_elem.get_text(strip=True)
            else:
                summary_elem = soup.select_one('.related-info .indent')
                info['summary'] = summary_elem.get_text(strip=True) if summary_elem else ''
            
            # 标签
            tags = []
            tags_elems = soup.select('.tags-body a')
            for tag_elem in tags_elems:
                tags.append(tag_elem.get_text(strip=True))
            info['tags'] = tags
            
            # 图片
            img_elem = soup.select_one('#mainpic img')
            info['image_url'] = img_elem.get('src') if img_elem else ''
            
            # 完整信息
            detail = {
                'movie_id': movie_id,
                **info,
                'url': url,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.movie_cache[movie_id] = detail
            
            print(f"[{datetime.now()}] 成功获取电影详细信息")
            return detail
            
        except Exception as e:
            print(f"获取电影详细信息时出错: {str(e)}")
            return None
    
    def get_movie_comments(self, movie_id: str, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        获取电影短评
        
        Args:
            movie_id: 电影ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 短评列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取电影短评: {movie_id} (第{page}页)")
            
            cache_key = f"{movie_id}_{page}"
            if cache_key in self.comment_cache:
                print(f"从缓存获取评论数据")
                return self.comment_cache[cache_key]
            
            url = f"https://movie.douban.com/subject/{movie_id}/comments"
            params = {
                'start': (page - 1) * page_size,
                'limit': page_size,
                'sort': 'new_score',  # 按最新评分排序
                'status': 'P',
            }
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取评论失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            comments = []
            
            # 查找评论项
            comment_items = soup.select('.comment-item')
            
            for item in comment_items:
                try:
                    comment = self._parse_comment_item(item)
                    if comment:
                        comments.append(comment)
                except Exception as e:
                    print(f"解析评论项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(comments)} 条短评")
            
            # 缓存数据
            self.comment_cache[cache_key] = comments
            
            return comments
            
        except Exception as e:
            print(f"获取电影评论时出错: {str(e)}")
            return None
    
    def _parse_comment_item(self, item) -> Optional[Dict]:
        """
        解析评论项
        
        Args:
            item: BeautifulSoup元素
            
        Returns:
            Dict: 评论信息
        """
        try:
            # 用户信息
            user_elem = item.select_one('.comment-info a')
            user_name = user_elem.get_text(strip=True) if user_elem else '匿名用户'
            user_url = user_elem.get('href') if user_elem else ''
            
            # 评分
            rating_elem = item.select_one('.comment-info .rating')
            rating = 0
            if rating_elem:
                rating_class = rating_elem.get('class', [])
                for cls in rating_class:
                    if cls.startswith('allstar'):
                        rating = int(cls[7:]) / 10  # allstar40 -> 4.0
                        break
            
            # 评论时间
            time_elem = item.select_one('.comment-info .comment-time')
            comment_time = time_elem.get_text(strip=True) if time_elem else ''
            
            # 评论内容
            content_elem = item.select_one('.comment-content')
            content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 有用数
            votes_elem = item.select_one('.comment-vote .votes')
            votes = int(votes_elem.get_text(strip=True)) if votes_elem else 0
            
            comment_info = {
                'user_name': user_name,
                'user_url': user_url,
                'rating': rating,
                'comment_time': comment_time,
                'content': content,
                'votes': votes,
                'comment_id': item.get('data-cid', ''),
            }
            
            return comment_info
            
        except Exception as e:
            print(f"解析评论项时出错: {str(e)}")
            return None
    
    def analyze_movie_metrics(self, movie_detail: Dict, comments: List[Dict]) -> Dict:
        """
        分析电影指标
        
        Args:
            movie_detail: 电影详细信息
            comments: 评论列表
            
        Returns:
            Dict: 分析指标
        """
        try:
            metrics = {
                'rating': movie_detail.get('rating', 0),
                'votes': movie_detail.get('votes', 0),
                'year': movie_detail.get('year', 0),
            }
            
            # 如果有评论数据，分析评论
            if comments:
                total_comments = len(comments)
                total_rating = sum(c.get('rating', 0) for c in comments)
                avg_comment_rating = total_rating / total_comments if total_comments > 0 else 0
                
                # 评分分布
                rating_dist = {}
                for comment in comments:
                    rating = comment.get('rating', 0)
                    if rating > 0:
                        rating_key = int(rating * 2) / 2  # 转换为0.5的倍数
                        rating_dist[rating_key] = rating_dist.get(rating_key, 0) + 1
                
                # 评论情感分析（简化版）
                positive_words = ['好', '精彩', '喜欢', '推荐', '优秀', '很棒', '经典']
                negative_words = ['差', '无聊', '失望', '糟糕', '烂', '难看', '垃圾']
                
                positive_count = 0
                negative_count = 0
                
                for comment in comments:
                    content = comment.get('content', '').lower()
                    if any(word in content for word in positive_words):
                        positive_count += 1
                    if any(word in content for word in negative_words):
                        negative_count += 1
                
                positive_rate = (positive_count / total_comments) * 100 if total_comments > 0 else 0
                negative_rate = (negative_count / total_comments) * 100 if total_comments > 0 else 0
                
                metrics.update({
                    'comment_count': total_comments,
                    'avg_comment_rating': round(avg_comment_rating, 2),
                    'comment_rating_distribution': rating_dist,
                    'positive_rate': round(positive_rate, 2),
                    'negative_rate': round(negative_rate, 2),
                    'sentiment_score': round(positive_rate - negative_rate, 2),
                })
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析电影指标时出错: {str(e)}")
            return {}
    
    def save_to_csv(self, data: List[Dict], filename: Optional[str] = None):
        """
        保存数据到CSV文件
        
        Args:
            data: 要保存的数据列表
            filename: 文件名，默认为当前时间戳
        """
        if not data:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"douban_movies_{timestamp}.csv"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 提取所有可能的字段
            all_fields = set()
            for item in data:
                all_fields.update(item.keys())
            
            fieldnames = sorted(all_fields)
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"数据已保存到CSV: {filepath}")
            
        except Exception as e:
            print(f"保存数据到CSV时出错: {str(e)}")
    
    def run(self, search_keywords: List[str] = None, get_top250: bool = True, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            search_keywords: 搜索关键词列表
            get_top250: 是否获取Top250电影
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("豆瓣电影爬虫开始运行")
        print("=" * 50)
        
        if search_keywords is None:
            search_keywords = ['科幻', '爱情', '悬疑']
        
        all_movies = []
        
        # 获取Top250电影
        if get_top250:
            print("\n获取豆瓣Top250电影...")
            top_movies = self.get_top250_movies(start=0, count=25)
            
            if top_movies:
                for movie in top_movies[:10]:  # 只处理前10个
                    try:
                        movie_id = movie.get('movie_id')
                        if not movie_id:
                            continue
                        
                        # 获取详细信息
                        detail = self.get_movie_detail(movie_id)
                        if not detail:
                            continue
                        
                        # 获取评论
                        comments = self.get_movie_comments(movie_id, page=1, page_size=20)
                        
                        # 分析指标
                        metrics = self.analyze_movie_metrics(detail, comments or [])
                        
                        # 合并数据
                        complete_data = {
                            **movie,
                            **detail,
                            'comments_count': len(comments) if comments else 0,
                            'sample_comments': comments[:5] if comments else [],  # 保存5条样本评论
                            **metrics,
                            'source': 'top250',
                        }
                        
                        all_movies.append(complete_data)
                        
                        print(f"  已处理: {movie.get('title')} (评分: {movie.get('rating', 0)})")
                        
                        # 避免请求过快
                        time.sleep(random.uniform(2, 3))
                        
                    except Exception as e:
                        print(f"处理电影 {movie.get('title')} 时出错: {str(e)}")
                        continue
        
        # 搜索关键词电影
        for keyword in search_keywords:
            print(f"\n搜索关键词: {keyword}")
            
            movies = self.search_movies(keyword, page=1)
            
            if movies:
                for movie in movies[:5]:  # 每个关键词只处理前5个
                    try:
                        movie_id = movie.get('movie_id')
                        if not movie_id or any(m.get('movie_id') == movie_id for m in all_movies):
                            continue  # 避免重复
                        
                        # 获取详细信息
                        detail = self.get_movie_detail(movie_id)
                        if not detail:
                            continue
                        
                        # 获取评论
                        comments = self.get_movie_comments(movie_id, page=1, page_size=15)
                        
                        # 分析指标
                        metrics = self.analyze_movie_metrics(detail, comments or [])
                        
                        # 合并数据
                        complete_data = {
                            **movie,
                            **detail,
                            'comments_count': len(comments) if comments else 0,
                            'sample_comments': comments[:3] if comments else [],
                            **metrics,
                            'source': f'search_{keyword}',
                        }
                        
                        all_movies.append(complete_data)
                        
                        print(f"  已处理: {movie.get('title')}")
                        
                        time.sleep(random.uniform(2, 3))
                        
                    except Exception as e:
                        print(f"处理电影时出错: {str(e)}")
                        continue
        
        # 保存到文件
        if save_to_file and all_movies:
            self.save_to_csv(all_movies)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_movies)} 部电影数据")
        print("=" * 50)
        
        return all_movies


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = DoubanMovieCrawler()
        
        # 运行爬虫
        movies = crawler.run(
            search_keywords=['科幻', '爱情'],  # 可以修改搜索关键词
            get_top250=True,
            save_to_file=True
        )
        
        if movies:
            print(f"\n数据统计:")
            print(f"总电影数: {len(movies)}")
            
            # 按评分排序
            sorted_movies = sorted(movies, key=lambda x: x.get('rating', 0), reverse=True)
            
            print(f"\n评分最高的前5部电影:")
            for idx, movie in enumerate(sorted_movies[:5], 1):
                title = movie.get('title', '')[:40]
                if len(movie.get('title', '')) > 40:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     评分: {movie.get('rating', 0):.1f} | "
                      f"评价人数: {movie.get('votes', 0):,}")
                print(f"     年份: {movie.get('year', '')} | "
                      f"导演: {movie.get('director', '')[:20]}")
                
                if movie.get('comment_count', 0) > 0:
                    print(f"     评论情感分: {movie.get('sentiment_score', 0):.2f}")
        else:
            print("未能获取电影数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()