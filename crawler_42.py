"""
爬虫 42: 抖音网红数据爬虫
功能: 爬取抖音网红账号数据、视频信息和粉丝分析
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import hashlib
import urllib.parse
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import re
import csv


class DouyinInfluencerCrawler:
    """抖音网红数据爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # 抖音API相关URL
        self.search_url = "https://www.douyin.com/aweme/v1/web/discover/search/"
        self.user_info_url = "https://www.douyin.com/aweme/v1/web/user/profile/other/"
        self.user_videos_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
        self.hot_videos_url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.douyin.com/',
            'Origin': 'https://www.douyin.com',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存已获取的用户数据
        self.user_cache = {}
        
    def _sign_url(self, url: str) -> str:
        """
        为抖音URL生成签名（简化版）
        
        Args:
            url: 原始URL
            
        Returns:
            str: 带签名的URL
        """
        # 在实际应用中，这里需要实现抖音的反爬虫签名算法
        # 这里使用简化版本，实际使用时需要根据抖音的算法更新
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # 添加时间戳
        query_params['_signature'] = ['simulated_signature']
        query_params['msToken'] = ['simulated_msToken']
        query_params['X-Bogus'] = ['simulated_X-Bogus']
        
        # 重新构造URL
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        signed_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
        
        return signed_url
    
    def search_influencers(self, keyword: str, count: int = 20) -> Optional[List[Dict]]:
        """
        搜索抖音网红账号
        
        Args:
            keyword: 搜索关键词
            count: 返回数量
            
        Returns:
            List[Dict]: 网红账号列表
        """
        try:
            print(f"[{datetime.now()}] 开始搜索抖音网红: {keyword}")
            
            # 构造搜索参数
            params = {
                'keyword': keyword,
                'search_source': 'normal_search',
                'search_id': '',
                'count': min(count, 20),
                'offset': 0,
                'is_full_text': 1,
                'search_type': 'user',
            }
            
            # 随机延迟
            time.sleep(random.uniform(2, 4))
            
            # 发送请求
            response = self.session.get(
                self.search_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"搜索失败，状态码: {response.status_code}")
                return self._retry_search(keyword, count)
            
            # 解析响应
            data = response.json()
            
            if data.get('status_code') != 0:
                print(f"搜索返回错误: {data.get('status_msg', '未知错误')}")
                return None
            
            user_list = data.get('user_list', [])
            influencers = []
            
            for user in user_list[:count]:
                try:
                    user_info = user.get('user_info', {})
                    
                    influencer = {
                        'user_id': user_info.get('uid', ''),
                        'sec_uid': user_info.get('sec_uid', ''),
                        'nickname': user_info.get('nickname', ''),
                        'unique_id': user_info.get('unique_id', ''),
                        'signature': user_info.get('signature', ''),
                        'avatar_url': user_info.get('avatar_larger', {}).get('url_list', [''])[0],
                        'follower_count': user_info.get('follower_count', 0),
                        'following_count': user_info.get('following_count', 0),
                        'total_favorited': user_info.get('total_favorited', 0),  # 获赞总数
                        'aweme_count': user_info.get('aweme_count', 0),  # 作品数
                        'is_verified': user_info.get('is_verified', False),
                        'verified_type': user_info.get('custom_verify', ''),
                        'search_score': user.get('position', 999),  # 搜索排名
                        'url': f"https://www.douyin.com/user/{user_info.get('sec_uid', '')}"
                    }
                    
                    influencers.append(influencer)
                    
                except Exception as e:
                    print(f"处理用户数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功搜索到 {len(influencers)} 个网红账号")
            return influencers
            
        except requests.exceptions.Timeout:
            print("搜索请求超时")
            return self._retry_search(keyword, count)
        except requests.exceptions.ConnectionError:
            print("搜索连接错误")
            return self._retry_search(keyword, count)
        except json.JSONDecodeError:
            print("搜索响应JSON解析错误")
            return None
        except Exception as e:
            print(f"搜索网红时发生未知错误: {str(e)}")
            return None
    
    def _retry_search(self, keyword: str, count: int) -> Optional[List[Dict]]:
        """
        重试搜索
        
        Returns:
            List[Dict]: 网红账号列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.search_influencers(keyword, count)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_user_detail(self, sec_uid: str) -> Optional[Dict]:
        """
        获取网红详细资料
        
        Args:
            sec_uid: 用户sec_uid
            
        Returns:
            Dict: 用户详细资料
        """
        # 检查缓存
        if sec_uid in self.user_cache:
            print(f"从缓存获取用户 {sec_uid} 的数据")
            return self.user_cache[sec_uid]
        
        try:
            print(f"[{datetime.now()}] 开始获取用户详细资料: {sec_uid}")
            
            # 构造参数
            params = {
                'sec_user_id': sec_uid,
                'device_platform': 'web',
                'aid': 6383,
            }
            
            time.sleep(random.uniform(3, 5))
            
            response = self.session.get(
                self.user_info_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取用户资料失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('status_code') != 0:
                print(f"获取用户资料错误: {data.get('status_msg', '未知错误')}")
                return None
            
            user_info = data.get('user', {})
            
            # 解析详细资料
            detail = {
                'user_id': user_info.get('uid', ''),
                'sec_uid': sec_uid,
                'nickname': user_info.get('nickname', ''),
                'unique_id': user_info.get('unique_id', ''),
                'signature': user_info.get('signature', ''),
                'avatar_url': user_info.get('avatar_larger', {}).get('url_list', [''])[0],
                'follower_count': user_info.get('follower_count', 0),
                'following_count': user_info.get('following_count', 0),
                'total_favorited': user_info.get('total_favorited', 0),
                'aweme_count': user_info.get('aweme_count', 0),
                'is_verified': user_info.get('is_verified', False),
                'verified_type': user_info.get('custom_verify', ''),
                'region': user_info.get('region', ''),
                'birthday': user_info.get('birthday', ''),
                'constellation': user_info.get('constellation', ''),
                'school_name': user_info.get('school_name', ''),
                'enterprise_verify_reason': user_info.get('enterprise_verify_reason', ''),
                'live_status': user_info.get('room_id', 0) > 0,  # 是否在直播
                'live_room_id': user_info.get('room_id', ''),
                'ip_location': user_info.get('ip_location', ''),
                'collected_video_count': user_info.get('collected_video_count', 0),  # 收藏数
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.user_cache[sec_uid] = detail
            
            print(f"[{datetime.now()}] 成功获取用户详细资料")
            return detail
            
        except Exception as e:
            print(f"获取用户详细资料时出错: {str(e)}")
            return None
    
    def get_user_videos(self, sec_uid: str, count: int = 10) -> Optional[List[Dict]]:
        """
        获取网红发布的视频
        
        Args:
            sec_uid: 用户sec_uid
            count: 视频数量
            
        Returns:
            List[Dict]: 视频列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取用户视频: {sec_uid}")
            
            videos = []
            max_cursor = 0
            has_more = True
            
            while has_more and len(videos) < count:
                params = {
                    'sec_user_id': sec_uid,
                    'count': 20,
                    'max_cursor': max_cursor,
                    'device_platform': 'web',
                    'aid': 6383,
                }
                
                time.sleep(random.uniform(2, 3))
                
                response = self.session.get(
                    self.user_videos_url,
                    params=params,
                    headers=self.headers,
                    proxies=self.proxy,
                    timeout=15
                )
                
                if response.status_code != 200:
                    print(f"获取视频失败，状态码: {response.status_code}")
                    break
                
                data = response.json()
                
                if data.get('status_code') != 0:
                    print(f"获取视频错误: {data.get('status_msg', '未知错误')}")
                    break
                
                aweme_list = data.get('aweme_list', [])
                has_more = data.get('has_more', False)
                max_cursor = data.get('max_cursor', 0)
                
                for video in aweme_list:
                    if len(videos) >= count:
                        break
                    
                    try:
                        video_info = {
                            'video_id': video.get('aweme_id', ''),
                            'desc': video.get('desc', ''),
                            'create_time': video.get('create_time', 0),
                            'video_url': video.get('video', {}).get('play_addr', {}).get('url_list', [''])[0],
                            'cover_url': video.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                            'duration': video.get('duration', 0),
                            'width': video.get('video', {}).get('width', 0),
                            'height': video.get('video', {}).get('height', 0),
                            'statistics': {
                                'digg_count': video.get('statistics', {}).get('digg_count', 0),
                                'comment_count': video.get('statistics', {}).get('comment_count', 0),
                                'share_count': video.get('statistics', {}).get('share_count', 0),
                                'collect_count': video.get('statistics', {}).get('collect_count', 0),
                                'play_count': video.get('statistics', {}).get('play_count', 0),
                            },
                            'music': {
                                'title': video.get('music', {}).get('title', ''),
                                'author': video.get('music', {}).get('author', ''),
                            },
                            'hashtags': [tag.get('hashtag_name', '') for tag in video.get('text_extra', [])],
                            'url': f"https://www.douyin.com/video/{video.get('aweme_id', '')}"
                        }
                        videos.append(video_info)
                    except Exception as e:
                        print(f"处理视频数据时出错: {str(e)}")
                        continue
                
                if not aweme_list:
                    break
            
            print(f"[{datetime.now()}] 成功获取 {len(videos)} 个视频")
            return videos[:count]
            
        except Exception as e:
            print(f"获取用户视频时出错: {str(e)}")
            return None
    
    def analyze_influencer_metrics(self, user_detail: Dict, videos: List[Dict]) -> Dict:
        """
        分析网红指标
        
        Args:
            user_detail: 用户详细资料
            videos: 视频列表
            
        Returns:
            Dict: 分析指标
        """
        try:
            if not videos:
                return {
                    'avg_likes': 0,
                    'avg_comments': 0,
                    'avg_shares': 0,
                    'avg_plays': 0,
                    'engagement_rate': 0,
                    'content_quality_score': 0,
                }
            
            # 计算平均数据
            total_likes = sum(v['statistics']['digg_count'] for v in videos)
            total_comments = sum(v['statistics']['comment_count'] for v in videos)
            total_shares = sum(v['statistics']['share_count'] for v in videos)
            total_plays = sum(v['statistics']['play_count'] for v in videos)
            
            avg_likes = total_likes / len(videos)
            avg_comments = total_comments / len(videos)
            avg_shares = total_shares / len(videos)
            avg_plays = total_plays / len(videos)
            
            # 计算互动率（点赞+评论+分享）/ 播放量
            total_interactions = total_likes + total_comments + total_shares
            engagement_rate = (total_interactions / total_plays * 100) if total_plays > 0 else 0
            
            # 内容质量评分（简化版）
            content_quality_score = min(100, (
                (avg_likes / 1000 * 30) +  # 点赞权重
                (avg_comments / 100 * 20) +  # 评论权重
                (avg_shares / 50 * 20) +  # 分享权重
                (engagement_rate * 30)  # 互动率权重
            ))
            
            return {
                'avg_likes': round(avg_likes, 2),
                'avg_comments': round(avg_comments, 2),
                'avg_shares': round(avg_shares, 2),
                'avg_plays': round(avg_plays, 2),
                'engagement_rate': round(engagement_rate, 2),
                'content_quality_score': round(content_quality_score, 2),
                'follower_count': user_detail.get('follower_count', 0),
                'video_count': len(videos),
                'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
        except Exception as e:
            print(f"分析网红指标时出错: {str(e)}")
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
            filename = f"douyin_influencers_{timestamp}.csv"
        
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
    
    def run(self, keywords: List[str] = None, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            keywords: 搜索关键词列表，默认为常见网红类型
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("抖音网红数据爬虫开始运行")
        print("=" * 50)
        
        if keywords is None:
            keywords = ['美妆博主', '穿搭博主', '美食博主', '旅行博主', '健身博主']
        
        all_influencers = []
        
        for keyword in keywords:
            print(f"\n搜索关键词: {keyword}")
            
            # 搜索网红
            influencers = self.search_influencers(keyword, count=10)
            
            if not influencers:
                print(f"未找到关键词 '{keyword}' 的网红")
                continue
            
            # 获取每个网红的详细数据
            for influencer in influencers[:5]:  # 每个关键词只处理前5个
                try:
                    sec_uid = influencer.get('sec_uid')
                    if not sec_uid:
                        continue
                    
                    # 获取详细资料
                    detail = self.get_user_detail(sec_uid)
                    if not detail:
                        continue
                    
                    # 获取视频数据
                    videos = self.get_user_videos(sec_uid, count=5)
                    
                    # 分析指标
                    metrics = self.analyze_influencer_metrics(detail, videos or [])
                    
                    # 合并数据
                    complete_data = {
                        **influencer,
                        **detail,
                        'videos_count': len(videos) if videos else 0,
                        **metrics,
                    }
                    
                    all_influencers.append(complete_data)
                    
                    print(f"  已处理: {influencer.get('nickname')} (粉丝: {detail.get('follower_count', 0):,})")
                    
                    # 避免请求过快
                    time.sleep(random.uniform(3, 5))
                    
                except Exception as e:
                    print(f"处理网红 {influencer.get('nickname')} 时出错: {str(e)}")
                    continue
        
        # 保存到文件
        if save_to_file and all_influencers:
            self.save_to_csv(all_influencers)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_influencers)} 个网红数据")
        print("=" * 50)
        
        return all_influencers


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = DouyinInfluencerCrawler()
        
        # 运行爬虫
        influencers = crawler.run(
            keywords=['美妆博主', '穿搭博主'],  # 可以修改搜索关键词
            save_to_file=True
        )
        
        if influencers:
            print(f"\n数据统计:")
            print(f"总网红数: {len(influencers)}")
            
            # 按粉丝数排序
            sorted_influencers = sorted(influencers, key=lambda x: x.get('follower_count', 0), reverse=True)
            
            print(f"\n粉丝最多的前5名网红:")
            for idx, inf in enumerate(sorted_influencers[:5], 1):
                print(f"  {idx}. {inf.get('nickname')} - 粉丝: {inf.get('follower_count', 0):,}")
                print(f"     互动率: {inf.get('engagement_rate', 0):.2f}%")
                print(f"     内容质量评分: {inf.get('content_quality_score', 0):.2f}")
        else:
            print("未能获取网红数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()