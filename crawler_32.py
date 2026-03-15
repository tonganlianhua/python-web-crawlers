#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律法规爬虫 - 从中国法律数据库获取法律法规信息
目标网站: 中国法律法规数据库 (模拟)
功能: 爬取法律条文、司法解释、行政法规等
"""

import requests
import time
import random
import re
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
import logging
import sqlite3
from typing import List, Dict, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('law_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LawDatabaseCrawler:
    """法律法规数据库爬虫"""
    
    def __init__(self, base_url="http://law.example.com"):
        """
        初始化爬虫
        
        Args:
            base_url: 法律法规数据库基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session_headers()
        
        # 数据存储配置
        self.data_dir = "law_data"
        self.setup_data_directory()
        
        # 数据库连接
        self.db_path = os.path.join(self.data_dir, "laws.db")
        self.init_database()
        
        # 爬虫状态
        self.crawl_stats = {
            'total_laws': 0,
            'total_articles': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _setup_session_headers(self):
        """设置会话头信息"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': self.base_url,
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(headers)
    
    def setup_data_directory(self):
        """创建数据存储目录"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            os.makedirs(os.path.join(self.data_dir, 'raw_html'))
            os.makedirs(os.path.join(self.data_dir, 'json'))
            os.makedirs(os.path.join(self.data_dir, 'csv'))
            logger.info(f"创建数据目录: {self.data_dir}")
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建法律表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS laws (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    law_id TEXT UNIQUE,
                    title TEXT,
                    law_type TEXT,
                    publish_date TEXT,
                    effective_date TEXT,
                    issuing_authority TEXT,
                    law_level TEXT,
                    status TEXT,
                    summary TEXT,
                    url TEXT,
                    source TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建条文表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    law_id TEXT,
                    article_number TEXT,
                    chapter TEXT,
                    section TEXT,
                    content TEXT,
                    keywords TEXT,
                    interpretation TEXT,
                    FOREIGN KEY (law_id) REFERENCES laws (law_id)
                )
            ''')
            
            # 创建分类表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE,
                    description TEXT
                )
            ''')
            
            # 创建关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS law_categories (
                    law_id TEXT,
                    category_id INTEGER,
                    FOREIGN KEY (law_id) REFERENCES laws (law_id),
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def safe_request(self, url: str, method: str = 'GET', 
                    params: Optional[Dict] = None, 
                    data: Optional[Dict] = None,
                    max_retries: int = 3,
                    timeout: int = 15) -> Optional[requests.Response]:
        """
        安全发送HTTP请求，带重试和错误处理
        
        Args:
            url: 请求URL
            method: HTTP方法
            params: 查询参数
            data: 请求数据
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, data=data, timeout=timeout)
                else:
                    logger.error(f"不支持的HTTP方法: {method}")
                    return None
                
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                # 检查响应内容
                if len(response.content) < 100:
                    logger.warning(f"响应内容过短: {url}")
                    return None
                
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {url}, 尝试 {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"请求超时达到最大重试次数: {url}")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'Unknown'
                logger.error(f"HTTP错误: {url}, 状态码: {status_code}")
                
                if status_code in [403, 404]:
                    return None  # 特定错误码不再重试
                    
                if attempt == max_retries - 1:
                    return None
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误: {url}, 尝试 {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"连接错误达到最大重试次数: {url}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {url}, 错误: {e}")
                if attempt == max_retries - 1:
                    return None
            
            # 指数退避
            wait_time = (2 ** attempt) + random.random()
            logger.info(f"等待 {wait_time:.2f} 秒后重试")
            time.sleep(wait_time)
        
        return None
    
    def get_law_categories(self) -> List[Dict]:
        """
        获取法律分类
        
        Returns:
            分类列表
        """
        logger.info("正在获取法律分类...")
        
        # 模拟分类数据（实际应解析网页）
        categories = [
            {'id': '1', 'name': '宪法相关法', 'url': '/category/1'},
            {'id': '2', 'name': '民法商法', 'url': '/category/2'},
            {'id': '3', 'name': '行政法', 'url': '/category/3'},
            {'id': '4', 'name': '经济法', 'url': '/category/4'},
            {'id': '5', 'name': '社会法', 'url': '/category/5'},
            {'id': '6', 'name': '刑法', 'url': '/category/6'},
            {'id': '7', 'name': '诉讼与非诉讼程序法', 'url': '/category/7'},
            {'id': '8', 'name': '司法解释', 'url': '/category/8'},
            {'id': '9', 'name': '行政法规', 'url': '/category/9'},
            {'id': '10', 'name': '部门规章', 'url': '/category/10'},
        ]
        
        # 为每个分类添加完整URL
        for category in categories:
            category['full_url'] = urljoin(self.base_url, category['url'])
        
        logger.info(f"找到 {len(categories)} 个法律分类")
        return categories
    
    def search_laws(self, category_id: str, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        搜索指定分类的法律
        
        Args:
            category_id: 分类ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            法律列表
        """
        logger.info(f"搜索分类 {category_id} 的第 {page} 页法律")
        
        # 模拟搜索URL（实际应构建真实URL）
        search_url = urljoin(self.base_url, f"/search?category={category_id}&page={page}")
        
        response = self.safe_request(search_url)
        if not response:
            logger.warning(f"搜索失败: {search_url}")
            return []
        
        # 解析搜索结果
        laws = self._parse_search_results(response.text)
        
        # 保存原始HTML（用于调试）
        self._save_raw_html(response.text, f"search_{category_id}_page{page}.html")
        
        return laws[:page_size]  # 限制返回数量
    
    def _parse_search_results(self, html: str) -> List[Dict]:
        """
        解析搜索结果HTML
        
        Args:
            html: HTML内容
            
        Returns:
            法律信息列表
        """
        laws = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 模拟解析（实际应根据网站结构调整）
            # 假设每个法律项目在class为'law-item'的div中
            law_items = soup.find_all('div', class_='law-item')
            
            if not law_items:
                # 尝试其他选择器
                law_items = soup.find_all('li', class_='result-item')
            
            for item in law_items:
                try:
                    law = self._parse_law_item(item)
                    if law:
                        laws.append(law)
                except Exception as e:
                    logger.error(f"解析法律项失败: {e}")
                    continue
            
            # 如果没有找到，生成模拟数据
            if not laws:
                laws = self._generate_mock_laws(10)
            
            logger.info(f"解析到 {len(laws)} 条法律")
            
        except Exception as e:
            logger.error(f"解析搜索结果失败: {e}")
            laws = self._generate_mock_laws(5)
        
        return laws
    
    def _parse_law_item(self, item) -> Optional[Dict]:
        """
        解析单个法律项
        
        Args:
            item: BeautifulSoup元素
            
        Returns:
            法律信息字典
        """
        try:
            # 提取标题和链接
            title_elem = item.find('a', class_='title') or item.find('h3')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            href = title_elem.get('href', '')
            
            # 提取其他信息
            law_id = self._extract_law_id(href) or f"LAW_{random.randint(10000, 99999)}"
            
            # 提取发布日期
            date_elem = item.find('span', class_='date') or item.find('time')
            publish_date = date_elem.get_text(strip=True) if date_elem else ''
            
            # 提取发布机构
            authority_elem = item.find('span', class_='authority')
            issuing_authority = authority_elem.get_text(strip=True) if authority_elem else ''
            
            # 提取法律类型
            type_elem = item.find('span', class_='type')
            law_type = type_elem.get_text(strip=True) if type_elem else '未知'
            
            law = {
                'law_id': law_id,
                'title': title,
                'url': urljoin(self.base_url, href) if href else '',
                'publish_date': publish_date,
                'issuing_authority': issuing_authority,
                'law_type': law_type,
                'status': '现行有效',
                'summary': '',
                'source': self.base_url,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return law
            
        except Exception as e:
            logger.error(f"解析法律项异常: {e}")
            return None
    
    def _extract_law_id(self, url: str) -> Optional[str]:
        """从URL中提取法律ID"""
        try:
            # 尝试从URL路径中提取ID
            match = re.search(r'/(\d+)/?$', url)
            if match:
                return match.group(1)
            
            # 尝试从查询参数中提取
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            
            for key in ['id', 'law_id', 'code']:
                if key in query and query[key]:
                    return query[key][0]
            
            return None
            
        except Exception:
            return None
    
    def _generate_mock_laws(self, count: int) -> List[Dict]:
        """生成模拟法律数据（用于测试）"""
        mock_titles = [
            "中华人民共和国宪法",
            "中华人民共和国民法典",
            "中华人民共和国刑法",
            "中华人民共和国行政处罚法",
            "中华人民共和国公司法",
            "中华人民共和国劳动法",
            "中华人民共和国合同法",
            "中华人民共和国知识产权法",
            "中华人民共和国环境保护法",
            "中华人民共和国网络安全法"
        ]
        
        mock_authorities = [
            "全国人民代表大会",
            "全国人民代表大会常务委员会",
            "国务院",
            "最高人民法院",
            "最高人民检察院"
        ]
        
        laws = []
        for i in range(min(count, len(mock_titles))):
            law = {
                'law_id': f"MOCK_{i+1}",
                'title': mock_titles[i],
                'url': f"{self.base_url}/law/{i+1}",
                'publish_date': f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                'issuing_authority': random.choice(mock_authorities),
                'law_type': random.choice(['法律', '行政法规', '司法解释']),
                'status': '现行有效',
                'summary': f"这是关于{mock_titles[i]}的简要说明",
                'source': self.base_url,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            laws.append(law)
        
        return laws
    
    def get_law_detail(self, law_url: str) -> Optional[Dict]:
        """
        获取法律详情
        
        Args:
            law_url: 法律详情页URL
            
        Returns:
            法律详情字典
        """
        logger.info(f"获取法律详情: {law_url}")
        
        response = self.safe_request(law_url)
        if not response:
            logger.warning(f"获取法律详情失败: {law_url}")
            return None
        
        # 解析详情页
        detail = self._parse_law_detail(response.text, law_url)
        
        # 保存原始HTML
        law_id = self._extract_law_id(law_url) or 'unknown'
        self._save_raw_html(response.text, f"law_{law_id}_detail.html")
        
        return detail
    
    def _parse_law_detail(self, html: str, law_url: str) -> Dict:
        """
        解析法律详情页
        
        Args:
            html: HTML内容
            law_url: 法律URL
            
        Returns:
            法律详情
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取基本信息
            title = self._extract_detail_text(soup, ['h1', '.title', '.law-title'])
            publish_date = self._extract_detail_text(soup, ['.publish-date', '.date'])
            effective_date = self._extract_detail_text(soup, ['.effective-date'])
            issuing_authority = self._extract_detail_text(soup, ['.authority', '.issuing-department'])
            
            # 提取法律条文
            articles = self._extract_law_articles(soup)
            
            # 提取关键词
            keywords = self._extract_keywords(soup)
            
            # 构建详情对象
            detail = {
                'title': title or '未知标题',
                'publish_date': publish_date,
                'effective_date': effective_date,
                'issuing_authority': issuing_authority,
                'total_articles': len(articles),
                'articles': articles,
                'keywords': keywords,
                'url': law_url,
                'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"解析到法律详情: {title}, 共 {len(articles)} 条条文")
            
            return detail
            
        except Exception as e:
            logger.error(f"解析法律详情失败: {e}")
            # 返回模拟详情
            return self._generate_mock_detail(law_url)
    
    def _extract_detail_text(self, soup, selectors: List[str]) -> str:
        """使用多个选择器提取文本"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return ''
    
    def _extract_law_articles(self, soup) -> List[Dict]:
        """提取法律条文"""
        articles = []
        
        try:
            # 查找条文容器
            article_container = soup.find('div', class_='articles') or soup.find('div', id='content')
            
            if not article_container:
                return articles
            
            # 查找条文项
            article_elements = article_container.find_all(['div', 'p'], class_='article')
            
            for elem in article_elements:
                try:
                    # 提取条文编号
                    article_number = ''
                    number_elem = elem.find('span', class_='number')
                    if number_elem:
                        article_number = number_elem.get_text(strip=True)
                    
                    # 提取条文内容
                    content = elem.get_text(strip=True)
                    if number_elem:
                        content = content.replace(number_elem.get_text(strip=True), '').strip()
                    
                    if content:
                        article = {
                            'article_number': article_number or f"第{len(articles)+1}条",
                            'content': content,
                            'chapter': '',
                            'section': ''
                        }
                        articles.append(article)
                        
                except Exception as e:
                    logger.error(f"提取单条条文失败: {e}")
                    continue
            
            # 如果没有找到条文，生成模拟条文
            if not articles:
                articles = self._generate_mock_articles(10)
            
        except Exception as e:
            logger.error(f"提取条文失败: {e}")
            articles = self._generate_mock_articles(5)
        
        return articles
    
    def _extract_keywords(self, soup) -> List[str]:
        """提取关键词"""
        keywords = []
        
        try:
            # 查找关键词元素
            keyword_elements = soup.find_all('a', class_='keyword') or soup.find_all('span', class_='tag')
            
            for elem in keyword_elements:
                keyword = elem.get_text(strip=True)
                if keyword and len(keyword) <= 20:  # 避免提取过长文本
                    keywords.append(keyword)
            
            # 去重
            keywords = list(set(keywords))
            
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
        
        return keywords[:10]  # 限制最多10个关键词
    
    def _generate_mock_articles(self, count: int) -> List[Dict]:
        """生成模拟条文"""
        articles = []
        
        for i in range(count):
            article = {
                'article_number': f"第{i+1}条",
                'content': f"这是第{i+1}条法律条文的内容。法律条文应当明确、具体，具有可操作性。",
                'chapter': f"第{(i//5)+1}章",
                'section': f"第{(i%5)+1}节"
            }
            articles.append(article)
        
        return articles
    
    def _generate_mock_detail(self, law_url: str) -> Dict:
        """生成模拟法律详情"""
        return {
            'title': '模拟法律',
            'publish_date': '2023-01-01',
            'effective_date': '2023-01-01',
            'issuing_authority': '模拟机构',
            'total_articles': 10,
            'articles': self._generate_mock_articles(10),
            'keywords': ['法律', '法规', '条文'],
            'url': law_url,
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _save_raw_html(self, html: str, filename: str):
        """保存原始HTML"""
        try:
            raw_dir = os.path.join(self.data_dir, 'raw_html')
            filepath = os.path.join(raw_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
        except Exception as e:
            logger.error(f"保存HTML失败: {e}")
    
    def save_law_to_database(self, law_info: Dict, detail: Dict):
        """保存法律到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 保存基本信息
            cursor.execute('''
                INSERT OR REPLACE INTO laws 
                (law_id, title, law_type, publish_date, effective_date, 
                 issuing_authority, law_level, status, summary, url, 
                 source, crawl_time, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                law_info.get('law_id'),
                law_info.get('title'),
                law_info.get('law_type'),
                law_info.get('publish_date'),
                detail.get('effective_date'),
                law_info.get('issuing_authority'),
                '国家级',  # 法律层级
                law_info.get('status', '现行有效'),
                law_info.get('summary', ''),
                law_info.get('url'),
                law_info.get('source'),
                law_info.get('crawl_time'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # 保存条文
            law_id = law_info.get('law_id')
            articles = detail.get('articles', [])
            
            # 删除旧的条文
            cursor.execute('DELETE FROM articles WHERE law_id = ?', (law_id,))
            
            for article in articles:
                cursor.execute('''
                    INSERT INTO articles 
                    (law_id, article_number, chapter, section, content, keywords, interpretation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    law_id,
                    article.get('article_number'),
                    article.get('chapter'),
                    article.get('section'),
                    article.get('content'),
                    '',  # 关键词
                    ''   # 解释
                ))
            
            conn.commit()
            self.crawl_stats['successful'] += 1
            logger.info(f"保存到数据库: {law_info.get('title')}")
            
        except sqlite3.Error as e:
            self.crawl_stats['failed'] += 1
            logger.error(f"保存到数据库失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def save_to_json(self, data: Any, filename: str):
        """保存数据到JSON文件"""
        try:
            json_dir = os.path.join(self.data_dir, 'json')
            filepath = os.path.join(json_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据保存到JSON: {filepath}")
            
        except Exception as e:
            logger.error(f"保存JSON失败: {e}")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """保存数据到CSV文件"""
        if not data:
            logger.warning("没有数据可保存到CSV")
            return
        
        try:
            csv_dir = os.path.join(self.data_dir, 'csv')
            filepath = os.path.join(csv_dir, filename)
            
            # 获取所有字段
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"数据保存到CSV: {filepath}")
            
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")
    
    def run(self, max_categories: int = 3, laws_per_category: int = 2):
        """
        运行爬虫
        
        Args:
            max_categories: 最大分类数
            laws_per_category: 每个分类最大法律数
        """
        logger.info("=== 法律法规爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取分类
            categories = self.get_law_categories()
            
            if not categories:
                logger.error("未能获取分类信息")
                return
            
            # 2. 处理每个分类
            all_laws = []
            all_details = []
            
            for i, category in enumerate(categories[:max_categories]):
                logger.info(f"处理分类 {i+1}/{min(len(categories), max_categories)}: {category['name']}")
                
                # 搜索法律
                laws = self.search_laws(category['id'], page=1, page_size=laws_per_category)
                
                # 获取法律详情
                for j, law in enumerate(laws):
                    logger.info(f"  处理法律 {j+1}/{len(laws)}: {law.get('title', '未知标题')}")
                    
                    if law.get('url'):
                        detail = self.get_law_detail(law['url'])
                        if detail:
                            # 合并信息
                            full_law = {**law, **detail}
                            all_details.append(full_law)
                            
                            # 保存到数据库
                            self.save_law_to_database(law, detail)
                            
                            # 随机延迟
                            time.sleep(random.uniform(1, 2))
                    
                    all_laws.append(law)
                
                # 保存分类数据
                if laws:
                    self.save_to_csv(laws, f"category_{category['id']}_laws.csv")
            
            # 3. 保存所有数据
            if all_laws:
                self.save_to_csv(all_laws, "all_laws.csv")
            
            if all_details:
                self.save_to_json(all_details, "all_law_details.json")
            
            # 4. 更新统计信息
            self.crawl_stats.update({
                'total_laws': len(all_laws),
                'total_articles': sum(len(d.get('articles', [])) for d in all_details),
                'end_time': datetime.now()
            })
            
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== 法律法规爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = LawDatabaseCrawler()
    
    # 运行爬虫
    crawler.run(max_categories=2, laws_per_category=2)
    
    # 显示使用说明
    print("\n" + "="*60)
    print("法律法规爬虫使用说明")
    print("="*60)
    print("1. 获取法律分类:")
    print("   categories = crawler.get_law_categories()")
    print("\n2. 搜索法律:")
    print("   laws = crawler.search_laws('1', page=1, page_size=10)")
    print("\n3. 获取法律详情:")
    print("   detail = crawler.get_law_detail(law_url)")
    print("\n4. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("\n5. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   可以使用SQLite工具查看数据")

if __name__ == "__main__":
    main()