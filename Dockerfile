# 使用官方Python镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        wget \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 设置数据目录权限
RUN chmod -R 755 /app/data /app/logs

# 创建非root用户
RUN useradd -m -u 1000 crawler \
    && chown -R crawler:crawler /app

USER crawler

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; print('Health check passed')" || exit 1

# 暴露端口（如果需要的话）
EXPOSE 8000

# 设置默认命令
CMD ["python", "run_all.py"]

# 标签
LABEL maintainer="tonganlianhua <amoyeah@163.com>"
LABEL version="1.0.0"
LABEL description="50个专业Python爬虫程序集合"
LABEL org.opencontainers.image.source="https://github.com/tonganlianhua/python-web-crawlers"