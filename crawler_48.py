"""
爬虫 48: Stack Overflow热门问题爬虫
功能: 爬取Stack Overflow热门问题、回答和用户信息
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


class StackOverflowCrawler:
    """Stack Overflow爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # Stack Overflow相关URL
        self.base_url = "https://stackoverflow.com"
        self.questions_url = f"{self.base_url}/questions"
        self.tags_url = f"{self.base_url}/tags"
        self.users_url = f"{self.base_url}/users"
        self.api_url = "https://api.stackexchange.com/2.3"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://stackoverflow.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # API参数
        self.api_key = None  # Stack Exchange API key (可选)
        self.site = 'stackoverflow'
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.question_cache = {}
        self.answer_cache = {}
        self.user_cache = {}
        
    def get_hot_questions(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        获取热门问题
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 热门问题列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取Stack Overflow热门问题 (第{page}页)")
            
            # 使用Stack Exchange API
            api_params = {
                'order': 'desc',
                'sort': 'hot',
                'site': self.site,
                'pagesize': min(page_size, 100),
                'page': page,
                'filter': '!nKzQUR693x',  # 基础过滤器，包含问题基本信息
            }
            
            if self.api_key:
                api_params['key'] = self.api_key
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                f"{self.api_url}/questions",
                params=api_params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取热门问题失败，状态码: {response.status_code}")
                return self._retry_get_hot_questions(page, page_size)
            
            data = response.json()
            
            if data.get('error_id'):
                print(f"API错误: {data.get('error_name', '未知错误')} - {data.get('error_message', '')}")
                return None
            
            questions_data = data.get('items', [])
            questions = []
            
            for idx, question in enumerate(questions_data):
                try:
                    question_info = self._parse_question_api(question, idx + 1)
                    if question_info:
                        questions.append(question_info)
                except Exception as e:
                    print(f"解析问题数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(questions)} 个热门问题")
            return questions
            
        except requests.exceptions.Timeout:
            print("获取热门问题请求超时")
            return self._retry_get_hot_questions(page, page_size)
        except requests.exceptions.ConnectionError:
            print("获取热门问题连接错误")
            return self._retry_get_hot_questions(page, page_size)
        except json.JSONDecodeError:
            print("热门问题响应JSON解析错误")
            return None
        except Exception as e:
            print(f"获取热门问题时发生未知错误: {str(e)}")
            return None
    
    def _parse_question_api(self, question_data: Dict, rank: int) -> Optional[Dict]:
        """
        解析API返回的问题数据
        
        Args:
            question_data: API返回的问题数据
            rank: 排名
            
        Returns:
            Dict: 问题信息
        """
        try:
            question_id = question_data.get('question_id', '')
            title = question_data.get('title', '')
            
            # 清理标题
            title = re.sub(r'<[^>]+>', '', title)
            title = title.strip()
            
            # 提取标签
            tags = question_data.get('tags', [])
            
            # 问题统计数据
            view_count = question_data.get('view_count', 0)
            answer_count = question_data.get('answer_count', 0)
            score = question_data.get('score', 0)  # 投票数
            is_answered = question_data.get('is_answered', False)
            
            # 提问者信息
            owner_data = question_data.get('owner', {})
            owner_info = {
                'user_id': owner_data.get('user_id', ''),
                'display_name': owner_data.get('display_name', ''),
                'reputation': owner_data.get('reputation', 0),
                'profile_image': owner_data.get('profile_image', ''),
            }
            
            # 创建时间
            creation_date = question_data.get('creation_date', 0)
            if creation_date:
                created_time = datetime.fromtimestamp(creation_date).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_time = ''
            
            # 最后活动时间
            last_activity_date = question_data.get('last_activity_date', 0)
            if last_activity_date:
                last_activity_time = datetime.fromtimestamp(last_activity_date).strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_activity_time = ''
            
            question_info = {
                'question_id': question_id,
                'title': title,
                'tags': tags,
                'view_count': view_count,
                'answer_count': answer_count,
                'score': score,
                'is_answered': is_answered,
                'owner': owner_info,
                'created_time': created_time,
                'last_activity_time': last_activity_time,
                'rank': rank,
                'url': f"https://stackoverflow.com/questions/{question_id}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return question_info
            
        except Exception as e:
            print(f"解析问题API数据时出错: {str(e)}")
            return None
    
    def _retry_get_hot_questions(self, page: int, page_size: int) -> Optional[List[Dict]]:
        """
        重试获取热门问题
        
        Returns:
            List[Dict]: 热门问题列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_hot_questions(page, page_size)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_question_detail(self, question_id: str) -> Optional[Dict]:
        """
        获取问题详细信息
        
        Args:
            question_id: 问题ID
            
        Returns:
            Dict: 问题详细信息
        """
        # 检查缓存
        if question_id in self.question_cache:
            print(f"从缓存获取问题 {question_id} 的详细信息")
            return self.question_cache[question_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取问题详细信息: {question_id}")
            
            # 使用Stack Exchange API获取问题详情
            api_params = {
                'order': 'desc',
                'sort': 'activity',
                'site': self.site,
                'filter': '!6VvPDzOa1rHey',  # 包含问题体和其他详细信息
            }
            
            if self.api_key:
                api_params['key'] = self.api_key
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                f"{self.api_url}/questions/{question_id}",
                params=api_params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取问题详情失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error_id'):
                print(f"API错误: {data.get('error_name', '未知错误')} - {data.get('error_message', '')}")
                return None
            
            questions_data = data.get('items', [])
            if not questions_data:
                print(f"未找到问题 {question_id}")
                return None
            
            question_data = questions_data[0]
            
            # 解析详细信息
            detail = {
                'question_id': question_id,
                'title': question_data.get('title', ''),
                'body': self._clean_html(question_data.get('body', '')),
                'body_preview': self._clean_html(question_data.get('body', ''))[:500],
                'tags': question_data.get('tags', []),
                'view_count': question_data.get('view_count', 0),
                'answer_count': question_data.get('answer_count', 0),
                'score': question_data.get('score', 0),
                'is_answered': question_data.get('is_answered', False),
                'accepted_answer_id': question_data.get('accepted_answer_id'),
                'bounty_amount': question_data.get('bounty_amount', 0),  # 悬赏金额
                'bounty_closes_date': question_data.get('bounty_closes_date', 0),
                'closed_date': question_data.get('closed_date', 0),
                'closed_reason': question_data.get('closed_reason', ''),
                'comment_count': question_data.get('comment_count', 0),
                'favorite_count': question_data.get('favorite_count', 0),
                'owner': question_data.get('owner', {}),
                'created_time': self._timestamp_to_str(question_data.get('creation_date')),
                'last_activity_time': self._timestamp_to_str(question_data.get('last_activity_date')),
                'last_edit_time': self._timestamp_to_str(question_data.get('last_edit_date')),
                'url': f"https://stackoverflow.com/questions/{question_id}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.question_cache[question_id] = detail
            
            print(f"[{datetime.now()}] 成功获取问题详细信息")
            return detail
            
        except Exception as e:
            print(f"获取问题详细信息时出错: {str(e)}")
            return None
    
    def _clean_html(self, html: str) -> str:
        """
        清理HTML标签
        
        Args:
            html: 原始HTML
            
        Returns:
            str: 清理后的文本
        """
        if not html:
            return ""
        
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', html)
        # 解码HTML实体
        clean_text = re.sub(r'&nbsp;', ' ', clean_text)
        clean_text = re.sub(r'&lt;', '<', clean_text)
        clean_text = re.sub(r'&gt;', '>', clean_text)
        clean_text = re.sub(r'&amp;', '&', clean_text)
        clean_text = re.sub(r'&quot;', '"', clean_text)
        clean_text = re.sub(r'&#39;', "'", clean_text)
        # 移除多余空格
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def _timestamp_to_str(self, timestamp: int) -> str:
        """
        将时间戳转换为字符串
        
        Args:
            timestamp: Unix时间戳
            
        Returns:
            str: 格式化时间字符串
        """
        if not timestamp:
            return ''
        
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ''
    
    def get_question_answers(self, question_id: str, limit: int = 10) -> Optional[List[Dict]]:
        """
        获取问题回答
        
        Args:
            question_id: 问题ID
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 回答列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取问题回答: {question_id}")
            
            # 使用Stack Exchange API获取回答
            api_params = {
                'order': 'desc',
                'sort': 'votes',  # 按投票数排序
                'site': self.site,
                'pagesize': min(limit, 100),
                'filter': '!6VvPDzOa1rHey',  # 包含回答体和其他详细信息
            }
            
            if self.api_key:
                api_params['key'] = self.api_key
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                f"{self.api_url}/questions/{question_id}/answers",
                params=api_params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取回答失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error_id'):
                print(f"API错误: {data.get('error_name', '未知错误')} - {data.get('error_message', '')}")
                return None
            
            answers_data = data.get('items', [])
            answers = []
            
            for answer in answers_data:
                try:
                    answer_info = self._parse_answer_api(answer)
                    if answer_info:
                        answers.append(answer_info)
                except Exception as e:
                    print(f"解析回答数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(answers)} 个回答")
            return answers
            
        except Exception as e:
            print(f"获取问题回答时出错: {str(e)}")
            return None
    
    def _parse_answer_api(self, answer_data: Dict) -> Optional[Dict]:
        """
        解析API返回的回答数据
        
        Args:
            answer_data: API返回的回答数据
            
        Returns:
            Dict: 回答信息
        """
        try:
            answer_id = answer_data.get('answer_id', '')
            question_id = answer_data.get('question_id', '')
            
            # 回答内容
            body = self._clean_html(answer_data.get('body', ''))
            
            # 回答统计数据
            score = answer_data.get('score', 0)  # 投票数
            is_accepted = answer_data.get('is_accepted', False)
            comment_count = answer_data.get('comment_count', 0)
            
            # 回答者信息
            owner_data = answer_data.get('owner', {})
            owner_info = {
                'user_id': owner_data.get('user_id', ''),
                'display_name': owner_data.get('display_name', ''),
                'reputation': owner_data.get('reputation', 0),
                'profile_image': owner_data.get('profile_image', ''),
                'badge_counts': owner_data.get('badge_counts', {}),
            }
            
            # 创建时间
            creation_date = answer_data.get('creation_date', 0)
            created_time = self._timestamp_to_str(creation_date)
            
            # 最后编辑时间
            last_edit_date = answer_data.get('last_edit_date', 0)
            last_edit_time = self._timestamp_to_str(last_edit_date)
            
            answer_info = {
                'answer_id': answer_id,
                'question_id': question_id,
                'body_preview': body[:300] + '...' if len(body) > 300 else body,
                'body_length': len(body),
                'score': score,
                'is_accepted': is_accepted,
                'comment_count': comment_count,
                'owner': owner_info,
                'created_time': created_time,
                'last_edit_time': last_edit_time,
                'url': f"https://stackoverflow.com/a/{answer_id}",
            }
            
            return answer_info
            
        except Exception as e:
            print(f"解析回答API数据时出错: {str(e)}")
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        # 检查缓存
        if user_id in self.user_cache:
            print(f"从缓存获取用户 {user_id} 的信息")
            return self.user_cache[user_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取用户信息: {user_id}")
            
            # 使用Stack Exchange API获取用户信息
            api_params = {
                'order': 'desc',
                'sort': 'reputation',
                'site': self.site,
                'filter': '!9Z(-x.0nI',  # 包含用户基本信息
            }
            
            if self.api_key:
                api_params['key'] = self.api_key
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                f"{self.api_url}/users/{user_id}",
                params=api_params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取用户信息失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error_id'):
                print(f"API错误: {data.get('error_name', '未知错误')} - {data.get('error_message', '')}")
                return None
            
            users_data = data.get('items', [])
            if not users_data:
                print(f"未找到用户 {user_id}")
                return None
            
            user_data = users_data[0]
            
            user_info = {
                'user_id': user_id,
                'display_name': user_data.get('display_name', ''),
                'reputation': user_data.get('reputation', 0),
                'accept_rate': user_data.get('accept_rate', 0),  # 采纳率
                'profile_image': user_data.get('profile_image', ''),
                'profile_link': user_data.get('link', ''),
                'is_employee': user_data.get('is_employee', False),
                'user_type': user_data.get('user_type', ''),
                'website_url': user_data.get('website_url', ''),
                'location': user_data.get('location', ''),
                'about_me': self._clean_html(user_data.get('about_me', '')),
                'creation_date': self._timestamp_to_str(user_data.get('creation_date')),
                'last_access_date': self._timestamp_to_str(user_data.get('last_access_date')),
                'badge_counts': user_data.get('badge_counts', {}),
                'view_count': user_data.get('view_count', 0),
                'answer_count': user_data.get('answer_count', 0),
                'question_count': user_data.get('question_count', 0),
                'url': f"https://stackoverflow.com/users/{user_id}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.user_cache[user_id] = user_info
            
            print(f"[{datetime.now()}] 成功获取用户信息")
            return user_info
            
        except Exception as e:
            print(f"获取用户信息时出错: {str(e)}")
            return None
    
    def analyze_question_metrics(self, question_detail: Dict, answers: List[Dict]) -> Dict:
        """
        分析问题指标
        
        Args:
            question_detail: 问题详细信息
            answers: 回答列表
            
        Returns:
            Dict: 分析指标
        """
        try:
            metrics = {
                'view_count': question_detail.get('view_count', 0),
                'answer_count': question_detail.get('answer_count', 0),
                'score': question_detail.get('score', 0),
                'is_answered': question_detail.get('is_answered', False),
                'tag_count': len(question_detail.get('tags', [])),
            }
            
            # 分析回答数据
            if answers:
                total_answers = len(answers)
                total_score = sum(a.get('score', 0) for a in answers)
                accepted_answers = sum(1 for a in answers if a.get('is_accepted', False))
                total_comments = sum(a.get('comment_count', 0) for a in answers)
                
                avg_score = total_score / total_answers if total_answers > 0 else 0
                accepted_rate = (accepted_answers / total_answers) * 100 if total_answers > 0 else 0
                avg_comments = total_comments / total_answers if total_answers > 0 else 0
                
                # 高质量回答比例（分数>10）
                high_quality_answers = sum(1 for a in answers if a.get('score', 0) > 10)
                high_quality_rate = (high_quality_answers / total_answers) * 100 if total_answers > 0 else 0
                
                # 专业回答者比例（声望>1000）
                professional_authors = sum(1 for a in answers if a.get('owner', {}).get('reputation', 0) > 1000)
                professional_rate = (professional_authors / total_answers) * 100 if total_answers > 0 else 0
                
                metrics.update({
                    'total_answers_analyzed': total_answers,
                    'total_score': total_score,
                    'accepted_answer_count': accepted_answers,
                    'accepted_rate': round(accepted_rate, 2),
                    'avg_answer_score': round(avg_score, 2),
                    'avg_comments_per_answer': round(avg_comments, 2),
                    'high_quality_answer_rate': round(high_quality_rate, 2),
                    'professional_author_rate': round(professional_rate, 2),
                })
            
            # 计算质量评分
            metrics['quality_score'] = self._calculate_quality_score(question_detail, answers)
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析问题指标时出错: {str(e)}")
            return {}
    
    def _calculate_quality_score(self, question_detail: Dict, answers: List[Dict]) -> float:
        """
        计算质量评分
        
        Args:
            question_detail: 问题详细信息
            answers: 回答列表
            
        Returns:
            float: 质量评分
        """
        try:
            score = 0
            
            # 问题投票数权重
            question_score = question_detail.get('score', 0)
            score += min(question_score / 10 * 20, 20)
            
            # 回答数权重
            answer_count = question_detail.get('answer_count', 0)
            score += min(answer_count / 10 * 20, 20)
            
            # 采纳回答权重
            is_answered = question_detail.get('is_answered', False)
            if is_answered:
                score += 20
            
            # 回答质量权重
            if answers:
                avg_answer_score = sum(a.get('score', 0) for a in answers) / len(answers)
                score += min(avg_answer_score / 5 * 20, 20)
            
            # 活跃度权重（最近活动）
            last_activity = question_detail.get('last_activity_time', '')
            if last_activity:
                try:
                    last_activity_dt = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                    days_since = (datetime.now() - last_activity_dt).days
                    if days_since <= 7:  # 一周内有活动
                        score += 20
                    elif days_since <= 30:  # 一月内有活动
                        score += 10
                except:
                    pass
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def get_popular_tags(self, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取热门标签
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 热门标签列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取热门标签")
            
            api_params = {
                'order': 'desc',
                'sort': 'popular',
                'site': self.site,
                'pagesize': min(limit, 100),
            }
            
            if self.api_key:
                api_params['key'] = self.api_key
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                f"{self.api_url}/tags",
                params=api_params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取标签失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get('error_id'):
                print(f"API错误: {data.get('error_name', '未知错误')} - {data.get('error_message', '')}")
                return None
            
            tags_data = data.get('items', [])
            tags = []
            
            for tag in tags_data:
                try:
                    tag_info = {
                        'name': tag.get('name', ''),
                        'count': tag.get('count', 0),
                        'has_synonyms': tag.get('has_synonyms', False),
                        'is_moderator_only': tag.get('is_moderator_only', False),
                        'is_required': tag.get('is_required', False),
                    }
                    tags.append(tag_info)
                except Exception as e:
                    print(f"解析标签数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(tags)} 个热门标签")
            return tags
            
        except Exception as e:
            print(f"获取热门标签时出错: {str(e)}")
            return None
    
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
            filename = f"stackoverflow_questions_{timestamp}.csv"
        
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
    
    def run(self, get_hot_questions: bool = True, get_popular_tags: bool = True, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            get_hot_questions: 是否获取热门问题
            get_popular_tags: 是否获取热门标签
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("Stack Overflow爬虫开始运行")
        print("=" * 50)
        
        all_questions = []
        
        # 获取热门问题
        if get_hot_questions:
            print("\n获取Stack Overflow热门问题...")
            hot_questions = self.get_hot_questions(page=1, page_size=15)
            
            if hot_questions:
                for question in hot_questions[:10]:  # 只处理前10个
                    try:
                        question_id = question.get('question_id')
                        if not question_id:
                            continue
                        
                        # 获取详细信息
                        detail = self.get_question_detail(question_id)
                        if not detail:
                            continue
                        
                        # 获取回答
                        answers = self.get_question_answers(question_id, limit=10)
                        
                        # 获取高质量回答的作者信息
                        if answers:
                            for answer in answers[:3]:  # 只处理前3个高质量回答
                                user_id = answer.get('owner', {}).get('user_id')
                                if user_id:
                                    user_info = self.get_user_info(user_id)
                                    if user_info:
                                        answer['owner_detail'] = user_info
                        
                        # 分析指标
                        metrics = self.analyze_question_metrics(detail, answers or [])
                        
                        # 合并数据
                        complete_data = {
                            **question,
                            **detail,
                            'answers_count': len(answers) if answers else 0,
                            'sample_answers': answers[:3] if answers else [],  # 保存3条样本回答
                            **metrics,
                            'source': 'hot',
                        }
                        
                        all_questions.append(complete_data)
                        
                        print(f"  已处理: {question.get('title')} (浏览: {question.get('view_count', 0):,})")
                        
                        # 避免请求过快
                        time.sleep(random.uniform(2, 3))
                        
                    except Exception as e:
                        print(f"处理问题 {question.get('title')} 时出错: {str(e)}")
                        continue
        
        # 获取热门标签
        if get_popular_tags:
            print("\n获取热门标签...")
            popular_tags = self.get_popular_tags(limit=20)
            if popular_tags:
                print(f"热门标签TOP5:")
                for idx, tag in enumerate(popular_tags[:5], 1):
                    print(f"  {idx}. {tag['name']} (使用次数: {tag['count']:,})")
        
        # 保存到文件
        if save_to_file and all_questions:
            self.save_to_csv(all_questions)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_questions)} 个问题数据")
        print("=" * 50)
        
        return all_questions


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = StackOverflowCrawler()
        
        # 运行爬虫
        questions = crawler.run(
            get_hot_questions=True,
            get_popular_tags=True,
            save_to_file=True
        )
        
        if questions:
            print(f"\n数据统计:")
            print(f"总问题数: {len(questions)}")
            
            # 按浏览量排序
            sorted_questions = sorted(questions, key=lambda x: x.get('view_count', 0), reverse=True)
            
            print(f"\n浏览量最高的前5个问题:")
            for idx, question in enumerate(sorted_questions[:5], 1):
                title = question.get('title', '')[:60]
                if len(question.get('title', '')) > 60:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     浏览: {question.get('view_count', 0):,} | "
                      f"回答: {question.get('answer_count', 0)} | "
                      f"评分: {question.get('score', 0)}")
                print(f"     标签: {', '.join(question.get('tags', [])[:3])}")
                print(f"     质量评分: {question.get('quality_score', 0):.2f} | "
                      f"采纳率: {question.get('accepted_rate', 0):.2f}%")
        else:
            print("未能获取问题数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()