#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub数据爬虫 - 获取GitHub仓库和用户信息
网站：GitHub (https://github.com)
功能：获取仓库信息、用户信息、趋势项目、issue等
"""

import requests
import json
import time
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubCrawler:
    """GitHub数据爬虫类"""
    
    def __init__(self, timeout: int = 10, github_token: str = None, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            github_token: GitHub API令牌（可选，提高速率限制）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "https://api.github.com"
        self.github_token = github_token
        
        # 设置请求头
        headers = {
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/vnd.github.v3+json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # 如果有GitHub令牌，添加到请求头
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        self.session.headers.update(headers)
        
        # 速率限制跟踪
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        
    def _check_rate_limit(self, response: requests.Response = None) -> None:
        """
        检查速率限制
        
        Args:
            response: 响应对象（用于提取速率限制头信息）
        """
        if response:
            # 从响应头中获取速率限制信息
            self.rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            self.rate_limit_reset = response.headers.get('X-RateLimit-Reset')
            
            if self.rate_limit_remaining and int(self.rate_limit_remaining) < 10:
                logger.warning(f"GitHub API 速率限制剩余: {self.rate_limit_remaining}")
                
                if self.rate_limit_reset:
                    reset_time = datetime.fromtimestamp(int(self.rate_limit_reset))
                    logger.warning(f"速率限制重置时间: {reset_time}")
    
    def _make_request(self, endpoint: str, params: Dict = None, method: str = 'GET') -> Optional[Dict]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 查询参数
            method: HTTP方法
            
        Returns:
            JSON响应数据，失败则返回None
        """
        try:
            url = urljoin(self.base_url, endpoint)
            
            logger.debug(f"发送请求: {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            else:
                response = self.session.request(method, url, json=params, timeout=self.timeout)
            
            response.raise_for_status()
            
            # 检查速率限制
            self._check_rate_limit(response)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"API请求时发生未知错误: {str(e)}")
            return None
    
    def get_repository(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            仓库信息字典，失败则返回None
        """
        try:
            endpoint = f"/repos/{owner}/{repo}"
            logger.info(f"正在获取仓库: {owner}/{repo}")
            
            data = self._make_request(endpoint)
            
            if data:
                # 格式化仓库信息
                repo_info = {
                    'id': data.get('id'),
                    'full_name': data.get('full_name'),
                    'name': data.get('name'),
                    'owner': data.get('owner', {}).get('login'),
                    'description': data.get('description'),
                    'html_url': data.get('html_url'),
                    'clone_url': data.get('clone_url'),
                    'ssh_url': data.get('ssh_url'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'pushed_at': data.get('pushed_at'),
                    'size': data.get('size'),
                    'stargazers_count': data.get('stargazers_count'),
                    'watchers_count': data.get('watchers_count'),
                    'forks_count': data.get('forks_count'),
                    'open_issues_count': data.get('open_issues_count'),
                    'license': data.get('license', {}).get('name') if data.get('license') else None,
                    'language': data.get('language'),
                    'topics': data.get('topics', []),
                    'default_branch': data.get('default_branch'),
                    'homepage': data.get('homepage'),
                    'archived': data.get('archived'),
                    'disabled': data.get('disabled'),
                    'private': data.get('private'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'GitHub API',
                }
                
                logger.info(f"成功获取仓库: {owner}/{repo}")
                return repo_info
            else:
                logger.warning(f"无法获取仓库: {owner}/{repo}")
                return None
                
        except Exception as e:
            logger.error(f"获取仓库信息时发生错误: {str(e)}")
            return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            username: GitHub用户名
            
        Returns:
            用户信息字典，失败则返回None
        """
        try:
            endpoint = f"/users/{username}"
            logger.info(f"正在获取用户: {username}")
            
            data = self._make_request(endpoint)
            
            if data:
                # 格式化用户信息
                user_info = {
                    'id': data.get('id'),
                    'login': data.get('login'),
                    'name': data.get('name'),
                    'company': data.get('company'),
                    'blog': data.get('blog'),
                    'location': data.get('location'),
                    'email': data.get('email'),
                    'bio': data.get('bio'),
                    'twitter_username': data.get('twitter_username'),
                    'public_repos': data.get('public_repos'),
                    'public_gists': data.get('public_gists'),
                    'followers': data.get('followers'),
                    'following': data.get('following'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'avatar_url': data.get('avatar_url'),
                    'html_url': data.get('html_url'),
                    'type': data.get('type'),  # User or Organization
                    'site_admin': data.get('site_admin'),
                    'hireable': data.get('hireable'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'GitHub API',
                }
                
                logger.info(f"成功获取用户: {username}")
                return user_info
            else:
                logger.warning(f"无法获取用户: {username}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息时发生错误: {str(e)}")
            return None
    
    def get_repository_readme(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库README内容
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            README信息字典，失败则返回None
        """
        try:
            endpoint = f"/repos/{owner}/{repo}/readme"
            logger.info(f"正在获取README: {owner}/{repo}")
            
            data = self._make_request(endpoint)
            
            if data and data.get('content'):
                # 解码base64内容
                content_encoded = data.get('content', '')
                content_decoded = base64.b64decode(content_encoded).decode('utf-8')
                
                readme_info = {
                    'name': data.get('name'),
                    'path': data.get('path'),
                    'sha': data.get('sha'),
                    'size': data.get('size'),
                    'url': data.get('url'),
                    'html_url': data.get('html_url'),
                    'download_url': data.get('download_url'),
                    'type': data.get('type'),
                    'encoding': data.get('encoding'),
                    'content': content_decoded,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'GitHub API',
                }
                
                logger.info(f"成功获取README: {owner}/{repo}")
                return readme_info
            else:
                logger.warning(f"无法获取README: {owner}/{repo}")
                return None
                
        except Exception as e:
            logger.error(f"获取README时发生错误: {str(e)}")
            return None
    
    def get_repository_issues(self, owner: str, repo: str, state: str = 'open', limit: int = 10) -> List[Dict]:
        """
        获取仓库issues
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: issue状态（open, closed, all）
            limit: 返回数量限制
            
        Returns:
            issue列表
        """
        try:
            endpoint = f"/repos/{owner}/{repo}/issues"
            params = {
                'state': state,
                'per_page': min(limit, 100),  # GitHub API每页最多100条
                'page': 1,
            }
            
            logger.info(f"正在获取issues: {owner}/{repo} (状态: {state})")
            
            data = self._make_request(endpoint, params)
            
            if data:
                issues = []
                for issue in data[:limit]:
                    # 提取issue信息
                    issue_info = {
                        'id': issue.get('id'),
                        'number': issue.get('number'),
                        'title': issue.get('title'),
                        'state': issue.get('state'),
                        'created_at': issue.get('created_at'),
                        'updated_at': issue.get('updated_at'),
                        'closed_at': issue.get('closed_at'),
                        'body': issue.get('body'),
                        'user': issue.get('user', {}).get('login'),
                        'labels': [label.get('name') for label in issue.get('labels', [])],
                        'assignees': [assignee.get('login') for assignee in issue.get('assignees', [])],
                        'comments': issue.get('comments'),
                        'html_url': issue.get('html_url'),
                        'pull_request': 'pull_request' in issue,  # 是否是PR
                        'locked': issue.get('locked'),
                        'milestone': issue.get('milestone', {}).get('title') if issue.get('milestone') else None,
                    }
                    issues.append(issue_info)
                
                logger.info(f"成功获取 {len(issues)} 个issues")
                return issues
            else:
                logger.warning(f"无法获取issues: {owner}/{repo}")
                return []
                
        except Exception as e:
            logger.error(f"获取issues时发生错误: {str(e)}")
            return []
    
    def get_repository_contributors(self, owner: str, repo: str, limit: int = 20) -> List[Dict]:
        """
        获取仓库贡献者
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            limit: 返回数量限制
            
        Returns:
            贡献者列表
        """
        try:
            endpoint = f"/repos/{owner}/{repo}/contributors"
            params = {
                'per_page': min(limit, 100),
                'page': 1,
            }
            
            logger.info(f"正在获取贡献者: {owner}/{repo}")
            
            data = self._make_request(endpoint, params)
            
            if data:
                contributors = []
                for contributor in data[:limit]:
                    contributor_info = {
                        'login': contributor.get('login'),
                        'id': contributor.get('id'),
                        'avatar_url': contributor.get('avatar_url'),
                        'html_url': contributor.get('html_url'),
                        'type': contributor.get('type'),
                        'contributions': contributor.get('contributions'),
                    }
                    contributors.append(contributor_info)
                
                logger.info(f"成功获取 {len(contributors)} 个贡献者")
                return contributors
            else:
                logger.warning(f"无法获取贡献者: {owner}/{repo}")
                return []
                
        except Exception as e:
            logger.error(f"获取贡献者时发生错误: {str(e)}")
            return []
    
    def search_repositories(self, query: str, sort: str = 'stars', order: str = 'desc', limit: int = 10) -> List[Dict]:
        """
        搜索仓库
        
        Args:
            query: 搜索查询
            sort: 排序方式（stars, forks, updated）
            order: 排序顺序（asc, desc）
            limit: 返回数量限制
            
        Returns:
            仓库列表
        """
        try:
            endpoint = "/search/repositories"
            params = {
                'q': query,
                'sort': sort,
                'order': order,
                'per_page': min(limit, 100),
                'page': 1,
            }
            
            logger.info(f"正在搜索仓库: {query}")
            
            data = self._make_request(endpoint, params)
            
            if data and 'items' in data:
                repositories = []
                for repo in data['items'][:limit]:
                    repo_info = {
                        'id': repo.get('id'),
                        'full_name': repo.get('full_name'),
                        'name': repo.get('name'),
                        'owner': repo.get('owner', {}).get('login'),
                        'description': repo.get('description'),
                        'html_url': repo.get('html_url'),
                        'stargazers_count': repo.get('stargazers_count'),
                        'forks_count': repo.get('forks_count'),
                        'open_issues_count': repo.get('open_issues_count'),
                        'language': repo.get('language'),
                        'created_at': repo.get('created_at'),
                        'updated_at': repo.get('updated_at'),
                        'score': repo.get('score'),  # GitHub的搜索评分
                    }
                    repositories.append(repo_info)
                
                logger.info(f"搜索到 {len(repositories)} 个仓库")
                return repositories
            else:
                logger.warning(f"搜索仓库失败: {query}")
                return []
                
        except Exception as e:
            logger.error(f"搜索仓库时发生错误: {str(e)}")
            return []
    
    def get_trending_repositories(self, language: str = None, since: str = 'daily') -> List[Dict]:
        """
        获取趋势仓库（通过GitHub Trending页面）
        
        Args:
            language: 编程语言过滤（如：python, javascript）
            since: 时间范围（daily, weekly, monthly）
            
        Returns:
            趋势仓库列表
        """
        # 注意：GitHub Trending没有官方API，这里使用简化实现
        # 实际实现需要解析HTML页面
        logger.info(f"获取趋势仓库功能待实现 (语言: {language}, 时间: {since})")
        return []
    
    def get_repository_languages(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库使用的编程语言统计
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            语言统计字典，失败则返回None
        """
        try:
            endpoint = f"/repos/{owner}/{repo}/languages"
            logger.info(f"正在获取语言统计: {owner}/{repo}")
            
            data = self._make_request(endpoint)
            
            if data:
                # 计算百分比
                total_bytes = sum(data.values())
                languages = {}
                
                for lang, bytes_count in data.items():
                    percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                    languages[lang] = {
                        'bytes': bytes_count,
                        'percentage': round(percentage, 2)
                    }
                
                logger.info(f"成功获取语言统计: {owner}/{repo}")
                return languages
            else:
                logger.warning(f"无法获取语言统计: {owner}/{repo}")
                return None
                
        except Exception as e:
            logger.error(f"获取语言统计时发生错误: {str(e)}")
            return None
    
    def save_to_json(self, data: Dict, filename: str = None) -> bool:
        """
        将数据保存为JSON文件
        
        Args:
            data: 数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not data:
                logger.warning("没有数据可保存")
                return False
            
            if filename is None:
                # 根据数据类型生成文件名
                if 'full_name' in data:  # 仓库数据
                    name = data['full_name'].replace('/', '_')
                    prefix = 'repo'
                elif 'login' in data:  # 用户数据
                    name = data['login']
                    prefix = 'user'
                elif 'name' in data and 'path' in data:  # README数据
                    name = data['name'].replace('.', '_')
                    prefix = 'readme'
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"github_{timestamp}.json"
                
                if 'filename' not in locals():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{prefix}_{name}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def get_rate_limit_info(self) -> Optional[Dict]:
        """
        获取当前API速率限制信息
        
        Returns:
            速率限制信息字典
        """
        try:
            endpoint = "/rate_limit"
            logger.info("正在获取速率限制信息")
            
            data = self._make_request(endpoint)
            
            if data and 'resources' in data:
                rate_info = {
                    'core': data['resources'].get('core', {}),
                    'search': data['resources'].get('search', {}),
                    'graphql': data['resources'].get('graphql', {}),
                    'timestamp': datetime.now().isoformat(),
                }
                return rate_info
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取速率限制信息时发生错误: {str(e)}")
            return None


def main():
    """主函数，演示爬虫的使用"""
    print("GitHub数据爬虫演示")
    print("=" * 50)
    
    # 创建爬虫实例（可以传入GitHub令牌提高速率限制）
    # crawler = GitHubCrawler(timeout=15, github_token="your_github_token_here")
    crawler = GitHubCrawler(timeout=15)
    
    # 检查速率限制
    print("检查API速率限制...")
    rate_info = crawler.get_rate_limit_info()
    if rate_info:
        core_limit = rate_info['core']
        print(f"核心API限制: {core_limit.get('remaining', '未知')}/{core_limit.get('limit', '未知')}")
        print(f"重置时间: {datetime.fromtimestamp(core_limit.get('reset', 0))}")
    
    # 获取热门仓库信息
    print("\n" + "=" * 50)
    print("获取热门仓库信息...")
    
    # 获取facebook/react仓库信息
    repo_owner = "facebook"
    repo_name = "react"
    
    print(f"\n获取仓库: {repo_owner}/{repo_name}")
    repo_info = crawler.get_repository(repo_owner, repo_name)
    
    if repo_info:
        print(f"仓库名称: {repo_info['full_name']}")
        print(f"描述: {repo_info.get('description', '无描述')}")
        print(f"星标数: {repo_info.get('stargazers_count', 0):,}")
        print(f"Forks数: {repo_info.get('forks_count', 0):,}")
        print(f"问题数: {repo_info.get('open_issues_count', 0):,}")
        print(f"主要语言: {repo_info.get('language', '未知')}")
        print(f"创建时间: {repo_info.get('created_at', '未知')}")
        
        # 保存仓库信息
        crawler.save_to_json(repo_info)
        print(f"\n仓库信息已保存到JSON文件")
        
        # 获取README
        print(f"\n获取README...")
        readme_info = crawler.get_repository_readme(repo_owner, repo_name)
        if readme_info:
            content_preview = readme_info['content'][:200] + "..." if len(readme_info['content']) > 200 else readme_info['content']
            print(f"README预览: {content_preview}")
        
        # 获取贡献者
        print(f"\n获取前5位贡献者...")
        contributors = crawler.get_repository_contributors(repo_owner, repo_name, limit=5)
        if contributors:
            print("主要贡献者:")
            for i, contributor in enumerate(contributors, 1):
                print(f"  {i}. {contributor['login']} - {contributor['contributions']} 次贡献")
        
        # 获取语言统计
        print(f"\n获取语言使用统计...")
        languages = crawler.get_repository_languages(repo_owner, repo_name)
        if languages:
            print("语言使用情况:")
            for lang, stats in list(languages.items())[:5]:  # 只显示前5种语言
                print(f"  {lang}: {stats['percentage']}%")
    else:
        print(f"无法获取仓库 {repo_owner}/{repo_name} 的信息")
    
    # 搜索仓库
    print("\n" + "=" * 50)
    print("搜索Python机器学习仓库...")
    search_query = "machine learning language:python"
    search_results = crawler.search_repositories(search_query, limit=5)
    
    if search_results:
        print(f"找到 {len(search_results)} 个相关仓库:")
        for i, repo in enumerate(search_results, 1):
            print(f"{i}. {repo['full_name']} - {repo.get('description', '无描述')[:50]}...")
            print(f"   星标: {repo.get('stargazers_count', 0):,}  Forks: {repo.get('forks_count', 0):,}")
    
    # 获取用户信息
    print("\n" + "=" * 50)
    print("获取GitHub用户信息...")
    username = "torvalds"  # Linux创始人
    user_info = crawler.get_user(username)
    
    if user_info:
        print(f"用户名: {user_info['login']}")
        print(f"姓名: {user_info.get('name', '未知')}")
        print(f"公司: {user_info.get('company', '未知')}")
        print(f"位置: {user_info.get('location', '未知')}")
        print(f"公开仓库数: {user_info.get('public_repos', 0)}")
        print(f"关注者: {user_info.get('followers', 0):,}")
        print(f"关注: {user_info.get('following', 0)}")
        print(f"创建时间: {user_info.get('created_at', '未知')}")
    
    print("\n爬虫演示完成！")


if __name__ == "__main__":
    main()