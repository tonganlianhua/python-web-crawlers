#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术论文爬虫 - 获取学术论文信息
网站：arXiv、知网、Google Scholar等
功能：获取论文标题、作者、摘要、关键词、引用信息等
"""

import requests
import xml.etree.ElementTree as ET
import json
import time
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote, urlparse
import feedparser  # 用于解析RSS/Atom feed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperCrawler:
    """学术论文爬虫类"""
    
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
            'Accept': 'application/xml,application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        self.session.headers.update(self.headers)
        
        # 支持的学术平台配置
        self.platforms = {
            'arxiv': {
                'name': 'arXiv',
                'base_url': 'https://arxiv.org',
                'api_url': 'http://export.arxiv.org/api/query',
                'categories': {
                    'cs': 'Computer Science',
                    'math': 'Mathematics',
                    'physics': 'Physics',
                    'stat': 'Statistics',
                    'eess': 'Electrical Engineering and Systems Science',
                    'q-bio': 'Quantitative Biology',
                    'q-fin': 'Quantitative Finance',
                }
            },
            'cnki': {
                'name': '中国知网',
                'base_url': 'https://kns.cnki.net',
                'search_url': 'https://kns.cnki.net/kns8',
                'requires_login': True,  # 知网需要登录
            },
            'semanticscholar': {
                'name': 'Semantic Scholar',
                'base_url': 'https://api.semanticscholar.org',
                'api_url': 'https://api.semanticscholar.org/graph/v1',
                'api_key': None,  # 可以设置API key
            },
            'dblp': {
                'name': 'DBLP',
                'base_url': 'https://dblp.org',
                'search_url': 'https://dblp.org/search',
                'api_url': 'https://dblp.org/search/publ/api',
            },
            'ieee': {
                'name': 'IEEE Xplore',
                'base_url': 'https://ieeexplore.ieee.org',
                'search_url': 'https://ieeexplore.ieee.org/search',
                'requires_subscription': True,  # 需要订阅
            }
        }
    
    def search_arxiv_papers(self, query: str, max_results: int = 10, **kwargs) -> List[Dict]:
        """
        搜索arXiv论文
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            **kwargs: 其他参数
                - category: 分类（如：cs.AI）
                - sort_by: 排序方式（relevance, lastUpdatedDate, submittedDate）
                - sort_order: 排序顺序（ascending, descending）
            
        Returns:
            论文列表
        """
        try:
            api_url = self.platforms['arxiv']['api_url']
            
            # 构建查询参数
            params = {
                'search_query': query,
                'start': 0,
                'max_results': min(max_results, 100),
            }
            
            # 添加其他参数
            if 'category' in kwargs:
                params['search_query'] = f"cat:{kwargs['category']} AND {query}"
            
            if 'sort_by' in kwargs:
                params['sortBy'] = kwargs['sort_by']
            
            if 'sort_order' in kwargs:
                params['sortOrder'] = kwargs['sort_order']
            
            logger.info(f"正在搜索arXiv论文: {query}")
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析Atom feed
            feed = feedparser.parse(response.content)
            
            papers = []
            for entry in feed.entries[:max_results]:
                paper_info = self._parse_arxiv_entry(entry)
                if paper_info:
                    papers.append(paper_info)
            
            logger.info(f"成功搜索到 {len(papers)} 篇arXiv论文")
            return papers
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"搜索arXiv论文时发生错误: {str(e)}")
            return []
    
    def _parse_arxiv_entry(self, entry) -> Optional[Dict]:
        """解析arXiv条目"""
        try:
            paper_info = {
                'source': 'arXiv',
                'platform': 'arxiv',
            }
            
            # arXiv ID
            if 'id' in entry:
                paper_info['arxiv_id'] = entry.id.split('/')[-1]
                paper_info['url'] = entry.id
            
            # 标题
            if 'title' in entry:
                paper_info['title'] = entry.title.strip()
            
            # 摘要
            if 'summary' in entry:
                paper_info['abstract'] = entry.summary.strip()
            
            # 作者
            if 'authors' in entry:
                authors = []
                for author in entry.authors:
                    authors.append(author.name)
                paper_info['authors'] = authors
            
            # 发布时间
            if 'published' in entry:
                paper_info['published_date'] = entry.published
                
                # 转换为datetime对象
                try:
                    from dateutil import parser
                    paper_info['published_datetime'] = parser.parse(entry.published).isoformat()
                except:
                    pass
            
            # 更新时间
            if 'updated' in entry:
                paper_info['updated_date'] = entry.updated
            
            # 分类
            if 'arxiv_primary_category' in entry and 'term' in entry.arxiv_primary_category:
                paper_info['primary_category'] = entry.arxiv_primary_category.term
            
            # 所有分类
            if 'tags' in entry:
                categories = []
                for tag in entry.tags:
                    if 'term' in tag:
                        categories.append(tag.term)
                if categories:
                    paper_info['categories'] = categories
            
            # 评论（如果有）
            if 'arxiv_comment' in entry:
                paper_info['comment'] = entry.arxiv_comment
            
            # PDF链接
            if 'links' in entry:
                for link in entry.links:
                    if link.get('type') == 'application/pdf':
                        paper_info['pdf_url'] = link.href
                        break
            
            return paper_info
            
        except Exception as e:
            logger.error(f"解析arXiv条目时发生错误: {str(e)}")
            return None
    
    def get_arxiv_paper_detail(self, arxiv_id: str) -> Optional[Dict]:
        """
        获取arXiv论文详细信息
        
        Args:
            arxiv_id: arXiv ID（如：1706.03762）
            
        Returns:
            论文详细信息字典，失败则返回None
        """
        try:
            api_url = self.platforms['arxiv']['api_url']
            params = {
                'id_list': arxiv_id,
                'max_results': 1,
            }
            
            logger.info(f"正在获取arXiv论文详情: {arxiv_id}")
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.entries and len(feed.entries) > 0:
                paper_info = self._parse_arxiv_entry(feed.entries[0])
                
                if paper_info:
                    # 尝试获取更多信息
                    paper_info['timestamp'] = datetime.now().isoformat()
                    
                    # 从摘要中提取关键词（简单方法）
                    if 'abstract' in paper_info:
                        abstract = paper_info['abstract']
                        # 提取可能的关键词
                        keywords = self._extract_keywords_from_abstract(abstract)
                        if keywords:
                            paper_info['extracted_keywords'] = keywords
                    
                    logger.info(f"成功获取arXiv论文详情: {paper_info.get('title', '未知标题')}")
                    return paper_info
            
            logger.warning(f"未找到arXiv论文: {arxiv_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取arXiv论文详情时发生错误: {str(e)}")
            return None
    
    def _extract_keywords_from_abstract(self, abstract: str, max_keywords: int = 10) -> List[str]:
        """
        从摘要中提取关键词（简单实现）
        
        Args:
            abstract: 论文摘要
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        try:
            # 移除常见停用词
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
            
            # 提取单词
            words = re.findall(r'\b[a-zA-Z]{4,}\b', abstract.lower())
            
            # 过滤停用词和常见词
            filtered_words = [word for word in words if word not in stop_words]
            
            # 计算词频
            from collections import Counter
            word_counts = Counter(filtered_words)
            
            # 返回最常见的词
            keywords = [word for word, count in word_counts.most_common(max_keywords)]
            
            return keywords
            
        except Exception as e:
            logger.error(f"提取关键词时发生错误: {str(e)}")
            return []
    
    def search_semanticscholar_papers(self, query: str, limit: int = 10, **kwargs) -> List[Dict]:
        """
        搜索Semantic Scholar论文
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            **kwargs: 其他参数
                - year: 年份过滤
                - venue: 会议/期刊过滤
                - fields_of_study: 研究领域过滤
            
        Returns:
            论文列表
        """
        try:
            api_url = f"{self.platforms['semanticscholar']['api_url']}/paper/search"
            
            params = {
                'query': query,
                'limit': min(limit, 100),
                'fields': 'title,authors,abstract,venue,year,citationCount,referenceCount,influentialCitationCount,url,publicationTypes,publicationDate',
            }
            
            # 添加其他参数
            if 'year' in kwargs:
                params['year'] = kwargs['year']
            
            if 'venue' in kwargs:
                params['venue'] = kwargs['venue']
            
            if 'fields_of_study' in kwargs:
                params['fieldsOfStudy'] = kwargs['fields_of_study']
            
            # 如果有API key，添加到请求头
            headers = {}
            api_key = self.platforms['semanticscholar'].get('api_key')
            if api_key:
                headers['x-api-key'] = api_key
            
            logger.info(f"正在搜索Semantic Scholar论文: {query}")
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            papers = []
            if 'data' in data:
                for paper_data in data['data'][:limit]:
                    paper_info = self._parse_semanticscholar_paper(paper_data)
                    if paper_info:
                        papers.append(paper_info)
            
            logger.info(f"成功搜索到 {len(papers)} 篇Semantic Scholar论文")
            return papers
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"搜索Semantic Scholar论文时发生错误: {str(e)}")
            return []
    
    def _parse_semanticscholar_paper(self, paper_data: Dict) -> Optional[Dict]:
        """解析Semantic Scholar论文数据"""
        try:
            paper_info = {
                'source': 'Semantic Scholar',
                'platform': 'semanticscholar',
            }
            
            # 论文ID
            if 'paperId' in paper_data:
                paper_info['paper_id'] = paper_data['paperId']
            
            # 标题
            if 'title' in paper_data:
                paper_info['title'] = paper_data['title']
            
            # 摘要
            if 'abstract' in paper_data:
                paper_info['abstract'] = paper_data['abstract']
            
            # 作者
            if 'authors' in paper_data:
                authors = []
                for author in paper_data['authors']:
                    if 'name' in author:
                        authors.append(author['name'])
                if authors:
                    paper_info['authors'] = authors
            
            # 发布信息
            if 'venue' in paper_data:
                paper_info['venue'] = paper_data['venue']
            
            if 'year' in paper_data:
                paper_info['year'] = paper_data['year']
            
            if 'publicationDate' in paper_data:
                paper_info['publication_date'] = paper_data['publicationDate']
            
            # 引用信息
            if 'citationCount' in paper_data:
                paper_info['citation_count'] = paper_data['citationCount']
            
            if 'referenceCount' in paper_data:
                paper_info['reference_count'] = paper_data['referenceCount']
            
            if 'influentialCitationCount' in paper_data:
                paper_info['influential_citation_count'] = paper_data['influentialCitationCount']
            
            # URL
            if 'url' in paper_data:
                paper_info['url'] = paper_data['url']
            
            # 出版物类型
            if 'publicationTypes' in paper_data:
                paper_info['publication_types'] = paper_data['publicationTypes']
            
            return paper_info
            
        except Exception as e:
            logger.error(f"解析Semantic Scholar论文时发生错误: {str(e)}")
            return None
    
    def search_dblp_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        搜索DBLP论文
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            
        Returns:
            论文列表
        """
        try:
            api_url = self.platforms['dblp']['api_url']
            
            params = {
                'q': query,
                'format': 'json',
                'h': min(max_results, 100),
            }
            
            logger.info(f"正在搜索DBLP论文: {query}")
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            papers = []
            if 'result' in data and 'hits' in data['result'] and 'hit' in data['result']['hits']:
                for hit in data['result']['hits']['hit'][:max_results]:
                    paper_info = self._parse_dblp_hit(hit)
                    if paper_info:
                        papers.append(paper_info)
            
            logger.info(f"成功搜索到 {len(papers)} 篇DBLP论文")
            return papers
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"搜索DBLP论文时发生错误: {str(e)}")
            return []
    
    def _parse_dblp_hit(self, hit: Dict) -> Optional[Dict]:
        """解析DBLP命中结果"""
        try:
            paper_info = {
                'source': 'DBLP',
                'platform': 'dblp',
            }
            
            info = hit.get('info', {})
            
            # 标题
            if 'title' in info:
                paper_info['title'] = info['title']
            
            # 作者
            if 'authors' in info and 'author' in info['authors']:
                authors = info['authors']['author']
                if isinstance(authors, list):
                    paper_info['authors'] = authors
                else:
                    paper_info['authors'] = [authors]
            
            # 发布信息
            if 'venue' in info:
                paper_info['venue'] = info['venue']
            
            if 'year' in info:
                paper_info['year'] = info['year']
            
            # URL
            if 'url' in info:
                paper_info['url'] = info['url']
            
            # 类型
            if 'type' in info:
                paper_info['type'] = info['type']
            
            # 访问URL
            if 'url' in hit:
                paper_info['access_url'] = hit['url']
            
            # 评分
            if 'score' in hit:
                paper_info['score'] = hit['score']
            
            return paper_info
            
        except Exception as e:
            logger.error(f"解析DBLP命中结果时发生错误: {str(e)}")
            return None
    
    def get_latest_papers(self, category: str = 'cs.AI', max_results: int = 10) -> List[Dict]:
        """
        获取最新论文
        
        Args:
            category: 论文分类（arXiv类别）
            max_results: 最大返回结果数
            
        Returns:
            论文列表
        """
        try:
            # 使用arXiv API获取最新论文
            api_url = self.platforms['arxiv']['api_url']
            
            params = {
                'search_query': f"cat:{category}",
                'sortBy': 'submittedDate',
                'sortOrder': 'descending',
                'start': 0,
                'max_results': min(max_results, 50),
            }
            
            logger.info(f"正在获取最新论文: {category}")
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            papers = []
            for entry in feed.entries[:max_results]:
                paper_info = self._parse_arxiv_entry(entry)
                if paper_info:
                    papers.append(paper_info)
            
            logger.info(f"成功获取 {len(papers)} 篇最新论文")
            return papers
            
        except Exception as e:
            logger.error(f"获取最新论文时发生错误: {str(e)}")
            return []
    
    def search_crossref_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        使用Crossref API搜索论文
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            
        Returns:
            论文列表
        """
        try:
            crossref_url = "https://api.crossref.org/works"
            
            params = {
                'query': query,
                'rows': min(max_results, 100),
                'select': 'DOI,title,author,abstract,published,container-title,type',
            }
            
            logger.info(f"正在搜索Crossref论文: {query}")
            
            response = self.session.get(crossref_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            papers = []
            if 'message' in data and 'items' in data['message']:
                for item in data['message']['items'][:max_results]:
                    paper_info = self._parse_crossref_item(item)
                    if paper_info:
                        papers.append(paper_info)
            
            logger.info(f"成功搜索到 {len(papers)} 篇Crossref论文")
            return papers
            
        except Exception as e:
            logger.error(f"搜索Crossref论文时发生错误: {str(e)}")
            return []
    
    def _parse_crossref_item(self, item: Dict) -> Optional[Dict]:
        """解析Crossref项目"""
        try:
            paper_info = {
                'source': 'Crossref',
                'platform': 'crossref',
            }
            
            # DOI
            if 'DOI' in item:
                paper_info['doi'] = item['DOI']
                paper_info['url'] = f"https://doi.org/{item['DOI']}"
            
            # 标题
            if 'title' in item and len(item['title']) > 0:
                paper_info['title'] = item['title'][0]
            
            # 作者
            if 'author' in item:
                authors = []
                for author in item['author']:
                    if 'given' in author and 'family' in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif 'name' in author:
                        authors.append(author['name'])
                if authors:
                    paper_info['authors'] = authors
            
            # 摘要
            if 'abstract' in item:
                paper_info['abstract'] = item['abstract']
            
            # 发布时间
            if 'published' in item and 'date-parts' in item['published']:
                date_parts = item['published']['date-parts'][0]
                if len(date_parts) >= 3:
                    paper_info['published_date'] = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"
                elif len(date_parts) >= 2:
                    paper_info['published_date'] = f"{date_parts[0]}-{date_parts[1]:02d}"
                elif len(date_parts) >= 1:
                    paper_info['published_date'] = str(date_parts[0])
            
            # 期刊/会议名称
            if 'container-title' in item and len(item['container-title']) > 0:
                paper_info['journal_conference'] = item['container-title'][0]
            
            # 类型
            if 'type' in item:
                paper_info['type'] = item['type']
            
            return paper_info
            
        except Exception as e:
            logger.error(f"解析Crossref项目时发生错误: {str(e)}")
            return None
    
    def analyze_research_trends(self, keyword: str, years: List[int] = None, platform: str = 'arxiv') -> Dict:
        """
        分析研究趋势
        
        Args:
            keyword: 研究关键词
            years: 年份列表
            platform: 平台名称
            
        Returns:
            趋势分析结果
        """
        try:
            if years is None:
                current_year = datetime.now().year
                years = list(range(current_year - 5, current_year + 1))
            
            trends = {
                'keyword': keyword,
                'platform': platform,
                'years': years,
                'analysis_time': datetime.now().isoformat(),
                'yearly_counts': {},
                'total_papers': 0,
            }
            
            total_papers = 0
            
            for year in years:
                # 搜索该年份的论文
                if platform == 'arxiv':
                    query = f"{keyword} AND submittedDate:[{year}0101 TO {year}1231]"
                    papers = self.search_arxiv_papers(query, max_results=50)
                elif platform == 'semanticscholar':
                    papers = self.search_semanticscholar_papers(keyword, limit=50, year=year)
                else:
                    # 默认使用arXiv
                    query = f"{keyword} AND submittedDate:[{year}0101 TO {year}1231]"
                    papers = self.search_arxiv_papers(query, max_results=50)
                
                count = len(papers)
                trends['yearly_counts'][year] = count
                total_papers += count
            
            trends['total_papers'] = total_papers
            
            # 计算趋势
            if len(years) > 1:
                year_counts = list(trends['yearly_counts'].values())
                if sum(year_counts) > 0:
                    # 简单趋势分析
                    first_year_count = year_counts[0]
                    last_year_count = year_counts[-1]
                    
                    if first_year_count > 0:
                        growth_rate = ((last_year_count - first_year_count) / first_year_count) * 100
                        trends['growth_rate'] = round(growth_rate, 2)
                    
                    # 峰值年份
                    max_count = max(year_counts)
                    max_year = years[year_counts.index(max_count)]
                    trends['peak_year'] = max_year
                    trends['peak_count'] = max_count
            
            logger.info(f"研究趋势分析完成: {keyword}")
            return trends
            
        except Exception as e:
            logger.error(f"分析研究趋势时发生错误: {str(e)}")
            return {'error': str(e)}
    
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
                if 'title' in data:  # 单篇论文
                    title = data['title'].replace('/', '_').replace('\\', '_')[:50]
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"paper_{title}_{timestamp}.json"
                elif isinstance(data, list) and len(data) > 0 and 'title' in data[0]:  # 论文列表
                    keyword = data[0].get('source', 'papers').lower().replace(' ', '_')
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"papers_{keyword}_{timestamp}.json"
                elif 'keyword' in data and 'platform' in data:  # 分析结果
                    keyword = data['keyword'].replace(' ', '_')
                    platform = data['platform']
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"analysis_{platform}_{keyword}_{timestamp}.json"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"papers_{timestamp}.json"
            
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


def main():
    """主函数，演示爬虫的使用"""
    print("学术论文爬虫演示")
    print("=" * 50)
    print("支持平台: arXiv, Semantic Scholar, DBLP, Crossref等")
    print("功能: 搜索论文、获取详情、分析研究趋势")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = PaperCrawler(timeout=15)
    
    # 演示arXiv论文搜索
    print("\n搜索arXiv上的机器学习论文...")
    
    query = "machine learning"
    max_results = 5
    
    arxiv_papers = crawler.search_arxiv_papers(query, max_results=max_results)
    
    if arxiv_papers:
        print(f"找到 {len(arxiv_papers)} 篇arXiv论文:")
        for i, paper in enumerate(arxiv_papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   作者: {', '.join(paper.get('authors', ['未知']))[:50]}...")
            print(f"   发布时间: {paper.get('published_date', '未知')}")
            print(f"   分类: {paper.get('primary_category', '未知')}")
            print(f"   链接: {paper.get('url', '无')}")
            print()
        
        # 获取第一篇论文的详细信息
        if arxiv_papers[0].get('arxiv_id'):
            print("获取第一篇论文的详细信息...")
            paper_detail = crawler.get_arxiv_paper_detail(arxiv_papers[0]['arxiv_id'])
            
            if paper_detail:
                print(f"标题: {paper_detail.get('title', '未知')}")
                print(f"arXiv ID: {paper_detail.get('arxiv_id', '未知')}")
                print(f"作者: {', '.join(paper_detail.get('authors', ['未知']))}")
                print(f"发布时间: {paper_detail.get('published_date', '未知')}")
                
                if 'abstract' in paper_detail:
                    abstract_preview = paper_detail['abstract'][:200] + "..." if len(paper_detail['abstract']) > 200 else paper_detail['abstract']
                    print(f"摘要: {abstract_preview}")
                
                if 'extracted_keywords' in paper_detail:
                    print(f"提取关键词: {', '.join(paper_detail['extracted_keywords'])}")
                
                # 保存数据
                crawler.save_to_json(paper_detail)
                print(f"\n论文详情已保存到JSON文件")
    else:
        print("未找到相关论文")
    
    # 演示Semantic Scholar搜索
    print("\n" + "=" * 50)
    print("搜索Semantic Scholar上的自然语言处理论文...")
    
    query = "natural language processing"
    limit = 3
    
    ss_papers = crawler.search_semanticscholar_papers(query, limit=limit)
    
    if ss_papers:
        print(f"找到 {len(ss_papers)} 篇Semantic Scholar论文:")
        for i, paper in enumerate(ss_papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   作者: {', '.join(paper.get('authors', ['未知']))[:50]}...")
            print(f"   年份: {paper.get('year', '未知')}")
            print(f"   会议/期刊: {paper.get('venue', '未知')}")
            print(f"   引用数: {paper.get('citation_count', 0)}")
            print()
    
    # 演示获取最新论文
    print("\n" + "=" * 50)
    print("获取人工智能领域最新论文...")
    
    latest_papers = crawler.get_latest_papers('cs.AI', max_results=3)
    
    if latest_papers:
        print(f"找到 {len(latest_papers)} 篇最新AI论文:")
        for i, paper in enumerate(latest_papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   发布时间: {paper.get('published_date', '未知')}")
            print(f"   分类: {paper.get('primary_category', '未知')}")
            print()
    
    # 演示研究趋势分析
    print("\n" + "=" * 50)
    print("分析'深度学习'研究趋势...")
    
    trends = crawler.analyze_research_trends('deep learning', platform='arxiv')
    
    if 'error' not in trends:
        print(f"关键词: {trends['keyword']}")
        print(f"平台: {trends['platform']}")
        print(f"分析时间: {trends['analysis_time']}")
        print(f"总论文数: {trends['total_papers']}")
        
        print("\n年度论文数量:")
        for year, count in trends['yearly_counts'].items():
            print(f"  {year}: {count} 篇")
        
        if 'growth_rate' in trends:
            print(f"\n增长率: {trends['growth_rate']}%")
        
        if 'peak_year' in trends:
            print(f"峰值年份: {trends['peak_year']} ({trends['peak_count']} 篇)")
        
        # 保存分析结果
        crawler.save_to_json(trends)
        print(f"\n研究趋势分析已保存到JSON文件")
    else:
        print(f"趋势分析失败: {trends['error']}")
    
    # 演示Crossref搜索
    print("\n" + "=" * 50)
    print("使用Crossref搜索计算机科学论文...")
    
    crossref_papers = crawler.search_crossref_papers('computer science', max_results=3)
    
    if crossref_papers:
        print(f"找到 {len(crossref_papers)} 篇Crossref论文:")
        for i, paper in enumerate(crossref_papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   作者: {', '.join(paper.get('authors', ['未知']))[:50]}...")
            print(f"   期刊/会议: {paper.get('journal_conference', '未知')}")
            if 'doi' in paper:
                print(f"   DOI: {paper['doi']}")
            print()
    
    # 演示DBLP搜索
    print("\n" + "=" * 50)
    print("使用DBLP搜索数据库论文...")
    
    dblp_papers = crawler.search_dblp_papers('database', max_results=3)
    
    if dblp_papers:
        print(f"找到 {len(dblp_papers)} 篇DBLP论文:")
        for i, paper in enumerate(dblp_papers, 1):
            print(f"{i}. {paper.get('title', '未知标题')}")
            print(f"   作者: {', '.join(paper.get('authors', ['未知']))[:50]}...")
            print(f"   年份: {paper.get('year', '未知')}")
            print(f"   类型: {paper.get('type', '未知')}")
            print()
    
    print("\n爬虫演示完成！")
    print("\n高级功能:")
    print("1. 多平台联合搜索")
    print("2. 论文引用网络分析")
    print("3. 作者合作网络分析")
    print("4. 研究热点检测")
    print("5. 论文推荐系统")
    print("\n注意事项:")
    print("1. 遵守各学术平台的API使用政策")
    print("2. 注意API调用频率限制")
    print("3. 部分平台需要API key")
    print("4. 中文论文搜索需要特殊处理（如知网）")


if __name__ == "__main__":
    main()