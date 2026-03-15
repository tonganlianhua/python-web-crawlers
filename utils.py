#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫项目工具函数集合
"""

import os
import json
import time
import random
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urljoin, quote_plus

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from config import (
    HEADERS, REQUEST_TIMEOUT, REQUEST_RETRY, REQUEST_DELAY,
    REQUEST_RETRY_DELAY, PROXY_ENABLED, PROXY_URL,
    DATA_DIR, LOG_DIR, CACHE_DIR, CACHE_TTL, SAVE_FORMAT, SAVE_ENCODING
)

# ==================== 日志配置 ====================
def setup_logger(name: str, log_file: Optional[Path] = None, level: str = "INFO") -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建默认日志记录器
logger = setup_logger("crawler_utils")

# ==================== HTTP请求工具 ====================
def create_session() -> requests.Session:
    """
    创建带重试机制的会话
    
    Returns:
        requests.Session: 配置好的会话
    """
    session = requests.Session()
    
    # 重试策略
    retry_strategy = Retry(
        total=REQUEST_RETRY,
        backoff_factor=REQUEST_RETRY_DELAY,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置默认请求头
    session.headers.update(HEADERS)
    
    return session

def make_request(
    url: str,
    method: str = "GET",
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = REQUEST_TIMEOUT,
    use_proxy: bool = PROXY_ENABLED,
    retry_count: int = REQUEST_RETRY
) -> Optional[requests.Response]:
    """
    发送HTTP请求
    
    Args:
        url: 请求URL
        method: 请求方法
        params: URL参数
        data: 表单数据
        json_data: JSON数据
        headers: 请求头
        timeout: 超时时间
        use_proxy: 是否使用代理
        retry_count: 重试次数
        
    Returns:
        Optional[requests.Response]: 响应对象，失败返回None
    """
    session = create_session()
    
    # 合并请求头
    request_headers = HEADERS.copy()
    if headers:
        request_headers.update(headers)
    
    # 代理设置
    proxies = None
    if use_proxy and PROXY_URL:
        proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }
    
    # 延迟处理
    time.sleep(REQUEST_DELAY + random.uniform(0, 0.5))
    
    try:
        response = session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            headers=request_headers,
            timeout=timeout,
            proxies=proxies
        )
        response.raise_for_status()
        logger.info(f"成功请求 {url}，状态码: {response.status_code}")
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"请求失败 {url}: {e}")
        if retry_count > 0:
            logger.info(f"重试请求 {url}，剩余重试次数: {retry_count}")
            time.sleep(REQUEST_RETRY_DELAY)
            return make_request(
                url, method, params, data, json_data,
                headers, timeout, use_proxy, retry_count - 1
            )
        return None

# ==================== 数据解析工具 ====================
def parse_html(response: requests.Response, parser: str = "lxml") -> Any:
    """
    解析HTML响应
    
    Args:
        response: 响应对象
        parser: 解析器类型
        
    Returns:
        Any: BeautifulSoup对象或Element对象
    """
    from bs4 import BeautifulSoup
    
    try:
        soup = BeautifulSoup(response.content, parser)
        return soup
    except Exception as e:
        logger.error(f"HTML解析失败: {e}")
        return None

def parse_json(response: requests.Response) -> Optional[Union[Dict, List]]:
    """
    解析JSON响应
    
    Args:
        response: 响应对象
        
    Returns:
        Optional[Union[Dict, List]]: JSON数据
    """
    try:
        return response.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return None

# ==================== 数据存储工具 ====================
def save_data(
    data: Union[Dict, List],
    filename: str,
    format_type: str = SAVE_FORMAT,
    encoding: str = SAVE_ENCODING
) -> bool:
    """
    保存数据到文件
    
    Args:
        data: 要保存的数据
        filename: 文件名（不带后缀）
        format_type: 保存格式
        encoding: 文件编码
        
    Returns:
        bool: 是否保存成功
    """
    try:
        filepath = DATA_DIR / f"{filename}.{format_type}"
        
        if format_type == "json":
            with open(filepath, "w", encoding=encoding) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        elif format_type == "csv":
            import pandas as pd
            if isinstance(data, list):
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False, encoding=encoding)
            else:
                logger.warning("CSV格式需要列表数据")
                return False
                
        else:
            logger.error(f"不支持的格式: {format_type}")
            return False
        
        logger.info(f"数据已保存到: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"数据保存失败: {e}")
        return False

def load_data(
    filename: str,
    format_type: str = SAVE_FORMAT,
    encoding: str = SAVE_ENCODING
) -> Optional[Union[Dict, List]]:
    """
    从文件加载数据
    
    Args:
        filename: 文件名（不带后缀）
        format_type: 文件格式
        encoding: 文件编码
        
    Returns:
        Optional[Union[Dict, List]]: 加载的数据
    """
    try:
        filepath = DATA_DIR / f"{filename}.{format_type}"
        
        if not filepath.exists():
            logger.warning(f"文件不存在: {filepath}")
            return None
            
        if format_type == "json":
            with open(filepath, "r", encoding=encoding) as f:
                return json.load(f)
                
        elif format_type == "csv":
            import pandas as pd
            df = pd.read_csv(filepath, encoding=encoding)
            return df.to_dict("records")
            
        else:
            logger.error(f"不支持的格式: {format_type}")
            return None
            
    except Exception as e:
        logger.error(f"数据加载失败: {e}")
        return None

# ==================== 缓存工具 ====================
def get_cache_key(url: str, params: Optional[Dict] = None) -> str:
    """
    生成缓存键
    
    Args:
        url: URL
        params: 参数
        
    Returns:
        str: 缓存键
    """
    key_str = url
    if params:
        key_str += json.dumps(params, sort_keys=True)
    
    return hashlib.md5(key_str.encode()).hexdigest()

def save_to_cache(
    key: str,
    data: Any,
    ttl: int = CACHE_TTL
) -> bool:
    """
    保存数据到缓存
    
    Args:
        key: 缓存键
        data: 要缓存的数据
        ttl: 缓存有效时间（秒）
        
    Returns:
        bool: 是否保存成功
    """
    try:
        cache_file = CACHE_DIR / f"{key}.json"
        
        cache_data = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl
        }
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        logger.error(f"缓存保存失败: {e}")
        return False

def load_from_cache(key: str) -> Optional[Any]:
    """
    从缓存加载数据
    
    Args:
        key: 缓存键
        
    Returns:
        Optional[Any]: 缓存的数据，过期或不存在返回None
    """
    try:
        cache_file = CACHE_DIR / f"{key}.json"
        
        if not cache_file.exists():
            return None
            
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
        # 检查是否过期
        current_time = time.time()
        if current_time - cache_data["timestamp"] > cache_data["ttl"]:
            # 删除过期缓存
            cache_file.unlink()
            return None
            
        return cache_data["data"]
        
    except Exception as e:
        logger.error(f"缓存加载失败: {e}")
        return None

# ==================== 验证工具 ====================
def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        bool: 是否有效
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def clean_text(text: str) -> str:
    """
    清理文本
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 去除空白字符
    text = " ".join(text.split())
    
    # 去除特殊字符（保留中文、英文、数字、常用标点）
    import re
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:()\'\"\-]', '', text)
    
    return text.strip()

# ==================== 批量处理工具 ====================
def batch_process(
    items: List,
    process_func: callable,
    batch_size: int = 50,
    delay: float = 1.0
) -> List:
    """
    批量处理数据
    
    Args:
        items: 要处理的数据项列表
        process_func: 处理函数
        batch_size: 每批大小
        delay: 批次间延迟
        
    Returns:
        List: 处理结果
    """
    results = []
    total = len(items)
    
    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        batch_results = []
        
        for item in batch:
            try:
                result = process_func(item)
                batch_results.append(result)
            except Exception as e:
                logger.error(f"处理失败: {item}, 错误: {e}")
                batch_results.append(None)
        
        results.extend(batch_results)
        
        # 显示进度
        processed = min(i + batch_size, total)
        logger.info(f"处理进度: {processed}/{total} ({processed/total*100:.1f}%)")
        
        # 批次间延迟
        if i + batch_size < total:
            time.sleep(delay)
    
    return results

# ==================== 文件工具 ====================
def generate_filename(prefix: str = "data") -> str:
    """
    生成带时间戳的文件名
    
    Args:
        prefix: 文件名前缀
        
    Returns:
        str: 生成的文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"

def ensure_directory(directory: Path) -> bool:
    """
    确保目录存在
    
    Args:
        directory: 目录路径
        
    Returns:
        bool: 是否成功
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {directory}: {e}")
        return False

# ==================== 辅助函数 ====================
def get_current_timestamp() -> str:
    """
    获取当前时间戳
    
    Returns:
        str: 格式化的时间戳
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def random_user_agent() -> str:
    """
    生成随机User-Agent
    
    Returns:
        str: 随机User-Agent
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)

if __name__ == "__main__":
    # 测试工具函数
    print("工具函数测试:")
    print(f"当前时间戳: {get_current_timestamp()}")
    print(f"随机User-Agent: {random_user_agent()}")
    print(f"数据目录: {DATA_DIR}")
    print(f"日志目录: {LOG_DIR}")
    
    # 测试缓存功能
    test_key = get_cache_key("https://example.com")
    print(f"缓存键生成: {test_key}")