# 🚀 CI/CD 和部署指南

## GitHub Actions CI/CD 流水线

### 工作流功能

我们的CI/CD流水线包含以下工作：

1. **测试工作** (`test`):
   - Python多版本测试 (3.8, 3.9, 3.10, 3.11, 3.12)
   - 代码风格检查 (flake8, black, isort)
   - 单元测试和覆盖率检测
   - 覆盖率上传到Codecov

2. **文档部署** (`deploy-docs`):
   - 自动部署到GitHub Pages
   - 支持自定义域名
   - 实时更新文档

3. **Docker构建** (`docker-build`):
   - 自动构建Docker镜像
   - 推送到DockerHub
   - 多标签支持 (latest, commit-sha)

4. **发布管理** (`release`):
   - 自动创建GitHub Release
   - 打包发布文件
   - 版本标签管理

### 触发条件

- **push到main/master分支**：运行全部工作流
- **pull request**：运行测试工作
- **定时任务**：每周日运行一次
- **标签推送** (v*): 创建Release

## 📚 GitHub Pages 配置

### 访问地址

- 主站点: https://tonganlianhua.github.io/python-web-crawlers/
- 自定义域名: python-crawlers.tonganlianhua.github.io

### 站点结构

```
docs/
├── index.md          # 首页
├── guide.md          # 使用指南
├── _config.yml       # Jekyll配置
├── CNAME             # 自定义域名
└── assets/           # 静态资源
```

### 自动部署

每次推送到main分支时，GitHub Actions会自动：
1. 构建Jekyll站点
2. 部署到gh-pages分支
3. 更新在线文档

## 🐳 Docker 部署

### 镜像信息

```bash
# Docker Hub地址
tonganlianhua/python-web-crawlers

# 可用标签
latest          # 最新稳定版
<commit-sha>    # 特定提交版本
<version>       # 版本标签 (如v1.0.0)
```

### 运行方式

#### 简单运行
```bash
docker run -d \
  --name python-crawlers \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  tonganlianhua/python-web-crawlers:latest
```

#### 使用docker-compose
```bash
# 复制环境变量文件
cp .env.example .env

# 编辑环境变量
nano .env

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 生产环境部署
```bash
# 使用docker-compose.prod.yml
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 使用TLS加密
docker-compose -f docker-compose.yml -f docker-compose.tls.yml up -d
```

## 🔧 环境变量配置

### 必需配置
```bash
# 数据库连接
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis连接
REDIS_URL=redis://host:6379/0
```

### 可选配置
```bash
# 代理设置
PROXY_ENABLED=true
PROXY_URL=http://proxy-server:port

# API密钥
GITHUB_TOKEN=your_github_token
OPENWEATHER_API_KEY=your_api_key

# 日志设置
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

## 📊 监控和日志

### 内置监控
- **健康检查**: `/health` 端点
- **指标收集**: Prometheus metrics
- **日志聚合**: JSON格式日志

### 外部监控集成
```yaml
# Prometheus配置示例
scrape_configs:
  - job_name: 'python-crawlers'
    static_configs:
      - targets: ['localhost:8000']
```

### 日志查看
```bash
# 查看Docker日志
docker logs python-crawlers

# 实时日志
docker logs -f python-crawlers

# 查看特定时间的日志
docker logs --since 1h python-crawlers
```

## 🔐 安全配置

### 环境安全
1. **使用.env文件**存储敏感信息
2. **不要提交**.env文件到Git
3. **使用密钥管理** (GitHub Secrets, Docker Secrets)

### 网络安全
```yaml
# 限制网络访问
networks:
  crawler-network:
    driver: bridge
    internal: true  # 内部网络
```

### 容器安全
```dockerfile
# 使用非root用户
USER crawler:1000

# 限制权限
RUN chmod -R 755 /app/data
```

## 🆘 故障排除

### CI/CD问题

**问题**: GitHub Actions失败
**解决**:
1. 检查工作流日志
2. 验证环境变量
3. 检查依赖版本

**问题**: Docker构建失败
**解决**:
1. 检查Dockerfile语法
2. 验证基础镜像可用性
3. 检查网络连接

### 部署问题

**问题**: GitHub Pages无法访问
**解决**:
1. 检查CNAME配置
2. 验证仓库设置
3. 检查构建日志

**问题**: Docker容器无法启动
**解决**:
1. 检查端口冲突
2. 验证卷挂载
3. 查看容器日志

## 📈 性能优化

### CI/CD优化
```yaml
# 启用缓存
cache:
  paths:
    - ~/.cache/pip
    - ~/.npm
```

### Docker优化
```dockerfile
# 多阶段构建
FROM python:3.10-slim as builder
FROM python:3.10-slim as runtime
```

### 部署优化
```yaml
# 资源限制
resources:
  limits:
    cpus: '2'
    memory: 2G
  reservations:
    cpus: '1'
    memory: 1G
```

## 🔄 更新和维护

### 更新流程
1. 开发新功能
2. 提交到开发分支
3. 运行CI测试
4. 合并到main分支
5. 自动部署

### 回滚流程
```bash
# 回滚到上一个版本
docker-compose down
docker pull tonganlianhua/python-web-crawlers:previous-version
docker-compose up -d
```

### 监控维护
1. 定期检查日志
2. 监控资源使用
3. 更新安全补丁
4. 备份重要数据

---

**🎯 现在你的项目拥有完整的CI/CD和部署流水线！**