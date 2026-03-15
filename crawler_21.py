#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频网站数据爬虫 - 哔哩哔哩热门视频信息
爬取B站热门视频信息：标题、播放量、弹幕数、UP主等
"""

import requests
import json
import time
import random
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from datetime import datetime
import csv
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BilibiliVideo:
    """B站视频数据结构"""
    title: str
    bvid: str
    aid: int
    play: int  # 播放量
    danmaku: int  # 弹幕数
    reply: int  # 评论数
    favorite: int  # 收藏数
    coin: int  # 硬币数
    share: int  # 分享数
    like: int  # 点赞数
    author: str  # UP主
    duration: str  # 时长
    pubdate: int  # 发布时间戳
    desc: str  # 视频描述


class BilibiliCrawler:
    """B站视频爬虫类"""
    
    def __init__(self):
        self.base_url = "https://api.bilibili.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_popular_videos(self, pn: int = 1, ps: int = 20) -> List[BilibiliVideo]:
        """
        获取热门视频列表
        
        Args:
            pn: 页码，从1开始
            ps: 每页数量，最大50
            
        Returns:
            视频对象列表
        """
        url = f"{self.base_url}/x/web-interface/popular"
        params = {
            'pn': pn,
            'ps': ps
        }
        
        try:
            logger.info(f"正在获取热门视频，页码: {pn}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"API返回错误: {data.get('message')}")
                return []
            
            videos = []
            for item in data.get('data', {}).get('list', []):
                try:
                    video = BilibiliVideo(
                        title=item.get('title', ''),
                        bvid=item.get('bvid', ''),
                        aid=item.get('aid', 0),
                        play=item.get('stat', {}).get('view', 0),
                        danmaku=item.get('stat', {}).get('danmaku', 0),
                        reply=item.get('stat', {}).get('reply', 0),
                        favorite=item.get('stat', {}).get('favorite', 0),
                        coin=item.get('stat', {}).get('coin', 0),
                        share=item.get('stat', {}).get('share', 0),
                        like=item.get('stat', {}).get('like', 0),
                        author=item.get('owner', {}).get('name', ''),
                        duration=self._format_duration(item.get('duration', 0)),
                        pubdate=item.get('pubdate', 0),
                        desc=item.get('desc', '')[:100]  # 截取前100字符
                    )
                    videos.append(video)
                except Exception as e:
                    logger.warning(f"解析视频数据失败: {e}")
                    continue
                    
            logger.info(f"成功获取 {len(videos)} 个视频")
            return videos
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return []
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长（秒转换为时分秒）"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def get_video_details(self, bvid: str) -> Optional[Dict]:
        """
        获取视频详细信息
        
        Args:
            bvid: 视频BV号
            
        Returns:
            视频详细信息字典
        """
        url = f"{self.base_url}/x/web-interface/view"
        params = {'bvid': bvid}
        
        try:
            logger.info(f"正在获取视频详情: {bvid}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"获取视频详情失败: {data.get('message')}")
                return None
            
            return data.get('data')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
    
    def save_to_csv(self, videos: List[BilibiliVideo], filename: str = "bilibili_videos.csv"):
        """
        保存视频数据到CSV文件
        
        Args:
            videos: 视频对象列表
            filename: 输出文件名
        """
        if not videos:
            logger.warning("没有视频数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'title', 'bvid', 'aid', 'play', 'danmaku', 'reply', 
                    'favorite', 'coin', 'share', 'like', 'author', 
                    'duration', 'pubdate', 'desc'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for video in videos:
                    writer.writerow(video.__dict__)
            
            logger.info(f"已保存 {len(videos)} 条视频数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def save_to_json(self, videos: List[BilibiliVideo], filename: str = "bilibili_videos.json"):
        """
        保存视频数据到JSON文件
        
        Args:
            videos: 视频对象列表
            filename: 输出文件名
        """
        if not videos:
            logger.warning("没有视频数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                data = [video.__dict__ for video in videos]
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(videos)} 条视频数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("B站视频数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = BilibiliCrawler()
    
    try:
        # 1. 获取热门视频
        print("正在爬取热门视频数据...")
        videos = crawler.get_popular_videos(pn=1, ps=20)
        
        if not videos:
            print("未获取到视频数据，程序退出")
            return
        
        # 2. 显示统计信息
        print(f"\n成功获取 {len(videos)} 个热门视频:")
        print("-" * 30)
        
        # 按播放量排序
        top_videos = sorted(videos, key=lambda x: x.play, reverse=True)[:5]
        
        for i, video in enumerate(top_videos, 1):
            print(f"{i}. {video.title[:30]}...")
            print(f"   UP主: {video.author}, 播放: {video.play:,}, 时长: {video.duration}")
            print(f"   点赞: {video.like:,}, 硬币: {video.coin:,}, 收藏: {video.favorite:,}")
            print()
        
        # 3. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"bilibili_videos_{timestamp}.csv"
        json_file = f"bilibili_videos_{timestamp}.json"
        
        crawler.save_to_csv(videos, csv_file)
        crawler.save_to_json(videos, json_file)
        
        print(f"\n数据已保存到:")
        print(f"  - {csv_file}")
        print(f"  - {json_file}")
        
        # 4. 获取并展示一个视频的详细信息
        if videos:
            sample_video = videos[0]
            print(f"\n获取视频 '{sample_video.title[:20]}...' 的详细信息:")
            details = crawler.get_video_details(sample_video.bvid)
            
            if details:
                print(f"完整标题: {details.get('title')}")
                print(f"分区: {details.get('tname')}")
                print(f"简介: {details.get('desc', '')[:100]}...")
                
                # 获取标签
                tags = [tag.get('tag_name') for tag in details.get('tags', [])][:5]
                if tags:
                    print(f"标签: {', '.join(tags)}")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()