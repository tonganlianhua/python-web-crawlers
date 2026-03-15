"""
爬虫 49: GitHub Trending项目爬虫
功能: 爬取GitHub Trending仓库、开发者信息和项目数据
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


class GitHubTrendingCrawler:
    """GitHub Trending爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # GitHub相关URL
        self.base_url = "https://github.com"
        self.trending_url = f"{self.base_url}/trending"
        self.api_url = "https://api.github.com"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://github.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # GitHub API可能需要token
        self.github_token = None  # 可选，用于提高API限制
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.repo_cache = {}
        self.user_cache = {}
        
    def get_trending_repos(self, language: str = "", since: str = "daily", spoken_language: str = "") -> Optional[List[Dict]]:
        """
        获取GitHub Trending仓库
        
        Args:
            language: 编程语言过滤
            since: 时间范围 (daily, weekly, monthly)
            spoken_language: 语言过滤 (如zh, en等)
            
        Returns:
            List[Dict]: Trending仓库列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取GitHub Trending仓库 (语言: {language or 'all'}, 时间: {since})")
            
            params = {}
            if language:
                params['language'] = language
            if since:
                params['since'] = since
            if spoken_language:
                params['spoken_language_code'] = spoken_language
            
            time.sleep(random.uniform(2, 3))
            
            response = self.session.get(
                self.trending_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取Trending失败，状态码: {response.status_code}")
                return self._retry_get_trending_repos(language, since, spoken_language)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            repos = []
            
            # 查找仓库项
            repo_items = soup.select('.Box .Box-row')
            
            for idx, item in enumerate(repo_items):
                try:
                    repo = self._parse_repo_item(item, idx + 1)
                    if repo:
                        repo['language'] = language or 'all'
                        repo['since'] = since
                        repos.append(repo)
                except Exception as e:
                    print(f"解析仓库项时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(repos)} 个Trending仓库")
            return repos
            
        except requests.exceptions.Timeout:
            print("获取Trending请求超时")
            return self._retry_get_trending_repos(language, since, spoken_language)
        except requests.exceptions.ConnectionError:
            print("获取Trending连接错误")
            return self._retry_get_trending_repos(language, since, spoken_language)
        except Exception as e:
            print(f"获取Trending时发生未知错误: {str(e)}")
            return None
    
    def _parse_repo_item(self, item, rank: int) -> Optional[Dict]:
        """
        解析仓库项
        
        Args:
            item: BeautifulSoup元素
            rank: 排名
            
        Returns:
            Dict: 仓库信息
        """
        try:
            # 提取仓库名称和链接
            title_elem = item.select_one('h2 a')
            if not title_elem:
                return None
            
            repo_full_name = title_elem.get_text(strip=True).replace('\n', '').replace(' ', '')
            repo_url = title_elem.get('href', '')
            
            # 解析作者和仓库名
            author, repo_name = repo_full_name.split('/') if '/' in repo_full_name else ('', repo_full_name)
            
            # 提取描述
            desc_elem = item.select_one('p')
            description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # 提取编程语言
            lang_elem = item.select_one('[itemprop="programmingLanguage"]')
            language = lang_elem.get_text(strip=True) if lang_elem else ''
            
            # 提取星星数
            stars_elem = item.select_one('a[href*="stargazers"]')
            stars_text = stars_elem.get_text(strip=True) if stars_elem else ''
            stars_match = re.search(r'([\d,]+)', stars_text.replace(',', ''))
            stars = int(stars_match.group(1)) if stars_match else 0
            
            # 提取fork数
            forks_elem = item.select_one('a[href*="forks"]')
            forks_text = forks_elem.get_text(strip=True) if forks_elem else ''
            forks_match = re.search(r'([\d,]+)', forks_text.replace(',', ''))
            forks = int(forks_match.group(1)) if forks_match else 0
            
            # 提取今日星星数
            today_stars_elem = item.select_one('span:has(svg.octicon-star)')
            today_stars_text = ''
            if today_stars_elem:
                today_stars_text = today_stars_elem.get_text(strip=True)
                # 找到星星数后面的span
                for sibling in today_stars_elem.next_siblings:
                    if isinstance(sibling, str):
                        today_stars_text += sibling
                    elif sibling.name == 'span':
                        today_stars_text += sibling.get_text(strip=True)
            
            today_stars_match = re.search(r'([\d,]+)', today_stars_text.replace(',', ''))
            today_stars = int(today_stars_match.group(1)) if today_stars_match else 0
            
            # 提取贡献者（如果有）
            built_by_elem = item.select_one('span:has(span:contains("Built by"))')
            contributors = []
            if built_by_elem:
                contributor_elems = built_by_elem.select('a')
                for contributor in contributor_elems:
                    contributor_url = contributor.get('href', '')
                    contributor_name = contributor.get('aria-label', '').replace('@', '')
                    contributors.append({
                        'name': contributor_name,
                        'url': contributor_url
                    })
            
            repo_info = {
                'rank': rank,
                'author': author,
                'repo_name': repo_name,
                'full_name': repo_full_name,
                'description': description,
                'language': language,
                'stars': stars,
                'forks': forks,
                'today_stars': today_stars,
                'contributors': contributors,
                'url': f"https://github.com{repo_url}",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return repo_info
            
        except Exception as e:
            print(f"解析仓库项时出错: {str(e)}")
            return None
    
    def _retry_get_trending_repos(self, language: str, since: str, spoken_language: str) -> Optional[List[Dict]]:
        """
        重试获取Trending仓库
        
        Returns:
            List[Dict]: Trending仓库列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.get_trending_repos(language, since, spoken_language)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_repo_detail(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库详细信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            Dict: 仓库详细信息
        """
        # 检查缓存
        cache_key = f"{owner}/{repo}"
        if cache_key in self.repo_cache:
            print(f"从缓存获取仓库 {cache_key} 的详细信息")
            return self.repo_cache[cache_key]
        
        try:
            print(f"[{datetime.now()}] 开始获取仓库详细信息: {owner}/{repo}")
            
            # 使用GitHub API获取仓库信息
            api_headers = self.headers.copy()
            if self.github_token:
                api_headers['Authorization'] = f'token {self.github_token}'
            
            api_url = f"{self.api_url}/repos/{owner}/{repo}"
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                api_url,
                headers=api_headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"获取仓库详情失败，状态码: {response.status_code}")
                
                # 如果未授权，尝试不使用token
                if response.status_code == 401 and self.github_token:
                    print("尝试不使用token访问...")
                    del api_headers['Authorization']
                    response = self.session.get(
                        api_url,
                        headers=api_headers,
                        proxies=self.proxy,
                        timeout=15
                    )
                
                if response.status_code != 200:
                    return None
            
            repo_data = response.json()
            
            # 解析仓库信息
            detail = {
                'owner': owner,
                'repo': repo,
                'full_name': repo_data.get('full_name', ''),
                'description': repo_data.get('description', ''),
                'homepage': repo_data.get('homepage', ''),
                'language': repo_data.get('language', ''),
                'license': repo_data.get('license', {}).get('name', '') if repo_data.get('license') else '',
                'created_at': repo_data.get('created_at', ''),
                'updated_at': repo_data.get('updated_at', ''),
                'pushed_at': repo_data.get('pushed_at', ''),
                'size': repo_data.get('size', 0),
                'stars': repo_data.get('stargazers_count', 0),
                'watchers': repo_data.get('watchers_count', 0),
                'forks': repo_data.get('forks_count', 0),
                'open_issues': repo_data.get('open_issues_count', 0),
                'default_branch': repo_data.get('default_branch', ''),
                'is_fork': repo_data.get('fork', False),
                'is_archived': repo_data.get('archived', False),
                'is_disabled': repo_data.get('disabled', False),
                'is_template': repo_data.get('is_template', False),
                'topics': repo_data.get('topics', []),
                'visibility': repo_data.get('visibility', ''),
                'url': repo_data.get('html_url', ''),
                'api_url': repo_data.get('url', ''),
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 获取额外统计信息
            try:
                # 获取贡献者数量
                contributors_url = f"{self.api_url}/repos/{owner}/{repo}/contributors"
                time.sleep(0.5)
                
                contributors_response = self.session.get(
                    contributors_url,
                    headers=api_headers,
                    params={'per_page': 1, 'anon': 'true'},
                    proxies=self.proxy,
                    timeout=10
                )
                
                if contributors_response.status_code == 200:
                    # 从响应头获取总数
                    link_header = contributors_response.headers.get('Link', '')
                    if link_header:
                        # 解析Link头获取总页数
                        last_match = re.search(r'page=(\d+)>; rel="last"', link_header)
                        if last_match:
                            detail['contributor_count'] = int(last_match.group(1))
                    else:
                        detail['contributor_count'] = len(contributors_response.json())
                
                # 获取最近提交
                commits_url = f"{self.api_url}/repos/{owner}/{repo}/commits"
                time.sleep(0.5)
                
                commits_response = self.session.get(
                    commits_url,
                    headers=api_headers,
                    params={'per_page': 1},
                    proxies=self.proxy,
                    timeout=10
                )
                
                if commits_response.status_code == 200:
                    commits_data = commits_response.json()
                    if commits_data and isinstance(commits_data, list) and len(commits_data) > 0:
                        detail['last_commit'] = commits_data[0].get('commit', {}).get('author', {}).get('date', '')
                
            except Exception as e:
                print(f"获取额外统计信息时出错: {str(e)}")
            
            # 缓存数据
            self.repo_cache[cache_key] = detail
            
            print(f"[{datetime.now()}] 成功获取仓库详细信息")
            return detail
            
        except Exception as e:
            print(f"获取仓库详细信息时出错: {str(e)}")
            return None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            Dict: 用户信息
        """
        # 检查缓存
        if username in self.user_cache:
            print(f"从缓存获取用户 {username} 的信息")
            return self.user_cache[username]
        
        try:
            print(f"[{datetime.now()}] 开始获取用户信息: {username}")
            
            # 使用GitHub API获取用户信息
            api_headers = self.headers.copy()
            if self.github_token:
                api_headers['Authorization'] = f'token {self.github_token}'
            
            api_url = f"{self.api_url}/users/{username}"
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                api_url,
                headers=api_headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取用户信息失败，状态码: {response.status_code}")
                return None
            
            user_data = response.json()
            
            user_info = {
                'username': username,
                'name': user_data.get('name', ''),
                'bio': user_data.get('bio', ''),
                'company': user_data.get('company', ''),
                'blog': user_data.get('blog', ''),
                'location': user_data.get('location', ''),
                'email': user_data.get('email', ''),
                'hireable': user_data.get('hireable', False),
                'twitter_username': user_data.get('twitter_username', ''),
                'public_repos': user_data.get('public_repos', 0),
                'public_gists': user_data.get('public_gists', 0),
                'followers': user_data.get('followers', 0),
                'following': user_data.get('following', 0),
                'created_at': user_data.get('created_at', ''),
                'updated_at': user_data.get('updated_at', ''),
                'avatar_url': user_data.get('avatar_url', ''),
                'url': user_data.get('html_url', ''),
                'type': user_data.get('type', 'User'),  # User or Organization
                'site_admin': user_data.get('site_admin', False),
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 如果是组织，获取更多信息
            if user_data.get('type') == 'Organization':
                try:
                    org_url = f"{self.api_url}/orgs/{username}"
                    time.sleep(0.5)
                    
                    org_response = self.session.get(
                        org_url,
                        headers=api_headers,
                        proxies=self.proxy,
                        timeout=10
                    )
                    
                    if org_response.status_code == 200:
                        org_data = org_response.json()
                        user_info.update({
                            'description': org_data.get('description', ''),
                            'is_verified': org_data.get('is_verified', False),
                        })
                except:
                    pass
            
            # 缓存数据
            self.user_cache[username] = user_info
            
            print(f"[{datetime.now()}] 成功获取用户信息")
            return user_info
            
        except Exception as e:
            print(f"获取用户信息时出错: {str(e)}")
            return None
    
    def get_repo_languages(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库语言统计
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            Dict: 语言统计信息
        """
        try:
            print(f"[{datetime.now()}] 开始获取仓库语言统计: {owner}/{repo}")
            
            api_headers = self.headers.copy()
            if self.github_token:
                api_headers['Authorization'] = f'token {self.github_token}'
            
            api_url = f"{self.api_url}/repos/{owner}/{repo}/languages"
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                api_url,
                headers=api_headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取语言统计失败，状态码: {response.status_code}")
                return None
            
            languages_data = response.json()
            
            # 计算百分比
            total_bytes = sum(languages_data.values())
            languages_percent = {}
            
            for lang, bytes_count in languages_data.items():
                if total_bytes > 0:
                    percent = (bytes_count / total_bytes) * 100
                    languages_percent[lang] = round(percent, 2)
                else:
                    languages_percent[lang] = 0
            
            result = {
                'languages': languages_data,
                'languages_percent': languages_percent,
                'total_bytes': total_bytes,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            print(f"[{datetime.now()}] 成功获取仓库语言统计")
            return result
            
        except Exception as e:
            print(f"获取仓库语言统计时出错: {str(e)}")
            return None
    
    def analyze_repo_metrics(self, repo_detail: Dict, languages: Optional[Dict] = None) -> Dict:
        """
        分析仓库指标
        
        Args:
            repo_detail: 仓库详细信息
            languages: 语言统计信息
            
        Returns:
            Dict: 分析指标
        """
        try:
            metrics = {
                'stars': repo_detail.get('stars', 0),
                'forks': repo_detail.get('forks', 0),
                'watchers': repo_detail.get('watchers', 0),
                'open_issues': repo_detail.get('open_issues', 0),
                'size': repo_detail.get('size', 0),
                'age_days': self._calculate_age_days(repo_detail.get('created_at', '')),
                'last_updated_days': self._calculate_age_days(repo_detail.get('updated_at', ''), reverse=True),
            }
            
            # 计算活跃度
            metrics['activity_score'] = self._calculate_activity_score(repo_detail)
            
            # 计算流行度
            metrics['popularity_score'] = self._calculate_popularity_score(repo_detail)
            
            # 计算健康度
            metrics['health_score'] = self._calculate_health_score(repo_detail)
            
            # 语言多样性
            if languages and languages.get('languages_percent'):
                lang_percent = languages['languages_percent']
                lang_count = len(lang_percent)
                main_lang_percent = max(lang_percent.values()) if lang_percent else 0
                
                metrics.update({
                    'language_count': lang_count,
                    'main_language_percent': main_lang_percent,
                    'language_diversity': self._calculate_language_diversity(lang_percent),
                })
            
            metrics['analysis_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return metrics
            
        except Exception as e:
            print(f"分析仓库指标时出错: {str(e)}")
            return {}
    
    def _calculate_age_days(self, date_str: str, reverse: bool = False) -> int:
        """
        计算天数
        
        Args:
            date_str: 日期字符串
            reverse: 是否反向计算（从当前时间到该日期）
            
        Returns:
            int: 天数
        """
        if not date_str:
            return 0
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            now = datetime.now()
            
            if reverse:
                return (now - date_obj).days
            else:
                return (date_obj - now).days
        except:
            return 0
    
    def _calculate_activity_score(self, repo_detail: Dict) -> float:
        """
        计算活跃度评分
        
        Args:
            repo_detail: 仓库详细信息
            
        Returns:
            float: 活跃度评分
        """
        try:
            score = 0
            
            # 最近更新时间权重
            updated_days = self._calculate_age_days(repo_detail.get('updated_at', ''), reverse=True)
            if updated_days <= 7:  # 一周内有更新
                score += 40
            elif updated_days <= 30:  # 一月内有更新
                score += 20
            elif updated_days <= 90:  # 三月内有更新
                score += 10
            
            # 提交频率（如果有最后提交时间）
            if repo_detail.get('last_commit'):
                commit_days = self._calculate_age_days(repo_detail['last_commit'], reverse=True)
                if commit_days <= 1:  # 一天内有提交
                    score += 30
                elif commit_days <= 7:  # 一周内有提交
                    score += 20
                elif commit_days <= 30:  # 一月内有提交
                    score += 10
            
            # Issues活跃度
            open_issues = repo_detail.get('open_issues', 0)
            if open_issues > 0:
                score += min(open_issues / 10 * 10, 10)
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def _calculate_popularity_score(self, repo_detail: Dict) -> float:
        """
        计算流行度评分
        
        Args:
            repo_detail: 仓库详细信息
            
        Returns:
            float: 流行度评分
        """
        try:
            score = 0
            
            # 星星数权重
            stars = repo_detail.get('stars', 0)
            score += min(stars / 1000 * 40, 40)
            
            # Fork数权重
            forks = repo_detail.get('forks', 0)
            score += min(forks / 100 * 20, 20)
            
            # Watch数权重
            watchers = repo_detail.get('watchers', 0)
            score += min(watchers / 100 * 20, 20)
            
            # 贡献者数权重
            contributor_count = repo_detail.get('contributor_count', 0)
            score += min(contributor_count * 5, 20)
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def _calculate_health_score(self, repo_detail: Dict) -> float:
        """
        计算健康度评分
        
        Args:
            repo_detail: 仓库详细信息
            
        Returns:
            float: 健康度评分
        """
        try:
            score = 0
            
            # Issues处理状态
            open_issues = repo_detail.get('open_issues', 0)
            if open_issues == 0:
                score += 30
            elif open_issues <= 10:
                score += 20
            elif open_issues <= 50:
                score += 10
            
            # 是否有许可证
            if repo_detail.get('license'):
                score += 20
            
            # 是否有README（通过描述判断）
            if repo_detail.get('description'):
                score += 10
            
            # 是否活跃维护
            updated_days = self._calculate_age_days(repo_detail.get('updated_at', ''), reverse=True)
            if updated_days <= 90:  # 三月内有更新
                score += 40
            
            return round(min(score, 100), 2)
            
        except:
            return 0
    
    def _calculate_language_diversity(self, lang_percent: Dict) -> float:
        """
        计算语言多样性
        
        Args:
            lang_percent: 语言百分比字典
            
        Returns:
            float: 多样性评分（0-100）
        """
        try:
            if not lang_percent:
                return 0
            
            # 使用香农多样性指数
            total = sum(lang_percent.values())
            if total == 0:
                return 0
            
            # 转换为比例
            proportions = [p / total for p in lang_percent.values()]
            
            # 计算香农指数
            shannon = -sum(p * (p and (p * 100).log() or 0) for p in proportions)
            
            # 归一化到0-100
            max_shannon = (len(proportions) * 100).log()
            if max_shannon == 0:
                return 0
            
            diversity = (shannon / max_shannon) * 100
            return round(diversity, 2)
            
        except:
            return 0
    
    def get_trending_languages(self) -> Optional[List[str]]:
        """
        获取热门编程语言列表
        
        Returns:
            List[str]: 热门编程语言列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取热门编程语言")
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.trending_url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取语言列表失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            languages = []
            
            # 查找语言选择器
            lang_select = soup.select('select[id="language"] option')
            for option in lang_select:
                lang_value = option.get('value', '')
                if lang_value:
                    languages.append(lang_value)
            
            print(f"[{datetime.now()}] 成功获取 {len(languages)} 个编程语言")
            return languages
            
        except Exception as e:
            print(f"获取热门编程语言时出错: {str(e)}")
            return None
    
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
            filename = f"github_trending_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            print(f"保存数据到JSON时出错: {str(e)}")
    
    def run(self, languages: List[str] = None, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            languages: 要爬取的编程语言列表
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("GitHub Trending爬虫开始运行")
        print("=" * 50)
        
        if languages is None:
            languages = ['python', 'javascript', 'java', 'go']
        
        all_repos = []
        
        # 获取各语言Trending
        for language in languages:
            print(f"\n获取 {language} 语言Trending仓库...")
            trending_repos = self.get_trending_repos(language=language, since="daily")
            
            if trending_repos:
                for repo in trending_repos[:8]:  # 每种语言只处理前8个
                    try:
                        author = repo.get('author')
                        repo_name = repo.get('repo_name')
                        
                        if not author or not repo_name:
                            continue
                        
                        # 获取详细信息
                        detail = self.get_repo_detail(author, repo_name)
                        if not detail:
                            continue
                        
                        # 获取语言统计
                        languages_stats = self.get_repo_languages(author, repo_name)
                        
                        # 获取作者信息
                        author_info = self.get_user_info(author)
                        
                        # 分析指标
                        metrics = self.analyze_repo_metrics(detail, languages_stats)
                        
                        # 合并数据
                        complete_data = {
                            **repo,
                            **detail,
                            'languages_stats': languages_stats,
                            'author_info': author_info,
                            **metrics,
                            'source_language': language,
                        }
                        
                        all_repos.append(complete_data)
                        
                        print(f"  已处理: {author}/{repo_name} (星星: {repo.get('stars', 0):,})")
                        
                        # 避免请求过快
                        time.sleep(random.uniform(2, 3))
                        
                    except Exception as e:
                        print(f"处理仓库 {repo.get('full_name')} 时出错: {str(e)}")
                        continue
        
        # 获取热门语言列表
        print("\n获取热门编程语言...")
        trending_languages = self.get_trending_languages()
        if trending_languages:
            print(f"热门编程语言TOP10: {', '.join(trending_languages[:10])}")
        
        # 保存到文件
        if save_to_file and all_repos:
            self.save_to_json(all_repos)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_repos)} 个仓库数据")
        print("=" * 50)
        
        return all_repos


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = GitHubTrendingCrawler()
        
        # 运行爬虫
        repos = crawler.run(
            languages=['python', 'javascript'],  # 可以修改编程语言
            save_to_file=True
        )
        
        if repos:
            print(f"\n数据统计:")
            print(f"总仓库数: {len(repos)}")
            
            # 按今日星星数排序
            sorted_repos = sorted(repos, key=lambda x: x.get('today_stars', 0), reverse=True)
            
            print(f"\n今日星星增长最快的前5个仓库:")
            for idx, repo in enumerate(sorted_repos[:5], 1):
                full_name = repo.get('full_name', '')
                description = repo.get('description', '')[:60]
                if len(repo.get('description', '')) > 60:
                    description += "..."
                
                print(f"  {idx}. {full_name}")
                print(f"     今日星星: +{repo.get('today_stars', 0)} | "
                      f"总星星: {repo.get('stars', 0):,}")
                print(f"     语言: {repo.get('language', 'N/A')} | "
                      f"Forks: {repo.get('forks', 0):,}")
                print(f"     描述: {description}")
                print(f"     活跃度: {repo.get('activity_score', 0):.2f} | "
                      f"流行度: {repo.get('popularity_score', 0):.2f}")
        else:
            print("未能获取仓库数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()