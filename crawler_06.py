#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫06: 视频信息爬虫 - YouTube/B站视频信息获取
功能: 爬取视频信息、评论、相关视频，支持关键词搜索和频道分析
注意: 本爬虫仅用于学习研究，请遵守网站robots.txt和法律法规
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
import logging
import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote, parse_qs, urlparse
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_06.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoCrawler:
    """视频信息爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 各平台配置
        self.platform_config = {
            'youtube': {
                'base_url': 'https://www.youtube.com',
                'search_url': 'https://www.youtube.com/results',
                'watch_url': 'https://www.youtube.com/watch',
            },
            'bilibili': {
                'base_url': 'https://www.bilibili.com',
                'search_url': 'https://search.bilibili.com/video',
                'video_url': 'https://www.bilibili.com/video',
            },
            'douyin': {
                'base_url': 'https://www.douyin.com',
                'search_url': 'https://www.douyin.com/search',
            }
        }
    
    def search_videos(self, platform: str, keyword: str, page: int = 1, max_results: int = 20) -> List[Dict]:
        """
        搜索视频
        
        Args:
            platform: 平台 (youtube, bilibili, douyin)
            keyword: 搜索关键词
            page: 页码
            max_results: 最大结果数
            
        Returns:
            视频列表
        """
        try:
            logger.info(f"在 {platform} 搜索视频: {keyword}")
            
            if platform == 'youtube':
                return self._search_youtube(keyword, page, max_results)
            elif platform == 'bilibili':
                return self._search_bilibili(keyword, page, max_results)
            elif platform == 'douyin':
                return self._search_douyin(keyword, page, max_results)
            else:
                logger.warning(f"不支持的平台: {platform}")
                return []
                
        except Exception as e:
            logger.error(f"搜索视频失败: {e}")
            return []
    
    def _search_youtube(self, keyword: str, page: int, max_results: int) -> List[Dict]:
        """搜索YouTube视频"""
        videos = []
        
        try:
            config = self.platform_config['youtube']
            params = {
                'search_query': keyword,
                'page': page
            }
            
            response = self.session.get(config['search_url'], params=params, timeout=15)
            response.raise_for_status()
            
            # YouTube页面包含大量JavaScript，需要解析初始HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找视频容器
            script_tags = soup.find_all('script')
            
            # 尝试从script标签中提取数据
            for script in script_tags:
                if 'var ytInitialData' in str(script):
                    # 提取JSON数据
                    script_text = str(script)
                    start = script_text.find('var ytInitialData = ') + len('var ytInitialData = ')
                    end = script_text.find('};', start) + 1
                    
                    if start > 0 and end > start:
                        try:
                            json_str = script_text[start:end]
                            data = json.loads(json_str)
                            
                            # 解析视频数据
                            videos = self._parse_youtube_data(data, max_results)
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"解析YouTube JSON失败: {e}")
            
            # 如果JSON解析失败，尝试从HTML中解析
            if not videos:
                video_items = soup.select('ytd-video-renderer')
                
                for item in video_items[:max_results]:
                    try:
                        video = {}
                        
                        # 获取标题和链接
                        title_elem = item.select_one('#video-title')
                        if title_elem:
                            video['title'] = title_elem.get_text(strip=True)
                            video['url'] = urljoin(config['base_url'], title_elem.get('href', ''))
                            video['video_id'] = self._extract_video_id(video['url'])
                        
                        # 获取频道
                        channel_elem = item.select_one('#channel-name a')
                        if channel_elem:
                            video['channel'] = channel_elem.get_text(strip=True)
                            video['channel_url'] = urljoin(config['base_url'], channel_elem.get('href', ''))
                        
                        # 获取观看次数和发布时间
                        meta_elem = item.select_one('#metadata-line')
                        if meta_elem:
                            meta_text = meta_elem.get_text(strip=True)
                            # 简单解析
                            parts = meta_text.split('•')
                            if len(parts) >= 2:
                                video['views'] = parts[0].strip()
                                video['upload_time'] = parts[1].strip()
                        
                        # 获取时长
                        duration_elem = item.select_one('#overlays #text')
                        if duration_elem:
                            video['duration'] = duration_elem.get_text(strip=True)
                        
                        if video.get('video_id'):
                            video['platform'] = 'youtube'
                            video['crawled_at'] = datetime.now().isoformat()
                            videos.append(video)
                            
                    except Exception as e:
                        logger.debug(f"处理YouTube视频条目时出错: {e}")
                        continue
            
            logger.info(f"从YouTube找到 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            logger.error(f"搜索YouTube失败: {e}")
            return []
    
    def _parse_youtube_data(self, data: Dict, max_results: int) -> List[Dict]:
        """解析YouTube JSON数据"""
        videos = []
        
        try:
            # 这是一个简化的解析，实际数据结构可能更复杂
            # 查找视频内容
            contents = []
            
            # 尝试多种可能的路径
            possible_paths = [
                ['contents', 'twoColumnSearchResultsRenderer', 'primaryContents', 'sectionListRenderer', 'contents', 0, 'itemSectionRenderer', 'contents'],
                ['contents', 'twoColumnSearchResultsRenderer', 'primaryContents', 'sectionListRenderer', 'contents'],
                ['contents', 'twoColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents'],
            ]
            
            for path in possible_paths:
                try:
                    current = data
                    for key in path:
                        if isinstance(key, int):
                            if isinstance(current, list) and key < len(current):
                                current = current[key]
                            else:
                                break
                        else:
                            if key in current:
                                current = current[key]
                            else:
                                break
                    else:
                        contents = current
                        break
                except (KeyError, IndexError, TypeError):
                    continue
            
            if not contents:
                return videos
            
            for item in contents[:max_results]:
                try:
                    video = {}
                    
                    # 提取视频信息
                    if 'videoRenderer' in item:
                        vr = item['videoRenderer']
                        
                        video['video_id'] = vr.get('videoId', '')
                        video['title'] = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                        
                        # 获取链接
                        if video['video_id']:
                            video['url'] = f"https://www.youtube.com/watch?v={video['video_id']}"
                        
                        # 获取频道信息
                        owner_text = vr.get('ownerText', {}).get('runs', [{}])
                        if owner_text:
                            video['channel'] = owner_text[0].get('text', '')
                        
                        # 获取观看次数
                        view_count = vr.get('viewCountText', {}).get('simpleText', '')
                        if view_count:
                            video['views'] = view_count
                        
                        # 获取发布时间
                        published_time = vr.get('publishedTimeText', {}).get('simpleText', '')
                        if published_time:
                            video['upload_time'] = published_time
                        
                        # 获取时长
                        length_text = vr.get('lengthText', {}).get('simpleText', '')
                        if length_text:
                            video['duration'] = length_text
                        
                        # 获取缩略图
                        thumbnails = vr.get('thumbnail', {}).get('thumbnails', [])
                        if thumbnails:
                            video['thumbnail'] = thumbnails[-1].get('url', '')  # 取最高质量的
                        
                        if video['video_id']:
                            video['platform'] = 'youtube'
                            video['crawled_at'] = datetime.now().isoformat()
                            videos.append(video)
                            
                except Exception as e:
                    logger.debug(f"解析YouTube数据项时出错: {e}")
                    continue
            
            return videos
            
        except Exception as e:
            logger.error(f"解析YouTube数据失败: {e}")
            return []
    
    def _search_bilibili(self, keyword: str, page: int, max_results: int) -> List[Dict]:
        """搜索B站视频"""
        videos = []
        
        try:
            config = self.platform_config['bilibili']
            params = {
                'keyword': keyword,
                'page': page
            }
            
            response = self.session.get(config['search_url'], params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找视频项
            video_items = soup.select('.video-item')
            
            for item in video_items[:max_results]:
                try:
                    video = {}
                    
                    # 获取标题和链接
                    title_elem = item.select_one('.title')
                    if title_elem:
                        link_elem = title_elem.find('a')
                        if link_elem:
                            video['title'] = link_elem.get('title', '').strip()
                            video['url'] = urljoin(config['base_url'], link_elem.get('href', ''))
                            video['video_id'] = self._extract_bilibili_id(video['url'])
                    
                    # 获取UP主
                    up_elem = item.select_one('.up-name')
                    if up_elem:
                        video['up'] = up_elem.get_text(strip=True)
                    
                    # 获取播放量
                    play_elem = item.select_one('.play')
                    if play_elem:
                        video['play'] = play_elem.get_text(strip=True)
                    
                    # 获取弹幕数
                    dm_elem = item.select_one('.dm')
                    if dm_elem:
                        video['danmaku'] = dm_elem.get_text(strip=True)
                    
                    # 获取发布时间
                    time_elem = item.select_one('.time')
                    if time_elem:
                        video['upload_time'] = time_elem.get_text(strip=True)
                    
                    # 获取时长
                    duration_elem = item.select_one('.duration')
                    if duration_elem:
                        video['duration'] = duration_elem.get_text(strip=True)
                    
                    # 获取缩略图
                    img_elem = item.select_one('img')
                    if img_elem:
                        video['thumbnail'] = img_elem.get('src') or img_elem.get('data-src')
                        if video['thumbnail'] and video['thumbnail'].startswith('//'):
                            video['thumbnail'] = 'https:' + video['thumbnail']
                    
                    if video.get('video_id'):
                        video['platform'] = 'bilibili'
                        video['crawled_at'] = datetime.now().isoformat()
                        videos.append(video)
                        
                except Exception as e:
                    logger.debug(f"处理B站视频条目时出错: {e}")
                    continue
            
            logger.info(f"从B站找到 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            logger.error(f"搜索B站失败: {e}")
            return []
    
    def _search_douyin(self, keyword: str, page: int, max_results: int) -> List[Dict]:
        """搜索抖音视频"""
        videos = []
        
        try:
            config = self.platform_config['douyin']
            params = {
                'keyword': keyword,
                'page': page
            }
            
            response = self.session.get(config['search_url'], params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 抖音页面结构复杂，这里使用简化的解析
            # 实际使用可能需要处理JavaScript渲染
            
            # 查找视频卡片
            video_cards = soup.select('[data-e2e="search-card"]')
            
            for card in video_cards[:max_results]:
                try:
                    video = {}
                    
                    # 获取作者
                    author_elem = card.select_one('[data-e2e="search-card-user-unique-id"]')
                    if author_elem:
                        video['author'] = author_elem.get_text(strip=True)
                    
                    # 获取描述
                    desc_elem = card.select_one('[data-e2e="search-card-desc"]')
                    if desc_elem:
                        video['description'] = desc_elem.get_text(strip=True)
                    
                    # 获取点赞数
                    like_elem = card.select_one('[data-e2e="search-card-like-count"]')
                    if like_elem:
                        video['likes'] = like_elem.get_text(strip=True)
                    
                    # 获取评论数
                    comment_elem = card.select_one('[data-e2e="search-card-comment-count"]')
                    if comment_elem:
                        video['comments'] = comment_elem.get_text(strip=True)
                    
                    # 获取视频链接（可能需要从其他属性提取）
                    link_elem = card.find('a', href=True)
                    if link_elem:
                        video['url'] = urljoin(config['base_url'], link_elem.get('href', ''))
                    
                    if video.get('url'):
                        video['platform'] = 'douyin'
                        video['crawled_at'] = datetime.now().isoformat()
                        video['video_id'] = hashlib.md5(video['url'].encode()).hexdigest()[:8]
                        videos.append(video)
                        
                except Exception as e:
                    logger.debug(f"处理抖音视频条目时出错: {e}")
                    continue
            
            logger.info(f"从抖音找到 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            logger.error(f"搜索抖音失败: {e}")
            return []
    
    def get_video_details(self, video_url: str) -> Optional[Dict]:
        """
        获取视频详细信息
        
        Args:
            video_url: 视频URL
            
        Returns:
            视频详细信息
        """
        try:
            logger.info(f"获取视频详情: {video_url}")
            
            if 'youtube.com' in video_url:
                return self._get_youtube_details(video_url)
            elif 'bilibili.com' in video_url:
                return self._get_bilibili_details(video_url)
            else:
                logger.warning(f"不支持的视频URL: {video_url}")
                return None
                
        except Exception as e:
            logger.error(f"获取视频详情失败: {e}")
            return None
    
    def _get_youtube_details(self, video_url: str) -> Optional[Dict]:
        """获取YouTube视频详情"""
        try:
            response = self.session.get(video_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': video_url,
                'video_id': self._extract_video_id(video_url),
                'platform': 'youtube',
                'crawled_at': datetime.now().isoformat()
            }
            
            # 从meta标签获取信息
            meta_tags = soup.find_all('meta')
            
            for meta in meta_tags:
                prop = meta.get('property') or meta.get('name', '')
                content = meta.get('content', '')
                
                if 'og:title' in prop:
                    details['title'] = content
                elif 'og:description' in prop:
                    details['description'] = content[:500]  # 限制长度
                elif 'og:image' in prop:
                    details['thumbnail'] = content
                elif 'og:video:duration' in prop:
                    details['duration_seconds'] = int(content)
                elif 'og:video:width' in prop:
                    details['width'] = int(content)
                elif 'og:video:height' in prop:
                    details['height'] = int(content)
            
            # 尝试从script标签获取更多信息
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if 'var ytInitialPlayerResponse' in str(script):
                    try:
                        script_text = str(script)
                        start = script_text.find('var ytInitialPlayerResponse = ') + len('var ytInitialPlayerResponse = ')
                        end = script_text.find('};', start) + 1
                        
                        if start > 0 and end > start:
                            json_str = script_text[start:end]
                            player_data = json.loads(json_str)
                            
                            # 提取视频详情
                            video_details = player_data.get('videoDetails', {})
                            details['views'] = video_details.get('viewCount', '0')
                            details['author'] = video_details.get('author', '')
                            details['keywords'] = video_details.get('keywords', [])
                            
                            # 格式化时长
                            if 'duration_seconds' not in details and 'lengthSeconds' in video_details:
                                details['duration_seconds'] = int(video_details['lengthSeconds'])
                            
                            break
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析YouTube播放器数据失败: {e}")
            
            # 格式化时长
            if 'duration_seconds' in details:
                minutes = details['duration_seconds'] // 60
                seconds = details['duration_seconds'] % 60
                details['duration'] = f"{minutes}:{seconds:02d}"
            
            # 获取发布日期
            date_pattern = r'"publishDate":"([^"]+)"'
            date_match = re.search(date_pattern, response.text)
            if date_match:
                details['publish_date'] = date_match.group(1)
            
            logger.debug(f"获取到YouTube视频详情: {details.get('title', '未知标题')}")
            return details
            
        except Exception as e:
            logger.error(f"获取YouTube详情失败: {e}")
            return None
    
    def _get_bilibili_details(self, video_url: str) -> Optional[Dict]:
        """获取B站视频详情"""
        try:
            response = self.session.get(video_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': video_url,
                'video_id': self._extract_bilibili_id(video_url),
                'platform': 'bilibili',
                'crawled_at': datetime.now().isoformat()
            }
            
            # 获取标题
            title_elem = soup.select_one('.video-title')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # 获取UP主
            up_elem = soup.select_one('.up-name')
            if up_elem:
                details['up'] = up_elem.get_text(strip=True)
            
            # 获取播放量、弹幕数、发布时间
            info_elem = soup.select_one('.video-data')
            if info_elem:
                info_text = info_elem.get_text(strip=True)
                # 解析信息文本
                parts = re.split(r'[·•]', info_text)
                for part in parts:
                    part = part.strip()
                    if '播放' in part:
                        details['play'] = re.sub(r'[^\d.]', '', part)
                    elif '弹幕' in part:
                        details['danmaku'] = re.sub(r'[^\d.]', '', part)
                    elif '发布' in part:
                        details['upload_time'] = part
            
            # 获取简介
            desc_elem = soup.select_one('#v_desc')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # 获取分区
            category_elem = soup.select_one('.crumb a:last-child')
            if category_elem:
                details['category'] = category_elem.get_text(strip=True)
            
            # 获取点赞、投币、收藏、分享数
            ops = soup.select('.ops span')
            if len(ops) >= 4:
                details['like'] = ops[0].get_text(strip=True)
                details['coin'] = ops[1].get_text(strip=True)
                details['favorite'] = ops[2].get_text(strip=True)
                details['share'] = ops[3].get_text(strip=True)
            
            logger.debug(f"获取到B站视频详情: {details.get('title', '未知标题')}")
            return details
            
        except Exception as e:
            logger.error(f"获取B站详情失败: {e}")
            return None
    
    def _extract_video_id(self, url: str) -> str:
        """从URL提取视频ID"""
        try:
            if 'youtube.com' in url:
                # 解析查询参数
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                return query_params.get('v', [''])[0]
            return ''
        except:
            return ''
    
    def _extract_bilibili_id(self, url: str) -> str:
        """从URL提取B站视频ID"""
        try:
            # B站视频URL格式: https://www.bilibili.com/video/BVxxxxxx/
            match = re.search(r'/video/(BV[0-9A-Za-z]+)', url)
            if match:
                return match.group(1)
            
            # 另一种格式: https://b23.tv/xxxxxx
            match = re.search(r'b23\.tv/([0-9A-Za-z]+)', url)
            if match:
                return match.group(1)
            
            return ''
        except:
            return ''
    
    def analyze_video_data(self, videos: List[Dict]) -> Dict:
        """
        分析视频数据
        
        Args:
            videos: 视频列表
            
        Returns:
            分析结果
        """
        analysis = {
            'total_videos': len(videos),
            'platforms': {},
            'average_title_length': 0,
            'most_common_words': [],
            'duration_stats': {}
        }
        
        if not videos:
            return analysis
        
        # 平台统计
        for video in videos:
            platform = video.get('platform', 'unknown')
            analysis['platforms'][platform] = analysis['platforms'].get(platform, 0) + 1
        
        # 标题长度分析
        title_lengths = []
        all_words = []
        
        for video in videos:
            title = video.get('title', '')
            if title:
                title_lengths.append(len(title))
                
                # 分词（简单空格分割）
                words = re.findall(r'[\w\u4e00-\u9fff]+', title.lower())
                all_words.extend(words)
        
        if title_lengths:
            analysis['average_title_length'] = sum(title_lengths) / len(title_lengths)
            analysis['max_title_length'] = max(title_lengths)
            analysis['min_title_length'] = min(title_lengths)
        
        # 词频分析
        if all_words:
            from collections import Counter
            word_counts = Counter(all_words)
            analysis['most_common_words'] = word_counts.most_common(10)
        
        return analysis

def main():
    """主函数"""
    try:
        crawler = VideoCrawler()
        
        print("=== 视频信息爬虫 ===")
        print("支持平台: YouTube, Bilibili, 抖音")
        print()
        
        print("选择功能:")
        print("1. 搜索视频")
        print("2. 获取视频详情")
        print("3. 分析视频数据")
        print("4. 退出")
        
        choice = input("\n请选择功能 (1-4): ").strip()
        
        if choice == '1':
            print("\n选择平台:")
            print("1. YouTube")
            print("2. Bilibili")
            print("3. 抖音")
            
            platform_choice = input("请选择 (1-3): ").strip()
            platforms = ['youtube', 'bilibili', 'douyin']
            
            if platform_choice.isdigit() and 1 <= int(platform_choice) <= 3:
                platform = platforms[int(platform_choice) - 1]
            else:
                print("无效选择，使用默认: YouTube")
                platform = 'youtube'
            
            keyword = input("请输入搜索关键词: ").strip()
            if not keyword:
                print("关键词不能为空")
                return
            
            page = input("页码 (默认1): ").strip()
            page = int(page) if page.isdigit() else 1
            
            max_results = input("最大结果数 (默认20): ").strip()
            max_results = int(max_results) if max_results.isdigit() else 20
            
            print(f"\n正在搜索 {platform} 的视频...")
            videos = crawler.search_videos(platform, keyword, page, max_results)
            
            if videos:
                print(f"\n找到 {len(videos)} 个视频:")
                for i, video in enumerate(videos[:10], 1):
                    title = video.get('title', '无标题')
                    platform = video.get('platform', '未知')
                    
                    print(f"{i}. {title[:60]}... ({platform})")
                    
                    if 'views' in video:
                        print(f"   观看: {video['views']}")
                    if 'upload_time' in video:
                        print(f"   时间: {video['upload_time']}")
                    if 'duration' in video:
                        print(f"   时长: {video['duration']}")
                    print()
                
                # 保存搜索结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'video_search_{platform}_{keyword}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(videos, f, ensure_ascii=False, indent=2)
                print(f"搜索结果已保存到: {filename}")
            else:
                print("未找到相关视频")
                
        elif choice == '2':
            url = input("请输入视频URL: ").strip()
            if url:
                details = crawler.get_video_details(url)
                
                if details:
                    print(f"\n=== 视频详情 ===")
                    print(f"平台: {details.get('platform', '未知')}")
                    print(f"标题: {details.get('title', '无标题')}")
                    
                    if 'description' in details:
                        print(f"简介: {details.get('description', '')[:200]}...")
                    
                    # 显示统计信息
                    stats = []
                    if 'views' in details:
                        stats.append(f"观看: {details['views']}")
                    if 'play' in details:
                        stats.append(f"播放: {details['play']}")
                    if 'likes' in details:
                        stats.append(f"点赞: {details['likes']}")
                    if 'comments' in details:
                        stats.append(f"评论: {details['comments']}")
                    
                    if stats:
                        print(f"数据: {' | '.join(stats)}")
                    
                    if 'duration' in details:
                        print(f"时长: {details['duration']}")
                    if 'upload_time' in details:
                        print(f"发布时间: {details['upload_time']}")
                    if 'publish_date' in details:
                        print(f"发布日期: {details['publish_date']}")
                    
                    # 保存详情
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    video_id = details.get('video_id', 'unknown')
                    filename = f'video_details_{video_id}_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(details, f, ensure_ascii=False, indent=2)
                    print(f"\n详情已保存到: {filename}")
                else:
                    print("获取视频详情失败")
            else:
                print("URL不能为空")
                
        elif choice == '3':
            # 先搜索一些视频进行分析
            platform = input("请输入平台 (youtube/bilibili, 默认youtube): ").strip() or 'youtube'
            keyword = input("请输入关键词 (默认'tutorial'): ").strip() or 'tutorial'
            
            print(f"\n正在获取 {platform} 的视频数据进行分析...")
            videos = crawler.search_videos(platform, keyword, max_results=30)
            
            if videos:
                analysis = crawler.analyze_video_data(videos)
                
                print(f"\n=== 视频数据分析 ===")
                print(f"总视频数: {analysis['total_videos']}")
                print(f"平台分布: {analysis['platforms']}")
                
                if 'average_title_length' in analysis:
                    print(f"平均标题长度: {analysis['average_title_length']:.1f} 字符")
                
                if analysis['most_common_words']:
                    print(f"\n热门词汇:")
                    for word, count in analysis['most_common_words'][:5]:
                        print(f"  {word}: {count}次")
                
                # 保存分析结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'video_analysis_{platform}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                print(f"\n分析结果已保存到: {filename}")
            else:
                print("无视频数据可分析")
                
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