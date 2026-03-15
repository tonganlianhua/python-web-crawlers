"""
爬虫 43: B站热门视频爬虫
功能: 爬取Bilibili热门视频、分区视频和UP主信息
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import re
import csv


class BilibiliVideoCrawler:
    """B站视频爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # B站API相关URL
        self.base_api = "https://api.bilibili.com"
        self.hot_url = f"{self.base_api}/x/web-interface/popular"
        self.ranking_url = f"{self.base_api}/x/web-interface/ranking/v2"
        self.search_url = f"{self.base_api}/x/web-interface/search/type"
        self.video_info_url = f"{self.base_api}/x/web-interface/view"
        self.user_info_url = f"{self.base_api}/x/space/acc/info"
        self.user_videos_url = f"{self.base_api}/x/space/arc/search"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.bilibili.com/',
            'Origin': 'https://www.bilibili.com',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # B站分区ID映射
        self.zone_ids = {
            '动画': 1,
            '音乐': 3,
            '舞蹈': 129,
            '游戏': 4,
            '知识': 36,
            '科技': 188,
            '运动': 234,
            '生活': 160,
            '美食': 211,
            '动物': 217,
            '鬼畜': 119,
            '时尚': 155,
            '娱乐': 5,
            '影视': 181,
        }
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.video_cache = {}
        self.user_cache = {}
        
    def get_hot_videos(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        获取B站热门视频
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 热门视频列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取B站热门视频 (第{page}页)")
            
            params = {
                'pn': page,
                'ps': min(page_size, 50),
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.hot_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取热门视频失败，状态码: {response.status_code}")
                return self._retry_get_hot_videos(page, page_size)
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"获取热门视频错误: {data.get('message', '未知错误')}")
                return None
            
            video_list = data.get('data', {}).get('list', [])
            videos = []
            
            for video in video_list:
                try:
                    video_info = {
                        'bvid': video.get('bvid', ''),
                        'aid': video.get('aid', 0),
                        'title': video.get('title', ''),
                        'description': video.get('desc', ''),
                        'duration': video.get('duration', 0),
                        'pubdate': video.get('pubdate', 0),
                        'ctime': video.get('ctime', 0),
                        'owner': {
                            'mid': video.get('owner', {}).get('mid', 0),
                            'name': video.get('owner', {}).get('name', ''),
                        },
                        'stat': {
                            'view': video.get('stat', {}).get('view', 0),
                            'danmaku': video.get('stat', {}).get('danmaku', 0),
                            'reply': video.get('stat', {}).get('reply', 0),
                            'favorite': video.get('stat', {}).get('favorite', 0),
                            'coin': video.get('stat', {}).get('coin', 0),
                            'share': video.get('stat', {}).get('share', 0),
                            'like': video.get('stat', {}).get('like', 0),
                        },
                        'pic': video.get('pic', ''),
                        'tname': video.get('tname', ''),  # 分区名称
                        'copyright': video.get('copyright', 1),  # 1原创，2转载
                        'url': f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                        'hot_score': video.get('score', 0),  # 热度值
                    }
                    videos.append(video_info)
                    
                except Exception as e:
                    print(f"处理视频数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(videos)} 个热门视频")
            return videos
            
        except requests.exceptions.Timeout:
            print("获取热门视频请求超时")
            return self._retry_get_hot_videos(page, page_size)
        except requests.exceptions.ConnectionError:
            print("获取热门视频连接错误")
            return self._retry_get_hot_videos(page, page_size)
        except json.JSONDecodeError:
            print("热门视频响应JSON解析错误")
            return None
        except Exception as e:
            print(f"获取热门视频时发生未知错误: {str(e)}")
            return None
    
    def _retry_get_hot_videos(self, page: int, page_size: int) -> Optional[List[Dict]]:
        """
        重试获取热门视频
        
        Returns:
            List[Dict]: 热门视频列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_hot_videos(page, page_size)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_zone_videos(self, zone_name: str, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        获取分区热门视频
        
        Args:
            zone_name: 分区名称
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 分区视频列表
        """
        try:
            zone_id = self.zone_ids.get(zone_name)
            if not zone_id:
                print(f"未知的分区名称: {zone_name}")
                print(f"可用分区: {', '.join(self.zone_ids.keys())}")
                return None
            
            print(f"[{datetime.now()}] 开始获取 {zone_name} 分区视频 (第{page}页)")
            
            params = {
                'rid': zone_id,
                'type': 'all',
                'pn': page,
                'ps': min(page_size, 100),
            }
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.ranking_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取分区视频失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"获取分区视频错误: {data.get('message', '未知错误')}")
                return None
            
            video_list = data.get('data', {}).get('list', [])
            videos = []
            
            for video in video_list:
                try:
                    video_info = {
                        'bvid': video.get('bvid', ''),
                        'aid': video.get('aid', 0),
                        'title': video.get('title', ''),
                        'description': video.get('desc', ''),
                        'duration': video.get('duration', 0),
                        'pubdate': video.get('pubdate', 0),
                        'owner': {
                            'mid': video.get('owner', {}).get('mid', 0),
                            'name': video.get('owner', {}).get('name', ''),
                        },
                        'stat': {
                            'view': video.get('stat', {}).get('view', 0),
                            'danmaku': video.get('stat', {}).get('danmaku', 0),
                            'reply': video.get('stat', {}).get('reply', 0),
                            'favorite': video.get('stat', {}).get('favorite', 0),
                            'coin': video.get('stat', {}).get('coin', 0),
                            'share': video.get('stat', {}).get('share', 0),
                            'like': video.get('stat', {}).get('like', 0),
                        },
                        'pic': video.get('pic', ''),
                        'tname': zone_name,
                        'copyright': video.get('copyright', 1),
                        'url': f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                        'zone_rank': video.get('pts', 0),  # 分区排名分数
                    }
                    videos.append(video_info)
                    
                except Exception as e:
                    print(f"处理分区视频数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(videos)} 个 {zone_name} 分区视频")
            return videos
            
        except Exception as e:
            print(f"获取分区视频时出错: {str(e)}")
            return None
    
    def get_video_detail(self, bvid: str) -> Optional[Dict]:
        """
        获取视频详细信息
        
        Args:
            bvid: 视频BV号
            
        Returns:
            Dict: 视频详细信息
        """
        # 检查缓存
        if bvid in self.video_cache:
            print(f"从缓存获取视频 {bvid} 的详细信息")
            return self.video_cache[bvid]
        
        try:
            print(f"[{datetime.now()}] 开始获取视频详细信息: {bvid}")
            
            params = {
                'bvid': bvid,
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.video_info_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取视频详情失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"获取视频详情错误: {data.get('message', '未知错误')}")
                return None
            
            video_data = data.get('data', {})
            
            # 解析详细信息
            detail = {
                'bvid': bvid,
                'aid': video_data.get('aid', 0),
                'title': video_data.get('title', ''),
                'description': video_data.get('desc', ''),
                'pubdate': video_data.get('pubdate', 0),
                'ctime': video_data.get('ctime', 0),
                'duration': video_data.get('duration', 0),
                'owner': {
                    'mid': video_data.get('owner', {}).get('mid', 0),
                    'name': video_data.get('owner', {}).get('name', ''),
                    'face': video_data.get('owner', {}).get('face', ''),
                },
                'stat': {
                    'view': video_data.get('stat', {}).get('view', 0),
                    'danmaku': video_data.get('stat', {}).get('danmaku', 0),
                    'reply': video_data.get('stat', {}).get('reply', 0),
                    'favorite': video_data.get('stat', {}).get('favorite', 0),
                    'coin': video_data.get('stat', {}).get('coin', 0),
                    'share': video_data.get('stat', {}).get('share', 0),
                    'like': video_data.get('stat', {}).get('like', 0),
                    'dislike': video_data.get('stat', {}).get('dislike', 0),
                },
                'pages': video_data.get('pages', []),  # 分P信息
                'cid': video_data.get('cid', 0),  # 视频CID
                'pic': video_data.get('pic', ''),
                'tname': video_data.get('tname', ''),  # 分区名称
                'copyright': video_data.get('copyright', 1),
                'videos': video_data.get('videos', 1),  # 分P数
                'ugc_pay': video_data.get('rights', {}).get('ugc_pay', 0) == 1,  # 是否付费
                'is_union_video': video_data.get('rights', {}).get('is_union_video', 0) == 1,
                'tags': [tag.get('tag_name', '') for tag in video_data.get('tags', [])],
                'url': f"https://www.bilibili.com/video/{bvid}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.video_cache[bvid] = detail
            
            print(f"[{datetime.now()}] 成功获取视频详细信息")
            return detail
            
        except Exception as e:
            print(f"获取视频详细信息时出错: {str(e)}")
            return None
    
    def get_user_info(self, mid: int) -> Optional[Dict]:
        """
        获取UP主信息
        
        Args:
            mid: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        # 检查缓存
        if mid in self.user_cache:
            print(f"从缓存获取用户 {mid} 的信息")
            return self.user_cache[mid]
        
        try:
            print(f"[{datetime.now()}] 开始获取UP主信息: {mid}")
            
            params = {
                'mid': mid,
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.user_info_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取UP主信息失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"获取UP主信息错误: {data.get('message', '未知错误')}")
                return None
            
            user_data = data.get('data', {})
            
            # 解析用户信息
            user_info = {
                'mid': mid,
                'name': user_data.get('name', ''),
                'sex': user_data.get('sex', ''),
                'face': user_data.get('face', ''),
                'sign': user_data.get('sign', ''),  # 签名
                'rank': user_data.get('rank', 0),  # 等级
                'level': user_data.get('level', {}).get('current_level', 0),
                'vip': {
                    'type': user_data.get('vip', {}).get('type', 0),
                    'status': user_data.get('vip', {}).get('status', 0) == 1,
                    'label': user_data.get('vip', {}).get('label', {}).get('text', ''),
                },
                'official': {
                    'role': user_data.get('official', {}).get('role', 0),
                    'title': user_data.get('official', {}).get('title', ''),
                    'desc': user_data.get('official', {}).get('desc', ''),
                },
                'url': f"https://space.bilibili.com/{mid}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 获取用户统计数据
            stat_url = f"{self.base_api}/x/relation/stat"
            time.sleep(0.5)
            
            stat_response = self.session.get(
                stat_url,
                params={'vmid': mid},
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if stat_response.status_code == 200:
                stat_data = stat_response.json()
                if stat_data.get('code') == 0:
                    stat_info = stat_data.get('data', {})
                    user_info['stat'] = {
                        'following': stat_info.get('following', 0),  # 关注数
                        'follower': stat_info.get('follower', 0),  # 粉丝数
                        'whisper': stat_info.get('whisper', 0),  # 悄悄关注
                        'black': stat_info.get('black', 0),  # 黑名单
                    }
            
            # 缓存数据
            self.user_cache[mid] = user_info
            
            print(f"[{datetime.now()}] 成功获取UP主信息")
            return user_info
            
        except Exception as e:
            print(f"获取UP主信息时出错: {str(e)}")
            return None
    
    def analyze_video_metrics(self, video_detail: Dict) -> Dict:
        """
        分析视频指标
        
        Args:
            video_detail: 视频详细信息
            
        Returns:
            Dict: 分析指标
        """
        try:
            stat = video_detail.get('stat', {})
            
            # 计算互动率（点赞+硬币+收藏+分享+评论）/ 播放量
            view = stat.get('view', 0)
            if view == 0:
                return {
                    'interaction_rate': 0,
                    'quality_score': 0,
                    'popularity_score': 0,
                }
            
            interactions = (
                stat.get('like', 0) +
                stat.get('coin', 0) +
                stat.get('favorite', 0) +
                stat.get('share', 0) +
                stat.get('reply', 0)
            )
            
            interaction_rate = (interactions / view) * 100
            
            # 质量评分（点赞+硬币+收藏）/ 播放量 * 100
            quality_score = (
                (stat.get('like', 0) + stat.get('coin', 0) + stat.get('favorite', 0)) / view
            ) * 100 if view > 0 else 0
            
            # 热度评分（综合播放、弹幕、评论）
            popularity_score = min(100, (
                min(stat.get('view', 0) / 1000000, 40) +  # 播放量权重
                min(stat.get('danmaku', 0) / 1000, 20) +  # 弹幕权重
                min(stat.get('reply', 0) / 1000, 20) +  # 评论权重
                min(interaction_rate * 2, 20)  # 互动率权重
            ))
            
            return {
                'interaction_rate': round(interaction_rate, 2),
                'quality_score': round(quality_score, 2),
                'popularity_score': round(popularity_score, 2),
                'view_per_day': self._calculate_view_per_day(video_detail),
                'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
        except Exception as e:
            print(f"分析视频指标时出错: {str(e)}")
            return {}
    
    def _calculate_view_per_day(self, video_detail: Dict) -> float:
        """
        计算日均播放量
        
        Args:
            video_detail: 视频详细信息
            
        Returns:
            float: 日均播放量
        """
        try:
            pubdate = video_detail.get('pubdate', 0)
            if pubdate == 0:
                return 0
            
            view = video_detail.get('stat', {}).get('view', 0)
            
            # 计算发布天数
            pub_time = datetime.fromtimestamp(pubdate)
            now = datetime.now()
            days_passed = max((now - pub_time).total_seconds() / 86400, 1)  # 至少1天
            
            return round(view / days_passed, 2)
            
        except:
            return 0
    
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
            filename = f"bilibili_videos_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            print(f"保存数据到JSON时出错: {str(e)}")
    
    def run(self, zones: List[str] = None, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            zones: 分区列表，默认为热门分区
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("B站视频爬虫开始运行")
        print("=" * 50)
        
        if zones is None:
            zones = ['知识', '科技', '生活', '游戏']
        
        all_videos = []
        
        # 获取全站热门视频
        print("\n获取全站热门视频...")
        hot_videos = self.get_hot_videos(page=1, page_size=20)
        
        if hot_videos:
            for video in hot_videos[:10]:  # 只处理前10个
                try:
                    bvid = video.get('bvid')
                    if not bvid:
                        continue
                    
                    # 获取详细信息
                    detail = self.get_video_detail(bvid)
                    if not detail:
                        continue
                    
                    # 获取UP主信息
                    owner_mid = detail.get('owner', {}).get('mid')
                    user_info = None
                    if owner_mid:
                        user_info = self.get_user_info(owner_mid)
                    
                    # 分析指标
                    metrics = self.analyze_video_metrics(detail)
                    
                    # 合并数据
                    complete_data = {
                        **video,
                        **detail,
                        'owner_info': user_info,
                        **metrics,
                        'source': 'hot',
                    }
                    
                    all_videos.append(complete_data)
                    
                    print(f"  已处理: {video.get('title')} (播放: {video.get('stat', {}).get('view', 0):,})")
                    
                    # 避免请求过快
                    time.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    print(f"处理视频 {video.get('title')} 时出错: {str(e)}")
                    continue
        
        # 获取分区视频
        for zone in zones:
            print(f"\n获取 {zone} 分区视频...")
            zone_videos = self.get_zone_videos(zone, page=1, page_size=10)
            
            if zone_videos:
                for video in zone_videos[:5]:  # 每个分区只处理前5个
                    try:
                        bvid = video.get('bvid')
                        if not bvid or any(v.get('bvid') == bvid for v in all_videos):
                            continue  # 避免重复
                        
                        # 获取详细信息
                        detail = self.get_video_detail(bvid)
                        if not detail:
                            continue
                        
                        # 分析指标
                        metrics = self.analyze_video_metrics(detail)
                        
                        # 合并数据
                        complete_data = {
                            **video,
                            **detail,
                            **metrics,
                            'source': f'zone_{zone}',
                        }
                        
                        all_videos.append(complete_data)
                        
                        print(f"  已处理: {video.get('title')}")
                        
                        time.sleep(random.uniform(1, 2))
                        
                    except Exception as e:
                        print(f"处理分区视频时出错: {str(e)}")
                        continue
        
        # 保存到文件
        if save_to_file and all_videos:
            self.save_to_json(all_videos)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_videos)} 个视频数据")
        print("=" * 50)
        
        return all_videos


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = BilibiliVideoCrawler()
        
        # 运行爬虫
        videos = crawler.run(
            zones=['知识', '科技'],  # 可以修改分区
            save_to_file=True
        )
        
        if videos:
            print(f"\n数据统计:")
            print(f"总视频数: {len(videos)}")
            
            # 按播放量排序
            sorted_videos = sorted(videos, key=lambda x: x.get('stat', {}).get('view', 0), reverse=True)
            
            print(f"\n播放量最高的前5个视频:")
            for idx, video in enumerate(sorted_videos[:5], 1):
                title = video.get('title', '')[:50]
                if len(video.get('title', '')) > 50:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     播放: {video.get('stat', {}).get('view', 0):,} | "
                      f"点赞: {video.get('stat', {}).get('like', 0):,} | "
                      f"UP主: {video.get('owner', {}).get('name', '')}")
                print(f"     互动率: {video.get('interaction_rate', 0):.2f}% | "
                      f"质量评分: {video.get('quality_score', 0):.2f}")
        else:
            print("未能获取视频数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()