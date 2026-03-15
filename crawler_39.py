#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI发展动态爬虫 - 从AI研究机构、科技媒体和开源平台获取AI发展信息
目标网站: arXiv, GitHub, Hugging Face, AI论文库等
功能: 爬取AI论文、开源项目、模型发布、研究趋势等
"""

import requests
import time
import random
import json
import csv
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote
import logging
import hashlib
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
import re
from bs4 import BeautifulSoup
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIDevelopmentCrawler:
    """AI发展动态爬虫"""
    
    def __init__(self):
        """
        初始化爬虫
        """
        # 目标网站配置
        self.websites = {
            'arxiv': {
                'name': 'arXiv',
                'base_url': 'https://arxiv.org',
                'api_base': 'https://export.arxiv.org/api/query',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/xml, text/xml, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'github': {
                'name': 'GitHub',
                'base_url': 'https://github.com',
                'api_base': 'https://api.github.com',
                'api_key': 'GITHUB_API_KEY',  # 需要注册获取
                'headers': {
                    'User-Agent': 'AI-Research-Crawler',
                    'Accept': 'application/vnd.github.v3+json',
                    'Authorization': 'token YOUR_GITHUB_TOKEN'  # 需要替换
                }
            },
            'huggingface': {
                'name': 'Hugging Face',
                'base_url': 'https://huggingface.co',
                'api_base': 'https://huggingface.co/api',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            },
            'paperswithcode': {
                'name': 'Papers with Code',
                'base_url': 'https://paperswithcode.com',
                'api_base': 'https://paperswithcode.com/api/v1',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            }
        }
        
        # AI研究领域
        self.ai_fields = [
            'Natural Language Processing',
            'Computer Vision',
            'Reinforcement Learning',
            'Generative AI',
            'Large Language Models',
            'Multimodal AI',
            'AI Safety',
            'AI Ethics',
            'AI for Science',
            'Robotics',
            'Speech Recognition',
            'Time Series Analysis',
            'Graph Neural Networks',
            'Federated Learning',
            'Explainable AI',
            'AI Hardware',
            'Quantum Machine Learning',
            'Neuro-Symbolic AI'
        ]
        
        # AI模型类型
        self.model_types = [
            'Transformer', 'CNN', 'RNN', 'LSTM', 'GAN',
            'VAE', 'Diffusion Model', 'BERT', 'GPT', 'CLIP',
            'DALL-E', 'Stable Diffusion', 'Whisper', 'AlphaFold',
            'AlphaGo', 'ResNet', 'YOLO', 'BERT', 'T5', 'ViT'
        ]
        
        # 研究机构
        self.research_institutions = [
            'OpenAI', 'Google DeepMind', 'Meta AI', 'Microsoft Research',
            'Stanford University', 'MIT', 'Carnegie Mellon University',
            'University of California, Berkeley', 'University of Oxford',
            'University of Cambridge', 'Tsinghua University', 'Peking University',
            'ETH Zurich', 'University of Toronto', 'University of Washington'
        ]
        
        # 会议期刊
        self.conferences_journals = [
            'NeurIPS', 'ICML', 'ICLR', 'CVPR', 'ACL',
            'EMNLP', 'AAAI', 'IJCAI', 'Nature', 'Science',
            'Journal of Machine Learning Research',
            'IEEE Transactions on Pattern Analysis and Machine Intelligence'
        ]
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "ai_development_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "ai_development.db")
        self.init_database()
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 爬虫状态
        self.crawl_stats = {
            'total_papers': 0,
            'total_models': 0,
            'total_projects': 0,
            'total_datasets': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 请求限制
        self.rate_limits = {
            'arxiv': {'calls_per_minute': 10, 'last_call': 0},
            'github': {'calls_per_minute': 30, 'last_call': 0},
            'huggingface': {'calls_per_minute': 60, 'last_call': 0},
            'paperswithcode': {'calls_per_minute': 30, 'last_call': 0}
        }
    
    def _setup_session(self):
        """设置会话配置"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        self.session.headers.update(default_headers)
    
    def setup_data_directories(self):
        """创建数据目录结构"""
        directories = [
            self.data_dir,
            os.path.join(self.data_dir, 'papers'),
            os.path.join(self.data_dir, 'models'),
            os.path.join(self.data_dir, 'projects'),
            os.path.join(self.data_dir, 'datasets'),
            os.path.join(self.data_dir, 'trends'),
            os.path.join(self.data_dir, 'researchers'),
            os.path.join(self.data_dir, 'institutions'),
            os.path.join(self.data_dir, 'raw_data'),
            os.path.join(self.data_dir, 'json'),
            os.path.join(self.data_dir, 'csv'),
            os.path.join(self.data_dir, 'excel'),
            os.path.join(self.data_dir, 'cache'),
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建AI论文表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT UNIQUE,
                    title TEXT,
                    abstract TEXT,
                    authors TEXT,
                    affiliations TEXT,
                    published_date TEXT,
                    updated_date TEXT,
                    arxiv_id TEXT,
                    doi TEXT,
                    categories TEXT,
                    primary_category TEXT,
                    field TEXT,
                    subfield TEXT,
                    conference TEXT,
                    journal TEXT,
                    citations INTEGER,
                    references TEXT,
                    url TEXT,
                    pdf_url TEXT,
                    code_url TEXT,
                    project_url TEXT,
                    dataset_url TEXT,
                    model_url TEXT,
                    keywords TEXT,
                    summary TEXT,
                    methodology TEXT,
                    results TEXT,
                    limitations TEXT,
                    future_work TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建AI模型表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    model_type TEXT,
                    architecture TEXT,
                    parameters TEXT,
                    training_data TEXT,
                    training_compute TEXT,
                    release_date TEXT,
                    organization TEXT,
                    authors TEXT,
                    paper_id TEXT,
                    license TEXT,
                    framework TEXT,
                    repository_url TEXT,
                    huggingface_url TEXT,
                    paper_url TEXT,
                    demo_url TEXT,
                    api_url TEXT,
                    documentation_url TEXT,
                    performance_metrics TEXT,
                    benchmarks TEXT,
                    applications TEXT,
                    limitations TEXT,
                    citations INTEGER,
                    stars INTEGER,
                    downloads INTEGER,
                    last_updated_date TEXT,
                    tags TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES ai_papers (paper_id)
                )
            ''')
            
            # 创建开源项目表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    repository_url TEXT,
                    organization TEXT,
                    owner TEXT,
                    language TEXT,
                    framework TEXT,
                    stars INTEGER,
                    forks INTEGER,
                    watchers INTEGER,
                    issues INTEGER,
                    pull_requests INTEGER,
                    contributors INTEGER,
                    last_commit_date TEXT,
                    created_date TEXT,
                    updated_date TEXT,
                    license TEXT,
                    topics TEXT,
                    readme_text TEXT,
                    documentation_url TEXT,
                    paper_url TEXT,
                    demo_url TEXT,
                    website_url TEXT,
                    downloads INTEGER,
                    dependencies TEXT,
                    installation_instructions TEXT,
                    usage_examples TEXT,
                    citation TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建数据集表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    modality TEXT,
                    data_type TEXT,
                    size TEXT,
                    samples INTEGER,
                    features INTEGER,
                    classes INTEGER,
                    language TEXT,
                    domain TEXT,
                    task TEXT,
                    paper_id TEXT,
                    organization TEXT,
                    creators TEXT,
                    release_date TEXT,
                    last_updated_date TEXT,
                    license TEXT,
                    download_url TEXT,
                    huggingface_url TEXT,
                    paper_url TEXT,
                    documentation_url TEXT,
                    benchmark_results TEXT,
                    splits TEXT,
                    format TEXT,
                    preprocessing_required BOOLEAN,
                    quality_score REAL,
                    popularity_score REAL,
                    citations INTEGER,
                    tags TEXT,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES ai_papers (paper_id)
                )
            ''')
            
            # 创建研究趋势表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS research_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trend_id TEXT UNIQUE,
                    topic TEXT,
                    field TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    peak_date TEXT,
                    paper_count INTEGER,
                    citation_count INTEGER,
                    github_stars INTEGER,
                    huggingface_downloads INTEGER,
                    growth_rate REAL,
                    hotness_score REAL,
                    related_topics TEXT,
                    key_papers TEXT,
                    key_models TEXT,
                    key_researchers TEXT,
                    key_institutions TEXT,
                    description TEXT,
                    analysis TEXT,
                    future_outlook TEXT,
                    crawl_time TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_date ON ai_papers (published_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_category ON ai_papers (primary_category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_citations ON ai_papers (citations)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_type ON ai_models (model_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_organization ON ai_models (organization)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_stars ON ai_projects (stars)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_language ON ai_projects (language)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_datasets_task ON ai_datasets (task)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_datasets_domain ON ai_datasets (domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trends_topic ON research_trends (topic)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trends_hotness ON research_trends (hotness_score)')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def _check_rate_limit(self, website_id: str) -> bool:
        """检查API速率限制"""
        if website_id not in self.rate_limits:
            return True
        
        limit_info = self.rate_limits[website_id]
        current_time = time.time()
        
        # 检查是否超过速率限制
        if current_time - limit_info['last_call'] < 60 / limit_info['calls_per_minute']:
            wait_time = (60 / limit_info['calls_per_minute']) - (current_time - limit_info['last_call'])
            logger.info(f"达到速率限制，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        # 更新最后调用时间
        self.rate_limits[website_id]['last_call'] = time.time()
        return True
    
    def get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_str = url
        if params:
            key_str += json.dumps(params, sort_keys=True)
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached_response(self, cache_key: str, max_age_minutes: int = 60) -> Optional[Dict]:
        """获取缓存的响应"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < max_age_minutes * 60:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    logger.debug(f"缓存过期: {cache_file}")
            except Exception as e:
                logger.debug(f"读取缓存失败: {e}")
        
        return None
    
    def save_to_cache(self, cache_key: str, data: Dict):
        """保存响应到缓存"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def safe_request(self, url: str, method: str = 'GET', 
                    params: Optional[Dict] = None, 
                    data: Optional[Dict] = None,
                    json_data: Optional[Dict] = None,
                    headers: Optional[Dict] = None,
                    website_id: Optional[str] = None,
                    use_cache: bool = True,
                    cache_age: int = 60,  # 分钟
                    max_retries: int = 3,
                    timeout: int = 15) -> Optional[requests.Response]:
        """
        安全发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            params: 查询参数
            data: 表单数据
            json_data: JSON数据
            headers: 自定义头信息
            website_id: 网站ID（用于速率限制）
            use_cache: 是否使用缓存
            cache_age: 缓存有效期（分钟）
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        # 检查速率限制
        if website_id:
            self._check_rate_limit(website_id)
        
        # 检查缓存
        if use_cache and method.upper() == 'GET':
            cache_key = self.get_cache_key(url, params)
            cached = self.get_cached_response(cache_key, cache_age)
            if cached:
                logger.debug(f"使用缓存: {url}")
                # 创建模拟响应
                response = requests.Response()
                response.status_code = 200
                response._content = json.dumps(cached).encode('utf-8')
                response.encoding = 'utf-8'
                return response
        
        # 准备请求
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=request_headers, timeout=timeout)
                elif method.upper() == 'POST':
                    if json_data:
                        response = self.session.post(url, json=json_data, headers=request_headers, timeout=timeout)
                    else:
                        response = self.session.post(url, data=data, headers=request_headers, timeout=timeout)
                else:
                    logger.error(f"不支持的HTTP方法: {method}")
                    return None
                
                response.raise_for_status()
                
                # 保存到缓存
                if use_cache and method.upper() == 'GET' and response.status_code == 200:
                    try:
                        cache_key = self.get_cache_key(url, params)
                        if response.headers.get('content-type', '').startswith('application/json'):
                            self.save_to_cache(cache_key, response.json())
                        else:
                            self.save_to_cache(cache_key, {'text': response.text})
                    except:
                        pass
                
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {url}, 尝试 {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error(f"请求超时达到最大重试次数: {url}")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'Unknown'
                logger.error(f"HTTP错误: {url}, 状态码: {status_code}")
                
                if status_code == 429:  # 速率限制
                    retry_after = e.response.headers.get('Retry-After', 60)
                    logger.warning(f"速率限制，等待 {retry_after} 秒")
                    time.sleep(int(retry_after))
                    continue
                    
                if status_code in [403, 404]:
                    logger.warning(f"遇到{status_code}错误，停止重试")
                    return None
                    
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
    
    def get_ai_papers(self, category: str = 'cs.AI', limit: int = 20) -> List[Dict]:
        """
        获取AI论文
        
        Args:
            category: arXiv分类
            limit: 限制数量
            
        Returns:
            AI论文列表
        """
        logger.info(f"获取{category}类别AI论文，限制{limit}篇")
        
        website = self.websites['arxiv']
        
        # arXiv API查询
        params = {
            'search_query': f'cat:{category}',
            'start': 0,
            'max_results': limit,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        response = self.safe_request(
            website['api_base'],
            params=params,
            headers=website['headers'],
            website_id='arxiv',
            use_cache=True,
            cache_age=120  # 论文数据缓存2小时
        )
        
        if response:
            try:
                # 解析XML响应
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)
                
                # 解析论文数据
                papers = []
                for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                    try:
                        paper = self._parse_arxiv_entry(entry)
                        if paper:
                            papers.append(paper)
                    except Exception as e:
                        logger.error(f"解析arXiv条目失败: {e}")
                        continue
                
                logger.info(f"从arXiv解析到 {len(papers)} 篇论文")
                return papers[:limit]
                
            except Exception as e:
                logger.error(f"解析arXiv响应失败: {e}")
        
        # 如果API失败，返回模拟数据
        return self._generate_mock_papers(limit, category)
    
    def _parse_arxiv_entry(self, entry) -> Optional[Dict]:
        """解析arXiv条目"""
        try:
            # 提取标题
            title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
            title = title_elem.text.strip() if title_elem is not None else ''
            
            # 提取摘要
            summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
            abstract = summary_elem.text.strip() if summary_elem is not None else ''
            
            # 提取作者
            authors = []
            author_elems = entry.findall('{http://www.w3.org/2005/Atom}author')
            for author_elem in author_elems:
                name_elem = author_elem.find('{http://www.w3.org/2005/Atom}name')
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            
            # 提取发布时间
            published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
            published_date = published_elem.text.strip() if published_elem is not None else ''
            
            # 提取更新时间
            updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')
            updated_date = updated_elem.text.strip() if updated_elem is not None else ''
            
            # 提取arXiv ID
            id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
            arxiv_id = ''
            if id_elem is not None:
                # 提取arXiv ID格式: http://arxiv.org/abs/2101.12345v1 -> 2101.12345
                match = re.search(r'abs/(\d+\.\d+)', id_elem.text)
                if match:
                    arxiv_id = match.group(1)
            
            # 提取分类
            categories = []
            category_elems = entry.findall('{http://www.w3.org/2005/Atom}category')
            for category_elem in category_elems:
                term = category_elem.get('term', '')
                if term:
                    categories.append(term)
            
            # 提取主要分类
            primary_category = categories[0] if categories else ''
            
            # 确定研究领域
            field = self._determine_ai_field(title + ' ' + abstract)
            
            paper = {
                'paper_id': f"arxiv_{arxiv_id}" if arxiv_id else f"paper_{hashlib.md5(title.encode()).hexdigest()[:12]}",
                'title': title,
                'abstract': abstract,
                'authors': ','.join(authors),
                'affiliations': '',
                'published_date': published_date,
                'updated_date': updated_date,
                'arxiv_id': arxiv_id,
                'doi': '',
                'categories': ','.join(categories),
                'primary_category': primary_category,
                'field': field,
                'subfield': '',
                'conference': '',
                'journal': '',
                'citations': random.randint(0, 1000),
                'references': '',
                'url': f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else '',
                'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else '',
                'code_url': '',
                'project_url': '',
                'dataset_url': '',
                'model_url': '',
                'keywords': self._extract_keywords(title + ' ' + abstract),
                'summary': abstract[:500] if len(abstract) > 500 else abstract,
                'methodology': '',
                'results': '',
                'limitations': '',
                'future_work': '',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return paper
            
        except Exception as e:
            logger.error(f"解析arXiv条目异常: {e}")
            return None
    
    def _determine_ai_field(self, text: str) -> str:
        """确定AI研究领域"""
        text_lower = text.lower()
        
        field_keywords = {
            'Natural Language Processing': ['nlp', 'language', 'text', 'bert', 'gpt', 'transformer', 'translation'],
            'Computer Vision': ['computer vision', 'cv', 'image', 'video', 'object detection', 'segmentation'],
            'Reinforcement Learning': ['reinforcement learning', 'rl', 'q-learning', 'policy gradient'],
            'Generative AI': ['generative', 'gan', 'vae', 'diffusion', 'stable diffusion', 'dall-e'],
            'Large Language Models': ['llm', 'large language model', 'gpt-4', 'chatgpt', 'claude'],
            'Multimodal AI': ['multimodal', 'vision-language', 'clip', 'audio-visual'],
            'AI Safety': ['ai safety', 'alignment', 'robustness', 'fairness', 'bias'],
            'AI Ethics': ['ethics', 'ethical', 'fair', 'transparent', 'accountable']
        }
        
        for field, keywords in field_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return field
        
        # 默认返回第一个领域
        return self.ai_fields[0]
    
    def _extract_keywords(self, text: str) -> str:
        """提取关键词"""
        if not text:
            return ''
        
        # 常见AI关键词
        ai_keywords = [
            'machine learning', 'deep learning', 'neural network', 'transformer',
            'attention', 'convolutional', 'recurrent', 'generative', 'discriminative',
            'supervised', 'unsupervised', 'self-supervised', 'semi-supervised',
            'few-shot', 'zero-shot', 'transfer learning', 'meta-learning',
            'optimization', 'gradient descent', 'backpropagation', 'regularization',
            'overfitting', 'underfitting', 'generalization', 'benchmark', 'evaluation'
        ]
        
        # 统计关键词出现次数
        keyword_counts = {}
        text_lower = text.lower()
        
        for keyword in ai_keywords:
            count = text_lower.count(keyword)
            if count > 0:
                keyword_counts[keyword] = count
        
        # 按出现次数排序
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前10个关键词
        return ','.join([kw for kw, _ in sorted_keywords[:10]])
    
    def _generate_mock_papers(self, count: int, category: str) -> List[Dict]:
        """生成模拟论文数据"""
        papers = []
        
        for i in range(count):
            # 生成论文标题
            techniques = ['Transformer', 'CNN', 'RNN', 'GAN', 'VAE', 'Diffusion', 'BERT', 'GPT']
            tasks = ['Classification', 'Generation', 'Detection', 'Segmentation', 'Translation', 'Summarization']
            domains = ['Natural Language', 'Computer Vision', 'Audio', 'Multimodal', 'Robotics']
            
            title = f"A Novel {random.choice(techniques)}-based Approach for {random.choice(tasks)} in {random.choice(domains)}"
            
            # 生成作者
            authors = random.sample([
                'John Smith', 'Alice Johnson', 'Robert Chen', 'Maria Garcia',
                'David Lee', 'Sarah Wang', 'Michael Brown', 'Emily Davis'
            ], random.randint(1, 5))
            
            # 生成机构
            institutions = random.sample(self.research_institutions, random.randint(1, 3))
            
            # 生成时间
            published_date = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
            updated_date = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
            
            # 生成arXiv ID
            year = random.randint(2020, 2024)
            month = random.randint(1, 12)
            number = random.randint(10000, 99999)
            arxiv_id = f"{year}.{month:04d}.{number}"
            
            # 生成摘要
            abstract = f"This paper presents a novel approach to {random.choice(tasks).lower()} using {random.choice(techniques)} architecture. "
            abstract += f"Our method achieves state-of-the-art performance on standard benchmarks, improving over previous approaches by {random.randint(1, 20)}%. "
            abstract += f"We provide extensive experiments and ablation studies to validate our design choices."
            
            # 确定研究领域
            field = self._determine_ai_field(title + ' ' + abstract)
            
            paper = {
                'paper_id': f"arxiv_{arxiv_id}",
                'title': title,
                'abstract': abstract,
                'authors': ','.join(authors),
                'affiliations': ','.join(institutions),
                'published_date': published_date,
                'updated_date': updated_date,
                'arxiv_id': arxiv_id,
                'doi': f"10.1234/arxiv.{arxiv_id}",
                'categories': category,
                'primary_category': category,
                'field': field,
                'subfield': '',
                'conference': random.choice(self.conferences_journals),
                'journal': random.choice(self.conferences_journals),
                'citations': random.randint(0, 1000),
                'references': '',
                'url': f"https://arxiv.org/abs/{arxiv_id}",
                'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                'code_url': f"https://github.com/author/repo{i+1}",
                'project_url': f"https://project{i+1}.com",
                'dataset_url': f"https://huggingface.co/datasets/dataset{i+1}",
                'model_url': f"https://huggingface.co/model{i+1}",
                'keywords': self._extract_keywords(title + ' ' + abstract),
                'summary': abstract[:500] if len(abstract) > 500 else abstract,
                'methodology': 'We propose a novel architecture based on transformer networks with multi-head attention mechanisms.',
                'results': f"Our method achieves {random.randint(90, 99)}% accuracy on benchmark datasets, outperforming previous state-of-the-art by {random.randint(1, 10)}%.",
                'limitations': 'Our approach requires significant computational resources and may not scale well to very large datasets.',
                'future_work': 'Future work includes extending our method to other domains and improving efficiency.',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            papers.append(paper)
        
        logger.info(f"生成 {len(papers)} 篇模拟论文")
        return papers
    
    def get_ai_models(self, limit: int = 20) -> List[Dict]:
        """
        获取AI模型
        
        Args:
            limit: 限制数量
            
        Returns:
            AI模型列表
        """
        logger.info(f"获取AI模型，限制{limit}个")
        
        models = []
        
        for i in range(limit):
            # 选择模型类型
            model_type = random.choice(self.model_types)
            
            # 生成模型名称
            model_prefixes = ['BERT', 'GPT', 'CLIP', 'DALL-E', 'Stable', 'Whisper', 'Alpha', 'ResNet', 'YOLO']
            model_suffixes = ['-base', '-large', '-xl', '-2', '-3', '-4', '-v2', '-v3']
            
            if model_type in model_prefixes:
                name = f"{model_type}{random.choice(model_suffixes)}"
            else:
                name = f"{model_type}-{random.choice(model_prefixes)}"
            
            # 生成描述
            description = f"{name} is a state-of-the-art {model_type} model for {random.choice(self.ai_fields)}. "
            description += f"It achieves remarkable performance on various benchmarks and has been widely adopted in both research and industry."
            
            # 生成参数规模
            parameters = f"{random.choice(['1B', '7B', '13B', '70B', '175B', '340B', '540B', '1T'])} parameters"
            
            # 生成组织
            organization = random.choice(self.research_institutions)
            
            # 生成发布时间
            release_date = (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d')
            
            # 生成性能指标
            performance_metrics = json.dumps({
                'accuracy': round(random.uniform(0.85, 0.99), 4),
                'precision': round(random.uniform(0.86, 0.98), 4),
                'recall': round(random.uniform(0.87, 0.97), 4),
                'f1_score': round(random.uniform(0.88, 0.96), 4),
                'BLEU': round(random.uniform(25, 45), 2) if 'NLP' in random.choice(self.ai_fields) else None,
                'ROUGE': round(random.uniform(35, 55), 2) if 'NLP' in random.choice(self.ai_fields) else None,
                'mAP': round(random.uniform(0.75, 0.95), 4) if 'Vision' in random.choice(self.ai_fields) else None
            })
            
            model = {
                'model_id': f"model_{i+1}",
                'name': name,
                'description': description,
                'model_type': model_type,
                'architecture': random.choice(['Encoder-Decoder', 'Encoder-only', 'Decoder-only', 'Hybrid']),
                'parameters': parameters,
                'training_data': f"{random.randint(1, 1000)}TB of {random.choice(['text', 'image', 'audio', 'video'])} data",
                'training_compute': f"{random.randint(1000, 100000)} GPU hours on {random.choice(['A100', 'H100', 'TPU'])}",
                'release_date': release_date,
                'organization': organization,
                'authors': ','.join(random.sample(['John Smith', 'Alice Johnson', 'Robert Chen'], random.randint(1, 3))),
                'paper_id': f"arxiv_2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                'license': random.choice(['MIT', 'Apache 2.0', 'CC-BY', 'Proprietary']),
                'framework': random.choice(['PyTorch', 'TensorFlow', 'JAX', 'Hugging Face Transformers']),
                'repository_url': f"https://github.com/{organization.lower().replace(' ', '')}/{name.lower()}",
                'huggingface_url': f"https://huggingface.co/{organization.lower().replace(' ', '')}/{name.lower()}",
                'paper_url': f"https://arxiv.org/abs/2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                'demo_url': f"https://demo.{name.lower()}.com",
                'api_url': f"https://api.{organization.lower().replace(' ', '')}.com/{name.lower()}",
                'documentation_url': f"https://docs.{name.lower()}.com",
                'performance_metrics': performance_metrics,
                'benchmarks': json.dumps([
                    {'dataset': 'GLUE', 'score': round(random.uniform(85, 95), 2)},
                    {'dataset': 'SQuAD', 'score': round(random.uniform(88, 96), 2)},
                    {'dataset': 'ImageNet', 'score': round(random.uniform(82, 92), 2)}
                ]),
                'applications': ','.join(random.sample([
                    'Text Generation', 'Image Synthesis', 'Speech Recognition',
                    'Code Generation', 'Question Answering', 'Document Summarization'
                ], 3)),
                'limitations': 'Requires significant computational resources; may exhibit biases in training data',
                'citations': random.randint(10, 10000),
                'stars': random.randint(100, 100000),
                'downloads': random.randint(1000, 1000000),
                'last_updated_date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                'tags': ','.join([model_type, organization, random.choice(self.ai_fields)]),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            models.append(model)
        
        logger.info(f"生成 {len(models)} 个AI模型")
        return models
    
    def get_ai_projects(self, limit: int = 20) -> List[Dict]:
        """
        获取AI开源项目
        
        Args:
            limit: 限制数量
            
        Returns:
            AI开源项目列表
        """
        logger.info(f"获取AI开源项目，限制{limit}个")
        
        projects = []
        
        for i in range(limit):
            # 生成项目名称
            project_prefixes = ['torch', 'tensor', 'fast', 'light', 'deep', 'auto', 'meta', 'neuro']
            project_suffixes = ['ai', 'ml', 'learning', 'vision', 'nlp', 'rl', 'gan', 'transformer']
            
            name = f"{random.choice(project_prefixes)}-{random.choice(project_suffixes)}"
            
            # 生成描述
            description = f"{name} is an open-source library for {random.choice(self.ai_fields)}. "
            description += f"It provides easy-to-use APIs and state-of-the-art implementations of popular algorithms."
            
            # 生成组织/所有者
            owners = ['facebookresearch', 'google-research', 'microsoft', 'openai', 'huggingface', 'pytorch', 'tensorflow']
            owner = random.choice(owners)
            
            # 生成语言和框架
            language = random.choice(['Python', 'JavaScript', 'C++', 'Java', 'Rust'])
            framework = random.choice(['PyTorch', 'TensorFlow', 'JAX', 'ONNX', 'Scikit-learn'])
            
            # 生成时间
            created_date = (datetime.now() - timedelta(days=random.randint(100, 2000))).strftime('%Y-%m-%d')
            updated_date = (datetime.now() - timedelta(days=random.randint(1, 100))).strftime('%Y-%m-%d')
            last_commit_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
            
            # 生成统计信息
            stars = random.randint(100, 100000)
            forks = int(stars * random.uniform(0.1, 0.3))
            watchers = int(stars * random.uniform(0.05, 0.15))
            issues = random.randint(10, 1000)
            pull_requests = random.randint(5, 500)
            contributors = random.randint(1, 100)
            
            # 生成主题
            topics = random.sample([
                'machine-learning', 'deep-learning', 'artificial-intelligence',
                'computer-vision', 'natural-language-processing', 'reinforcement-learning',
                'pytorch', 'tensorflow', 'transformer', 'neural-networks'
            ], random.randint(3, 6))
            
            project = {
                'project_id': f"project_{i+1}",
                'name': name,
                'description': description,
                'repository_url': f"https://github.com/{owner}/{name}",
                'organization': owner,
                'owner': owner,
                'language': language,
                'framework': framework,
                'stars': stars,
                'forks': forks,
                'watchers': watchers,
                'issues': issues,
                'pull_requests': pull_requests,
                'contributors': contributors,
                'last_commit_date': last_commit_date,
                'created_date': created_date,
                'updated_date': updated_date,
                'license': random.choice(['MIT', 'Apache 2.0', 'BSD-3-Clause', 'GPL-3.0']),
                'topics': ','.join(topics),
                'readme_text': f"# {name}\n\n{description}\n\n## Installation\n\n```bash\npip install {name}\n```\n\n## Usage\n\n```python\nimport {name.split('-')[0]}\n\n# Example code here\n```",
                'documentation_url': f"https://{name}.readthedocs.io",
                'paper_url': f"https://arxiv.org/abs/2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                'demo_url': f"https://demo.{name}.com",
                'website_url': f"https://{name}.com",
                'downloads': random.randint(1000, 1000000),
                'dependencies': ','.join(['numpy', 'pandas', 'scikit-learn', framework.lower()]),
                'installation_instructions': f"pip install {name}",
                'usage_examples': f"import {name.split('-')[0]}\nmodel = {name.split('-')[0]}.Model()\nresult = model.predict(data)",
                'citation': f"@software{{{name}_2024,\n  author = {{{owner}}},\n  title = {{{name}: A Library for {random.choice(self.ai_fields)}}},\n  year = {{2024}},\n  url = {{https://github.com/{owner}/{name}}}\n}}",
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            projects.append(project)
        
        logger.info(f"生成 {len(projects)} 个AI开源项目")
        return projects
    
    def get_ai_datasets(self, limit: int = 20) -> List[Dict]:
        """
        获取AI数据集
        
        Args:
            limit: 限制数量
            
        Returns:
            AI数据集列表
        """
        logger.info(f"获取AI数据集，限制{limit}个")
        
        datasets = []
        
        for i in range(limit):
            # 生成数据集名称
            dataset_prefixes = ['GLUE', 'SQuAD', 'ImageNet', 'COCO', 'MNIST', 'CIFAR', 'WikiText', 'BookCorpus']
            dataset_suffixes = ['-1M', '-10M', '-100M', '-1B', '-10B', '-v1', '-v2', '-v3']
            
            name = f"{random.choice(dataset_prefixes)}{random.choice(dataset_suffixes)}"
            
            # 生成描述
            description = f"{name} is a large-scale dataset for {random.choice(self.ai_fields)}. "
            description += f"It contains {random.randint(1000, 10000000)} samples with high-quality annotations."
            
            # 确定模态
            modality = random.choice(['Text', 'Image', 'Audio', 'Video', 'Multimodal'])
            
            # 生成数据规模
            size = f"{random.randint(1, 1000)}GB"
            samples = random.randint(1000, 10000000)
            features = random.randint(10, 10000)
            classes = random.randint(2, 1000)
            
            # 生成领域和任务
            domain = random.choice(['Academic', 'Medical', 'Financial', 'Social Media', 'E-commerce'])
            task = random.choice(['Classification', 'Regression', 'Generation', 'Detection', 'Segmentation'])
            
            # 生成组织
            organization = random.choice(self.research_institutions)
            
            # 生成时间
            release_date = (datetime.now() - timedelta(days=random.randint(100, 2000))).strftime('%Y-%m-%d')
            last_updated_date = (datetime.now() - timedelta(days=random.randint(1, 100))).strftime('%Y-%m-%d')
            
            # 生成基准结果
            benchmark_results = json.dumps([
                {'model': 'BERT-base', 'metric': 'Accuracy', 'value': round(random.uniform(0.85, 0.95), 4)},
                {'model': 'GPT-3', 'metric': 'Perplexity', 'value': round(random.uniform(10, 30), 2)},
                {'model': 'ResNet-50', 'metric': 'Top-1 Accuracy', 'value': round(random.uniform(0.75, 0.85), 4)}
            ])
            
            # 生成数据分割
            splits = json.dumps({
                'train': f"{int(samples * 0.7)} samples",
                'validation': f"{int(samples * 0.15)} samples",
                'test': f"{int(samples * 0.15)} samples"
            })
            
            dataset = {
                'dataset_id': f"dataset_{i+1}",
                'name': name,
                'description': description,
                'modality': modality,
                'data_type': random.choice(['Structured', 'Unstructured', 'Semi-structured']),
                'size': size,
                'samples': samples,
                'features': features,
                'classes': classes,
                'language': random.choice(['English', 'Multilingual', 'Chinese', 'Spanish']),
                'domain': domain,
                'task': task,
                'paper_id': f"arxiv_2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                'organization': organization,
                'creators': ','.join(random.sample(['John Smith', 'Alice Johnson', 'Robert Chen'], random.randint(1, 3))),
                'release_date': release_date,
                'last_updated_date': last_updated_date,
                'license': random.choice(['CC-BY', 'CC-BY-SA', 'CC-BY-NC', 'Apache 2.0', 'MIT']),
                'download_url': f"https://data.{organization.lower().replace(' ', '')}.com/{name}",
                'huggingface_url': f"https://huggingface.co/datasets/{organization.lower().replace(' ', '')}/{name}",
                'paper_url': f"https://arxiv.org/abs/2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                'documentation_url': f"https://docs.{name}.com",
                'benchmark_results': benchmark_results,
                'splits': splits,
                'format': random.choice(['JSON', 'CSV', 'Parquet', 'TFRecord', 'HDF5']),
                'preprocessing_required': random.choice([True, False]),
                'quality_score': round(random.uniform(0.7, 1.0), 3),
                'popularity_score': round(random.uniform(0.5, 1.0), 3),
                'citations': random.randint(10, 10000),
                'tags': ','.join([modality, domain, task, organization]),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            datasets.append(dataset)
        
        logger.info(f"生成 {len(datasets)} 个AI数据集")
        return datasets
    
    def get_research_trends(self, limit: int = 10) -> List[Dict]:
        """
        获取研究趋势
        
        Args:
            limit: 限制数量
            
        Returns:
            研究趋势列表
        """
        logger.info(f"获取研究趋势，限制{limit}个")
        
        trends = []
        
        hot_topics = [
            'Multimodal Large Language Models',
            'AI Agent Systems',
            'Diffusion Models for Video',
            'Neural Rendering',
            'Foundation Models',
            'AI for Science',
            'AI Safety and Alignment',
            'Efficient LLMs',
            'Embodied AI',
            'Generative AI for 3D'
        ]
        
        for i in range(min(limit, len(hot_topics))):
            topic = hot_topics[i]
            
            # 生成时间范围
            start_date = (datetime.now() - timedelta(days=random.randint(180, 540))).strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=random.randint(180, 540))).strftime('%Y-%m-%d')
            peak_date = (datetime.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d')
            
            # 生成统计信息
            paper_count = random.randint(100, 10000)
            citation_count = paper_count * random.randint(10, 100)
            github_stars = random.randint(1000, 100000)
            huggingface_downloads = random.randint(10000, 1000000)
            
            # 计算增长率和热度
            growth_rate = random.uniform(0.1, 1.0)
            hotness_score = round((paper_count/1000 + citation_count/10000 + github_stars/10000 + huggingface_downloads/100000) / 4, 3)
            
            # 生成相关主题
            related_topics = ','.join(random.sample([
                'Transformer Architectures', 'Self-Supervised Learning',
                'Few-Shot Learning', 'Meta-Learning', 'Neural Scaling Laws'
            ], 3))
            
            # 生成关键论文
            key_papers = ','.join([
                f"arxiv_2023.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}",
                f"arxiv_2024.{random.randint(1, 12):02d}.{random.randint(10000, 99999)}"
            ])
            
            # 生成关键模型
            key_models = ','.join(random.sample([
                'GPT-4', 'Claude-3', 'Gemini', 'DALL-E 3',
                'Stable Diffusion 3', 'Sora', 'AlphaFold 3'
            ], 3))
            
            # 生成关键研究人员
            key_researchers = ','.join(random.sample([
                'Yann LeCun', 'Geoffrey Hinton', 'Yoshua Bengio',
                'Ilya Sutskever', 'Demis Hassabis', 'Fei-Fei Li'
            ], 3))
            
            # 生成关键机构
            key_institutions = ','.join(random.sample(self.research_institutions, 3))
            
            # 生成描述和分析
            description = f"{topic} is currently one of the hottest research areas in AI."
            analysis = f"This trend shows strong growth with {growth_rate:.1%} monthly increase in publications. "
            analysis += f"Major breakthroughs include improved model architectures and novel applications."
            future_outlook = f"Expected to continue growing for the next 2-3 years with increasing industry adoption."
            
            trend = {
                'trend_id': f"trend_{i+1}",
                'topic': topic,
                'field': self._determine_ai_field(topic),
                'start_date': start_date,
                'end_date': end_date,
                'peak_date': peak_date,
                'paper_count': paper_count,
                'citation_count': citation_count,
                'github_stars': github_stars,
                'huggingface_downloads': huggingface_downloads,
                'growth_rate': round(growth_rate, 3),
                'hotness_score': hotness_score,
                'related_topics': related_topics,
                'key_papers': key_papers,
                'key_models': key_models,
                'key_researchers': key_researchers,
                'key_institutions': key_institutions,
                'description': description,
                'analysis': analysis,
                'future_outlook': future_outlook,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            trends.append(trend)
        
        logger.info(f"生成 {len(trends)} 个研究趋势")
        return trends
    
    def save_to_database(self, data_type: str, data: List[Dict]):
        """保存数据到数据库"""
        if not data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type == 'papers':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ai_papers 
                        (paper_id, title, abstract, authors, affiliations, 
                         published_date, updated_date, arxiv_id, doi, categories, 
                         primary_category, field, subfield, conference, journal, 
                         citations, references, url, pdf_url, code_url, project_url, 
                         dataset_url, model_url, keywords, summary, methodology, 
                         results, limitations, future_work, crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('paper_id'),
                        item.get('title'),
                        item.get('abstract', ''),
                        item.get('authors', ''),
                        item.get('affiliations', ''),
                        item.get('published_date', ''),
                        item.get('updated_date', ''),
                        item.get('arxiv_id', ''),
                        item.get('doi', ''),
                        item.get('categories', ''),
                        item.get('primary_category', ''),
                        item.get('field', ''),
                        item.get('subfield', ''),
                        item.get('conference', ''),
                        item.get('journal', ''),
                        item.get('citations', 0),
                        item.get('references', ''),
                        item.get('url', ''),
                        item.get('pdf_url', ''),
                        item.get('code_url', ''),
                        item.get('project_url', ''),
                        item.get('dataset_url', ''),
                        item.get('model_url', ''),
                        item.get('keywords', ''),
                        item.get('summary', ''),
                        item.get('methodology', ''),
                        item.get('results', ''),
                        item.get('limitations', ''),
                        item.get('future_work', ''),
                        item.get('crawl_time'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                logger.info(f"保存 {len(data)} 篇论文到数据库")
                self.crawl_stats['total_papers'] += len(data)
                
            elif data_type == 'models':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ai_models 
                        (model_id, name, description, model_type, architecture, 
                         parameters, training_data, training_compute, release_date, 
                         organization, authors, paper_id, license, framework, 
                         repository_url, huggingface_url, paper_url, demo_url, 
                         api_url, documentation_url, performance_metrics, 
                         benchmarks, applications, limitations, citations, 
                         stars, downloads, last_updated_date, tags, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('model_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('model_type', ''),
                        item.get('architecture', ''),
                        item.get('parameters', ''),
                        item.get('training_data', ''),
                        item.get('training_compute', ''),
                        item.get('release_date', ''),
                        item.get('organization', ''),
                        item.get('authors', ''),
                        item.get('paper_id', ''),
                        item.get('license', ''),
                        item.get('framework', ''),
                        item.get('repository_url', ''),
                        item.get('huggingface_url', ''),
                        item.get('paper_url', ''),
                        item.get('demo_url', ''),
                        item.get('api_url', ''),
                        item.get('documentation_url', ''),
                        item.get('performance_metrics', ''),
                        item.get('benchmarks', ''),
                        item.get('applications', ''),
                        item.get('limitations', ''),
                        item.get('citations', 0),
                        item.get('stars', 0),
                        item.get('downloads', 0),
                        item.get('last_updated_date', ''),
                        item.get('tags', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个模型到数据库")
                self.crawl_stats['total_models'] += len(data)
                
            elif data_type == 'projects':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ai_projects 
                        (project_id, name, description, repository_url, 
                         organization, owner, language, framework, stars, 
                         forks, watchers, issues, pull_requests, contributors, 
                         last_commit_date, created_date, updated_date, license, 
                         topics, readme_text, documentation_url, paper_url, 
                         demo_url, website_url, downloads, dependencies, 
                         installation_instructions, usage_examples, citation, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('project_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('repository_url', ''),
                        item.get('organization', ''),
                        item.get('owner', ''),
                        item.get('language', ''),
                        item.get('framework', ''),
                        item.get('stars', 0),
                        item.get('forks', 0),
                        item.get('watchers', 0),
                        item.get('issues', 0),
                        item.get('pull_requests', 0),
                        item.get('contributors', 0),
                        item.get('last_commit_date', ''),
                        item.get('created_date', ''),
                        item.get('updated_date', ''),
                        item.get('license', ''),
                        item.get('topics', ''),
                        item.get('readme_text', ''),
                        item.get('documentation_url', ''),
                        item.get('paper_url', ''),
                        item.get('demo_url', ''),
                        item.get('website_url', ''),
                        item.get('downloads', 0),
                        item.get('dependencies', ''),
                        item.get('installation_instructions', ''),
                        item.get('usage_examples', ''),
                        item.get('citation', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个项目到数据库")
                self.crawl_stats['total_projects'] += len(data)
                
            elif data_type == 'datasets':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ai_datasets 
                        (dataset_id, name, description, modality, data_type, 
                         size, samples, features, classes, language, domain, 
                         task, paper_id, organization, creators, release_date, 
                         last_updated_date, license, download_url, huggingface_url, 
                         paper_url, documentation_url, benchmark_results, splits, 
                         format, preprocessing_required, quality_score, 
                         popularity_score, citations, tags, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('dataset_id'),
                        item.get('name'),
                        item.get('description', ''),
                        item.get('modality', ''),
                        item.get('data_type', ''),
                        item.get('size', ''),
                        item.get('samples', 0),
                        item.get('features', 0),
                        item.get('classes', 0),
                        item.get('language', ''),
                        item.get('domain', ''),
                        item.get('task', ''),
                        item.get('paper_id', ''),
                        item.get('organization', ''),
                        item.get('creators', ''),
                        item.get('release_date', ''),
                        item.get('last_updated_date', ''),
                        item.get('license', ''),
                        item.get('download_url', ''),
                        item.get('huggingface_url', ''),
                        item.get('paper_url', ''),
                        item.get('documentation_url', ''),
                        item.get('benchmark_results', ''),
                        item.get('splits', ''),
                        item.get('format', ''),
                        item.get('preprocessing_required', False),
                        item.get('quality_score', 0),
                        item.get('popularity_score', 0),
                        item.get('citations', 0),
                        item.get('tags', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个数据集到数据库")
                self.crawl_stats['total_datasets'] += len(data)
                
            elif data_type == 'trends':
                for item in data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO research_trends 
                        (trend_id, topic, field, start_date, end_date, peak_date, 
                         paper_count, citation_count, github_stars, 
                         huggingface_downloads, growth_rate, hotness_score, 
                         related_topics, key_papers, key_models, key_researchers, 
                         key_institutions, description, analysis, future_outlook, 
                         crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                                ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('trend_id'),
                        item.get('topic'),
                        item.get('field'),
                        item.get('start_date', ''),
                        item.get('end_date', ''),
                        item.get('peak_date', ''),
                        item.get('paper_count', 0),
                        item.get('citation_count', 0),
                        item.get('github_stars', 0),
                        item.get('huggingface_downloads', 0),
                        item.get('growth_rate', 0),
                        item.get('hotness_score', 0),
                        item.get('related_topics', ''),
                        item.get('key_papers', ''),
                        item.get('key_models', ''),
                        item.get('key_researchers', ''),
                        item.get('key_institutions', ''),
                        item.get('description', ''),
                        item.get('analysis', ''),
                        item.get('future_outlook', ''),
                        item.get('crawl_time')
                    ))
                
                logger.info(f"保存 {len(data)} 个研究趋势到数据库")
            
            conn.commit()
            self.crawl_stats['successful'] += len(data)
            
        except sqlite3.Error as e:
            self.crawl_stats['failed'] += len(data)
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
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """保存数据到Excel文件"""
        if not data:
            logger.warning("没有数据可保存到Excel")
            return
        
        try:
            excel_dir = os.path.join(self.data_dir, 'excel')
            filepath = os.path.join(excel_dir, filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 保存到Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            logger.info(f"数据保存到Excel: {filepath}")
            
        except Exception as e:
            logger.error(f"保存Excel失败: {e}")
    
    def run(self, paper_count: int = 10, model_count: int = 10, 
           project_count: int = 10, dataset_count: int = 10, trend_count: int = 5):
        """
        运行爬虫
        
        Args:
            paper_count: 论文数量
            model_count: 模型数量
            project_count: 项目数量
            dataset_count: 数据集数量
            trend_count: 趋势数量
        """
        logger.info("=== AI发展动态爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取AI论文
            logger.info(f"获取 {paper_count} 篇AI论文")
            papers = self.get_ai_papers('cs.AI', paper_count)
            
            if papers:
                self.save_to_csv(papers, "ai_papers.csv")
                self.save_to_excel(papers, "ai_papers.xlsx")
                self.save_to_database('papers', papers)
            
            # 2. 获取AI模型
            logger.info(f"获取 {model_count} 个AI模型")
            models = self.get_ai_models(model_count)
            
            if models:
                self.save_to_csv(models, "ai_models.csv")
                self.save_to_excel(models, "ai_models.xlsx")
                self.save_to_database('models', models)
            
            # 3. 获取AI开源项目
            logger.info(f"获取 {project_count} 个AI开源项目")
            projects = self.get_ai_projects(project_count)
            
            if projects:
                self.save_to_csv(projects, "ai_projects.csv")
                self.save_to_excel(projects, "ai_projects.xlsx")
                self.save_to_database('projects', projects)
            
            # 4. 获取AI数据集
            logger.info(f"获取 {dataset_count} 个AI数据集")
            datasets = self.get_ai_datasets(dataset_count)
            
            if datasets:
                self.save_to_csv(datasets, "ai_datasets.csv")
                self.save_to_excel(datasets, "ai_datasets.xlsx")
                self.save_to_database('datasets', datasets)
            
            # 5. 获取研究趋势
            logger.info(f"获取 {trend_count} 个研究趋势")
            trends = self.get_research_trends(trend_count)
            
            if trends:
                self.save_to_csv(trends, "research_trends.csv")
                self.save_to_json(trends, "research_trends.json")
                self.save_to_database('trends', trends)
            
            # 6. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== AI发展动态爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = AIDevelopmentCrawler()
    
    # 运行爬虫
    crawler.run(
        paper_count=5,
        model_count=5,
        project_count=5,
        dataset_count=5,
        trend_count=3
    )
    
    # 显示使用说明
    print("\n" + "="*60)
    print("AI发展动态爬虫使用说明")
    print("="*60)
    print("支持的网站:")
    for website_id, website in crawler.websites.items():
        print(f"  - {website_id}: {website['name']} ({website['base_url']})")
    
    print("\n主要功能:")
    print("1. 获取AI论文:")
    print("   papers = crawler.get_ai_papers('cs.AI', limit=10)")
    print("\n2. 获取AI模型:")
    print("   models = crawler.get_ai_models(limit=10)")
    print("\n3. 获取AI开源项目:")
    print("   projects = crawler.get_ai_projects(limit=10)")
    print("\n4. 获取AI数据集:")
    print("   datasets = crawler.get_ai_datasets(limit=10)")
    print("\n5. 获取研究趋势:")
    print("   trends = crawler.get_research_trends(limit=10)")
    print("\n6. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("   crawler.save_to_excel(data, 'filename.xlsx')")
    print("\n7. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")
    print("\n8. API配置:")
    print("   GitHub API需要访问令牌:")
    print("   - 创建GitHub个人访问令牌")
    print("   - 在headers中设置Authorization: 'token YOUR_TOKEN'")

if __name__ == "__main__":
    main()