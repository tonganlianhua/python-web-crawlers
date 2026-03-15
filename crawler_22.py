#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐平台数据爬虫 - 网易云音乐热歌榜
爬取网易云音乐热歌榜：歌曲名、歌手、专辑、时长、播放量等
"""

import requests
import json
import time
import hashlib
import base64
from typing import Dict, List, Optional, Tuple
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
class NeteaseSong:
    """网易云音乐歌曲数据结构"""
    name: str
    id: int
    artists: List[str]  # 歌手列表
    album: str
    duration: int  # 时长（毫秒）
    play_count: int  # 播放次数
    score: float  # 热度评分
    publish_time: str  # 发布时间
    url: str  # 歌曲链接（需要VIP）
    album_pic_url: str  # 专辑封面


class NeteaseCloudMusicCrawler:
    """网易云音乐爬虫类"""
    
    def __init__(self):
        self.base_url = "https://music.163.com"
        self.api_url = "https://music.163.com/weapi"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 网易云音乐API加密参数
        self.encSecKey = "257348aecb5e556c066de214e531faadd1c55d814f9be95fd06d6bff9f4c7a41f831f6394d5a3fd2e3881736d94a02ca919d952872e7d0a50ebfa1769a7a62d512f5f1ca21aec60bc3819a9c3ffca5eca9a0dba6d6f7249b06f5965ecfff3695b54e1c28f3f624750ed39e7de08fc8493242e26dbc4484a01c76f739e135637c"
        self.encKey = "0CoJUm6Qyw8W8jud"
        
    def _encrypt_params(self, data: Dict) -> Dict:
        """
        加密请求参数（模拟网易云音乐Web API加密）
        
        Args:
            data: 原始请求参数
            
        Returns:
            加密后的参数
        """
        import random
        import string
        
        try:
            # 转换为JSON字符串
            text = json.dumps(data)
            
            # 第一次加密
            first_key = self.encKey
            first_enc = self._aes_encrypt(text, first_key)
            
            # 第二次加密
            second_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            second_enc = self._aes_encrypt(first_enc, second_key)
            
            return {
                'params': second_enc,
                'encSecKey': self.encSecKey
            }
            
        except Exception as e:
            logger.error(f"加密参数失败: {e}")
            return {}
    
    def _aes_encrypt(self, text: str, key: str) -> str:
        """AES加密"""
        from Crypto.Cipher import AES
        import base64
        
        # 填充文本
        pad = 16 - len(text) % 16
        text = text + chr(pad) * pad
        
        # 加密
        cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, '0102030405060708'.encode('utf-8'))
        encrypted = cipher.encrypt(text.encode('utf-8'))
        
        # Base64编码
        return base64.b64encode(encrypted).decode('utf-8')
    
    def get_top_list(self, list_id: int = 3778678, limit: int = 100) -> List[NeteaseSong]:
        """
        获取排行榜歌曲列表
        
        Args:
            list_id: 榜单ID (3778678=热歌榜, 19723756=飙升榜, 3779629=新歌榜)
            limit: 获取数量
            
        Returns:
            歌曲对象列表
        """
        url = f"{self.api_url}/v3/playlist/detail"
        
        data = {
            'id': list_id,
            'n': limit,
            's': 8,  # 不知道干啥的，但是API需要
            'csrf_token': ''
        }
        
        encrypted_params = self._encrypt_params(data)
        
        try:
            logger.info(f"正在获取榜单 {list_id} 的歌曲，数量: {limit}")
            
            response = self.session.post(
                url, 
                data=encrypted_params,
                timeout=15
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') != 200:
                logger.error(f"API返回错误: {result.get('message')}")
                return []
            
            songs = []
            tracks = result.get('playlist', {}).get('tracks', [])
            
            for track in tracks:
                try:
                    # 获取艺术家列表
                    artists = [artist.get('name', '') for artist in track.get('ar', [])]
                    
                    song = NeteaseSong(
                        name=track.get('name', ''),
                        id=track.get('id', 0),
                        artists=artists,
                        album=track.get('al', {}).get('name', ''),
                        duration=track.get('dt', 0),  # 时长（毫秒）
                        play_count=track.get('pop', 0),  # 热度
                        score=track.get('pop', 0) / 1000.0,  # 转换热度评分
                        publish_time=self._timestamp_to_date(track.get('publishTime', 0)),
                        url=f"https://music.163.com/#/song?id={track.get('id', 0)}",
                        album_pic_url=track.get('al', {}).get('picUrl', '')
                    )
                    songs.append(song)
                    
                except Exception as e:
                    logger.warning(f"解析歌曲数据失败: {e}")
                    continue
            
            logger.info(f"成功获取 {len(songs)} 首歌曲")
            return songs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return []
    
    def _timestamp_to_date(self, timestamp: int) -> str:
        """时间戳转换为日期字符串"""
        if timestamp <= 0:
            return "未知"
        
        try:
            # 网易云音乐的时间戳通常是毫秒
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime("%Y-%m-%d")
        except:
            return "未知"
    
    def _format_duration(self, milliseconds: int) -> str:
        """格式化时长（毫秒转换为分:秒）"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def get_song_comments(self, song_id: int, limit: int = 20) -> List[Dict]:
        """
        获取歌曲评论
        
        Args:
            song_id: 歌曲ID
            limit: 评论数量
            
        Returns:
            评论列表
        """
        url = f"{self.api_url}/v1/resource/comments/R_SO_4_{song_id}"
        
        data = {
            'rid': f'R_SO_4_{song_id}',
            'offset': 0,
            'total': False,
            'limit': limit,
            'csrf_token': ''
        }
        
        encrypted_params = self._encrypt_params(data)
        
        try:
            logger.info(f"正在获取歌曲 {song_id} 的评论")
            
            response = self.session.post(
                url,
                data=encrypted_params,
                timeout=15
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') != 200:
                logger.error(f"获取评论失败: {result.get('message')}")
                return []
            
            comments = []
            for comment in result.get('comments', []):
                try:
                    comment_data = {
                        'user_id': comment.get('user', {}).get('userId', 0),
                        'user_name': comment.get('user', {}).get('nickname', ''),
                        'content': comment.get('content', ''),
                        'time': self._timestamp_to_date(comment.get('time', 0)),
                        'liked_count': comment.get('likedCount', 0),
                        'reply_count': comment.get('replyCount', 0)
                    }
                    comments.append(comment_data)
                except:
                    continue
            
            return comments
            
        except Exception as e:
            logger.error(f"获取评论失败: {e}")
            return []
    
    def save_to_csv(self, songs: List[NeteaseSong], filename: str = "netease_songs.csv"):
        """
        保存歌曲数据到CSV文件
        
        Args:
            songs: 歌曲对象列表
            filename: 输出文件名
        """
        if not songs:
            logger.warning("没有歌曲数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'name', 'id', 'artists', 'album', 'duration_ms', 
                    'duration_formatted', 'play_count', 'score', 
                    'publish_time', 'url', 'album_pic_url'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for song in songs:
                    row = song.__dict__.copy()
                    # 转换艺术家列表为字符串
                    row['artists'] = ', '.join(row['artists'])
                    # 添加格式化时长
                    row['duration_formatted'] = self._format_duration(row['duration'])
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(songs)} 首歌曲数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def analyze_songs(self, songs: List[NeteaseSong]) -> Dict:
        """
        分析歌曲数据
        
        Args:
            songs: 歌曲对象列表
            
        Returns:
            分析结果字典
        """
        if not songs:
            return {}
        
        try:
            # 统计信息
            total_duration = sum(song.duration for song in songs)
            avg_duration = total_duration / len(songs) if songs else 0
            
            # 最常见的艺术家
            artist_counts = {}
            for song in songs:
                for artist in song.artists:
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1
            
            top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 最热门的歌曲
            top_songs = sorted(songs, key=lambda x: x.play_count, reverse=True)[:5]
            
            # 最新发布的歌曲
            recent_songs = sorted(songs, key=lambda x: x.publish_time, reverse=True)[:5]
            
            return {
                'total_songs': len(songs),
                'avg_duration_ms': int(avg_duration),
                'avg_duration_formatted': self._format_duration(int(avg_duration)),
                'top_artists': top_artists,
                'top_songs': [(song.name, song.play_count) for song in top_songs],
                'recent_songs': [(song.name, song.publish_time) for song in recent_songs]
            }
            
        except Exception as e:
            logger.error(f"分析歌曲数据失败: {e}")
            return {}


def main():
    """主函数"""
    print("=" * 50)
    print("网易云音乐数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = NeteaseCloudMusicCrawler()
    
    try:
        # 1. 获取热歌榜
        print("正在爬取网易云音乐热歌榜...")
        songs = crawler.get_top_list(list_id=3778678, limit=50)
        
        if not songs:
            print("未获取到歌曲数据，程序退出")
            return
        
        # 2. 显示统计信息
        print(f"\n成功获取 {len(songs)} 首热门歌曲:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_songs(songs)
        
        if analysis:
            print(f"总计歌曲: {analysis['total_songs']}")
            print(f"平均时长: {analysis['avg_duration_formatted']}")
            print("\n最受欢迎的歌手:")
            for artist, count in analysis['top_artists']:
                print(f"  {artist}: {count} 首歌")
            
            print("\n播放量最高的歌曲:")
            for i, (name, play_count) in enumerate(analysis['top_songs'], 1):
                print(f"  {i}. {name[:30]}... - 播放: {play_count:,}")
        
        # 3. 显示前5首歌曲详情
        print("\n热歌榜 TOP 5:")
        print("-" * 30)
        for i, song in enumerate(songs[:5], 1):
            print(f"{i}. {song.name}")
            print(f"   歌手: {', '.join(song.artists)}")
            print(f"   专辑: {song.album}")
            print(f"   时长: {crawler._format_duration(song.duration)}")
            print(f"   热度: {song.play_count:,}")
            print()
        
        # 4. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"netease_songs_{timestamp}.csv"
        
        crawler.save_to_csv(songs, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 5. 获取并展示一首歌的评论
        if songs:
            sample_song = songs[0]
            print(f"\n获取歌曲 '{sample_song.name[:20]}...' 的热门评论:")
            comments = crawler.get_song_comments(sample_song.id, limit=5)
            
            if comments:
                for i, comment in enumerate(comments[:3], 1):
                    print(f"{i}. {comment['user_name']}: {comment['content'][:50]}...")
                    print(f"   时间: {comment['time']}, 点赞: {comment['liked_count']}")
                    print()
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()