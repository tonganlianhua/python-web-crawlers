#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术博客爬虫 - 获取技术博客文章
网站：多个技术博客（CSDN、博客园、掘金等）
功能：获取技术文章、作者信息、阅读量、标签等
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urljoin, quote, urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TechBlogCrawler:
    """技术博客爬虫类"""
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义User-Agent
        """
        self.timeout = timeout
        self.session = requests.Session()
        
        # 设置请求头
        self.headers = {
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session.headers.update(self.headers)
        
        # 支持的博客平台配置
        self.platforms = {
            'csdn': {
                'name': 'CSDN博客',
                'base_url': 'https://blog.csdn.net',
                'search_url': 'https://so.csdn.net/so/search',
                'article_patterns': [
                    r'^https://blog\.csdn\.net/[^/]+/article/details/\d+',
                    r'^https://blog\.csdn\.net/[^/]+/category_\d+\.html',
                ]
            },
            'cnblogs': {
                'name': '博客园',
                'base_url': 'https://www.cnblogs.com',
                'search_url': 'https://zzk.cnblogs.com/s',
                'article_patterns': [
                    r'^https://www\.cnblogs\.com/[^/]+/p/\d+\.html',
                ]
            },
            'juejin': {
                'name': '掘金',
                'base_url': 'https://juejin.cn',
                'search_url': 'https://juejin.cn/search',
                'article_patterns': [
                    r'^https://juejin\.cn/post/\d+',
                ]
            },
            'segmentfault': {
                'name': 'SegmentFault',
                'base_url': 'https://segmentfault.com',
                'search_url': 'https://segmentfault.com/search',
                'article_patterns': [
                    r'^https://segmentfault\.com/a/\d+',
                ]
            },
            'infoq': {
                'name': 'InfoQ',
                'base_url': 'https://www.infoq.cn',
                'search_url': 'https://www.infoq.cn/search',
                'article_patterns': [
                    r'^https://www\.infoq\.cn/article/\w+',
                ]
            }
        }
    
    def detect_platform(self, url: str) -> Optional[str]:
        """
        检测URL属于哪个博客平台
        
        Args:
            url: 博客文章URL
            
        Returns:
            平台名称，如果无法识别则返回None
        """
        for platform, config in self.platforms.items():
            for pattern in config.get('article_patterns', []):
                if re.match(pattern, url):
                    return platform
        
        # 尝试通过域名匹配
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'csdn' in domain:
            return 'csdn'
        elif 'cnblogs' in domain:
            return 'cnblogs'
        elif 'juejin' in domain:
            return 'juejin'
        elif 'segmentfault' in domain:
            return 'segmentfault'
        elif 'infoq' in domain:
            return 'infoq'
        
        return None
    
    def fetch_article(self, url: str) -> Optional[Dict]:
        """
        获取博客文章内容
        
        Args:
            url: 文章URL
            
        Returns:
            文章信息字典，失败则返回None
        """
        try:
            platform = self.detect_platform(url)
            if not platform:
                logger.warning(f"无法识别的博客平台: {url}")
                return None
            
            logger.info(f"正在获取 {self.platforms[platform]['name']} 文章: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 根据平台调用不同的解析方法
            if platform == 'csdn':
                article_data = self._parse_csdn_article(soup, url)
            elif platform == 'cnblogs':
                article_data = self._parse_cnblogs_article(soup, url)
            elif platform == 'juejin':
                article_data = self._parse_juejin_article(soup, url)
            elif platform == 'segmentfault':
                article_data = self._parse_segmentfault_article(soup, url)
            elif platform == 'infoq':
                article_data = self._parse_infoq_article(soup, url)
            else:
                article_data = self._parse_generic_article(soup, url)
            
            if article_data:
                article_data['platform'] = platform
                article_data['platform_name'] = self.platforms[platform]['name']
                article_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"成功获取文章: {article_data.get('title', '未知标题')}")
                return article_data
            else:
                logger.warning(f"解析文章失败: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取文章时发生未知错误: {str(e)}")
            return None
    
    def _parse_csdn_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析CSDN文章"""
        article_data = {
            'url': url,
            'source': 'CSDN博客',
        }
        
        try:
            # 标题
            title_tag = soup.find('h1', class_='title-article')
            if not title_tag:
                title_tag = soup.find('h1', id='articleContentId')
            if title_tag:
                article_data['title'] = title_tag.get_text(strip=True)
            
            # 作者
            author_tag = soup.find('a', class_='follow-nickName')
            if not author_tag:
                author_tag = soup.find('div', class_='profile-box').find('a') if soup.find('div', class_='profile-box') else None
            if author_tag:
                article_data['author'] = author_tag.get_text(strip=True)
                article_data['author_url'] = urljoin(url, author_tag.get('href', ''))
            
            # 发布时间
            time_tag = soup.find('span', class_='time')
            if not time_tag:
                time_tag = soup.find('div', class_='bar-content').find('span') if soup.find('div', class_='bar-content') else None
            if time_tag:
                article_data['publish_time'] = time_tag.get_text(strip=True)
            
            # 阅读量
            read_tag = soup.find('span', class_='read-count')
            if read_tag:
                read_text = read_tag.get_text(strip=True)
                match = re.search(r'(\d+)', read_text)
                if match:
                    article_data['read_count'] = int(match.group(1))
            
            # 点赞数
            like_tag = soup.find('span', class_='get-collection')
            if like_tag:
                like_text = like_tag.get_text(strip=True)
                match = re.search(r'(\d+)', like_text)
                if match:
                    article_data['like_count'] = int(match.group(1))
            
            # 评论数
            comment_tag = soup.find('span', class_='get-comment')
            if comment_tag:
                comment_text = comment_tag.get_text(strip=True)
                match = re.search(r'(\d+)', comment_text)
                if match:
                    article_data['comment_count'] = int(match.group(1))
            
            # 文章内容
            content_tag = soup.find('article')
            if not content_tag:
                content_tag = soup.find('div', id='content_views')
            if content_tag:
                # 提取文本内容
                content_text = content_tag.get_text(strip=True)
                # 清理多余空白
                content_text = re.sub(r'\s+', ' ', content_text)
                article_data['content'] = content_text[:5000]  # 限制长度
                
                # 提取HTML内容（如果需要保留格式）
                article_data['content_html'] = str(content_tag)
            
            # 标签
            tags = []
            tags_div = soup.find('div', class_='tags-box')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                article_data['tags'] = tags
            
            # 分类
            category_tag = soup.find('div', class_='category-link')
            if category_tag:
                article_data['category'] = category_tag.get_text(strip=True)
            
        except Exception as e:
            logger.error(f"解析CSDN文章时发生错误: {str(e)}")
        
        return article_data
    
    def _parse_cnblogs_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析博客园文章"""
        article_data = {
            'url': url,
            'source': '博客园',
        }
        
        try:
            # 标题
            title_tag = soup.find('a', id='cb_post_title_url')
            if title_tag:
                article_data['title'] = title_tag.get_text(strip=True)
            
            # 作者
            author_tag = soup.find('a', id='blogger')
            if author_tag:
                article_data['author'] = author_tag.get_text(strip=True)
                article_data['author_url'] = urljoin(url, author_tag.get('href', ''))
            
            # 发布时间
            time_tag = soup.find('span', id='post-date')
            if time_tag:
                article_data['publish_time'] = time_tag.get_text(strip=True)
            
            # 阅读量
            read_tag = soup.find('span', id='post_view_count')
            if read_tag:
                article_data['read_count'] = int(read_tag.get_text(strip=True))
            
            # 评论数
            comment_tag = soup.find('span', id='post_comment_count')
            if comment_tag:
                article_data['comment_count'] = int(comment_tag.get_text(strip=True))
            
            # 文章内容
            content_tag = soup.find('div', id='cnblogs_post_body')
            if content_tag:
                content_text = content_tag.get_text(strip=True)
                content_text = re.sub(r'\s+', ' ', content_text)
                article_data['content'] = content_text[:5000]
                article_data['content_html'] = str(content_tag)
            
            # 标签
            tags = []
            tags_div = soup.find('div', id='blog_post_info_tags')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                article_data['tags'] = tags
            
        except Exception as e:
            logger.error(f"解析博客园文章时发生错误: {str(e)}")
        
        return article_data
    
    def _parse_juejin_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析掘金文章"""
        article_data = {
            'url': url,
            'source': '掘金',
        }
        
        try:
            # 标题
            title_tag = soup.find('h1', class_='article-title')
            if title_tag:
                article_data['title'] = title_tag.get_text(strip=True)
            
            # 作者
            author_tag = soup.find('a', class_='username')
            if author_tag:
                article_data['author'] = author_tag.get_text(strip=True)
                article_data['author_url'] = urljoin(url, author_tag.get('href', ''))
            
            # 发布时间
            time_tag = soup.find('time')
            if time_tag:
                article_data['publish_time'] = time_tag.get_text(strip=True)
            
            # 点赞数
            like_tag = soup.find('span', class_='like-count')
            if like_tag:
                like_text = like_tag.get_text(strip=True)
                match = re.search(r'(\d+)', like_text)
                if match:
                    article_data['like_count'] = int(match.group(1))
            
            # 文章内容
            content_tag = soup.find('article')
            if content_tag:
                content_text = content_tag.get_text(strip=True)
                content_text = re.sub(r'\s+', ' ', content_text)
                article_data['content'] = content_text[:5000]
                article_data['content_html'] = str(content_tag)
            
            # 标签
            tags = []
            tags_div = soup.find('div', class_='tag-list')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                article_data['tags'] = tags
            
        except Exception as e:
            logger.error(f"解析掘金文章时发生错误: {str(e)}")
        
        return article_data
    
    def _parse_segmentfault_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析SegmentFault文章"""
        article_data = {
            'url': url,
            'source': 'SegmentFault',
        }
        
        try:
            # 标题
            title_tag = soup.find('h1', id='articleTitle')
            if title_tag:
                article_data['title'] = title_tag.get_text(strip=True)
            
            # 作者
            author_tag = soup.find('a', class_='user-info__name')
            if author_tag:
                article_data['author'] = author_tag.get_text(strip=True)
                article_data['author_url'] = urljoin(url, author_tag.get('href', ''))
            
            # 发布时间
            time_tag = soup.find('time')
            if time_tag:
                article_data['publish_time'] = time_tag.get('datetime', time_tag.get_text(strip=True))
            
            # 阅读量
            read_tag = soup.find('span', class_='text-muted')
            if read_tag and '阅读' in read_tag.get_text():
                read_text = read_tag.get_text(strip=True)
                match = re.search(r'(\d+)', read_text)
                if match:
                    article_data['read_count'] = int(match.group(1))
            
            # 文章内容
            content_tag = soup.find('article')
            if not content_tag:
                content_tag = soup.find('div', class_='article__content')
            if content_tag:
                content_text = content_tag.get_text(strip=True)
                content_text = re.sub(r'\s+', ' ', content_text)
                article_data['content'] = content_text[:5000]
                article_data['content_html'] = str(content_tag)
            
            # 标签
            tags = []
            tags_div = soup.find('ul', class_='taglist--inline')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                article_data['tags'] = tags
            
        except Exception as e:
            logger.error(f"解析SegmentFault文章时发生错误: {str(e)}")
        
        return article_data
    
    def _parse_infoq_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析InfoQ文章"""
        article_data = {
            'url': url,
            'source': 'InfoQ',
        }
        
        try:
            # 标题
            title_tag = soup.find('h1', class_='article-title')
            if title_tag:
                article_data['title'] = title_tag.get_text(strip=True)
            
            # 作者
            author_tag = soup.find('a', class_='user-link')
            if author_tag:
                article_data['author'] = author_tag.get_text(strip=True)
                article_data['author_url'] = urljoin(url, author_tag.get('href', ''))
            
            # 发布时间
            time_tag = soup.find('time')
            if time_tag:
                article_data['publish_time'] = time_tag.get('datetime', time_tag.get_text(strip=True))
            
            # 文章内容
            content_tag = soup.find('div', class_='article-content')
            if content_tag:
                content_text = content_tag.get_text(strip=True)
                content_text = re.sub(r'\s+', ' ', content_text)
                article_data['content'] = content_text[:5000]
                article_data['content_html'] = str(content_tag)
            
            # 标签
            tags = []
            tags_div = soup.find('div', class_='article-tag')
            if tags_div:
                tag_links = tags_div.find_all('a')
                for tag in tag_links:
                    tags.append(tag.get_text(strip=True))
            if tags:
                article_data['tags'] = tags
            
        except Exception as e:
            logger.error(f"解析InfoQ文章时发生错误: {str(e)}")
        
        return article_data
    
    def _parse_generic_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """通用文章解析方法"""
        article_data = {
            'url': url,
            'source': '未知博客平台',
        }
        
        try:
            # 尝试查找标题（常见的选择器）
            title_selectors = ['h1', 'h2', '.post-title', '.article-title', '.entry-title', '.title']
            for selector in title_selectors:
                title_tag = soup.find(selector)
                if title_tag:
                    article_data['title'] = title_tag.get_text(strip=True)
                    break
            
            # 尝试查找作者
            author_selectors = ['.author', '.post-author', '.article-author', '.byline']
            for selector in author_selectors:
                author_tag = soup.find(class_=selector)
                if author_tag:
                    article_data['author'] = author_tag.get_text(strip=True)
                    # 尝试获取作者链接
                    author_link = author_tag.find('a')
                    if author_link:
                        article_data['author_url'] = urljoin(url, author_link.get('href', ''))
                    break
            
            # 尝试查找发布时间
            time_selectors = ['time', '.post-date', '.article-date', '.published', '.date']
            for selector in time_selectors:
                time_tag = soup.find(selector)
                if time_tag:
                    article_data['publish_time'] = time_tag.get_text(strip=True)
                    # 尝试获取datetime属性
                    if time_tag.get('datetime'):
                        article_data['publish_time'] = time_tag.get('datetime')
                    break
            
            # 尝试查找文章内容
            content_selectors = ['article', '.post-content', '.article-content', '.entry-content', '.content']
            for selector in content_selectors:
                content_tag = soup.find(selector)
                if content_tag:
                    content_text = content_tag.get_text(strip=True)
                    content_text = re.sub(r'\s+', ' ', content_text)
                    article_data['content'] = content_text[:5000]
                    article_data['content_html'] = str(content_tag)
                    break
            
            # 尝试查找标签
            tags = []
            tags_selectors = ['.tags', '.post-tags', '.article-tags', '.tag-list']
            for selector in tags_selectors:
                tags_div = soup.find(class_=selector)
                if tags_div:
                    tag_links = tags_div.find_all('a')
                    for tag in tag_links:
                        tags.append(tag.get_text(strip=True))
                    if tags:
                        article_data['tags'] = tags
                    break
            
        except Exception as e:
            logger.error(f"通用解析时发生错误: {str(e)}")
        
        return article_data
    
    def search_articles(self, query: str, platform: str = 'csdn', limit: int = 10) -> List[Dict]:
        """
        搜索文章
        
        Args:
            query: 搜索关键词
            platform: 平台名称
            limit: 返回文章数量限制
            
        Returns:
            文章列表
        """
        if platform not in self.platforms:
            logger.error(f"不支持的平台: {platform}")
            return []
        
        # 注意：实际搜索实现需要解析各个平台的搜索结果页
        # 这里简化处理，返回空列表
        logger.info(f"搜索 {self.platforms[platform]['name']} 文章: {query}")
        logger.warning("搜索功能需要针对各平台单独实现")
        return []
    
    def get_popular_articles(self, platform: str = 'csdn', category: str = None, limit: int = 10) -> List[Dict]:
        """
        获取热门文章
        
        Args:
            platform: 平台名称
            category: 分类（可选）
            limit: 返回文章数量限制
            
        Returns:
            文章列表
        """
        # 注意：实际实现需要解析各个平台的热门页面
        logger.info(f"获取 {self.platforms[platform]['name']} 热门文章")
        logger.warning("热门文章功能需要针对各平台单独实现")
        return []
    
    def save_to_json(self, article_data: Dict, filename: str = None) -> bool:
        """
        将文章数据保存为JSON文件
        
        Args:
            article_data: 文章数据字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存成功返回True，失败返回False
        """
        try:
            if not article_data:
                logger.warning("没有文章数据可保存")
                return False
            
            if filename is None:
                title = article_data.get('title', 'unknown').replace('/', '_').replace('\\', '_')
                platform = article_data.get('platform', 'unknown')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"article_{platform}_{title[:50]}_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"文章数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {str(e)}")
            return False
    
    def fetch_multiple_articles(self, urls: List[str]) -> List[Dict]:
        """
        批量获取多篇文章
        
        Args:
            urls: 文章URL列表
            
        Returns:
            文章数据列表
        """
        results = []
        
        for url in urls:
            logger.info(f"正在处理文章: {url}")
            article_data = self.fetch_article(url)
            if article_data:
                results.append(article_data)
            
            # 添加延迟，避免请求过快
            time.sleep(1)
        
        return results


def main():
    """主函数，演示爬虫的使用"""
    print("技术博客爬虫演示")
    print("=" * 50)
    print("支持平台: CSDN、博客园、掘金、SegmentFault、InfoQ等")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = TechBlogCrawler(timeout=15)
    
    # 测试文章URL（这些是示例URL，实际使用时可能需要更新）
    test_urls = [
        # CSDN示例文章（Python相关）
        "https://blog.csdn.net/weixin_42301220/article/details/130000000",  # 示例URL
        # 博客园示例文章
        "https://www.cnblogs.com/dotnetcrazy/p/10400000.html",  # 示例URL
        # 掘金示例文章  
        "https://juejin.cn/post/1234567890123456",  # 示例URL
    ]
    
    print("\n获取CSDN文章示例...")
    # 由于示例URL可能不存在，我们演示解析逻辑
    csdn_url = "https://blog.csdn.net/qq_41185868/article/details/103000000"  # 另一个示例URL
    print(f"尝试解析: {csdn_url}")
    
    # 检测平台
    platform = crawler.detect_platform(csdn_url)
    if platform:
        print(f"检测到平台: {crawler.platforms[platform]['name']}")
        
        # 在实际使用中，这里会调用fetch_article
        # 但由于示例URL可能不存在，我们跳过实际请求
        print("注意: 示例URL可能不存在，跳过实际请求")
        print("您可以使用真实的博客文章URL进行测试")
    else:
        print("无法识别平台")
    
    # 演示通用解析方法
    print("\n" + "=" * 50)
    print("演示多个平台的解析能力...")
    
    # 创建模拟的BeautifulSoup对象来演示解析逻辑
    print("\n解析逻辑演示:")
    print("1. CSDN文章解析:")
    print("   - 查找标题: h1.title-article 或 h1#articleContentId")
    print("   - 查找作者: a.follow-nickName")
    print("   - 查找内容: article 或 div#content_views")
    
    print("\n2. 博客园文章解析:")
    print("   - 查找标题: a#cb_post_title_url")
    print("   - 查找作者: a#blogger")
    print("   - 查找内容: div#cnblogs_post_body")
    
    print("\n3. 掘金文章解析:")
    print("   - 查找标题: h1.article-title")
    print("   - 查找作者: a.username")
    print("   - 查找内容: article")
    
    # 使用真实可访问的测试URL（如果有）
    print("\n" + "=" * 50)
    print("使用真实URL测试（可选）...")
    print("您可以将下面的URL替换为真实的博客文章URL进行测试")
    
    # 提供一个简单的测试函数
    def test_with_real_url():
        real_url = input("请输入一个真实的博客文章URL（或按Enter跳过）: ").strip()
        if real_url:
            print(f"\n正在解析: {real_url}")
            article_data = crawler.fetch_article(real_url)
            
            if article_data:
                print(f"成功获取文章!")
                print(f"标题: {article_data.get('title', '未知')}")
                print(f"作者: {article_data.get('author', '未知')}")
                print(f"平台: {article_data.get('platform_name', '未知')}")
                print(f"发布时间: {article_data.get('publish_time', '未知')}")
                
                if 'read_count' in article_data:
                    print(f"阅读量: {article_data['read_count']}")
                
                if 'content' in article_data:
                    content_preview = article_data['content'][:200] + "..." if len(article_data['content']) > 200 else article_data['content']
                    print(f"内容预览: {content_preview}")
                
                # 保存数据
                crawler.save_to_json(article_data)
                print(f"\n文章数据已保存到JSON文件")
            else:
                print("无法获取文章数据")
    
    # 注释掉实际测试，避免在演示中要求输入
    # test_with_real_url()
    
    print("\n爬虫演示完成！")
    print("\n使用说明:")
    print("1. 创建TechBlogCrawler实例")
    print("2. 调用fetch_article(url)获取文章数据")
    print("3. 支持CSDN、博客园、掘金、SegmentFault、InfoQ等平台")
    print("4. 自动检测平台并使用相应的解析方法")
    print("5. 支持保存为JSON文件")


if __name__ == "__main__":
    main()