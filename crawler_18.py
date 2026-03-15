#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招聘信息爬虫 - 获取各大招聘网站职位信息
网站：智联招聘、前程无忧、BOSS直聘等
功能：获取职位信息、公司信息、薪资范围、工作地点等
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin, quote, urlparse, parse_qs

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobCrawler:
    """招聘信息爬虫类"""
    
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
        
        # 支持的招聘平台配置
        self.platforms = {
            'zhilian': {
                'name': '智联招聘',
                'base_url': 'https://sou.zhaopin.com',
                'search_url': 'https://sou.zhaopin.com',
                'job_detail_pattern': r'https://jobs\.zhaopin\.com/\w+\.html',
            },
            'qiancheng': {
                'name': '前程无忧',
                'base_url': 'https://search.51job.com',
                'search_url': 'https://search.51job.com',
                'job_detail_pattern': r'https://jobs\.51job\.com/\w+/\d+\.html',
            },
            'boss': {
                'name': 'BOSS直聘',
                'base_url': 'https://www.zhipin.com',
                'search_url': 'https://www.zhipin.com/web/geek/job',
                'job_detail_pattern': r'https://www\.zhipin\.com/job_detail/\w+\.html',
            },
            'lagou': {
                'name': '拉勾网',
                'base_url': 'https://www.lagou.com',
                'search_url': 'https://www.lagou.com/jobs/list',
                'job_detail_pattern': r'https://www\.lagou\.com/jobs/\d+\.html',
            },
            'liepin': {
                'name': '猎聘网',
                'base_url': 'https://www.liepin.com',
                'search_url': 'https://www.liepin.com/zhaopin',
                'job_detail_pattern': r'https://www\.liepin\.com/job/\d+\.shtml',
            }
        }
        
        # 热门城市代码映射
        self.city_codes = {
            '北京': '010000',
            '上海': '020000',
            '广州': '030200',
            '深圳': '030300',
            '杭州': '080200',
            '南京': '070200',
            '成都': '090200',
            '武汉': '180200',
            '西安': '200200',
            '天津': '050000',
        }
        
        # 热门职位类别映射
        self.job_categories = {
            '技术': ['Java', 'Python', '前端', '后端', '算法', '测试', '运维'],
            '产品': ['产品经理', '产品助理', '产品运营'],
            '设计': ['UI设计', 'UX设计', '视觉设计', '交互设计'],
            '运营': ['用户运营', '内容运营', '活动运营', '数据运营'],
            '市场': ['市场营销', '品牌推广', '公关', '媒介'],
        }
    
    def detect_platform(self, url: str) -> Optional[str]:
        """
        检测URL属于哪个招聘平台
        
        Args:
            url: 招聘URL
            
        Returns:
            平台名称，如果无法识别则返回None
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'zhaopin.com' in domain:
            return 'zhilian'
        elif '51job.com' in domain:
            return 'qiancheng'
        elif 'zhipin.com' in domain:
            return 'boss'
        elif 'lagou.com' in domain:
            return 'lagou'
        elif 'liepin.com' in domain:
            return 'liepin'
        
        return None
    
    def search_jobs(self, keyword: str, city: str = None, platform: str = 'zhilian', 
                   limit: int = 10, **kwargs) -> List[Dict]:
        """
        搜索职位
        
        Args:
            keyword: 搜索关键词
            city: 城市名称
            platform: 平台名称
            limit: 返回职位数量限制
            **kwargs: 其他搜索参数
            
        Returns:
            职位列表
        """
        if platform not in self.platforms:
            logger.error(f"不支持的平台: {platform}")
            return []
        
        try:
            if platform == 'zhilian':
                return self._search_zhilian_jobs(keyword, city, limit, **kwargs)
            elif platform == 'qiancheng':
                return self._search_qiancheng_jobs(keyword, city, limit, **kwargs)
            elif platform == 'boss':
                return self._search_boss_jobs(keyword, city, limit, **kwargs)
            elif platform == 'lagou':
                return self._search_lagou_jobs(keyword, city, limit, **kwargs)
            elif platform == 'liepin':
                return self._search_liepin_jobs(keyword, city, limit, **kwargs)
            else:
                return []
                
        except Exception as e:
            logger.error(f"搜索职位时发生错误: {str(e)}")
            return []
    
    def _search_zhilian_jobs(self, keyword: str, city: str = None, limit: int = 10, **kwargs) -> List[Dict]:
        """搜索智联招聘职位"""
        jobs = []
        
        try:
            search_url = "https://sou.zhaopin.com"
            params = {
                'jl': self.city_codes.get(city, '') if city else '',
                'kw': keyword,
                'p': 1,  # 页码
                'pageSize': min(limit, 90),
            }
            
            # 添加其他参数
            params.update(kwargs)
            
            logger.info(f"正在搜索智联招聘职位: {keyword} ({city or '全国'})")
            
            response = self.session.get(search_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析职位列表
            job_items = soup.find_all('div', class_='joblist-box')
            
            for item in job_items[:limit]:
                job_info = self._parse_zhilian_job_item(item)
                if job_info:
                    jobs.append(job_info)
            
            logger.info(f"成功搜索到 {len(jobs)} 个职位")
            
        except Exception as e:
            logger.error(f"搜索智联招聘职位时发生错误: {str(e)}")
        
        return jobs
    
    def _parse_zhilian_job_item(self, item) -> Optional[Dict]:
        """解析智联招聘职位列表项"""
        try:
            job_info = {
                'platform': 'zhilian',
                'platform_name': '智联招聘',
            }
            
            # 职位标题和链接
            title_tag = item.find('a', class_='job-title')
            if title_tag:
                job_info['title'] = title_tag.get_text(strip=True)
                job_info['url'] = title_tag.get('href', '')
            
            # 公司名称
            company_tag = item.find('a', class_='company-title')
            if company_tag:
                job_info['company'] = company_tag.get_text(strip=True)
                job_info['company_url'] = company_tag.get('href', '')
            
            # 薪资
            salary_tag = item.find('span', class_='salary')
            if salary_tag:
                job_info['salary'] = salary_tag.get_text(strip=True)
            
            # 工作地点
            location_tag = item.find('span', class_='job-city')
            if location_tag:
                job_info['location'] = location_tag.get_text(strip=True)
            
            # 经验要求
            exp_tag = item.find('span', class_='job-experience')
            if exp_tag:
                job_info['experience'] = exp_tag.get_text(strip=True)
            
            # 学历要求
            edu_tag = item.find('span', class_='job-degree')
            if edu_tag:
                job_info['education'] = edu_tag.get_text(strip=True)
            
            # 发布时间
            time_tag = item.find('span', class_='time')
            if time_tag:
                job_info['publish_time'] = time_tag.get_text(strip=True)
            
            # 职位标签
            tags = []
            tags_div = item.find('div', class_='job-tags')
            if tags_div:
                tag_spans = tags_div.find_all('span')
                for tag in tag_spans:
                    tags.append(tag.get_text(strip=True))
            if tags:
                job_info['tags'] = tags
            
            return job_info if 'title' in job_info else None
            
        except Exception as e:
            logger.error(f"解析智联招聘职位项时发生错误: {str(e)}")
            return None
    
    def _search_qiancheng_jobs(self, keyword: str, city: str = None, limit: int = 10, **kwargs) -> List[Dict]:
        """搜索前程无忧职位"""
        jobs = []
        
        try:
            search_url = "https://search.51job.com"
            params = {
                'keyword': keyword,
                'jobarea': self.city_codes.get(city, '') if city else '000000',
                'curr_page': 1,
            }
            
            # 添加其他参数
            params.update(kwargs)
            
            logger.info(f"正在搜索前程无忧职位: {keyword} ({city or '全国'})")
            
            response = self.session.get(search_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'gbk'  # 51job使用GBK编码
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析职位列表
            job_items = soup.find_all('div', class_='j_joblist')
            
            for item in job_items[:limit]:
                job_info = self._parse_qiancheng_job_item(item)
                if job_info:
                    jobs.append(job_info)
            
            logger.info(f"成功搜索到 {len(jobs)} 个职位")
            
        except Exception as e:
            logger.error(f"搜索前程无忧职位时发生错误: {str(e)}")
        
        return jobs
    
    def _parse_qiancheng_job_item(self, item) -> Optional[Dict]:
        """解析前程无忧职位列表项"""
        try:
            job_info = {
                'platform': 'qiancheng',
                'platform_name': '前程无忧',
            }
            
            # 职位标题和链接
            title_tag = item.find('span', class_='jname')
            if title_tag:
                job_info['title'] = title_tag.get_text(strip=True)
            
            link_tag = item.find('a')
            if link_tag:
                job_info['url'] = link_tag.get('href', '')
            
            # 公司名称
            company_tag = item.find('span', class_='cname')
            if company_tag:
                job_info['company'] = company_tag.get_text(strip=True)
            
            # 薪资
            salary_tag = item.find('span', class_='sal')
            if salary_tag:
                job_info['salary'] = salary_tag.get_text(strip=True)
            
            # 工作地点
            location_tag = item.find('span', class_='d at')
            if location_tag:
                job_info['location'] = location_tag.get_text(strip=True)
            
            # 经验要求
            exp_tag = item.find('span', class_='d at')
            if exp_tag:
                # 可能需要从文本中提取经验信息
                text = exp_tag.get_text(strip=True)
                if '经验' in text:
                    job_info['experience'] = text
            
            # 职位福利
            welfare_tags = item.find_all('span', class_='tags')
            if welfare_tags:
                welfares = []
                for tag in welfare_tags:
                    welfares.append(tag.get_text(strip=True))
                job_info['welfare'] = welfares
            
            return job_info if 'title' in job_info else None
            
        except Exception as e:
            logger.error(f"解析前程无忧职位项时发生错误: {str(e)}")
            return None
    
    def _search_boss_jobs(self, keyword: str, city: str = None, limit: int = 10, **kwargs) -> List[Dict]:
        """搜索BOSS直聘职位"""
        # BOSS直聘需要处理复杂的反爬机制
        # 这里简化处理，返回空列表
        logger.info(f"正在搜索BOSS直聘职位: {keyword} ({city or '全国'})")
        logger.warning("BOSS直聘搜索功能需要处理反爬机制，建议使用官方API")
        return []
    
    def _search_lagou_jobs(self, keyword: str, city: str = None, limit: int = 10, **kwargs) -> List[Dict]:
        """搜索拉勾网职位"""
        # 拉勾网需要处理Ajax请求和反爬机制
        logger.info(f"正在搜索拉勾网职位: {keyword} ({city or '全国'})")
        logger.warning("拉勾网搜索功能需要处理Ajax请求和反爬机制")
        return []
    
    def _search_liepin_jobs(self, keyword: str, city: str = None, limit: int = 10, **kwargs) -> List[Dict]:
        """搜索猎聘网职位"""
        # 猎聘网需要处理复杂的页面结构
        logger.info(f"正在搜索猎聘网职位: {keyword} ({city or '全国'})")
        logger.warning("猎聘网搜索功能需要处理复杂页面结构")
        return []
    
    def get_job_detail(self, url: str) -> Optional[Dict]:
        """
        获取职位详细信息
        
        Args:
            url: 职位详情页URL
            
        Returns:
            职位详细信息字典，失败则返回None
        """
        try:
            platform = self.detect_platform(url)
            if not platform:
                logger.warning(f"无法识别的招聘平台: {url}")
                return None
            
            logger.info(f"正在获取 {self.platforms[platform]['name']} 职位详情: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 根据平台设置编码
            if platform == 'qiancheng':
                response.encoding = 'gbk'
            else:
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 根据平台调用不同的解析方法
            if platform == 'zhilian':
                job_detail = self._parse_zhilian_job_detail(soup, url)
            elif platform == 'qiancheng':
                job_detail = self._parse_qiancheng_job_detail(soup, url)
            else:
                job_detail = self._parse_generic_job_detail(soup, url, platform)
            
            if job_detail:
                job_detail['platform'] = platform
                job_detail['platform_name'] = self.platforms[platform]['name']
                job_detail['url'] = url
                job_detail['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                logger.info(f"成功获取职位详情: {job_detail.get('title', '未知职位')}")
                return job_detail
            else:
                logger.warning(f"解析职位详情失败: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取职位详情时发生未知错误: {str(e)}")
            return None
    
    def _parse_zhilian_job_detail(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析智联招聘职位详情"""
        job_detail = {
            'source': '智联招聘',
        }
        
        try:
            # 职位标题
            title_tag = soup.find('h1')
            if title_tag:
                job_detail['title'] = title_tag.get_text(strip=True)
            
            # 公司信息
            company_tag = soup.find('a', class_='company__title')
            if company_tag:
                job_detail['company'] = company_tag.get_text(strip=True)
                job_detail['company_url'] = company_tag.get('href', '')
            
            # 薪资
            salary_tag = soup.find('span', class_='salary')
            if not salary_tag:
                salary_tag = soup.find('div', class_='salary')
            if salary_tag:
                job_detail['salary'] = salary_tag.get_text(strip=True)
            
            # 工作地点
            location_tag = soup.find('span', class_='job-address')
            if location_tag:
                job_detail['location'] = location_tag.get_text(strip=True)
            
            # 经验要求
            exp_tag = soup.find('span', class_='experience')
            if exp_tag:
                job_detail['experience'] = exp_tag.get_text(strip=True)
            
            # 学历要求
            edu_tag = soup.find('span', class_='degree')
            if edu_tag:
                job_detail['education'] = edu_tag.get_text(strip=True)
            
            # 职位描述
            desc_tag = soup.find('div', class_='describtion')
            if desc_tag:
                job_detail['description'] = desc_tag.get_text(strip=True)
            
            # 职位要求
            requirement_tag = soup.find('div', class_='requirement')
            if requirement_tag:
                job_detail['requirements'] = requirement_tag.get_text(strip=True)
            
            # 公司介绍
            company_desc_tag = soup.find('div', class_='company-intro')
            if company_desc_tag:
                job_detail['company_description'] = company_desc_tag.get_text(strip=True)
            
            # 公司规模
            scale_tag = soup.find('span', class_='scale')
            if scale_tag:
                job_detail['company_scale'] = scale_tag.get_text(strip=True)
            
            # 公司行业
            industry_tag = soup.find('span', class_='industry')
            if industry_tag:
                job_detail['company_industry'] = industry_tag.get_text(strip=True)
            
        except Exception as e:
            logger.error(f"解析智联招聘职位详情时发生错误: {str(e)}")
        
        return job_detail
    
    def _parse_qiancheng_job_detail(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析前程无忧职位详情"""
        job_detail = {
            'source': '前程无忧',
        }
        
        try:
            # 职位标题
            title_tag = soup.find('h1')
            if title_tag:
                job_detail['title'] = title_tag.get_text(strip=True)
            
            # 公司名称
            company_tag = soup.find('p', class_='cname')
            if company_tag:
                company_link = company_tag.find('a')
                if company_link:
                    job_detail['company'] = company_link.get_text(strip=True)
                    job_detail['company_url'] = company_link.get('href', '')
            
            # 薪资
            salary_tag = soup.find('strong')
            if salary_tag:
                job_detail['salary'] = salary_tag.get_text(strip=True)
            
            # 职位信息（包含地点、经验、学历等）
            info_tags = soup.find_all('p', class_='msg')
            for tag in info_tags:
                text = tag.get_text(strip=True)
                if '上班地址' in text:
                    job_detail['location'] = text.replace('上班地址：', '')
                elif '经验' in text:
                    job_detail['experience'] = text
                elif '学历' in text:
                    job_detail['education'] = text
            
            # 职位描述
            desc_tag = soup.find('div', class_='bmsg job_msg inbox')
            if desc_tag:
                job_detail['description'] = desc_tag.get_text(strip=True)
            
            # 公司信息
            company_info_tag = soup.find('div', class_='tmsg inbox')
            if company_info_tag:
                job_detail['company_description'] = company_info_tag.get_text(strip=True)
            
        except Exception as e:
            logger.error(f"解析前程无忧职位详情时发生错误: {str(e)}")
        
        return job_detail
    
    def _parse_generic_job_detail(self, soup: BeautifulSoup, url: str, platform: str) -> Dict:
        """通用职位详情解析方法"""
        job_detail = {
            'source': self.platforms.get(platform, {}).get('name', '未知平台'),
        }
        
        try:
            # 尝试查找标题
            title_selectors = ['h1', '.job-title', '.position-title', '.title']
            for selector in title_selectors:
                title_tag = soup.find(selector)
                if title_tag:
                    job_detail['title'] = title_tag.get_text(strip=True)
                    break
            
            # 尝试查找公司
            company_selectors = ['.company', '.employer', '.firm', '.corp']
            for selector in company_selectors:
                company_tag = soup.find(class_=selector)
                if company_tag:
                    job_detail['company'] = company_tag.get_text(strip=True)
                    # 尝试获取公司链接
                    company_link = company_tag.find('a')
                    if company_link:
                        job_detail['company_url'] = company_link.get('href', '')
                    break
            
            # 尝试查找薪资
            salary_selectors = ['.salary', '.pay', '.money', '.compensation']
            for selector in salary_selectors:
                salary_tag = soup.find(class_=selector)
                if salary_tag:
                    job_detail['salary'] = salary_tag.get_text(strip=True)
                    break
            
            # 尝试查找工作地点
            location_selectors = ['.location', '.address', '.city', '.place']
            for selector in location_selectors:
                location_tag = soup.find(class_=selector)
                if location_tag:
                    job_detail['location'] = location_tag.get_text(strip=True)
                    break
            
            # 尝试查找职位描述
            desc_selectors = ['.description', '.job-desc', '.position-desc', '.content']
            for selector in desc_selectors:
                desc_tag = soup.find(class_=selector)
                if desc_tag:
                    job_detail['description'] = desc_tag.get_text(strip=True)
                    break
            
        except Exception as e:
            logger.error(f"通用职位详情解析时发生错误: {str(e)}")
        
        return job_detail
    
    def search_by_criteria(self, criteria: Dict) -> List[Dict]:
        """
        根据多种条件搜索职位
        
        Args:
            criteria: 搜索条件字典
                - keyword: 关键词
                - city: 城市
                - salary_min: 最低薪资
                - salary_max: 最高薪资
                - experience: 经验要求
                - education: 学历要求
                - job_type: 职位类型
                - platform: 平台名称
            
        Returns:
            职位列表
        """
        keyword = criteria.get('keyword', '')
        city = criteria.get('city')
        platform = criteria.get('platform', 'zhilian')
        limit = criteria.get('limit', 20)
        
        # 先搜索基本职位
        jobs = self.search_jobs(keyword, city, platform, limit)
        
        # 应用其他筛选条件
        filtered_jobs = []
        
        for job in jobs:
            if self._match_criteria(job, criteria):
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def _match_criteria(self, job: Dict, criteria: Dict) -> bool:
        """
        检查职位是否匹配搜索条件
        
        Args:
            job: 职位信息
            criteria: 搜索条件
            
        Returns:
            是否匹配
        """
        # 薪资筛选
        salary = job.get('salary', '')
        if salary and 'salary_min' in criteria:
            # 尝试从薪资字符串中提取数字
            match = re.search(r'(\d+)[kK]?-?(\d+)?[kK]?', salary)
            if match:
                min_salary = match.group(1)
                max_salary = match.group(2) or min_salary
                
                criteria_min = criteria.get('salary_min')
                criteria_max = criteria.get('salary_max')
                
                if criteria_min and int(min_salary) < criteria_min:
                    return False
                if criteria_max and int(max_salary) > criteria_max:
                    return False
        
        # 经验筛选
        experience = job.get('experience', '')
        if experience and 'experience' in criteria:
            criteria_exp = criteria['experience']
            # 简单匹配，实际应用需要更复杂的逻辑
            if criteria_exp not in experience:
                return False
        
        # 学历筛选
        education = job.get('education', '')
        if education and 'education' in criteria:
            criteria_edu = criteria['education']
            if criteria_edu not in education:
                return False
        
        return True
    
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
                if 'title' in data:  # 职位数据
                    title = data['title'].replace('/', '_').replace('\\', '_')[:50]
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"job_{title}_{timestamp}.json"
                elif isinstance(data, list) and len(data) > 0 and 'title' in data[0]:  # 职位列表
                    keyword = data[0].get('platform', 'jobs')
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"jobs_{keyword}_{timestamp}.json"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"jobs_{timestamp}.json"
            
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
    
    def analyze_job_market(self, keyword: str, city: str = None, platform: str = 'zhilian', 
                          limit: int = 100) -> Dict:
        """
        分析职位市场情况
        
        Args:
            keyword: 职位关键词
            city: 城市名称
            platform: 平台名称
            limit: 分析的数据量
            
        Returns:
            市场分析结果
        """
        try:
            # 搜索职位
            jobs = self.search_jobs(keyword, city, platform, limit)
            
            if not jobs:
                return {'error': '未找到相关职位'}
            
            analysis = {
                'keyword': keyword,
                'city': city or '全国',
                'platform': platform,
                'total_jobs': len(jobs),
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 薪资分析
            salaries = []
            for job in jobs:
                salary = job.get('salary')
                if salary:
                    # 提取薪资数字
                    match = re.search(r'(\d+)[kK]?-?(\d+)?[kK]?', salary)
                    if match:
                        min_salary = int(match.group(1))
                        max_salary = int(match.group(2)) if match.group(2) else min_salary
                        avg_salary = (min_salary + max_salary) / 2
                        salaries.append(avg_salary)
            
            if salaries:
                analysis['salary_analysis'] = {
                    'average': sum(salaries) / len(salaries),
                    'min': min(salaries),
                    'max': max(salaries),
                    'sample_count': len(salaries),
                }
            
            # 公司分析
            companies = {}
            for job in jobs:
                company = job.get('company')
                if company:
                    companies[company] = companies.get(company, 0) + 1
            
            if companies:
                # 按招聘数量排序
                sorted_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)
                analysis['company_analysis'] = {
                    'total_companies': len(companies),
                    'top_companies': sorted_companies[:10],  # 前10名公司
                }
            
            # 经验要求分析
            experience_counts = {}
            for job in jobs:
                experience = job.get('experience', '经验不限')
                experience_counts[experience] = experience_counts.get(experience, 0) + 1
            
            if experience_counts:
                analysis['experience_analysis'] = experience_counts
            
            # 学历要求分析
            education_counts = {}
            for job in jobs:
                education = job.get('education', '学历不限')
                education_counts[education] = education_counts.get(education, 0) + 1
            
            if education_counts:
                analysis['education_analysis'] = education_counts
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析职位市场时发生错误: {str(e)}")
            return {'error': str(e)}


def main():
    """主函数，演示爬虫的使用"""
    print("招聘信息爬虫演示")
    print("=" * 50)
    print("支持平台: 智联招聘、前程无忧、BOSS直聘、拉勾网、猎聘网")
    print("功能: 搜索职位、获取详情、市场分析")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = JobCrawler(timeout=15)
    
    # 演示搜索职位
    print("\n搜索Python开发职位...")
    
    keyword = "Python"
    city = "北京"
    platform = "zhilian"  # 使用智联招聘
    
    print(f"关键词: {keyword}")
    print(f"城市: {city}")
    print(f"平台: {crawler.platforms[platform]['name']}")
    
    # 搜索职位
    jobs = crawler.search_jobs(keyword, city, platform, limit=5)
    
    if jobs:
        print(f"\n找到 {len(jobs)} 个职位:")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.get('title', '未知职位')}")
            print(f"   公司: {job.get('company', '未知公司')}")
            print(f"   薪资: {job.get('salary', '面议')}")
            print(f"   地点: {job.get('location', '未知')}")
            print(f"   链接: {job.get('url', '无')[:80]}...")
            print()
        
        # 获取第一个职位的详细信息
        if jobs[0].get('url'):
            print("获取第一个职位的详细信息...")
            job_detail = crawler.get_job_detail(jobs[0]['url'])
            
            if job_detail:
                print(f"职位标题: {job_detail.get('title', '未知')}")
                print(f"公司名称: {job_detail.get('company', '未知')}")
                print(f"工作地点: {job_detail.get('location', '未知')}")
                print(f"薪资范围: {job_detail.get('salary', '面议')}")
                print(f"经验要求: {job_detail.get('experience', '不限')}")
                print(f"学历要求: {job_detail.get('education', '不限')}")
                
                if 'description' in job_detail:
                    desc_preview = job_detail['description'][:200] + "..." if len(job_detail['description']) > 200 else job_detail['description']
                    print(f"职位描述: {desc_preview}")
                
                # 保存数据
                crawler.save_to_json(job_detail)
                print(f"\n职位详情已保存到JSON文件")
    else:
        print("未找到相关职位")
    
    # 演示多条件搜索
    print("\n" + "=" * 50)
    print("多条件搜索演示...")
    
    criteria = {
        'keyword': 'Java',
        'city': '上海',
        'salary_min': 15,  # 15k以上
        'experience': '3-5年',
        'platform': 'zhilian',
        'limit': 10,
    }
    
    print(f"搜索条件: {critriteria}")
    
    filtered_jobs = crawler.search_by_criteria(criteria)
    print(f"符合条件职位: {len(filtered_jobs)} 个")
    
    # 演示市场分析
    print("\n" + "=" * 50)
    print("职位市场分析演示...")
    
    analysis = crawler.analyze_job_market('数据分析', '上海', 'zhilian', 50)
    
    if 'error' not in analysis:
        print(f"关键词: {analysis['keyword']}")
        print(f"城市: {analysis['city']}")
        print(f"平台: {analysis['platform']}")
        print(f"分析职位数: {analysis['total_jobs']}")
        
        if 'salary_analysis' in analysis:
            salary_info = analysis['salary_analysis']
            print(f"\n薪资分析:")
            print(f"  平均薪资: {salary_info['average']:.1f}k")
            print(f"  最低薪资: {salary_info['min']}k")
            print(f"  最高薪资: {salary_info['max']}k")
            print(f"  样本数: {salary_info['sample_count']}")
        
        if 'company_analysis' in analysis:
            company_info = analysis['company_analysis']
            print(f"\n公司分析:")
            print(f"  招聘公司总数: {company_info['total_companies']}")
            print(f"  前10名招聘公司:")
            for i, (company, count) in enumerate(company_info['top_companies'][:5], 1):
                print(f"    {i}. {company}: {count} 个职位")
        
        # 保存分析结果
        crawler.save_to_json(analysis, f"market_analysis_{analysis['keyword']}_{analysis['city']}.json")
        print(f"\n市场分析结果已保存到JSON文件")
    else:
        print(f"市场分析失败: {analysis['error']}")
    
    # 演示不同平台的搜索
    print("\n" + "=" * 50)
    print("不同平台搜索演示...")
    
    platforms_to_test = ['zhilian', 'qiancheng']
    
    for platform in platforms_to_test:
        print(f"\n{crawler.platforms[platform]['name']} 搜索:")
        test_jobs = crawler.search_jobs('前端', '深圳', platform, limit=3)
        print(f"  找到 {len(test_jobs)} 个职位")
        if test_jobs:
            for job in test_jobs[:2]:  # 只显示前2个
                print(f"  - {job.get('title', '未知')} ({job.get('salary', '面议')})")
    
    print("\n爬虫演示完成！")
    print("\n注意事项:")
    print("1. 遵守各招聘平台的robots.txt规则")
    print("2. 设置合理的请求频率，避免被封IP")
    print("3. 部分平台需要处理反爬机制（如验证码）")
    print("4. 对于需要登录的平台，建议使用官方API")
    print("5. 定期更新解析规则，适应网站改版")


if __name__ == "__main__":
    main()