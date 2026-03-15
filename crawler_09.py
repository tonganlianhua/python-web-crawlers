#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫09: GitHub仓库信息爬虫
功能: 爬取GitHub仓库、用户、趋势项目信息，支持搜索和数据分析
注意: 请遵守GitHub API使用限制，合理使用Token
"""

import requests
import json
import time
from datetime import datetime, timedelta
import logging
import os
import base64
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_09.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GitHubCrawler:
    """GitHub仓库爬虫"""
    
    def __init__(self, github_token: str = None):
        """
        初始化GitHub爬虫
        
        Args:
            github_token: GitHub个人访问令牌（可选，提高API限制）
        """
        self.base_url = "https://api.github.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/vnd.github.v3+json',
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        }
        
        if github_token:
            self.headers['Authorization'] = f'token {github_token}'
            logger.info("使用GitHub Token，API限制提高")
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 记录API调用次数
        self.api_calls = 0
        self.rate_limit_remaining = 60  # 默认限制
        
        logger.info("GitHub爬虫初始化完成")
    
    def check_rate_limit(self):
        """检查API速率限制"""
        try:
            response = self.session.get(f"{self.base_url}/rate_limit", timeout=5)
            if response.status_code == 200:
                data = response.json()
                resources = data.get('resources', {})
                core = resources.get('core', {})
                
                self.rate_limit_remaining = core.get('remaining', 60)
                reset_time = core.get('reset', 0)
                
                if self.rate_limit_remaining < 10:
                    reset_datetime = datetime.fromtimestamp(reset_time)
                    wait_seconds = (reset_datetime - datetime.now()).total_seconds()
                    
                    if wait_seconds > 0:
                        logger.warning(f"API限制接近，剩余: {self.rate_limit_remaining}，将在 {reset_datetime} 重置")
                
                logger.debug(f"API剩余调用次数: {self.rate_limit_remaining}")
                
        except Exception as e:
            logger.warning(f"检查速率限制失败: {e}")
    
    def search_repositories(self, query: str, sort: str = 'stars', order: str = 'desc', 
                           per_page: int = 30, page: int = 1) -> List[Dict]:
        """
        搜索GitHub仓库
        
        Args:
            query: 搜索查询
            sort: 排序方式 (stars, forks, updated)
            order: 排序顺序 (desc, asc)
            per_page: 每页数量
            page: 页码
            
        Returns:
            仓库列表
        """
        try:
            self.check_rate_limit()
            
            logger.info(f"搜索GitHub仓库: {query}")
            
            url = f"{self.base_url}/search/repositories"
            params = {
                'q': query,
                'sort': sort,
                'order': order,
                'per_page': per_page,
                'page': page
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            self.api_calls += 1
            data = response.json()
            
            repositories = []
            for item in data.get('items', []):
                repo = self._parse_repository(item)
                repositories.append(repo)
            
            logger.info(f"搜索到 {len(repositories)} 个仓库 (总计: {data.get('total_count', 0)})")
            return repositories
            
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索仓库失败: {e}")
            return []
        except Exception as e:
            logger.error(f"处理仓库数据失败: {e}")
            return []
    
    def get_trending_repos(self, language: str = '', since: str = 'daily') -> List[Dict]:
        """
        获取GitHub趋势仓库（通过爬取趋势页面）
        
        Args:
            language: 编程语言
            since: 时间范围 (daily, weekly, monthly)
            
        Returns:
            趋势仓库列表
        """
        try:
            logger.info(f"获取GitHub趋势仓库: language={language}, since={since}")
            
            # GitHub趋势页面URL
            url = "https://github.com/trending"
            if language:
                url += f"/{language}"
            
            url += f"?since={since}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            trending_repos = []
            repo_items = soup.select('article.Box-row')
            
            for item in repo_items:
                try:
                    repo = {
                        'source': 'trending',
                        'language': language or 'all',
                        'since': since,
                        'crawled_at': datetime.now().isoformat()
                    }
                    
                    # 获取仓库链接和名称
                    link_elem = item.select_one('h2 a')
                    if link_elem:
                        repo['full_name'] = link_elem.get('href', '').lstrip('/')
                        repo['name'] = repo['full_name'].split('/')[-1]
                        repo['owner'] = repo['full_name'].split('/')[0]
                        repo['html_url'] = f"https://github.com{link_elem.get('href', '')}"
                    
                    # 获取描述
                    desc_elem = item.select_one('p')
                    if desc_elem:
                        repo['description'] = desc_elem.get_text(strip=True)
                    
                    # 获取编程语言
                    lang_elem = item.select_one('[itemprop="programmingLanguage"]')
                    if lang_elem:
                        repo['language'] = lang_elem.get_text(strip=True)
                    
                    # 获取星标数
                    star_elem = item.select_one('a[href$="/stargazers"]')
                    if star_elem:
                        star_text = star_elem.get_text(strip=True)
                        repo['stargazers_count'] = self._parse_count(star_text)
                    
                    # 获取fork数
                    fork_elem = item.select_one('a[href$="/forks"]')
                    if fork_elem:
                        fork_text = fork_elem.get_text(strip=True)
                        repo['forks_count'] = self._parse_count(fork_text)
                    
                    # 获取今日星标增长
                    today_stars_elem = item.select_one('span.d-inline-block.float-sm-right')
                    if today_stars_elem:
                        stars_text = today_stars_elem.get_text(strip=True)
                        repo['today_stars'] = self._parse_count(stars_text.replace('stars today', ''))
                    
                    if repo.get('full_name'):
                        trending_repos.append(repo)
                        
                except Exception as e:
                    logger.debug(f"处理趋势仓库条目时出错: {e}")
                    continue
            
            logger.info(f"获取到 {len(trending_repos)} 个趋势仓库")
            return trending_repos
            
        except Exception as e:
            logger.error(f"获取趋势仓库失败: {e}")
            return []
    
    def get_repository_details(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库详细信息
        
        Args:
            owner: 所有者用户名
            repo: 仓库名
            
        Returns:
            仓库详细信息
        """
        try:
            self.check_rate_limit()
            
            logger.info(f"获取仓库详情: {owner}/{repo}")
            
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            self.api_calls += 1
            data = response.json()
            
            repo_details = self._parse_repository(data)
            
            # 获取额外信息
            try:
                # 获取贡献者
                contributors = self._get_contributors(owner, repo)
                if contributors:
                    repo_details['contributors'] = contributors[:10]  # 只取前10个
                
                # 获取语言使用情况
                languages = self._get_repo_languages(owner, repo)
                if languages:
                    repo_details['languages'] = languages
                
                # 获取README内容
                readme = self._get_readme(owner, repo)
                if readme:
                    repo_details['readme'] = readme[:1000]  # 限制长度
                
            except Exception as e:
                logger.warning(f"获取额外信息失败: {e}")
            
            logger.debug(f"获取到仓库详情: {owner}/{repo}")
            return repo_details
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取仓库详情失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理仓库详情失败: {e}")
            return None
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        获取GitHub用户信息
        
        Args:
            username: 用户名
            
        Returns:
            用户信息
        """
        try:
            self.check_rate_limit()
            
            logger.info(f"获取用户信息: {username}")
            
            url = f"{self.base_url}/users/{username}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            self.api_calls += 1
            data = response.json()
            
            user_info = {
                'login': data.get('login'),
                'name': data.get('name'),
                'avatar_url': data.get('avatar_url'),
                'html_url': data.get('html_url'),
                'type': data.get('type'),
                'company': data.get('company'),
                'blog': data.get('blog'),
                'location': data.get('location'),
                'email': data.get('email'),
                'bio': data.get('bio'),
                'public_repos': data.get('public_repos'),
                'public_gists': data.get('public_gists'),
                'followers': data.get('followers'),
                'following': data.get('following'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'crawled_at': datetime.now().isoformat()
            }
            
            # 获取用户仓库
            try:
                repos = self._get_user_repos(username)
                if repos:
                    user_info['repositories'] = repos[:10]
            except Exception as e:
                logger.warning(f"获取用户仓库失败: {e}")
            
            logger.debug(f"获取到用户信息: {username}")
            return user_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理用户信息失败: {e}")
            return None
    
    def _parse_repository(self, data: Dict) -> Dict:
        """解析仓库数据"""
        return {
            'id': data.get('id'),
            'name': data.get('name'),
            'full_name': data.get('full_name'),
            'owner': data.get('owner', {}).get('login') if data.get('owner') else None,
            'html_url': data.get('html_url'),
            'description': data.get('description'),
            'fork': data.get('fork'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
            'pushed_at': data.get('pushed_at'),
            'homepage': data.get('homepage'),
            'size': data.get('size'),
            'stargazers_count': data.get('stargazers_count'),
            'watchers_count': data.get('watchers_count'),
            'language': data.get('language'),
            'has_issues': data.get('has_issues'),
            'has_projects': data.get('has_projects'),
            'has_downloads': data.get('has_downloads'),
            'has_wiki': data.get('has_wiki'),
            'has_pages': data.get('has_pages'),
            'forks_count': data.get('forks_count'),
            'archived': data.get('archived'),
            'disabled': data.get('disabled'),
            'open_issues_count': data.get('open_issues_count'),
            'license': data.get('license', {}).get('name') if data.get('license') else None,
            'topics': data.get('topics', []),
            'default_branch': data.get('default_branch'),
            'crawled_at': datetime.now().isoformat()
        }
    
    def _get_contributors(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库贡献者"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
            params = {'per_page': 100}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            self.api_calls += 1
            contributors = response.json()
            
            return [
                {
                    'login': c.get('login'),
                    'avatar_url': c.get('avatar_url'),
                    'html_url': c.get('html_url'),
                    'contributions': c.get('contributions')
                }
                for c in contributors
            ]
            
        except Exception as e:
            logger.warning(f"获取贡献者失败: {e}")
            return []
    
    def _get_repo_languages(self, owner: str, repo: str) -> Dict:
        """获取仓库语言使用情况"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/languages"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            self.api_calls += 1
            languages = response.json()
            
            # 计算百分比
            total_bytes = sum(languages.values())
            if total_bytes > 0:
                languages_percent = {
                    lang: (bytes / total_bytes * 100)
                    for lang, bytes in languages.items()
                }
                return languages_percent
            
            return languages
            
        except Exception as e:
            logger.warning(f"获取语言使用情况失败: {e}")
            return {}
    
    def _get_readme(self, owner: str, repo: str) -> Optional[str]:
        """获取README内容"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/readme"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            self.api_calls += 1
            data = response.json()
            
            if data.get('content'):
                # Base64解码
                content = base64.b64decode(data['content']).decode('utf-8')
                return content
            
            return None
            
        except Exception as e:
            logger.warning(f"获取README失败: {e}")
            return None
    
    def _get_user_repos(self, username: str) -> List[Dict]:
        """获取用户仓库"""
        try:
            url = f"{self.base_url}/users/{username}/repos"
            params = {
                'sort': 'updated',
                'per_page': 30,
                'page': 1
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            self.api_calls += 1
            repos_data = response.json()
            
            return [self._parse_repository(repo) for repo in repos_data]
            
        except Exception as e:
            logger.warning(f"获取用户仓库失败: {e}")
            return []
    
    def _parse_count(self, text: str) -> int:
        """解析数量文本（如1.2k -> 1200）"""
        try:
            text = text.strip().lower()
            
            if 'k' in text:
                number = float(text.replace('k', '').replace(',', ''))
                return int(number * 1000)
            elif 'm' in text:
                number = float(text.replace('m', '').replace(',', ''))
                return int(number * 1000000)
            else:
                # 移除逗号和其他非数字字符
                number_str = ''.join(c for c in text if c.isdigit())
                return int(number_str) if number_str else 0
                
        except Exception:
            return 0
    
    def analyze_repositories(self, repositories: List[Dict]) -> Dict:
        """
        分析仓库数据
        
        Args:
            repositories: 仓库列表
            
        Returns:
            分析结果
        """
        analysis = {
            'total_repos': len(repositories),
            'language_stats': {},
            'stars_stats': {},
            'forks_stats': {},
            'top_repositories': [],
            'recently_updated': []
        }
        
        if not repositories:
            return analysis
        
        # 语言统计
        for repo in repositories:
            language = repo.get('language')
            if language:
                analysis['language_stats'][language] = analysis['language_stats'].get(language, 0) + 1
        
        # 星标和fork统计
        stars = []
        forks = []
        
        for repo in repositories:
            stars_count = repo.get('stargazers_count', 0)
            forks_count = repo.get('forks_count', 0)
            
            if isinstance(stars_count, (int, float)):
                stars.append(stars_count)
            if isinstance(forks_count, (int, float)):
                forks.append(forks_count)
        
        if stars:
            analysis['stars_stats']['average'] = sum(stars) / len(stars)
            analysis['stars_stats']['max'] = max(stars)
            analysis['stars_stats']['min'] = min(stars)
            analysis['stars_stats']['total'] = sum(stars)
        
        if forks:
            analysis['forks_stats']['average'] = sum(forks) / len(forks)
            analysis['forks_stats']['max'] = max(forks)
            analysis['forks_stats']['min'] = min(forks)
            analysis['forks_stats']['total'] = sum(forks)
        
        # 按星标排序的顶级仓库
        sorted_by_stars = sorted(
            repositories,
            key=lambda x: x.get('stargazers_count', 0),
            reverse=True
        )
        analysis['top_repositories'] = sorted_by_stars[:10]
        
        # 最近更新的仓库
        sorted_by_updated = sorted(
            repositories,
            key=lambda x: x.get('updated_at', ''),
            reverse=True
        )
        analysis['recently_updated'] = sorted_by_updated[:10]
        
        return analysis

def main():
    """主函数"""
    try:
        print("=== GitHub仓库爬虫 ===")
        print("注意: 未认证用户每小时60次API调用限制")
        print("      使用GitHub Token可提高限制")
        print()
        
        github_token = input("请输入GitHub Token（可选，按Enter跳过）: ").strip()
        
        crawler = GitHubCrawler(github_token if github_token else None)
        
        print("\n选择功能:")
        print("1. 搜索GitHub仓库")
        print("2. 获取趋势仓库")
        print("3. 获取仓库详情")
        print("4. 获取用户信息")
        print("5. 分析仓库数据")
        print("6. 退出")
        
        choice = input("\n请选择功能 (1-6): ").strip()
        
        if choice == '1':
            query = input("请输入搜索关键词 (例如: python machine learning): ").strip()
            if not query:
                print("关键词不能为空")
                return
            
            sort = input("排序方式 (stars/forks/updated, 默认stars): ").strip() or 'stars'
            order = input("排序顺序 (desc/asc, 默认desc): ").strip() or 'desc'
            
            per_page = input("每页数量 (默认30): ").strip()
            per_page = int(per_page) if per_page.isdigit() else 30
            
            page = input("页码 (默认1): ").strip()
            page = int(page) if page.isdigit() else 1
            
            print(f"\n正在搜索GitHub仓库...")
            repositories = crawler.search_repositories(query, sort, order, per_page, page)
            
            if repositories:
                print(f"\n找到 {len(repositories)} 个仓库:")
                for i, repo in enumerate(repositories[:10], 1):
                    name = repo.get('full_name', '未知仓库')
                    stars = repo.get('stargazers_count', 0)
                    forks = repo.get('forks_count', 0)
                    language = repo.get('language', '未知')
                    
                    print(f"{i}. {name}")
                    print(f"   描述: {repo.get('description', '无描述')[:80]}...")
                    print(f"   语言: {language} | 星标: {stars:,} | Fork: {forks:,}")
                    print()
                
                # 保存搜索结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'github_search_{query}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(repositories, f, ensure_ascii=False, indent=2)
                print(f"搜索结果已保存到: {filename}")
            else:
                print("未找到相关仓库")
                
        elif choice == '2':
            print("\n选择趋势仓库:")
            print("1. 每日趋势")
            print("2. 每周趋势")
            print("3. 每月趋势")
            
            trend_choice = input("请选择 (1-3): ").strip()
            since_map = {'1': 'daily', '2': 'weekly', '3': 'monthly'}
            since = since_map.get(trend_choice, 'daily')
            
            language = input("编程语言 (留空获取所有语言): ").strip()
            
            print(f"\n正在获取GitHub趋势仓库...")
            trending_repos = crawler.get_trending_repos(language, since)
            
            if trending_repos:
                print(f"\nGitHub趋势仓库 ({since}):")
                for i, repo in enumerate(trending_repos[:15], 1):
                    name = repo.get('full_name', '未知仓库')
                    stars = repo.get('stargazers_count', 0)
                    today_stars = repo.get('today_stars', 0)
                    language = repo.get('language', '未知')
                    
                    print(f"{i}. {name}")
                    print(f"   描述: {repo.get('description', '无描述')[:60]}...")
                    print(f"   语言: {language} | 总星标: {stars:,} | 今日增长: {today_stars:,}")
                    print()
                
                # 保存趋势数据
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'github_trending_{since}_{language or "all"}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(trending_repos, f, ensure_ascii=False, indent=2)
                print(f"趋势数据已保存到: {filename}")
            else:
                print("未获取到趋势仓库")
                
        elif choice == '3':
            repo_input = input("请输入仓库全名 (例如: octocat/Hello-World): ").strip()
            if '/' in repo_input:
                owner, repo_name = repo_input.split('/', 1)
                
                print(f"\n正在获取仓库详情: {owner}/{repo_name}")
                details = crawler.get_repository_details(owner, repo_name)
                
                if details:
                    print(f"\n=== 仓库详情: {details.get('full_name')} ===")
                    print(f"描述: {details.get('description', '无描述')}")
                    print(f"创建时间: {details.get('created_at')}")
                    print(f"更新时间: {details.get('updated_at')}")
                    print(f"星标: {details.get('stargazers_count', 0):,}")
                    print(f"Fork: {details.get('forks_count', 0):,}")
                    print(f"问题数: {details.get('open_issues_count', 0)}")
                    print(f"语言: {details.get('language', '未知')}")
                    
                    if 'license' in details and details['license']:
                        print(f"许可证: {details['license']}")
                    
                    if 'topics' in details and details['topics']:
                        print(f"主题: {', '.join(details['topics'][:10])}")
                    
                    if 'languages' in details:
                        print(f"\n语言使用情况:")
                        for lang, percent in list(details['languages'].items())[:5]:
                            print(f"  {lang}: {percent:.1f}%")
                    
                    if 'contributors' in details:
                        print(f"\n主要贡献者:")
                        for contributor in details['contributors'][:5]:
                            print(f"  {contributor.get('login')}: {contributor.get('contributions')}次贡献")
                    
                    # 保存详情
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'github_repo_{owner}_{repo_name}_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(details, f, ensure_ascii=False, indent=2)
                    print(f"\n详情已保存到: {filename}")
                else:
                    print("获取仓库详情失败")
            else:
                print("请输入正确的仓库格式: owner/repo")
                
        elif choice == '4':
            username = input("请输入GitHub用户名: ").strip()
            if username:
                print(f"\n正在获取用户信息: {username}")
                user_info = crawler.get_user_info(username)
                
                if user_info:
                    print(f"\n=== 用户信息: {user_info.get('login')} ===")
                    print(f"名称: {user_info.get('name', '未设置')}")
                    print(f"简介: {user_info.get('bio', '未设置')}")
                    print(f"公司: {user_info.get('company', '未设置')}")
                    print(f"位置: {user_info.get('location', '未设置')}")
                    print(f"博客: {user_info.get('blog', '未设置')}")
                    print(f"邮箱: {user_info.get('email', '未设置')}")
                    print(f"关注者: {user_info.get('followers', 0):,}")
                    print(f"正在关注: {user_info.get('following', 0):,}")
                    print(f"公开仓库: {user_info.get('public_repos', 0)}")
                    print(f"创建时间: {user_info.get('created_at')}")
                    
                    if 'repositories' in user_info:
                        print(f"\n最近更新的仓库:")
                        for repo in user_info['repositories'][:5]:
                            print(f"  {repo.get('name')}: {repo.get('stargazers_count', 0)}星标")
                    
                    # 保存用户信息
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'github_user_{username}_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(user_info, f, ensure_ascii=False, indent=2)
                    print(f"\n用户信息已保存到: {filename}")
                else:
                    print("获取用户信息失败")
            else:
                print("用户名不能为空")
                
        elif choice == '5':
            # 先搜索一些仓库进行分析
            query = input("请输入搜索关键词 (例如: python, 默认python): ").strip() or 'python'
            
            print(f"\n正在获取 {query} 相关仓库进行分析...")
            repositories = crawler.search_repositories(query, per_page=50)
            
            if repositories:
                analysis = crawler.analyze_repositories(repositories)
                
                print(f"\n=== 仓库数据分析 ===")
                print(f"总仓库数: {analysis['total_repos']}")
                
                if analysis['language_stats']:
                    print(f"\n语言分布 (前5):")
                    sorted_langs = sorted(
                        analysis['language_stats'].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    for lang, count in sorted_langs[:5]:
                        percent = (count / analysis['total_repos']) * 100
                        print(f"  {lang}: {count}个 ({percent:.1f}%)")
                
                if 'stars_stats' in analysis:
                    print(f"\n星标统计:")
                    print(f"  平均星标: {analysis['stars_stats'].get('average', 0):.1f}")
                    print(f"  最高星标: {analysis['stars_stats'].get('max', 0):,}")
                    print(f"  总星标数: {analysis['stars_stats'].get('total', 0):,}")
                
                if analysis['top_repositories']:
                    print(f"\n热门仓库 (按星标):")
                    for repo in analysis['top_repositories'][:5]:
                        name = repo.get('full_name', '未知')
                        stars = repo.get('stargazers_count', 0)
                        print(f"  {name}: {stars:,}星标")
                
                # 保存分析结果
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'github_analysis_{query}_{timestamp}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                print(f"\n分析结果已保存到: {filename}")
            else:
                print("无仓库数据可分析")
                
        elif choice == '6':
            print("退出程序")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()