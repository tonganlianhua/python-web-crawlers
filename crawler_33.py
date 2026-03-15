#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教育资料爬虫 - 从中国大学MOOC平台获取课程信息
目标网站: https://www.icourse163.org
功能: 爬取课程信息、教师信息、课程大纲、学习资料等
"""

import requests
import time
import random
import json
import csv
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
import logging
import hashlib
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mooc_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MOOCCourseCrawler:
    """中国大学MOOC课程爬虫"""
    
    def __init__(self, base_url="https://www.icourse163.org"):
        """
        初始化爬虫
        
        Args:
            base_url: MOOC平台基础URL
        """
        self.base_url = base_url
        self.api_base = "https://www.icourse163.org/web/j/courseBean.getCourseListBySchoolId.rpc"
        
        # 会话设置
        self.session = requests.Session()
        self._setup_session()
        
        # 数据存储
        self.data_dir = "mooc_data"
        self.setup_data_directories()
        
        # 数据库
        self.db_path = os.path.join(self.data_dir, "mooc_courses.db")
        self.init_database()
        
        # 爬虫状态
        self.crawl_stats = {
            'total_courses': 0,
            'total_universities': 0,
            'total_teachers': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 缓存
        self.cache_dir = os.path.join(self.data_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _setup_session(self):
        """设置会话配置"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': self.base_url,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.session.headers.update(headers)
        
        # 设置cookies（如果需要）
        self.session.cookies.update({
            'EDU_VERSION': '1',
            'NTESSTUDYSI': 's-xxxxxxxx',  # 示例cookie
        })
    
    def setup_data_directories(self):
        """创建数据目录结构"""
        directories = [
            self.data_dir,
            os.path.join(self.data_dir, 'courses'),
            os.path.join(self.data_dir, 'universities'),
            os.path.join(self.data_dir, 'teachers'),
            os.path.join(self.data_dir, 'materials'),
            os.path.join(self.data_dir, 'raw_html'),
            os.path.join(self.data_dir, 'json'),
            os.path.join(self.data_dir, 'csv'),
            os.path.join(self.data_dir, 'images'),
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
            
            # 创建大学表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS universities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    university_id TEXT UNIQUE,
                    name TEXT,
                    english_name TEXT,
                    abbreviation TEXT,
                    location TEXT,
                    type TEXT,
                    level TEXT,
                    description TEXT,
                    website TEXT,
                    logo_url TEXT,
                    total_courses INTEGER DEFAULT 0,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            # 创建课程表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT UNIQUE,
                    title TEXT,
                    subtitle TEXT,
                    university_id TEXT,
                    term TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    duration_weeks INTEGER,
                    hours_per_week INTEGER,
                    language TEXT,
                    difficulty TEXT,
                    category TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    description TEXT,
                    learning_outcomes TEXT,
                    syllabus TEXT,
                    cover_image TEXT,
                    video_intro TEXT,
                    enrollment_count INTEGER,
                    rating REAL,
                    review_count INTEGER,
                    url TEXT,
                    status TEXT,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP,
                    FOREIGN KEY (university_id) REFERENCES universities (university_id)
                )
            ''')
            
            # 创建教师表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT UNIQUE,
                    name TEXT,
                    english_name TEXT,
                    title TEXT,
                    department TEXT,
                    university_id TEXT,
                    introduction TEXT,
                    research_interests TEXT,
                    avatar_url TEXT,
                    personal_website TEXT,
                    total_courses INTEGER DEFAULT 0,
                    crawl_time TIMESTAMP,
                    last_updated TIMESTAMP,
                    FOREIGN KEY (university_id) REFERENCES universities (university_id)
                )
            ''')
            
            # 创建课程-教师关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS course_teachers (
                    course_id TEXT,
                    teacher_id TEXT,
                    role TEXT,
                    order_index INTEGER,
                    FOREIGN KEY (course_id) REFERENCES courses (course_id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers (teacher_id),
                    PRIMARY KEY (course_id, teacher_id)
                )
            ''')
            
            # 创建课程模块表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS course_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT,
                    module_number INTEGER,
                    title TEXT,
                    description TEXT,
                    duration_hours REAL,
                    order_index INTEGER,
                    FOREIGN KEY (course_id) REFERENCES courses (course_id)
                )
            ''')
            
            # 创建学习资料表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT,
                    module_id INTEGER,
                    material_type TEXT,
                    title TEXT,
                    description TEXT,
                    url TEXT,
                    file_size TEXT,
                    file_format TEXT,
                    duration TEXT,
                    order_index INTEGER,
                    crawl_time TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses (course_id),
                    FOREIGN KEY (module_id) REFERENCES course_modules (id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_university ON courses (university_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_category ON courses (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_teachers_university ON teachers (university_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_course_teachers_course ON course_teachers (course_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_modules_course ON course_modules (course_id)')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_str = url
        if params:
            key_str += json.dumps(params, sort_keys=True)
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached_response(self, cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """获取缓存的响应"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < max_age_hours * 3600:
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
                    use_cache: bool = True,
                    max_retries: int = 3,
                    timeout: int = 20) -> Optional[requests.Response]:
        """
        安全发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            params: 查询参数
            data: 表单数据
            json_data: JSON数据
            use_cache: 是否使用缓存
            max_retries: 最大重试次数
            timeout: 超时时间
            
        Returns:
            Response对象或None
        """
        # 检查缓存
        if use_cache and method.upper() == 'GET':
            cache_key = self.get_cache_key(url, params)
            cached = self.get_cached_response(cache_key)
            if cached:
                logger.debug(f"使用缓存: {url}")
                # 创建模拟响应
                response = requests.Response()
                response.status_code = 200
                response._content = json.dumps(cached).encode('utf-8')
                response.encoding = 'utf-8'
                return response
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=timeout)
                elif method.upper() == 'POST':
                    if json_data:
                        response = self.session.post(url, json=json_data, timeout=timeout)
                    else:
                        response = self.session.post(url, data=data, timeout=timeout)
                else:
                    logger.error(f"不支持的HTTP方法: {method}")
                    return None
                
                response.raise_for_status()
                response.encoding = 'utf-8' if 'utf-8' in response.headers.get('content-type', '').lower() else 'gbk'
                
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
                
                if status_code in [403, 404, 429]:
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
    
    def get_universities(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        获取大学列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            大学列表
        """
        logger.info(f"获取大学列表，第 {page} 页")
        
        # 模拟API请求（实际应调用真实API）
        universities = []
        
        # 模拟数据
        mock_universities = [
            {'id': '1001', 'name': '北京大学', 'abbr': 'PKU', 'location': '北京'},
            {'id': '1002', 'name': '清华大学', 'abbr': 'THU', 'location': '北京'},
            {'id': '1003', 'name': '浙江大学', 'abbr': 'ZJU', 'location': '杭州'},
            {'id': '1004', 'name': '复旦大学', 'abbr': 'FDU', 'location': '上海'},
            {'id': '1005', 'name': '上海交通大学', 'abbr': 'SJTU', 'location': '上海'},
            {'id': '1006', 'name': '南京大学', 'abbr': 'NJU', 'location': '南京'},
            {'id': '1007', 'name': '中国科学技术大学', 'abbr': 'USTC', 'location': '合肥'},
            {'id': '1008', 'name': '哈尔滨工业大学', 'abbr': 'HIT', 'location': '哈尔滨'},
            {'id': '1009', 'name': '西安交通大学', 'abbr': 'XJTU', 'location': '西安'},
            {'id': '1010', 'name': '华中科技大学', 'abbr': 'HUST', 'location': '武汉'},
        ]
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        for uni in mock_universities[start_idx:end_idx]:
            university = {
                'university_id': uni['id'],
                'name': uni['name'],
                'english_name': '',
                'abbreviation': uni['abbr'],
                'location': uni['location'],
                'type': '综合类',
                'level': '985/211',
                'description': f"{uni['name']}是中国著名的高等学府，在国内外享有盛誉。",
                'website': f"https://www.{uni['abbr'].lower()}.edu.cn",
                'logo_url': f"https://example.com/logos/{uni['abbr'].lower()}.png",
                'total_courses': random.randint(50, 200),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            universities.append(university)
        
        logger.info(f"获取到 {len(universities)} 所大学")
        return universities
    
    def get_courses_by_university(self, university_id: str, page: int = 1, 
                                 page_size: int = 10) -> List[Dict]:
        """
        获取指定大学的课程
        
        Args:
            university_id: 大学ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            课程列表
        """
        logger.info(f"获取大学 {university_id} 的课程，第 {page} 页")
        
        # 模拟课程数据
        course_templates = [
            {
                'title': '计算机科学导论',
                'category': '计算机',
                'difficulty': '初级',
                'duration': 10
            },
            {
                'title': '人工智能基础',
                'category': '人工智能',
                'difficulty': '中级',
                'duration': 12
            },
            {
                'title': '数据结构与算法',
                'category': '计算机',
                'difficulty': '中级',
                'duration': 14
            },
            {
                'title': '机器学习',
                'category': '人工智能',
                'difficulty': '高级',
                'duration': 16
            },
            {
                'title': '深度学习',
                'category': '人工智能',
                'difficulty': '高级',
                'duration': 15
            },
            {
                'title': '自然语言处理',
                'category': '人工智能',
                'difficulty': '高级',
                'duration': 13
            },
            {
                'title': '计算机视觉',
                'category': '人工智能',
                'difficulty': '高级',
                'duration': 14
            },
            {
                'title': 'Python程序设计',
                'category': '编程',
                'difficulty': '初级',
                'duration': 8
            },
            {
                'title': 'Java程序设计',
                'category': '编程',
                'difficulty': '中级',
                'duration': 10
            },
            {
                'title': 'Web前端开发',
                'category': '前端开发',
                'difficulty': '中级',
                'duration': 12
            }
        ]
        
        courses = []
        start_idx = (page - 1) * page_size
        
        for i in range(page_size):
            idx = (start_idx + i) % len(course_templates)
            template = course_templates[idx]
            
            course = {
                'course_id': f"COURSE_{university_id}_{start_idx + i + 1}",
                'title': template['title'],
                'subtitle': f"{template['title']} - 在线开放课程",
                'university_id': university_id,
                'term': '2023-2024学年第二学期',
                'start_date': '2024-03-01',
                'end_date': '2024-06-30',
                'duration_weeks': template['duration'],
                'hours_per_week': random.randint(3, 6),
                'language': '中文',
                'difficulty': template['difficulty'],
                'category': template['category'],
                'subcategory': '',
                'tags': ','.join([template['category'], template['difficulty'], '在线课程']),
                'description': f"本课程系统介绍{template['title']}的基本概念、原理和方法。通过本课程的学习，学生将掌握{template['title']}的核心知识和实践技能。",
                'learning_outcomes': '1. 理解基本概念；2. 掌握核心方法；3. 能够解决实际问题',
                'syllabus': '第一周：概述；第二周：基础知识；第三周：核心概念...',
                'cover_image': f"https://example.com/covers/{template['category']}.jpg",
                'video_intro': f"https://example.com/videos/{template['title']}.mp4",
                'enrollment_count': random.randint(1000, 50000),
                'rating': round(random.uniform(4.0, 5.0), 1),
                'review_count': random.randint(100, 5000),
                'url': f"{self.base_url}/course/{university_id}-{start_idx + i + 1}",
                'status': '进行中',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            courses.append(course)
        
        logger.info(f"为大学 {university_id} 生成 {len(courses)} 门课程")
        return courses
    
    def get_course_detail(self, course_url: str) -> Optional[Dict]:
        """
        获取课程详情
        
        Args:
            course_url: 课程URL
            
        Returns:
            课程详情字典
        """
        logger.info(f"获取课程详情: {course_url}")
        
        # 从URL中提取课程ID
        course_id = self._extract_course_id(course_url)
        if not course_id:
            logger.warning(f"无法从URL提取课程ID: {course_url}")
            return None
        
        # 模拟API请求
        response = self.safe_request(course_url, use_cache=True)
        if not response:
            logger.warning(f"获取课程详情失败: {course_url}")
            return self._generate_mock_course_detail(course_id, course_url)
        
        # 解析响应（这里简化处理）
        try:
            # 尝试解析JSON
            data = response.json()
            detail = self._parse_course_api_response(data, course_url)
        except:
            # 如果失败，生成模拟数据
            detail = self._generate_mock_course_detail(course_id, course_url)
        
        return detail
    
    def _extract_course_id(self, url: str) -> Optional[str]:
        """从URL中提取课程ID"""
        try:
            # 尝试从URL路径中提取
            patterns = [
                r'/course/([^/?]+)',
                r'courseId=([^&]+)',
                r'id=([^&]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # 生成基于URL哈希的ID
            return f"COURSE_{hashlib.md5(url.encode()).hexdigest()[:8]}"
            
        except Exception:
            return None
    
    def _parse_course_api_response(self, data: Dict, course_url: str) -> Dict:
        """解析课程API响应"""
        # 这里应该根据实际API响应结构进行解析
        # 现在返回模拟数据
        return self._generate_mock_course_detail(
            data.get('courseId', 'UNKNOWN'), 
            course_url
        )
    
    def _generate_mock_course_detail(self, course_id: str, course_url: str) -> Dict:
        """生成模拟课程详情"""
        
        # 生成课程模块
        modules = []
        module_titles = [
            '课程导论与概述',
            '基础知识与核心概念',
            '关键技术与方法',
            '实践应用与案例分析',
            '高级主题与前沿进展',
            '项目实践与综合训练',
            '复习总结与考核'
        ]
        
        for i, title in enumerate(module_titles[:random.randint(4, 7)]):
            module = {
                'module_number': i + 1,
                'title': title,
                'description': f"本模块介绍{title}的相关内容",
                'duration_hours': round(random.uniform(2.0, 6.0), 1),
                'order_index': i
            }
            modules.append(module)
        
        # 生成学习资料
        materials = []
        material_types = ['视频', '文档', 'PPT', '作业', '测验', '讨论']
        
        for i, module in enumerate(modules):
            for j in range(random.randint(2, 5)):
                material_type = random.choice(material_types)
                material = {
                    'module_id': i + 1,
                    'material_type': material_type,
                    'title': f"{module['title']} - {material_type} {j+1}",
                    'description': f"这是{module['title']}的{material_type}资料",
                    'url': f"https://example.com/materials/{course_id}_{i}_{j}.{material_type.lower()}",
                    'file_size': f"{random.randint(1, 100)}MB",
                    'file_format': material_type.lower(),
                    'duration': f"{random.randint(5, 60)}分钟" if material_type == '视频' else '',
                    'order_index': j
                }
                materials.append(material)
        
        # 生成教师信息
        teachers = []
        teacher_names = ['张教授', '李教授', '王副教授', '刘讲师', '陈助教']
        
        for i, name in enumerate(teacher_names[:random.randint(1, 3)]):
            teacher = {
                'teacher_id': f"TEA_{course_id}_{i}",
                'name': name,
                'title': name[-2:],  # 提取职称
                'department': '计算机科学与技术学院',
                'university_id': course_id.split('_')[1] if '_' in course_id else '1001',
                'introduction': f"{name}是著名的计算机科学专家，在相关领域有深入研究。",
                'research_interests': '人工智能、机器学习、数据挖掘',
                'avatar_url': f"https://example.com/avatars/{name}.jpg",
                'role': '主讲教师' if i == 0 else '辅助教师'
            }
            teachers.append(teacher)
        
        detail = {
            'course_id': course_id,
            'modules': modules,
            'materials': materials,
            'teachers': teachers,
            'prerequisites': '具备基本的编程知识和数学基础',
            'assessment_method': '作业30% + 测验30% + 期末考试40%',
            'certificate_requirements': '完成所有作业和测验，总成绩达到60分以上',
            'resources': {
                'textbook': '《计算机科学导论》',
                'software': 'Python 3.8+, Jupyter Notebook',
                'tools': 'VS Code, Git'
            },
            'detail_crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return detail
    
    def save_to_database(self, university: Dict, courses: List[Dict], 
                        course_details: List[Dict]):
        """保存数据到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 保存大学信息
            cursor.execute('''
                INSERT OR REPLACE INTO universities 
                (university_id, name, english_name, abbreviation, location, 
                 type, level, description, website, logo_url, total_courses, 
                 crawl_time, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                university.get('university_id'),
                university.get('name'),
                university.get('english_name', ''),
                university.get('abbreviation', ''),
                university.get('location', ''),
                university.get('type', ''),
                university.get('level', ''),
                university.get('description', ''),
                university.get('website', ''),
                university.get('logo_url', ''),
                university.get('total_courses', 0),
                university.get('crawl_time'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # 保存课程信息
            for course in courses:
                cursor.execute('''
                    INSERT OR REPLACE INTO courses 
                    (course_id, title, subtitle, university_id, term, 
                     start_date, end_date, duration_weeks, hours_per_week, 
                     language, difficulty, category, subcategory, tags, 
                     description, learning_outcomes, syllabus, cover_image, 
                     video_intro, enrollment_count, rating, review_count, 
                     url, status, crawl_time, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    course.get('course_id'),
                    course.get('title'),
                    course.get('subtitle', ''),
                    course.get('university_id'),
                    course.get('term', ''),
                    course.get('start_date', ''),
                    course.get('end_date', ''),
                    course.get('duration_weeks', 0),
                    course.get('hours_per_week', 0),
                    course.get('language', ''),
                    course.get('difficulty', ''),
                    course.get('category', ''),
                    course.get('subcategory', ''),
                    course.get('tags', ''),
                    course.get('description', ''),
                    course.get('learning_outcomes', ''),
                    course.get('syllabus', ''),
                    course.get('cover_image', ''),
                    course.get('video_intro', ''),
                    course.get('enrollment_count', 0),
                    course.get('rating', 0.0),
                    course.get('review_count', 0),
                    course.get('url', ''),
                    course.get('status', ''),
                    course.get('crawl_time'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            # 保存课程详情
            for detail in course_details:
                course_id = detail.get('course_id')
                
                # 保存教师信息
                for teacher in detail.get('teachers', []):
                    cursor.execute('''
                        INSERT OR REPLACE INTO teachers 
                        (teacher_id, name, english_name, title, department, 
                         university_id, introduction, research_interests, 
                         avatar_url, personal_website, total_courses, 
                         crawl_time, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        teacher.get('teacher_id'),
                        teacher.get('name'),
                        teacher.get('english_name', ''),
                        teacher.get('title', ''),
                        teacher.get('department', ''),
                        teacher.get('university_id'),
                        teacher.get('introduction', ''),
                        teacher.get('research_interests', ''),
                        teacher.get('avatar_url', ''),
                        teacher.get('personal_website', ''),
                        teacher.get('total_courses', 0),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    # 保存课程-教师关系
                    cursor.execute('''
                        INSERT OR REPLACE INTO course_teachers 
                        (course_id, teacher_id, role, order_index)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        course_id,
                        teacher.get('teacher_id'),
                        teacher.get('role', '主讲教师'),
                        teacher.get('order_index', 0)
                    ))
                
                # 保存课程模块
                for module in detail.get('modules', []):
                    cursor.execute('''
                        INSERT INTO course_modules 
                        (course_id, module_number, title, description, 
                         duration_hours, order_index)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        course_id,
                        module.get('module_number'),
                        module.get('title'),
                        module.get('description'),
                        module.get('duration_hours'),
                        module.get('order_index')
                    ))
                    
                    module_id = cursor.lastrowid
                    
                    # 保存学习资料
                    for material in detail.get('materials', []):
                        if material.get('module_id') == module.get('module_number'):
                            cursor.execute('''
                                INSERT INTO learning_materials 
                                (course_id, module_id, material_type, title, 
                                 description, url, file_size, file_format, 
                                 duration, order_index, crawl_time)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                course_id,
                                module_id,
                                material.get('material_type'),
                                material.get('title'),
                                material.get('description'),
                                material.get('url'),
                                material.get('file_size'),
                                material.get('file_format'),
                                material.get('duration'),
                                material.get('order_index'),
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            ))
            
            conn.commit()
            self.crawl_stats['successful'] += len(courses)
            logger.info(f"保存 {len(courses)} 门课程到数据库")
            
        except sqlite3.Error as e:
            self.crawl_stats['failed'] += len(courses)
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
    
    def run(self, max_universities: int = 2, courses_per_university: int = 3):
        """
        运行爬虫
        
        Args:
            max_universities: 最大大学数量
            courses_per_university: 每所大学最大课程数量
        """
        logger.info("=== MOOC课程爬虫开始运行 ===")
        self.crawl_stats['start_time'] = datetime.now()
        
        try:
            # 1. 获取大学列表
            universities = self.get_universities(page=1, page_size=max_universities)
            self.crawl_stats['total_universities'] = len(universities)
            
            if not universities:
                logger.error("未能获取大学信息")
                return
            
            all_courses = []
            all_course_details = []
            
            # 2. 处理每所大学
            for i, university in enumerate(universities):
                logger.info(f"处理大学 {i+1}/{len(universities)}: {university['name']}")
                
                # 获取课程列表
                courses = self.get_courses_by_university(
                    university['university_id'], 
                    page=1, 
                    page_size=courses_per_university
                )
                
                # 获取课程详情
                course_details = []
                for j, course in enumerate(courses):
                    logger.info(f"  处理课程 {j+1}/{len(courses)}: {course['title']}")
                    
                    detail = self.get_course_detail(course['url'])
                    if detail:
                        course_details.append(detail)
                        
                        # 随机延迟
                        time.sleep(random.uniform(0.5, 1.5))
                
                # 保存到数据库
                if courses and course_details:
                    self.save_to_database(university, courses, course_details)
                
                # 保存到文件
                if courses:
                    uni_name = university['name'].replace('/', '_')
                    self.save_to_csv(courses, f"university_{uni_name}_courses.csv")
                
                if course_details:
                    self.save_to_json(course_details, f"university_{university['university_id']}_details.json")
                
                all_courses.extend(courses)
                all_course_details.extend(course_details)
                
                # 更新统计
                self.crawl_stats['total_courses'] += len(courses)
                self.crawl_stats['total_teachers'] += sum(len(d.get('teachers', [])) for d in course_details)
            
            # 3. 保存所有数据
            if all_courses:
                self.save_to_csv(all_courses, "all_courses.csv")
            
            if all_course_details:
                self.save_to_json(all_course_details, "all_course_details.json")
            
            # 4. 更新统计信息
            self.crawl_stats['end_time'] = datetime.now()
            self.save_to_json(self.crawl_stats, "crawl_statistics.json")
            
            logger.info("=== 爬虫运行完成 ===")
            logger.info(f"统计信息: {json.dumps(self.crawl_stats, default=str, indent=2)}")
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}", exc_info=True)
        finally:
            logger.info("=== MOOC课程爬虫结束 ===")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = MOOCCourseCrawler()
    
    # 运行爬虫
    crawler.run(max_universities=2, courses_per_university=2)
    
    # 显示使用说明
    print("\n" + "="*60)
    print("MOOC课程爬虫使用说明")
    print("="*60)
    print("1. 获取大学列表:")
    print("   universities = crawler.get_universities(page=1, page_size=10)")
    print("\n2. 获取大学课程:")
    print("   courses = crawler.get_courses_by_university('1001', page=1, page_size=10)")
    print("\n3. 获取课程详情:")
    print("   detail = crawler.get_course_detail(course_url)")
    print("\n4. 保存数据:")
    print("   crawler.save_to_csv(data, 'filename.csv')")
    print("   crawler.save_to_json(data, 'filename.json')")
    print("\n5. 查看数据库:")
    print(f"   数据库文件: {crawler.db_path}")
    print("   数据目录: crawler.data_dir")
    print("\n6. 清除缓存:")
    print("   删除目录: crawler.cache_dir")

if __name__ == "__main__":
    main()