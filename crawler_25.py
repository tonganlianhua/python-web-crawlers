#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康资讯爬虫 - 丁香医生健康科普文章
爬取丁香医生网站的健康科普文章：标题、作者、分类、发布时间、内容摘要等
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import csv
import os
from bs4 import BeautifulSoup
import html

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class HealthArticle:
    """健康文章数据结构"""
    title: str
    url: str
    author: str
    publish_date: str
    category: str  # 文章分类
    tags: List[str]  # 文章标签
    summary: str  # 文章摘要
    content_preview: str  # 内容预览（前200字符）
    view_count: int  # 阅读量
    like_count: int  # 点赞数
    comment_count: int  # 评论数
    image_url: str  # 文章配图


class DingxiangHealthCrawler:
    """丁香医生爬虫类"""
    
    def __init__(self):
        self.base_url = "https://dxy.com"
        self.api_url = "https://dxy.com/article"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 健康分类映射
        self.categories = {
            'disease': '疾病防治',
            'medicine': '用药指南', 
            'nutrition': '营养饮食',
            'exercise': '运动健康',
            'mental': '心理健康',
            'women': '女性健康',
            'children': '儿童健康',
            'elderly': '老年健康',
            'lifestyle': '生活方式',
            'prevention': '疾病预防'
        }
    
    def get_latest_articles(self, category: str = None, limit: int = 30) -> List[HealthArticle]:
        """
        获取最新健康文章
        
        Args:
            category: 文章分类（可选）
            limit: 获取数量
            
        Returns:
            文章对象列表
        """
        articles = []
        page = 1
        
        try:
            logger.info(f"正在获取健康文章，分类: {category or '全部'}, 数量: {limit}")
            
            while len(articles) < limit:
                # 构建URL
                if category and category in self.categories:
                    url = f"{self.base_url}/category/{category}"
                else:
                    url = f"{self.base_url}/article"
                
                params = {'page': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找文章列表
                article_elements = soup.select('.article-item, .post-item, .content-item')
                
                if not article_elements:
                    # 尝试其他选择器
                    article_elements = soup.select('article, .post, .card')
                
                if not article_elements:
                    logger.warning("未找到文章元素，可能页面结构已变化")
                    break
                
                # 解析每篇文章
                new_articles = 0
                for element in article_elements:
                    if len(articles) >= limit:
                        break
                    
                    article = self._parse_article_element(element)
                    if article:
                        articles.append(article)
                        new_articles += 1
                
                if new_articles == 0:
                    logger.info(f"第 {page} 页没有新文章，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_articles} 篇文章，总计 {len(articles)} 篇")
                page += 1
                
                # 避免请求过快
                time.sleep(1)
            
            logger.info(f"成功获取 {len(articles)} 篇健康文章")
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析文章失败: {e}")
            return []
    
    def _parse_article_element(self, element) -> Optional[HealthArticle]:
        """解析文章HTML元素"""
        try:
            # 提取标题
            title_element = element.select_one('.title, h2, h3, .article-title, .post-title')
            title = title_element.get_text(strip=True) if title_element else ''
            
            if not title:
                return None
            
            # 提取链接
            link_element = element.select_one('a')
            if not link_element or not link_element.get('href'):
                return None
            
            article_url = link_element['href']
            if not article_url.startswith('http'):
                article_url = self.base_url + article_url
            
            # 提取作者
            author_element = element.select_one('.author, .meta-author, .post-author')
            author = author_element.get_text(strip=True) if author_element else '丁香医生'
            
            # 提取发布日期
            date_element = element.select_one('.date, .time, .post-date, .meta-date')
            publish_date = date_element.get_text(strip=True) if date_element else ''
            
            # 提取分类
            category_element = element.select_one('.category, .tag, .post-category')
            category = category_element.get_text(strip=True) if category_element else ''
            
            # 提取摘要
            summary_element = element.select_one('.summary, .excerpt, .post-excerpt')
            summary = summary_element.get_text(strip=True) if summary_element else ''
            
            # 提取内容预览（如果有）
            content_element = element.select_one('.content, .post-content')
            content_preview = content_element.get_text(strip=True)[:200] if content_element else summary[:200]
            
            # 提取图片
            image_element = element.select_one('img')
            image_url = image_element['src'] if image_element and image_element.get('src') else ''
            
            # 提取统计数据（阅读量、点赞数等）
            stats_elements = element.select('.stats, .meta-stats')
            view_count = 0
            like_count = 0
            comment_count = 0
            
            for stats in stats_elements:
                stats_text = stats.get_text()
                if '阅读' in stats_text or 'view' in stats_text.lower():
                    match = re.search(r'(\d+)', stats_text)
                    if match:
                        view_count = int(match.group(1))
                elif '点赞' in stats_text or 'like' in stats_text.lower():
                    match = re.search(r'(\d+)', stats_text)
                    if match:
                        like_count = int(match.group(1))
                elif '评论' in stats_text or 'comment' in stats_text.lower():
                    match = re.search(r'(\d+)', stats_text)
                    if match:
                        comment_count = int(match.group(1))
            
            # 提取标签
            tags = []
            tag_elements = element.select('.tag-item, .label, .badge')
            for tag_element in tag_elements:
                tag_text = tag_element.get_text(strip=True)
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
            
            # 如果没有找到标签，尝试从分类中提取
            if not tags and category:
                tags = [category]
            
            article = HealthArticle(
                title=html.unescape(title),
                url=article_url,
                author=html.unescape(author),
                publish_date=html.unescape(publish_date),
                category=html.unescape(category),
                tags=[html.unescape(tag) for tag in tags],
                summary=html.unescape(summary),
                content_preview=html.unescape(content_preview),
                view_count=view_count,
                like_count=like_count,
                comment_count=comment_count,
                image_url=image_url
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"解析文章元素失败: {e}")
            return None
    
    def get_article_detail(self, url: str) -> Optional[Dict]:
        """
        获取文章详细信息
        
        Args:
            url: 文章URL
            
        Returns:
            文章详细信息字典
        """
        try:
            logger.info(f"正在获取文章详情: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取详细内容
            content_element = soup.select_one('.article-content, .post-content, .content')
            if not content_element:
                return None
            
            # 清理HTML，提取纯文本
            content_text = content_element.get_text(strip=True)
            
            # 提取所有图片
            images = []
            for img in content_element.select('img'):
                src = img.get('src')
                if src and src not in images:
                    images.append(src)
            
            # 提取所有小标题
            headings = []
            for heading in content_element.select('h2, h3, h4'):
                heading_text = heading.get_text(strip=True)
                if heading_text and heading_text not in headings:
                    headings.append(heading_text)
            
            # 提取参考文献（如果有）
            references = []
            ref_section = soup.select_one('.references, .footnotes')
            if ref_section:
                for ref in ref_section.select('li'):
                    ref_text = ref.get_text(strip=True)
                    if ref_text:
                        references.append(ref_text)
            
            return {
                'full_content': content_text,
                'content_length': len(content_text),
                'images_count': len(images),
                'headings': headings,
                'references_count': len(references),
                'html_content': str(content_element)[:1000] + '...' if len(str(content_element)) > 1000 else str(content_element)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取文章详情失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析文章详情失败: {e}")
            return None
    
    def search_articles(self, query: str, limit: int = 20) -> List[HealthArticle]:
        """
        搜索健康文章
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            文章对象列表
        """
        search_url = f"{self.base_url}/search"
        params = {
            'q': query,
            'type': 'article'
        }
        
        try:
            logger.info(f"正在搜索健康文章: {query}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            search_results = soup.select('.search-result, .result-item')
            
            for result in search_results[:limit]:
                article = self._parse_search_result(result)
                if article:
                    articles.append(article)
            
            logger.info(f"搜索到 {len(articles)} 篇相关文章")
            return articles
            
        except Exception as e:
            logger.error(f"搜索文章失败: {e}")
            return []
    
    def _parse_search_result(self, element) -> Optional[HealthArticle]:
        """解析搜索结果元素"""
        try:
            # 搜索结果的解析逻辑可能与普通文章不同
            title_element = element.select_one('.title, h3, .result-title')
            title = title_element.get_text(strip=True) if title_element else ''
            
            if not title:
                return None
            
            link_element = element.select_one('a')
            if not link_element or not link_element.get('href'):
                return None
            
            article_url = link_element['href']
            if not article_url.startswith('http'):
                article_url = self.base_url + article_url
            
            # 搜索结果的摘要通常更完整
            summary_element = element.select_one('.summary, .snippet, .description')
            summary = summary_element.get_text(strip=True) if summary_element else ''
            
            # 其他信息可能较少
            article = HealthArticle(
                title=html.unescape(title),
                url=article_url,
                author='未知',
                publish_date='',
                category='',
                tags=[],
                summary=html.unescape(summary),
                content_preview=html.unescape(summary[:200]),
                view_count=0,
                like_count=0,
                comment_count=0,
                image_url=''
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"解析搜索结果失败: {e}")
            return None
    
    def analyze_articles(self, articles: List[HealthArticle]) -> Dict:
        """
        分析文章数据
        
        Args:
            articles: 文章对象列表
            
        Returns:
            分析结果字典
        """
        if not articles:
            return {}
        
        try:
            # 统计信息
            total_articles = len(articles)
            
            # 分类统计
            category_counts = {}
            tag_counts = {}
            author_counts = {}
            
            total_views = 0
            total_likes = 0
            total_comments = 0
            
            for article in articles:
                # 分类统计
                if article.category:
                    category_counts[article.category] = category_counts.get(article.category, 0) + 1
                
                # 标签统计
                for tag in article.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # 作者统计
                author_counts[article.author] = author_counts.get(article.author, 0) + 1
                
                # 统计数据
                total_views += article.view_count
                total_likes += article.like_count
                total_comments += article.comment_count
            
            # 最常见的分类、标签、作者
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 平均统计数据
            avg_views = total_views / total_articles if total_articles > 0 else 0
            avg_likes = total_likes / total_articles if total_articles > 0 else 0
            avg_comments = total_comments / total_articles if total_articles > 0 else 0
            
            # 最受欢迎的文章（按阅读量）
            top_viewed = sorted(articles, key=lambda x: x.view_count, reverse=True)[:5]
            
            return {
                'total_articles': total_articles,
                'total_views': total_views,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'avg_views': avg_views,
                'avg_likes': avg_likes,
                'avg_comments': avg_comments,
                'top_categories': top_categories,
                'top_tags': top_tags,
                'top_authors': top_authors,
                'top_viewed_articles': [(a.title[:30], a.view_count) for a in top_viewed]
            }
            
        except Exception as e:
            logger.error(f"分析文章数据失败: {e}")
            return {}
    
    def save_to_csv(self, articles: List[HealthArticle], filename: str = "health_articles.csv"):
        """
        保存文章数据到CSV文件
        
        Args:
            articles: 文章对象列表
            filename: 输出文件名
        """
        if not articles:
            logger.warning("没有文章数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'title', 'url', 'author', 'publish_date', 'category', 
                    'tags', 'summary', 'content_preview', 'view_count', 
                    'like_count', 'comment_count', 'image_url'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for article in articles:
                    row = article.__dict__.copy()
                    # 转换标签列表为字符串
                    row['tags'] = ', '.join(row['tags'])
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(articles)} 篇文章数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("丁香医生健康资讯爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = DingxiangHealthCrawler()
    
    try:
        # 1. 显示可用分类
        print("可用健康分类:")
        print("-" * 30)
        for key, name in crawler.categories.items():
            print(f"  {key}: {name}")
        print()
        
        # 2. 获取文章（可选择分类）
        category_choice = input("请输入分类代码（直接回车获取全部）: ").strip().lower()
        
        if category_choice and category_choice not in crawler.categories:
            print(f"无效分类代码，将获取全部文章")
            category_choice = None
        
        print(f"\n正在爬取健康文章...")
        articles = crawler.get_latest_articles(category=category_choice, limit=20)
        
        if not articles:
            print("未获取到文章数据，程序退出")
            return
        
        # 3. 显示统计信息
        print(f"\n成功获取 {len(articles)} 篇健康文章:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_articles(articles)
        
        if analysis:
            print(f"总计文章: {analysis['total_articles']}")
            print(f"总阅读量: {analysis['total_views']:,}")
            print(f"总点赞数: {analysis['total_likes']:,}")
            print(f"平均阅读量: {analysis['avg_views']:.1f}")
            
            if analysis['top_categories']:
                print("\n文章分类分布:")
                for category, count in analysis['top_categories']:
                    print(f"  {category}: {count} 篇")
            
            if analysis['top_tags']:
                print("\n热门健康标签:")
                for tag, count in analysis['top_tags'][:5]:
                    print(f"  {tag}: {count} 次")
        
        # 4. 显示前5篇文章详情
        print("\n最新健康文章 TOP 5:")
        print("-" * 30)
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article.title}")
            print(f"   作者: {article.author}, 发布时间: {article.publish_date}")
            print(f"   分类: {article.category}")
            print(f"   摘要: {article.summary[:80]}...")
            print(f"   阅读: {article.view_count:,}, 点赞: {article.like_count:,}")
            print()
        
        # 5. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"health_articles_{timestamp}.csv"
        
        crawler.save_to_csv(articles, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 6. 获取并展示一篇文章的详细信息
        if articles:
            sample_article = articles[0]
            print(f"\n获取文章 '{sample_article.title[:20]}...' 的详细内容:")
            details = crawler.get_article_detail(sample_article.url)
            
            if details:
                print(f"内容长度: {details['content_length']} 字符")
                print(f"包含图片: {details['images_count']} 张")
                print(f"参考文献: {details['references_count']} 条")
                
                if details['headings']:
                    print("\n文章小标题:")
                    for heading in details['headings'][:3]:
                        print(f"  - {heading}")
                
                print(f"\n内容预览（前300字符）:")
                print(details['full_content'][:300] + "...")
        
        # 7. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示搜索功能:")
        search_query = input("请输入要搜索的健康关键词（直接回车跳过）: ").strip()
        
        if search_query:
            print(f"\n正在搜索 '{search_query}'...")
            search_results = crawler.search_articles(search_query, limit=10)
            
            if search_results:
                print(f"找到 {len(search_results)} 篇相关文章:")
                for i, article in enumerate(search_results[:3], 1):
                    print(f"{i}. {article.title}")
                    print(f"   摘要: {article.summary[:60]}...")
            else:
                print("未找到相关文章")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()