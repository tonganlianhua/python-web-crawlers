#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府公开数据爬虫 - 从中国政府网获取政策文件信息
目标网站: http://www.gov.cn
功能: 爬取最新政策文件、通知公告、政策解读等信息
"""

import requests
import time
import random
from bs4 import BeautifulSoup
import csv
import json
import os
from datetime import datetime
from urllib.parse import urljoin
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GovPolicyCrawler:
    """中国政府网政策文件爬虫"""
    
    def __init__(self, base_url="http://www.gov.cn"):
        """
        初始化爬虫
        
        Args:
            base_url: 网站基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 创建数据存储目录
        self.data_dir = "gov_policy_data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def make_request(self, url, max_retries=3, timeout=10):
        """
        发送HTTP请求，带重试机制
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象
            
        Raises:
            requests.exceptions.RequestException: 请求失败
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                response.encoding = 'utf-8'  # 设置编码
                return response
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {url}, 尝试次数: {attempt+1}")
                if attempt == max_retries - 1:
                    raise
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP错误: {url}, 状态码: {e.response.status_code}")
                if e.response.status_code in [403, 404, 500]:
                    return None  # 特定错误码直接返回None
                if attempt == max_retries - 1:
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {url}, 错误: {e}")
                if attempt == max_retries - 1:
                    raise
            
            # 指数退避重试
            wait_time = (2 ** attempt) + random.random()
            logger.info(f"等待 {wait_time:.2f} 秒后重试")
            time.sleep(wait_time)
        
        return None
    
    def get_policy_categories(self):
        """
        获取政策分类页面链接
        
        Returns:
            list: 分类链接列表
        """
        categories = []
        try:
            url = urljoin(self.base_url, "/zhengce/index.htm")
            response = self.make_request(url)
            if not response:
                return categories
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找分类导航
            nav_containers = soup.find_all('div', class_='list list_1')
            for container in nav_containers:
                links = container.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    categories.append({
                        'name': link.get_text(strip=True),
                        'url': href,
                        'description': link.get('title', '')
                    })
            
            logger.info(f"找到 {len(categories)} 个政策分类")
            return categories[:10]  # 限制前10个分类
            
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            return categories
    
    def parse_policy_list(self, url, max_pages=5):
        """
        解析政策列表页
        
        Args:
            url: 列表页URL
            max_pages: 最大爬取页数
            
        Returns:
            list: 政策文章信息列表
        """
        articles = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                # 构建分页URL
                if current_page == 1:
                    page_url = url
                else:
                    # 处理不同网站的分页规则
                    if '?' in url:
                        page_url = f"{url}&page={current_page}"
                    else:
                        page_url = f"{url}?page={current_page}"
                
                logger.info(f"正在爬取第 {current_page} 页: {page_url}")
                
                response = self.make_request(page_url)
                if not response:
                    logger.warning(f"无法获取页面: {page_url}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找文章列表（根据实际网站结构调整）
                article_list = soup.find('ul', class_='list_1') or soup.find('div', class_='list')
                
                if not article_list:
                    # 尝试其他选择器
                    article_list = soup.find('div', {'id': 'list'}) or soup.find('ul', {'id': 'list'})
                
                if not article_list:
                    logger.warning(f"未找到文章列表: {page_url}")
                    break
                
                # 提取文章项
                items = article_list.find_all('li') or article_list.find_all('div', class_='item')
                
                if not items:
                    logger.warning(f"页面没有文章: {page_url}")
                    break
                
                for item in items:
                    try:
                        article = self.parse_article_item(item, page_url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"解析文章项失败: {e}")
                        continue
                
                # 检查是否有下一页
                next_page = soup.find('a', text='下一页') or soup.find('a', text='>')
                if not next_page:
                    logger.info(f"没有更多页面了")
                    break
                
                current_page += 1
                
                # 随机延迟，避免过快请求
                time.sleep(random.uniform(1, 3))
            
            logger.info(f"从列表页爬取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"解析列表页失败: {e}")
            return articles
    
    def parse_article_item(self, item, page_url):
        """
        解析单个文章项
        
        Args:
            item: BeautifulSoup文章项
            page_url: 当前页面URL
            
        Returns:
            dict: 文章信息
        """
        try:
            # 获取文章标题和链接
            title_tag = item.find('a')
            if not title_tag:
                return None
            
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href', '')
            
            if not href.startswith('http'):
                href = urljoin(page_url, href)
            
            # 获取发布时间
            date_tag = item.find('span', class_='date') or item.find('em')
            publish_date = ''
            if date_tag:
                publish_date = date_tag.get_text(strip=True)
            
            # 获取摘要
            summary_tag = item.find('p', class_='summary') or item.find('div', class_='desc')
            summary = ''
            if summary_tag:
                summary = summary_tag.get_text(strip=True)
            
            article = {
                'title': title,
                'url': href,
                'publish_date': publish_date,
                'summary': summary,
                'source_page': page_url,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
            
        except Exception as e:
            logger.error(f"解析文章项异常: {e}")
            return None
    
    def get_article_detail(self, article_url):
        """
        获取文章详情
        
        Args:
            article_url: 文章详情页URL
            
        Returns:
            dict: 文章详情
        """
        try:
            response = self.make_request(article_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = ''
            title_tag = soup.find('h1') or soup.find('div', class_='title')
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # 提取发布时间
            publish_time = ''
            time_tag = soup.find('span', class_='time') or soup.find('div', class_='time')
            if time_tag:
                publish_time = time_tag.get_text(strip=True)
            
            # 提取来源
            source = ''
            source_tag = soup.find('span', class_='source') or soup.find('div', class_='source')
            if source_tag:
                source = source_tag.get_text(strip=True)
            
            # 提取正文内容
            content = ''
            content_tag = soup.find('div', class_='content') or soup.find('div', class_='article')
            if content_tag:
                # 移除script和style标签
                for tag in content_tag(['script', 'style', 'iframe']):
                    tag.decompose()
                content = content_tag.get_text('\n', strip=True)
            
            # 提取附件链接
            attachments = []
            attachment_tags = content_tag.find_all('a', href=True) if content_tag else []
            for tag in attachment_tags:
                href = tag['href']
                if href.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar')):
                    if not href.startswith('http'):
                        href = urljoin(article_url, href)
                    
                    attachments.append({
                        'name': tag.get_text(strip=True),
                        'url': href
                    })
            
            detail = {
                'title': title,
                'publish_time': publish_time,
                'source': source,
                'content': content,
                'attachments': attachments,
                'url': article_url,
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return detail
            
        except Exception as e:
            logger.error(f"获取文章详情失败: {article_url}, 错误: {e}")
            return None
    
    def save_to_csv(self, data, filename):
        """
        保存数据到CSV文件
        
        Args:
            data: 数据列表
            filename: 文件名
        """
        if not data:
            logger.warning("没有数据可保存")
            return
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                if data:
                    # 获取所有字段
                    all_keys = set()
                    for item in data:
                        all_keys.update(item.keys())
                    
                    # 排序字段
                    fieldnames = sorted(all_keys)
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            
            logger.info(f"数据已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def save_to_json(self, data, filename):
        """
        保存数据到JSON文件
        
        Args:
            data: 数据
            filename: 文件名
        """
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def run(self, max_categories=3, max_articles_per_category=5):
        """
        运行爬虫主程序
        
        Args:
            max_categories: 最大爬取分类数
            max_articles_per_category: 每个分类最大文章数
        """
        logger.info("=== 政府公开数据爬虫开始运行 ===")
        
        try:
            # 1. 获取分类
            logger.info("正在获取政策分类...")
            categories = self.get_policy_categories()
            
            if not categories:
                logger.error("未能获取到分类信息")
                return
            
            # 2. 爬取每个分类的文章
            all_articles = []
            all_details = []
            
            for i, category in enumerate(categories[:max_categories]):
                logger.info(f"处理分类 {i+1}/{min(len(categories), max_categories)}: {category['name']}")
                
                # 爬取文章列表
                articles = self.parse_policy_list(category['url'], max_pages=2)
                
                # 限制每个分类的文章数
                articles = articles[:max_articles_per_category]
                
                # 获取文章详情
                for j, article in enumerate(articles):
                    logger.info(f"  获取文章 {j+1}/{len(articles)}: {article['title']}")
                    
                    detail = self.get_article_detail(article['url'])
                    if detail:
                        # 合并列表信息和详情信息
                        full_article = {**article, **detail}
                        all_details.append(full_article)
                        
                        # 随机延迟
                        time.sleep(random.uniform(1, 2))
                
                all_articles.extend(articles)
                
                # 保存每个分类的数据
                if articles:
                    cat_name = category['name'].replace('/', '_')
                    self.save_to_csv(articles, f"category_{cat_name}_articles.csv")
            
            # 3. 保存所有数据
            if all_articles:
                self.save_to_csv(all_articles, "all_policy_articles.csv")
            
            if all_details:
                self.save_to_json(all_details, "all_policy_details.json")
            
            # 4. 生成统计信息
            stats = {
                'total_categories': len(categories[:max_categories]),
                'total_articles': len(all_articles),
                'total_details': len(all_details),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_dir': self.data_dir
            }
            
            self.save_to_json(stats, "crawl_statistics.json")
            
            logger.info(f"爬虫完成！共爬取 {len(all_articles)} 篇文章，{len(all_details)} 篇详情")
            logger.info(f"数据保存在: {self.data_dir}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 政府公开数据爬虫运行结束 ===")

def main():
    """
    主函数
    """
    # 创建爬虫实例
    crawler = GovPolicyCrawler()
    
    # 运行爬虫（限制规模）
    crawler.run(max_categories=2, max_articles_per_category=3)
    
    # 使用示例
    print("\n=== 爬虫使用示例 ===")
    print("1. 获取政策分类:")
    print("   crawler.get_policy_categories()")
    print("\n2. 爬取特定分类文章:")
    print("   articles = crawler.parse_policy_list(url, max_pages=2)")
    print("\n3. 获取文章详情:")
    print("   detail = crawler.get_article_detail(article_url)")
    print("\n4. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")

if __name__ == "__main__":
    main()