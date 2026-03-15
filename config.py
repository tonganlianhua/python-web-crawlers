#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫项目配置文件
"""

import os
from pathlib import Path

# ==================== 项目路径配置 ====================
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# 创建必要的目录
for directory in [DATA_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ==================== 请求配置 ====================
# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# 请求参数
REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
REQUEST_RETRY = 3     # 重试次数
REQUEST_DELAY = 1.0   # 请求延迟（秒）
REQUEST_RETRY_DELAY = 5.0  # 重试延迟（秒）

# ==================== 代理配置 ====================
PROXY_ENABLED = False  # 是否启用代理
PROXY_URL = None       # 代理地址，例如: "http://127.0.0.1:7890"

# ==================== 数据库配置 ====================
DATABASE_ENABLED = False
DATABASE_TYPE = "sqlite"  # sqlite/mysql/postgresql
DATABASE_URL = f"sqlite:///{DATA_DIR}/crawler.db"  # SQLite默认路径

# MySQL配置示例
# DATABASE_URL = "mysql://username:password@localhost:3306/crawler_db"

# PostgreSQL配置示例
# DATABASE_URL = "postgresql://username:password@localhost:5432/crawler_db"

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"  # DEBUG/INFO/WARNING/ERROR/CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOG_DIR / "crawler.log"

# ==================== 邮件通知配置 ====================
EMAIL_ENABLED = False
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_SENDER = "your-email@gmail.com"
EMAIL_PASSWORD = "your-password"
EMAIL_RECEIVERS = ["receiver1@example.com", "receiver2@example.com"]

# ==================== 缓存配置 ====================
CACHE_ENABLED = True
CACHE_DIR = DATA_DIR / "cache"
CACHE_TTL = 3600  # 缓存有效时间（秒）

# ==================== 数据存储配置 ====================
# 数据保存格式
SAVE_FORMAT = "json"  # json/csv/sqlite
SAVE_ENCODING = "utf-8"

# 批量保存大小
BATCH_SIZE = 100

# ==================== 验证码配置 ====================
CAPTCHA_ENABLED = False
CAPTCHA_API_KEY = None

# ==================== 浏览器自动化配置 ====================
BROWSER_ENABLED = False
BROWSER_TYPE = "chrome"  # chrome/firefox/edge
BROWSER_HEADLESS = True  # 是否无头模式
BROWSER_TIMEOUT = 30     # 浏览器超时时间（秒）

# ==================== API密钥配置 ====================
# 各个API服务的密钥配置
API_KEYS = {
    "openweathermap": None,  # 天气API
    "alphavantage": None,    # 股票数据API
    "github": None,          # GitHub API
    "reddit": None,          # Reddit API
    "twitter": None,         # Twitter API
    "youtube": None,         # YouTube API
    "tiktok": None,          # TikTok API
    "instagram": None,       # Instagram API
}

# ==================== 功能开关 ====================
FEATURE_FLAGS = {
    "enable_parallel": True,      # 启用并行处理
    "enable_retry": True,         # 启用重试机制
    "enable_logging": True,       # 启用日志记录
    "enable_cache": True,         # 启用缓存
    "enable_proxy_rotation": False,  # 启用代理轮换
    "enable_rate_limit": True,    # 启用速率限制
    "enable_validation": True,    # 启用数据验证
}

# ==================== 速率限制配置 ====================
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 10   # 每秒请求数
RATE_LIMIT_PERIOD = 1.0    # 时间窗口（秒）

# ==================== 错误处理配置 ====================
ERROR_HANDLING = {
    "max_retries": 3,              # 最大重试次数
    "retry_delay": 5,              # 重试延迟（秒）
    "log_errors": True,            # 记录错误
    "notify_errors": False,        # 错误通知
    "stop_on_critical": False,     # 关键错误时停止
}

# ==================== 监控配置 ====================
MONITORING_ENABLED = True
MONITORING_INTERVAL = 60  # 监控间隔（秒）

# ==================== 导出配置 ====================
EXPORT_CONFIG = {
    "json": {
        "indent": 2,
        "ensure_ascii": False,
    },
    "csv": {
        "encoding": "utf-8-sig",
        "index": False,
    },
    "excel": {
        "sheet_name": "Data",
        "index": False,
    }
}

# ==================== 环境变量覆盖 ====================
# 允许通过环境变量覆盖配置
import os
for key in dir():
    if key.isupper():
        env_key = f"CRAWLER_{key}"
        if env_key in os.environ:
            current_value = locals()[key]
            env_value = os.environ[env_key]
            
            # 尝试转换类型
            if isinstance(current_value, bool):
                globals()[key] = env_value.lower() in ("true", "1", "yes")
            elif isinstance(current_value, int):
                globals()[key] = int(env_value)
            elif isinstance(current_value, float):
                globals()[key] = float(env_value)
            elif isinstance(current_value, str):
                globals()[key] = env_value
            elif isinstance(current_value, list):
                globals()[key] = env_value.split(",")
            elif isinstance(current_value, dict):
                # 对于字典，需要特殊处理
                import json
                try:
                    globals()[key] = json.loads(env_value)
                except:
                    pass