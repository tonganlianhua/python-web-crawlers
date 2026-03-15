"""
爬虫 44: 斗鱼直播数据爬虫
功能: 爬取斗鱼直播平台的主播信息、直播间数据和弹幕统计
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import hashlib
import websocket
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime
import random
import re
import csv


class DouyuLiveCrawler:
    """斗鱼直播爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # 斗鱼API相关URL
        self.base_api = "https://www.douyu.com"
        self.hot_live_url = f"{self.base_api}/japi/weblist/apinc/allpage/1/20"
        self.room_info_url = f"{self.base_api}/japi/weblist/apinc/room/{{}}"
        self.anchor_info_url = f"{self.base_api}/japi/weblist/apinc/anchor/{{}}"
        self.category_url = f"{self.base_api}/japi/weblist/apinc/game/1"
        self.search_url = f"{self.base_api}/japi/search/api/searchShow"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.douyu.com/',
            'Origin': 'https://www.douyu.com',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 弹幕收集相关
        self.danmu_data = {}
        self.danmu_lock = threading.Lock()
        self.ws_connections = {}
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.room_cache = {}
        self.anchor_cache = {}
        
    def get_hot_lives(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        获取热门直播间
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 热门直播间列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取斗鱼热门直播 (第{page}页)")
            
            # 斗鱼的热门接口参数
            params = {
                'type': 'json',
                'page': page,
                'limit': min(page_size, 100),
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.hot_live_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取热门直播失败，状态码: {response.status_code}")
                return self._retry_get_hot_lives(page, page_size)
            
            data = response.json()
            
            if data.get('error') != 0:
                print(f"获取热门直播错误: {data.get('msg', '未知错误')}")
                return None
            
            room_list = data.get('data', {}).get('rl', [])
            lives = []
            
            for room in room_list:
                try:
                    live_info = {
                        'room_id': room.get('rid', ''),
                        'room_name': room.get('rn', ''),
                        'room_title': room.get('roomName', ''),
                        'anchor_name': room.get('nn', ''),
                        'anchor_avatar': room.get('rs1', ''),  # 主播头像
                        'online_count': room.get('ol', 0),  # 在线人数
                        'category': room.get('c2name', ''),  # 分类名称
                        'category_id': room.get('cid2', ''),  # 分类ID
                        'is_official': room.get('isOfficial', 0) == 1,  # 是否官方
                        'is_hot': room.get('isHot', 0) == 1,  # 是否热门
                        'start_time': room.get('start_time', 0),
                        'room_url': f"https://www.douyu.com/{room.get('rid', '')}",
                        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    lives.append(live_info)
                    
                except Exception as e:
                    print(f"处理直播间数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(lives)} 个热门直播间")
            return lives
            
        except requests.exceptions.Timeout:
            print("获取热门直播请求超时")
            return self._retry_get_hot_lives(page, page_size)
        except requests.exceptions.ConnectionError:
            print("获取热门直播连接错误")
            return self._retry_get_hot_lives(page, page_size)
        except json.JSONDecodeError:
            print("热门直播响应JSON解析错误")
            return None
        except Exception as e:
            print(f"获取热门直播时发生未知错误: {str(e)}")
            return None
    
    def _retry_get_hot_lives(self, page: int, page_size: int) -> Optional[List[Dict]]:
        """
        重试获取热门直播
        
        Returns:
            List[Dict]: 热门直播间列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_hot_lives(page, page_size)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_categories(self) -> Optional[List[Dict]]:
        """
        获取直播分类
        
        Returns:
            List[Dict]: 分类列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取斗鱼直播分类")
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.category_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取分类失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error') != 0:
                print(f"获取分类错误: {data.get('msg', '未知错误')}")
                return None
            
            category_list = data.get('data', [])
            categories = []
            
            for category in category_list:
                try:
                    cat_info = {
                        'cid': category.get('cid', ''),
                        'cname': category.get('cname', ''),
                        'ename': category.get('ename', ''),
                        'room_count': category.get('room_count', 0),  # 当前房间数
                        'hot_value': category.get('hot_value', 0),  # 热度值
                        'icon_url': category.get('icon_url', ''),
                        'url': f"https://www.douyu.com/g_{category.get('ename', '')}",
                    }
                    categories.append(cat_info)
                    
                except Exception as e:
                    print(f"处理分类数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(categories)} 个分类")
            return categories
            
        except Exception as e:
            print(f"获取分类时出错: {str(e)}")
            return None
    
    def get_room_detail(self, room_id: str) -> Optional[Dict]:
        """
        获取直播间详细信息
        
        Args:
            room_id: 房间ID
            
        Returns:
            Dict: 直播间详细信息
        """
        # 检查缓存
        if room_id in self.room_cache:
            print(f"从缓存获取房间 {room_id} 的详细信息")
            return self.room_cache[room_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取直播间详细信息: {room_id}")
            
            url = self.room_info_url.format(room_id)
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取房间详情失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error') != 0:
                print(f"获取房间详情错误: {data.get('msg', '未知错误')}")
                return None
            
            room_data = data.get('data', {})
            
            # 解析详细信息
            detail = {
                'room_id': room_id,
                'room_name': room_data.get('room_name', ''),
                'room_title': room_data.get('room_title', ''),
                'room_status': room_data.get('room_status', 0),  # 房间状态
                'show_status': room_data.get('show_status', 0),  # 显示状态
                'online_count': room_data.get('online', 0),  # 在线人数
                'fans_count': room_data.get('fans_num', 0),  # 粉丝数
                'start_time': room_data.get('start_time', 0),  # 开播时间
                'is_official': room_data.get('is_official', 0) == 1,
                'is_hot': room_data.get('is_hot', 0) == 1,
                'is_vertical': room_data.get('is_vertical', 0) == 1,  # 是否竖屏
                'category': {
                    'cid': room_data.get('cid', ''),
                    'cname': room_data.get('cname', ''),
                },
                'anchor': {
                    'uid': room_data.get('owner_uid', ''),
                    'nickname': room_data.get('nickname', ''),
                    'avatar': room_data.get('avatar', ''),
                    'level': room_data.get('anchor_level', {}),
                },
                'stream': {
                    'hls_url': room_data.get('hls_url', ''),
                    'rtmp_url': room_data.get('rtmp_url', ''),
                    'flv_url': room_data.get('flv_url', ''),
                },
                'gift_rank': room_data.get('gift_rank', []),  # 礼物榜
                'room_url': f"https://www.douyu.com/{room_id}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.room_cache[room_id] = detail
            
            print(f"[{datetime.now()}] 成功获取直播间详细信息")
            return detail
            
        except Exception as e:
            print(f"获取直播间详细信息时出错: {str(e)}")
            return None
    
    def get_anchor_detail(self, anchor_id: str) -> Optional[Dict]:
        """
        获取主播详细信息
        
        Args:
            anchor_id: 主播ID
            
        Returns:
            Dict: 主播详细信息
        """
        # 检查缓存
        if anchor_id in self.anchor_cache:
            print(f"从缓存获取主播 {anchor_id} 的详细信息")
            return self.anchor_cache[anchor_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取主播详细信息: {anchor_id}")
            
            url = self.anchor_info_url.format(anchor_id)
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取主播详情失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error') != 0:
                print(f"获取主播详情错误: {data.get('msg', '未知错误')}")
                return None
            
            anchor_data = data.get('data', {})
            
            # 解析详细信息
            detail = {
                'anchor_id': anchor_id,
                'nickname': anchor_data.get('nickname', ''),
                'avatar': anchor_data.get('avatar', ''),
                'gender': anchor_data.get('gender', ''),
                'birthday': anchor_data.get('birthday', ''),
                'location': anchor_data.get('location', ''),
                'signature': anchor_data.get('signature', ''),
                'level_info': anchor_data.get('level_info', {}),
                'fans_count': anchor_data.get('fans_num', 0),
                'follow_count': anchor_data.get('follow_num', 0),
                'room_id': anchor_data.get('room_id', ''),
                'room_name': anchor_data.get('room_name', ''),
                'room_title': anchor_data.get('room_title', ''),
                'is_living': anchor_data.get('is_living', 0) == 1,
                'is_official': anchor_data.get('is_official', 0) == 1,
                'is_verified': anchor_data.get('is_verified', 0) == 1,
                'total_live_time': anchor_data.get('total_live_time', 0),  # 总直播时长(秒)
                'total_live_days': anchor_data.get('total_live_days', 0),  # 总直播天数
                'start_time': anchor_data.get('start_time', 0),  # 开始直播时间
                'url': f"https://www.douyu.com/{anchor_data.get('room_id', '')}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.anchor_cache[anchor_id] = detail
            
            print(f"[{datetime.now()}] 成功获取主播详细信息")
            return detail
            
        except Exception as e:
            print(f"获取主播详细信息时出错: {str(e)}")
            return None
    
    def collect_danmu(self, room_id: str, duration: int = 30) -> Optional[Dict]:
        """
        收集直播间弹幕
        
        Args:
            room_id: 房间ID
            duration: 收集时长(秒)
            
        Returns:
            Dict: 弹幕统计数据
        """
        try:
            print(f"[{datetime.now()}] 开始收集房间 {room_id} 的弹幕，时长 {duration} 秒")
            
            # 初始化弹幕数据
            self.danmu_data[room_id] = {
                'total_count': 0,
                'users': set(),
                'messages': [],
                'start_time': datetime.now(),
                'end_time': None,
            }
            
            # 这里简化实现，实际需要连接斗鱼WebSocket
            # 由于WebSocket连接较复杂，这里使用模拟数据
            print("注意: 弹幕收集功能需要WebSocket连接，这里使用模拟数据")
            
            # 模拟收集弹幕
            danmu_stats = self._simulate_danmu_collection(room_id, duration)
            
            print(f"[{datetime.now()}] 弹幕收集完成")
            return danmu_stats
            
        except Exception as e:
            print(f"收集弹幕时出错: {str(e)}")
            return None
    
    def _simulate_danmu_collection(self, room_id: str, duration: int) -> Dict:
        """
        模拟弹幕收集（简化版）
        
        Args:
            room_id: 房间ID
            duration: 收集时长
            
        Returns:
            Dict: 模拟的弹幕统计数据
        """
        # 模拟弹幕数据
        sample_messages = [
            "666", "主播加油", "厉害了", "哈哈哈", "太强了",
            "这操作可以", "学到了", "感谢主播", "礼物走一波",
            "关注了", "下次还来", "技术不错", "节目效果拉满",
        ]
        
        sample_users = [
            "用户1", "用户2", "用户3", "用户4", "用户5",
            "用户6", "用户7", "用户8", "用户9", "用户10",
        ]
        
        # 模拟收集过程
        total_messages = random.randint(50, 200)
        unique_users = random.sample(sample_users, random.randint(5, 10))
        
        messages = []
        for i in range(min(total_messages, 20)):  # 只记录部分消息
            msg = {
                'user': random.choice(unique_users),
                'content': random.choice(sample_messages),
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'type': 'danmu',
            }
            messages.append(msg)
        
        # 计算统计数据
        stats = {
            'room_id': room_id,
            'total_messages': total_messages,
            'unique_users': len(unique_users),
            'avg_messages_per_minute': round(total_messages / (duration / 60), 2),
            'messages_per_user': round(total_messages / len(unique_users), 2) if unique_users else 0,
            'sample_messages': messages[:10],  # 只保留10条样本
            'collection_duration': duration,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': (datetime.now() + timedelta(seconds=duration)).strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return stats
    
    def analyze_live_metrics(self, room_detail: Dict, danmu_stats: Optional[Dict] = None) -> Dict:
        """
        分析直播间指标
        
        Args:
            room_detail: 直播间详细信息
            danmu_stats: 弹幕统计数据
            
        Returns:
            Dict: 分析指标
        """
        try:
            online_count = room_detail.get('online_count', 0)
            fans_count = room_detail.get('fans_count', 0)
            
            # 基础指标
            metrics = {
                'online_count': online_count,
                'fans_count': fans_count,
                'fans_ratio': round((fans_count / online_count) * 100, 2) if online_count > 0 else 0,
                'is_official': room_detail.get('is_official', False),
                'is_hot': room_detail.get('is_hot', False),
                'is_living': room_detail.get('room_status', 0) == 1,
            }
            
            # 如果有弹幕数据，添加互动指标
            if danmu_stats:
                metrics.update({
                    'danmu_total': danmu_stats.get('total_messages', 0),
                    'danmu_unique_users': danmu_stats.get('unique_users', 0),
                    'danmu_per_minute': danmu_stats.get('avg_messages_per_minute', 0),
                    'interaction_rate': self._calculate_interaction_rate(online_count, danmu_stats),
                })
            
            # 计算热度评分
            metrics['hot_score'] = self._calculate_hot_score(room_detail, danmu_stats)
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析直播间指标时出错: {str(e)}")
            return {}
    
    def _calculate_interaction_rate(self, online_count: int, danmu_stats: Dict) -> float:
        """
        计算互动率
        
        Args:
            online_count: 在线人数
            danmu_stats: 弹幕统计数据
            
        Returns:
            float: 互动率
        """
        try:
            total_messages = danmu_stats.get('total_messages', 0)
            unique_users = danmu_stats.get('unique_users', 0)
            duration = danmu_stats.get('collection_duration', 30)
            
            if online_count == 0 or duration == 0:
                return 0
            
            # 每分钟平均弹幕数 / 在线人数 * 100
            messages_per_minute = total_messages / (duration / 60)
            interaction_rate = (messages_per_minute / online_count) * 100
            
            return round(interaction_rate, 2)
            
        except:
            return 0
    
    def _calculate_hot_score(self, room_detail: Dict, danmu_stats: Optional[Dict]) -> float:
        """
        计算热度评分
        
        Args:
            room_detail: 直播间详细信息
            danmu_stats: 弹幕统计数据
            
        Returns:
            float: 热度评分
        """
        try:
            score = 0
            
            # 在线人数权重
            online_count = room_detail.get('online_count', 0)
            score += min(online_count / 10000 * 40, 40)
            
            # 粉丝数权重
            fans_count = room_detail.get('fans_count', 0)
            score += min(fans_count / 100000 * 20, 20)
            
            # 弹幕互动权重
            if danmu_stats:
                messages_per_minute = danmu_stats.get('avg_messages_per_minute', 0)
                score += min(messages_per_minute / 50 * 20, 20)
            
            # 官方认证权重
            if room_detail.get('is_official'):
                score += 10
            
            # 热门标签权重
            if room_detail.get('is_hot'):
                score += 10
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
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
            filename = f"douyu_lives_{timestamp}.csv"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 提取所有可能的字段
            all_fields = set()
            for item in data:
                all_fields.update(item.keys())
            
            # 处理嵌套字典
            flat_data = []
            for item in data:
                flat_item = {}
                for key, value in item.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_item[f"{key}_{sub_key}"] = sub_value
                    else:
                        flat_item[key] = value
                flat_data.append(flat_item)
            
            # 重新提取字段
            all_fields = set()
            for item in flat_data:
                all_fields.update(item.keys())
            
            fieldnames = sorted(all_fields)
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_data)
            
            print(f"数据已保存到CSV: {filepath}")
            
        except Exception as e:
            print(f"保存数据到CSV时出错: {str(e)}")
    
    def run(self, collect_danmu: bool = False, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            collect_danmu: 是否收集弹幕
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("斗鱼直播爬虫开始运行")
        print("=" * 50)
        
        all_lives = []
        
        # 获取热门直播
        print("\n获取热门直播间...")
        hot_lives = self.get_hot_lives(page=1, page_size=20)
        
        if hot_lives:
            for live in hot_lives[:10]:  # 只处理前10个
                try:
                    room_id = live.get('room_id')
                    if not room_id:
                        continue
                    
                    # 获取详细信息
                    detail = self.get_room_detail(room_id)
                    if not detail:
                        continue
                    
                    # 获取主播信息
                    anchor_id = detail.get('anchor', {}).get('uid')
                    anchor_info = None
                    if anchor_id:
                        anchor_info = self.get_anchor_detail(anchor_id)
                    
                    # 收集弹幕
                    danmu_stats = None
                    if collect_danmu and detail.get('room_status') == 1:  # 只在直播时收集
                        danmu_stats = self.collect_danmu(room_id, duration=30)
                    
                    # 分析指标
                    metrics = self.analyze_live_metrics(detail, danmu_stats)
                    
                    # 合并数据
                    complete_data = {
                        **live,
                        **detail,
                        'anchor_detail': anchor_info,
                        'danmu_stats': danmu_stats,
                        **metrics,
                    }
                    
                    all_lives.append(complete_data)
                    
                    print(f"  已处理: {live.get('room_name')} (在线: {live.get('online_count', 0):,})")
                    
                    # 避免请求过快
                    time.sleep(random.uniform(2, 3))
                    
                except Exception as e:
                    print(f"处理直播间 {live.get('room_name')} 时出错: {str(e)}")
                    continue
        
        # 获取分类信息
        print("\n获取直播分类...")
        categories = self.get_categories()
        
        # 保存到文件
        if save_to_file and all_lives:
            self.save_to_csv(all_lives)
            
        if categories:
            print(f"\n热门分类:")
            for cat in categories[:5]:
                print(f"  {cat.get('cname')}: {cat.get('room_count')} 个房间")
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_lives)} 个直播间数据")
        print("=" * 50)
        
        return all_lives


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = DouyuLiveCrawler()
        
        # 运行爬虫
        lives = crawler.run(
            collect_danmu=False,  # 弹幕收集较慢，设为False加快速度
            save_to_file=True
        )
        
        if lives:
            print(f"\n数据统计:")
            print(f"总直播间数: {len(lives)}")
            
            # 按在线人数排序
            sorted_lives = sorted(lives, key=lambda x: x.get('online_count', 0), reverse=True)
            
            print(f"\n在线人数最高的前5个直播间:")
            for idx, live in enumerate(sorted_lives[:5], 1):
                room_name = live.get('room_name', '')[:30]
                if len(live.get('room_name', '')) > 30:
                    room_name += "..."
                
                print(f"  {idx}. {room_name}")
                print(f"     在线: {live.get('online_count', 0):,} | "
                      f"主播: {live.get('anchor_name', '')}")
                print(f"     分类: {live.get('category', '')} | "
                      f"热度评分: {live.get('hot_score', 0):.2f}")
                
                if live.get('danmu_stats'):
                    print(f"     弹幕: {live.get('danmu_stats', {}).get('total_messages', 0)} 条 | "
                          f"互动率: {live.get('interaction_rate', 0):.2f}%")
        else:
            print("未能获取直播数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()