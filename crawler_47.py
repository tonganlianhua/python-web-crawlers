"""
爬虫 47: 知乎热门问题爬虫
功能: 爬取知乎热门问题、回答和用户信息
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


class ZhihuCrawler:
    """知乎爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # 知乎相关URL
        self.base_url = "https://www.zhihu.com"
        self.hot_url = f"{self.base_url}/hot"
        self.topic_url = f"{self.base_url}/topic"
        self.question_url = f"{self.base_url}/question"
        self.answer_url = f"{self.base_url}/answer"
        self.api_url = f"{self.base_url}/api/v4"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.zhihu.com/',
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
        self.question_cache = {}
        self.answer_cache = {}
        self.user_cache = {}
        
    def get_hot_questions(self, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取知乎热榜
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 热榜问题列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取知乎热榜")
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.hot_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取热榜失败，状态码: {response.status_code}")
                return self._retry_get_hot_questions(limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            questions = []
            
            # 查找热榜项
            hot_items = soup.select('.HotList-list .HotItem')
            
            for idx, item in enumerate(hot_items[:limit]):
                try:
                    question = self._parse_hot_item(item, idx + 1)
                    if question:
                        questions.append(question)
                except Exception as e:
                    print(f"解析热榜项时出错: {str(e)}")
                    continue
            
            # 如果没有找到，尝试其他选择器
            if not questions:
                hot_items = soup.select('.HotList .HotItem-content')
                for idx, item in enumerate(hot_items[:limit]):
                    try:
                        question = self._parse_hot_item_alt(item, idx + 1)
                        if question:
                            questions.append(question)
                    except Exception as e:
                        print(f"解析热榜项(备选)时出错: {str(e)}")
                        continue
            
            print(f"[{datetime.now()}] 成功获取 {len(questions)} 个热榜问题")
            return questions
            
        except requests.exceptions.Timeout:
            print("获取热榜请求超时")
            return self._retry_get_hot_questions(limit)
        except requests.exceptions.ConnectionError:
            print("获取热榜连接错误")
            return self._retry_get_hot_questions(limit)
        except Exception as e:
            print(f"获取热榜时发生未知错误: {str(e)}")
            return None
    
    def _parse_hot_item(self, item, rank: int) -> Optional[Dict]:
        """
        解析热榜项
        
        Args:
            item: BeautifulSoup元素
            rank: 排名
            
        Returns:
            Dict: 问题信息
        """
        try:
            # 提取问题标题和链接
            title_elem = item.select_one('.HotItem-title')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # 提取链接
            link_elem = item.select_one('a')
            if not link_elem:
                return None
            
            href = link_elem.get('href', '')
            
            # 解析问题ID
            question_id = None
            if '/question/' in href:
                match = re.search(r'/question/(\d+)', href)
                if match:
                    question_id = match.group(1)
            
            # 提取热度值
            hot_elem = item.select_one('.HotItem-metrics')
            hot_text = hot_elem.get_text(strip=True) if hot_elem else ''
            hot_match = re.search(r'(\d+(?:\.\d+)?)', hot_text.replace(',', ''))
            hot_value = float(hot_match.group(1)) if hot_match else 0
            
            # 提取摘要
            excerpt_elem = item.select_one('.HotItem-excerpt')
            excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ''
            
            question_info = {
                'question_id': question_id,
                'title': title,
                'excerpt': excerpt,
                'hot_value': hot_value,
                'rank': rank,
                'url': href if href.startswith('http') else f"https://www.zhihu.com{href}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return question_info
            
        except Exception as e:
            print(f"解析热榜项时出错: {str(e)}")
            return None
    
    def _parse_hot_item_alt(self, item, rank: int) -> Optional[Dict]:
        """
        解析热榜项（备选方案）
        
        Args:
            item: BeautifulSoup元素
            rank: 排名
            
        Returns:
            Dict: 问题信息
        """
        try:
            # 提取标题
            title_elem = item.select_one('h2')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # 提取链接
            link_elem = item.select_one('a')
            if not link_elem:
                return None
            
            href = link_elem.get('href', '')
            
            # 解析问题ID
            question_id = None
            if '/question/' in href:
                match = re.search(r'/question/(\d+)', href)
                if match:
                    question_id = match.group(1)
            
            # 提取热度
            hot_elem = item.select_one('.HotItem-content .HotItem-metrics')
            hot_text = hot_elem.get_text(strip=True) if hot_elem else ''
            hot_match = re.search(r'(\d+(?:\.\d+)?)', hot_text.replace(',', ''))
            hot_value = float(hot_match.group(1)) if hot_match else 0
            
            question_info = {
                'question_id': question_id,
                'title': title,
                'hot_value': hot_value,
                'rank': rank,
                'url': href if href.startswith('http') else f"https://www.zhihu.com{href}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return question_info
            
        except Exception as e:
            print(f"解析热榜项(备选)时出错: {str(e)}")
            return None
    
    def _retry_get_hot_questions(self, limit: int) -> Optional[List[Dict]]:
        """
        重试获取热榜问题
        
        Returns:
            List[Dict]: 热榜问题列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_hot_questions(limit)
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
            
            url = f"https://www.zhihu.com/question/{question_id}"
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取问题详情失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取问题信息
            info = {}
            
            # 标题
            title_elem = soup.select_one('.QuestionHeader .QuestionHeader-title')
            info['title'] = title_elem.get_text(strip=True) if title_elem else ''
            
            # 问题描述
            content_elem = soup.select_one('.QuestionHeader-detail .RichText')
            if content_elem:
                info['content'] = content_elem.get_text(strip=True)
            else:
                content_elem = soup.select_one('.QuestionHeader-detail span')
                info['content'] = content_elem.get_text(strip=True) if content_elem else ''
            
            # 关注数
            follow_elem = soup.select_one('.NumberBoard-item:first-child .NumberBoard-itemValue')
            if follow_elem:
                follow_text = follow_elem.get_text(strip=True)
                follow_match = re.search(r'(\d+(?:\.\d+)?)', follow_text.replace(',', ''))
                info['follow_count'] = int(float(follow_match.group(1))) if follow_match else 0
            
            # 浏览数
            view_elem = soup.select_one('.NumberBoard-item:last-child .NumberBoard-itemValue')
            if view_elem:
                view_text = view_elem.get_text(strip=True)
                view_match = re.search(r'(\d+(?:\.\d+)?)', view_text.replace(',', ''))
                info['view_count'] = int(float(view_match.group(1))) if view_match else 0
            
            # 回答数
            answer_elem = soup.select_one('.List-headerText span')
            if answer_elem:
                answer_text = answer_elem.get_text(strip=True)
                answer_match = re.search(r'(\d+(?:\.\d+)?)', answer_text.replace(',', ''))
                info['answer_count'] = int(float(answer_match.group(1))) if answer_match else 0
            
            # 创建时间
            time_elem = soup.select_one('.QuestionHeader .QuestionHeader-footer .QuestionHeader-Comment button')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 尝试提取时间信息
                info['created_time_text'] = time_text
            
            # 话题标签
            topics = []
            topic_elems = soup.select('.QuestionHeader-topics .TopicLink')
            for topic_elem in topic_elems:
                topic_name = topic_elem.get_text(strip=True)
                topic_url = topic_elem.get('href', '')
                topics.append({
                    'name': topic_name,
                    'url': topic_url if topic_url.startswith('http') else f"https://www.zhihu.com{topic_url}"
                })
            info['topics'] = topics
            
            # 提问者信息
            author_elem = soup.select_one('.QuestionHeader .AuthorInfo')
            if author_elem:
                author_name_elem = author_elem.select_one('.AuthorInfo-name')
                author_name = author_name_elem.get_text(strip=True) if author_name_elem else ''
                
                author_url_elem = author_elem.select_one('.AuthorInfo-link')
                author_url = author_url_elem.get('href') if author_url_elem else ''
                
                info['author'] = {
                    'name': author_name,
                    'url': author_url if author_url.startswith('http') else f"https://www.zhihu.com{author_url}"
                }
            
            # 完整信息
            detail = {
                'question_id': question_id,
                **info,
                'url': url,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 缓存数据
            self.question_cache[question_id] = detail
            
            print(f"[{datetime.now()}] 成功获取问题详细信息")
            return detail
            
        except Exception as e:
            print(f"获取问题详细信息时出错: {str(e)}")
            return None
    
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
            
            # 使用知乎API获取回答
            api_url = f"{self.api_url}/questions/{question_id}/answers"
            params = {
                'include': 'data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,is_sticky,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,relevant_info,question,excerpt,is_labeled,paid_info,paid_info_content,relationship.is_authorized,is_author,voting,is_thanked,is_nothelp,is_recognized;data[*].mark_infos[*].url;data[*].author.follower_count,badge[*].topics',
                'limit': min(limit, 20),
                'offset': 0,
                'platform': 'desktop',
                'sort_by': 'default',
            }
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                api_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取回答失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            answers_data = data.get('data', [])
            answers = []
            
            for answer in answers_data:
                try:
                    answer_info = self._parse_answer_data(answer)
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
    
    def _parse_answer_data(self, answer_data: Dict) -> Optional[Dict]:
        """
        解析回答数据
        
        Args:
            answer_data: 回答数据字典
            
        Returns:
            Dict: 回答信息
        """
        try:
            answer_id = answer_data.get('id', '')
            content = answer_data.get('content', '')
            
            # 清理HTML标签
            if content:
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
            
            # 作者信息
            author_data = answer_data.get('author', {})
            author_info = {
                'id': author_data.get('id', ''),
                'name': author_data.get('name', '匿名用户'),
                'url_token': author_data.get('url_token', ''),
                'headline': author_data.get('headline', ''),
                'follower_count': author_data.get('follower_count', 0),
                'avatar_url': author_data.get('avatar_url', ''),
            }
            
            # 回答统计
            voteup_count = answer_data.get('voteup_count', 0)
            comment_count = answer_data.get('comment_count', 0)
            created_time = answer_data.get('created_time', 0)
            
            if created_time:
                created_time_str = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_time_str = ''
            
            answer_info = {
                'answer_id': answer_id,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'content_length': len(content),
                'voteup_count': voteup_count,
                'comment_count': comment_count,
                'created_time': created_time_str,
                'author': author_info,
                'url': f"https://www.zhihu.com/answer/{answer_id}",
                'excerpt': answer_data.get('excerpt', ''),
            }
            
            return answer_info
            
        except Exception as e:
            print(f"解析回答数据时出错: {str(e)}")
            return None
    
    def get_user_info(self, user_url_token: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            user_url_token: 用户URL token
            
        Returns:
            Dict: 用户信息
        """
        # 检查缓存
        if user_url_token in self.user_cache:
            print(f"从缓存获取用户 {user_url_token} 的信息")
            return self.user_cache[user_url_token]
        
        try:
            print(f"[{datetime.now()}] 开始获取用户信息: {user_url_token}")
            
            api_url = f"{self.api_url}/members/{user_url_token}"
            params = {
                'include': 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics',
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                api_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取用户信息失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            user_info = {
                'id': data.get('id', ''),
                'url_token': user_url_token,
                'name': data.get('name', ''),
                'headline': data.get('headline', ''),
                'gender': data.get('gender', 0),  # 0未知，1男，-1女
                'follower_count': data.get('follower_count', 0),
                'following_count': data.get('following_count', 0),
                'answer_count': data.get('answer_count', 0),
                'articles_count': data.get('articles_count', 0),
                'question_count': data.get('question_count', 0),
                'voteup_count': data.get('voteup_count', 0),
                'thanked_count': data.get('thanked_count', 0),
                'favorited_count': data.get('favorited_count', 0),
                'avatar_url': data.get('avatar_url', ''),
                'url': f"https://www.zhihu.com/people/{user_url_token}",
                'is_org': data.get('is_org', False),
                'is_followed': data.get('is_followed', False),
                'is_following': data.get('is_following', False),
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 工作信息
            employments = data.get('employments', [])
            if employments:
                user_info['employment'] = employments[0].get('job', {}).get('name', '')
                user_info['company'] = employments[0].get('company', {}).get('name', '')
            
            # 教育信息
            educations = data.get('educations', [])
            if educations:
                user_info['education'] = educations[0].get('school', {}).get('name', '')
            
            # 缓存数据
            self.user_cache[user_url_token] = user_info
            
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
                'follow_count': question_detail.get('follow_count', 0),
                'view_count': question_detail.get('view_count', 0),
                'answer_count': question_detail.get('answer_count', 0),
                'topic_count': len(question_detail.get('topics', [])),
            }
            
            # 分析回答数据
            if answers:
                total_answers = len(answers)
                total_votes = sum(a.get('voteup_count', 0) for a in answers)
                total_comments = sum(a.get('comment_count', 0) for a in answers)
                
                avg_votes = total_votes / total_answers if total_answers > 0 else 0
                avg_comments = total_comments / total_answers if total_answers > 0 else 0
                
                # 高质量回答比例（赞数>100）
                high_quality_answers = sum(1 for a in answers if a.get('voteup_count', 0) > 100)
                high_quality_rate = (high_quality_answers / total_answers) * 100 if total_answers > 0 else 0
                
                # 专业回答者比例（粉丝>1000）
                professional_authors = sum(1 for a in answers if a.get('author', {}).get('follower_count', 0) > 1000)
                professional_rate = (professional_authors / total_answers) * 100 if total_answers > 0 else 0
                
                metrics.update({
                    'total_answers_analyzed': total_answers,
                    'total_votes': total_votes,
                    'total_comments': total_comments,
                    'avg_votes_per_answer': round(avg_votes, 2),
                    'avg_comments_per_answer': round(avg_comments, 2),
                    'high_quality_answer_rate': round(high_quality_rate, 2),
                    'professional_author_rate': round(professional_rate, 2),
                })
            
            # 计算热度评分
            metrics['hot_score'] = self._calculate_hot_score(question_detail, answers)
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析问题指标时出错: {str(e)}")
            return {}
    
    def _calculate_hot_score(self, question_detail: Dict, answers: List[Dict]) -> float:
        """
        计算热度评分
        
        Args:
            question_detail: 问题详细信息
            answers: 回答列表
            
        Returns:
            float: 热度评分
        """
        try:
            score = 0
            
            # 关注数权重
            follow_count = question_detail.get('follow_count', 0)
            score += min(follow_count / 1000 * 20, 20)
            
            # 浏览数权重
            view_count = question_detail.get('view_count', 0)
            score += min(view_count / 10000 * 20, 20)
            
            # 回答数权重
            answer_count = question_detail.get('answer_count', 0)
            score += min(answer_count / 100 * 20, 20)
            
            # 回答质量权重
            if answers:
                avg_votes = sum(a.get('voteup_count', 0) for a in answers) / len(answers)
                score += min(avg_votes / 100 * 20, 20)
            
            # 话题多样性权重
            topic_count = len(question_detail.get('topics', []))
            score += min(topic_count * 5, 20)
            
            return round(min(score, 100), 2)
            
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
            filename = f"zhihu_questions_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            print(f"保存数据到JSON时出错: {str(e)}")
    
    def run(self, get_hot_questions: bool = True, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            get_hot_questions: 是否获取热榜问题
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("知乎爬虫开始运行")
        print("=" * 50)
        
        all_questions = []
        
        # 获取热榜问题
        if get_hot_questions:
            print("\n获取知乎热榜问题...")
            hot_questions = self.get_hot_questions(limit=15)
            
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
                                author_token = answer.get('author', {}).get('url_token')
                                if author_token:
                                    user_info = self.get_user_info(author_token)
                                    if user_info:
                                        answer['author_detail'] = user_info
                        
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
                        
                        print(f"  已处理: {question.get('title')} (热度: {question.get('hot_value', 0):.1f})")
                        
                        # 避免请求过快
                        time.sleep(random.uniform(3, 4))
                        
                    except Exception as e:
                        print(f"处理问题 {question.get('title')} 时出错: {str(e)}")
                        continue
        
        # 保存到文件
        if save_to_file and all_questions:
            self.save_to_json(all_questions)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_questions)} 个问题数据")
        print("=" * 50)
        
        return all_questions


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = ZhihuCrawler()
        
        # 运行爬虫
        questions = crawler.run(
            get_hot_questions=True,
            save_to_file=True
        )
        
        if questions:
            print(f"\n数据统计:")
            print(f"总问题数: {len(questions)}")
            
            # 按热度排序
            sorted_questions = sorted(questions, key=lambda x: x.get('hot_value', 0), reverse=True)
            
            print(f"\n热度最高的前5个问题:")
            for idx, question in enumerate(sorted_questions[:5], 1):
                title = question.get('title', '')[:50]
                if len(question.get('title', '')) > 50:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     热度: {question.get('hot_value', 0):.1f} | "
                      f"排名: {question.get('rank', 0)}")
                print(f"     关注: {question.get('follow_count', 0):,} | "
                      f"浏览: {question.get('view_count', 0):,} | "
                      f"回答: {question.get('answer_count', 0)}")
                print(f"     热度评分: {question.get('hot_score', 0):.2f}")
                
                if question.get('topics'):
                    topics = [t['name'] for t in question['topics'][:3]]
                    print(f"     话题: {', '.join(topics)}")
        else:
            print("未能获取问题数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()