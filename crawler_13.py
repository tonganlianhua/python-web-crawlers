#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电影信息爬虫 - 获取豆瓣电影信息
网站：豆瓣电影 (https://movie.douban.com)
功能：获取电影评分、简介、演员、评论等信息
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import quote, urljoin

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MovieCrawler:
    """电影信息爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "https://movie.douban.com"
        
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
            'Referer': 'https://www.douban.com/',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session.headers.update(self.headers)
        
        # 添加cookies（模拟真实用户）
        self.session.cookies.update({
            'bid': 'abcdefghijklmnopqrstuvwxyz123',
            'dbcl2': '1234567890:abcdefghijklmnopqrstuvwxyz',
        })
    
    def search_movie(self, movie_name: str, limit: int = 5) -> List[Dict]:
        """
        搜索电影
        
        Args:
            movie_name: 电影名称
            limit: 返回结果数量限制
            
        Returns:
            搜索结果列表
        """
        try:
            search_url = f"{self.base_url}/subject_search"
            params = {
                'search_text': movie_name,
                'cat': '1002',  # 电影分类
            }
            
            logger.info(f"正在搜索电影: {movie_name}")
            
            response = self.session.get(search_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_search_results(soup, limit)
            
            logger.info(f"搜索到 {len(results)} 个结果")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"搜索电影时发生未知错误: {str(e)}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup, limit: int) -> List[Dict]:
        """
        解析搜索结果页面
        
        Args:
            soup: BeautifulSoup对象
            limit: 结果数量限制
            
        Returns:
            搜索结果列表
        """
        results = []
        
        try:
            # 查找搜索结果项
            result_items = soup.find_all('div', class_='item-root')
            
            for item in result_items[:limit]:
                result = {}
                
                # 电影链接和ID
                link_tag = item.find('a', class_='title-text')
                if link_tag:
                    result['url'] = link_tag.get('href', '')
                    # 从URL提取电影ID
                    match = re.search(r'subject/(\d+)/', result['url'])
                    if match:
                        result['id'] = match.group(1)
                
                # 电影标题
                if link_tag:
                    result['title'] = link_tag.get_text(strip=True)
                
                # 评分
                rating_tag = item.find('span', class_='rating_nums')
                if rating_tag:
                    result['rating'] = rating_tag.get_text(strip=True)
                
                # 评价人数
                votes_tag = item.find('span', class_='pl')
                if votes_tag:
                    votes_text = votes_tag.get_text(strip=True)
                    # 提取数字
                    match = re.search(r'(\d+)', votes_text.replace(',', ''))
                    if match:
                        result['votes'] = int(match.group(1))
                
                # 导演和演员
                info_tag = item.find('div', class_='meta abstract')
                if info_tag:
                    result['info'] = info_tag.get_text(strip=True)
                
                # 海报
                img_tag = item.find('img')
                if img_tag:
                    result['poster'] = img_tag.get('src', '')
                
                if result:
                    results.append(result)
        
        except Exception as e:
            logger.error(f"解析搜索结果时发生错误: {str(e)}")
        
        return results
    
    def get_movie_detail(self, movie_id: str = None, movie_url: str = None) -> Optional[Dict]:
        """
        获取电影详细信息
        
        Args:
            movie_id: 电影ID
            movie_url: 电影URL（如果提供了movie_id，则忽略此参数）
            
        Returns:
            电影详细信息字典，失败则返回None
        """
        try:
            if movie_id and not movie_url:
                movie_url = f"{self.base_url}/subject/{movie_id}/"
            elif not movie_url:
                logger.error("必须提供movie_id或movie_url")
                return None
            
            logger.info(f"正在获取电影详情: {movie_url}")
            
            response = self.session.get(movie_url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            movie_data = self._parse_movie_detail(soup, movie_url)
            
            if movie_data:
                logger.info(f"成功获取电影 '{movie_data.get('title', '未知')}' 的详细信息")
                return movie_data
            else:
                logger.warning("解析电影详情失败")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取电影详情时发生未知错误: {str(e)}")
            return None
    
    def _parse_movie_detail(self, soup: BeautifulSoup, movie_url: str) -> Dict:
        """
        解析电影详情页面
        
        Args:
            soup: BeautifulSoup对象
            movie_url: 电影URL
            
        Returns:
            电影详细信息字典
        """
        movie_data = {
            'url': movie_url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': '豆瓣电影',
        }
        
        try:
            # 提取电影ID
            match = re.search(r'subject/(\d+)/', movie_url)
            if match:
                movie_data['id'] = match.group(1)
            
            # 电影标题
            title_tag = soup.find('span', property='v:itemreviewed')
            if title_tag:
                movie_data['title'] = title_tag.get_text(strip=True)
            
            # 年份
            year_tag = soup.find('span', class_='year')
            if year_tag:
                year_text = year_tag.get_text(strip=True)
                match = re.search(r'(\d{4})', year_text)
                if match:
                    movie_data['year'] = match.group(1)
            
            # 评分信息
            rating_tag = soup.find('strong', class_='ll rating_num')
            if rating_tag:
                movie_data['rating'] = rating_tag.get_text(strip=True)
            
            # 评分人数
            rating_people_tag = soup.find('span', property='v:votes')
            if rating_people_tag:
                movie_data['rating_people'] = rating_people_tag.get_text(strip=True)
            
            # 评分分布
            rating_dist = {}
            rating_stars = soup.find_all('span', class_='rating_per')
            for i, star in enumerate(rating_stars):
                rating_dist[f'{5-i}星'] = star.get_text(strip=True)
            if rating_dist:
                movie_data['rating_distribution'] = rating_dist
            
            # 基本信息
            info = soup.find('div', id='info')
            if info:
                info_text = info.get_text()
                lines = info_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == '导演':
                            # 提取导演列表
                            directors = []
                            director_tags = info.find_all('a', rel='v:directedBy')
                            for tag in director_tags:
                                directors.append(tag.get_text(strip=True))
                            if directors:
                                movie_data['directors'] = directors
                        elif key == '编剧':
                            # 提取编剧列表
                            writers = []
                            writer_spans = info.find_all('span', class_='attrs')
                            for span in writer_spans:
                                # 查找包含编剧信息的span
                                if '编剧' in span.find_previous('span', class_='pl').get_text():
                                    writer_links = span.find_all('a')
                                    for link in writer_links:
                                        writers.append(link.get_text(strip=True))
                            if writers:
                                movie_data['writers'] = writers
                        elif key == '主演':
                            # 提取演员列表
                            actors = []
                            actor_tags = info.find_all('a', rel='v:starring')
                            for tag in actor_tags:
                                actors.append(tag.get_text(strip=True))
                            if actors:
                                movie_data['actors'] = actors
                        elif key == '类型':
                            # 提取类型
                            genres = []
                            genre_tags = info.find_all('span', property='v:genre')
                            for tag in genre_tags:
                                genres.append(tag.get_text(strip=True))
                            if genres:
                                movie_data['genres'] = genres
                        elif key == '制片国家/地区':
                            movie_data['countries'] = [c.strip() for c in value.split('/')]
                        elif key == '语言':
                            movie_data['languages'] = [l.strip() for l in value.split('/')]
                        elif key == '上映日期':
                            # 提取上映日期
                            release_dates = []
                            date_tags = info.find_all('span', property='v:initialReleaseDate')
                            for tag in date_tags:
                                release_dates.append(tag.get_text(strip=True))
                            if release_dates:
                                movie_data['release_dates'] = release_dates
                        elif key == '片长':
                            length_tag = info.find('span', property='v:runtime')
                            if length_tag:
                                movie_data['duration'] = length_tag.get_text(strip=True)
                        elif key == '又名':
                            movie_data['also_known_as'] = value
                        elif key == 'IMDb':
                            movie_data['imdb'] = value
            
            # 剧情简介
            summary_tag = soup.find('span', property='v:summary')
            if summary_tag:
                summary = summary_tag.get_text(strip=True)
                # 清理空白字符
                summary = re.sub(r'\s+', ' ', summary)
                movie_data['summary'] = summary
            
            # 海报
            poster_tag = soup.find('img', rel='v:image')
            if poster_tag:
                movie_data['poster'] = poster_tag.get('src', '')
            
            # 短评数量
            comments_tag = soup.find('a', href=re.compile(r'comments$'))
            if comments_tag:
                comments_text = comments_tag.get_text(strip=True)
                match = re.search(r'(\d+)', comments_text.replace(',', ''))
                if match:
                    movie_data['comment_count'] = int(match.group(1))
            
            # 影评数量
            reviews_tag = soup.find('a', href=re.compile(r'reviews$'))
            if reviews_tag:
                reviews_text = reviews_tag.get_text(strip=True)
                match = re.search(r'(\d+)', reviews_text.replace(',', ''))
                if match:
                    movie_data['review_count'] = int(match.group(1))
            
            # 标签
            tags = []
            tags_div = soup.find('div', class_='tags-body')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                movie_data['tags'] = tags
            
            # 推荐电影
            recommendations = []
            rec_section = soup.find('div', class_='recommendations-bd')
            if rec_section:
                rec_items = rec_section.find_all('dl')
                for item in rec_items:
                    rec = {}
                    
                    # 电影链接
                    link_tag = item.find('a')
                    if link_tag:
                        rec['url'] = link_tag.get('href', '')
                    
                    # 电影标题
                    title_tag = item.find('img')
                    if title_tag:
                        rec['title'] = title_tag.get('alt', '')
                    
                    # 海报
                    if title_tag:
                        rec['poster'] = title_tag.get('src', '')
                    
                    if rec:
                        recommendations.append(rec)
            
            if recommendations:
                movie_data['recommendations'] = recommendations
            
        except Exception as e:
            logger.error(f"解析电影详情时发生错误: {str(e)}")
        
        return movie_data
    
    def get_movie_comments(self, movie_id: str, limit: int = 10) -> List[Dict]:
        """
        获取电影短评
        
        Args:
            movie_id: 电影ID
            limit: 返回评论数量限制
            
        Returns:
            评论列表
        """
        try:
            comments_url = f"{self.base_url}/subject/{movie_id}/comments"
            params = {
                'sort': 'new_score',  # 按最新评分排序
                'limit': limit,
            }
            
            logger.info(f"正在获取电影 {movie_id} 的短评")
            
            response = self.session.get(comments_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            comments = self._parse_comments(soup, limit)
            
            logger.info(f"成功获取 {len(comments)} 条短评")
            return comments
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取评论请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取电影评论时发生未知错误: {str(e)}")
            return []
    
    def _parse_comments(self, soup: BeautifulSoup, limit: int) -> List[Dict]:
        """
        解析评论页面
        
        Args:
            soup: BeautifulSoup对象
            limit: 评论数量限制
            
        Returns:
            评论列表
        """
        comments = []
        
        try:
            comment_items = soup.find_all('div', class_='comment-item')
            
            for item in comment_items[:limit]:
                comment = {}
                
                # 用户信息
                user_tag = item.find('a', class_='')
                if user_tag:
                    comment['user'] = user_tag.get_text(strip=True)
                    comment['user_url'] = user_tag.get('href', '')
                
                # 评分
                rating_tag = item.find('span', class_=re.compile(r'rating'))
                if rating_tag:
                    # 提取评分值
                    class_names = rating_tag.get('class', [])
                    for cls in class_names:
                        if cls.startswith('allstar'):
                            rating = cls.replace('allstar', '')
                            if rating.isdigit():
                                comment['rating'] = int(rating) // 10  # 转换为5分制
                                break
                
                # 评论时间
                time_tag = item.find('span', class_='comment-time')
                if time_tag:
                    comment['time'] = time_tag.get_text(strip=True)
                
                # 评论内容
                content_tag = item.find('span', class_='short')
                if content_tag:
                    comment['content'] = content_tag.get_text(strip=True)
                
                # 有用数
                votes_tag = item.find('span', class_='votes')
                if votes_tag:
                    comment['useful_votes'] = votes_tag.get_text(strip=True)
                
                if comment:
                    comments.append(comment)
        
        except Exception as e:
            logger.error(f"解析评论时发生错误: {str(e)}")
        
        return comments
    
    def save_to_json(self, movie_data: Dict, filename: str = None) -> bool:
        """
        将电影数据保存为JSON文件
        
        Args:
            movie_data: 电影数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not movie_data:
                logger.warning("没有电影数据可保存")
                return False
            
            if filename is None:
                title = movie_data.get('title', 'unknown').replace('/', '_').replace('\\', '_')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"movie_{title}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(movie_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"电影数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def get_top_movies(self, category: str = 'hot', limit: int = 10) -> List[Dict]:
        """
        获取热门电影榜单
        
        Args:
            category: 榜单类型（hot: 热门, top250: Top250）
            limit: 返回数量限制
            
        Returns:
            电影列表
        """
        # 注意：实际实现需要更复杂的解析
        logger.info(f"获取 {category} 电影榜单功能待实现")
        return []


def main():
    """主函数，演示爬虫的使用"""
    print("电影信息爬虫演示")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = MovieCrawler(timeout=15)
    
    # 搜索电影
    movie_name = "肖申克的救赎"
    print(f"\n搜索电影: {movie_name}")
    search_results = crawler.search_movie(movie_name, limit=3)
    
    if search_results:
        print(f"找到 {len(search_results)} 个结果:")
        for i, result in enumerate(search_results, 1):
            print(f"{i}. {result.get('title', '未知')} - 评分: {result.get('rating', '无')}")
        
        # 获取第一个结果的详细信息
        if search_results[0].get('url'):
            print(f"\n获取详细信息: {search_results[0]['title']}")
            movie_detail = crawler.get_movie_detail(movie_url=search_results[0]['url'])
            
            if movie_detail:
                print(f"电影标题: {movie_detail.get('title', '未知')}")
                print(f"上映年份: {movie_detail.get('year', '未知')}")
                print(f"豆瓣评分: {movie_detail.get('rating', '未知')}")
                print(f"评分人数: {movie_detail.get('rating_people', '未知')}")
                
                if 'directors' in movie_detail:
                    print(f"导演: {', '.join(movie_detail['directors'])}")
                
                if 'actors' in movie_detail:
                    actors = movie_detail['actors'][:3]  # 只显示前3个演员
                    print(f"主演: {', '.join(actors)}")
                
                if 'genres' in movie_detail:
                    print(f"类型: {', '.join(movie_detail['genres'])}")
                
                if 'summary' in movie_detail:
                    summary = movie_detail['summary'][:100] + "..." if len(movie_detail['summary']) > 100 else movie_detail['summary']
                    print(f"简介: {summary}")
                
                # 保存数据
                crawler.save_to_json(movie_detail)
                print(f"\n数据已保存到JSON文件")
                
                # 获取评论
                if 'id' in movie_detail:
                    print(f"\n获取短评...")
                    comments = crawler.get_movie_comments(movie_detail['id'], limit=3)
                    if comments:
                        print(f"最新短评:")
                        for i, comment in enumerate(comments, 1):
                            user = comment.get('user', '匿名用户')
                            rating = comment.get('rating', '无评分')
                            content = comment.get('content', '')[:50] + "..." if len(comment.get('content', '')) > 50 else comment.get('content', '')
                            print(f"  {i}. {user} ({rating}星): {content}")
            else:
                print("无法获取电影详情")
    else:
        print(f"未找到电影: {movie_name}")
    
    # 演示搜索多个电影
    print("\n" + "=" * 50)
    print("搜索多个热门电影...")
    movies_to_search = ["盗梦空间", "阿甘正传", "泰坦尼克号"]
    
    for movie in movies_to_search:
        print(f"\n搜索: {movie}")
        results = crawler.search_movie(movie, limit=1)
        if results:
            print(f"  结果: {results[0].get('title', '未知')} - 评分: {results[0].get('rating', '无')}")
        else:
            print(f"  未找到结果")
    
    print("\n爬虫演示完成！")


if __name__ == "__main__":
    main()