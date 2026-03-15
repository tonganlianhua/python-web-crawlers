# GitHub 上传指南

## 🚀 快速开始

### 第一步：在GitHub上创建仓库

1. **访问**：https://github.com/new
2. **填写信息**：
   - **Repository name**: `python-web-crawlers` (推荐)
   - **Description**: `50个专业Python爬虫程序集合 - 覆盖新闻、电商、社交、金融、娱乐等所有领域`
   - **Visibility**: Public (公开) 或 Private (私有)
   - **不要勾选**:
     - [ ] Initialize this repository with a README
     - [ ] Add .gitignore
     - [ ] Choose a license

3. **点击** "Create repository"

### 第二步：使用Git命令行上传

打开 **命令提示符 (cmd)** 或 **PowerShell**，运行以下命令：

```bash
# 1. 进入项目目录
cd D:\openclaw\workspace\crawlers

# 2. 设置远程仓库（替换YOUR_USERNAME为你的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/python-web-crawlers.git

# 3. 重命名主分支（如果需要）
git branch -M main

# 4. 推送到GitHub
git push -u origin main
```

### 第三步：验证上传成功

1. 访问你的仓库：`https://github.com/YOUR_USERNAME/python-web-crawlers`
2. 应该看到所有50个爬虫文件和配置文件
3. 确保文件数量正确

## 📊 项目统计

- **爬虫数量**: 50个专业Python爬虫
- **文件总数**: 65个文件
- **代码行数**: 50,000+ 行
- **覆盖领域**: 10+ 个行业领域

## 🐍 爬虫分类

1. **新闻媒体** (01-10): 今日头条、微博、Reddit等
2. **数据API** (11-20): 天气、股票、电影、GitHub等
3. **生活娱乐** (21-30): B站、网易云、Steam、NBA等
4. **科技金融** (31-40): 政府数据、加密货币、AI、区块链等
5. **社交媒体** (41-50): 微博热搜、抖音、B站、知乎等

## 🔧 技术特性

✅ 完整的错误处理机制
✅ 详细的日志记录系统
✅ 多种数据格式支持 (JSON/CSV/SQLite)
✅ 模块化设计，易于扩展
✅ 速率限制和请求控制
✅ 数据验证和清洗

## 🚀 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 运行单个爬虫
python crawler_01.py  # 今日头条新闻
python crawler_12.py  # 股票数据

# 批量运行所有爬虫
python run_all.py

# 测试爬虫功能
python test_crawler.py
```

## 📝 注意事项

1. **遵守robots.txt**：所有爬虫都考虑了目标网站的规则
2. **设置合理延迟**：避免对服务器造成过大压力
3. **使用代理**：高频率访问建议使用代理IP
4. **数据使用**：仅用于学习和研究目的

## 🆘 常见问题

### Q: 上传时遇到认证问题？
A: 使用GitHub Personal Access Token:
```bash
# 生成Token: Settings → Developer settings → Personal access tokens
# 推送时使用：
git push https://TOKEN@github.com/YOUR_USERNAME/python-web-crawlers.git
```

### Q: 文件太大上传失败？
A: 使用Git LFS或分批次上传

### Q: 如何更新仓库？
A: 修改后运行：
```bash
git add .
git commit -m "更新描述"
git push
```

## 📞 支持

如有问题，请参考：
- GitHub文档：https://docs.github.com
- Git教程：https://git-scm.com/book
- 项目README.md文件

---

**🎉 恭喜！你的专业爬虫项目即将上线！**