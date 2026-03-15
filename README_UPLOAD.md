# 🚀 GitHub上传指南

## 快速开始

### 第一步：创建GitHub仓库
1. 访问：https://github.com/new
2. 填写信息：
   - **Repository name**: `python-web-crawlers`
   - **Description**: `50个专业Python爬虫程序集合`
   - **Public** (选择公开)
   - **不要**初始化README、.gitignore、license
3. 点击 "Create repository"

### 第二步：修改上传脚本
用记事本打开 `upload_to_github.bat`，将：
```
set GITHUB_USER=YOUR_GITHUB_USERNAME
```
改为你的GitHub用户名，例如：
```
set GITHUB_USER=amoyeah
```

### 第三步：运行上传脚本
双击 `upload_to_github.bat`，按照提示操作。

## 详细步骤

### 方法A：使用批处理脚本 (推荐)
1. 右键点击 `upload_to_github.bat`
2. 选择 "以管理员身份运行"
3. 按照提示输入GitHub凭据

### 方法B：使用PowerShell脚本
1. 右键点击 `upload_to_github.ps1`
2. 选择 "使用PowerShell运行"
3. 如果遇到安全策略问题，运行：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### 方法C：手动命令
打开命令提示符，运行：
```cmd
cd D:\openclaw\workspace\crawlers
git remote add origin https://github.com/你的用户名/python-web-crawlers.git
git branch -M main
git push -u origin main
```

## 🔑 GitHub认证

### 使用密码（不推荐）
直接输入GitHub密码

### 使用Personal Access Token（推荐）
1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：`repo` (全选)
4. 生成Token并复制
5. 推送时，密码处粘贴Token

## 🆘 常见问题

### Q1: 提示 "Repository not found"
A: 确保仓库已创建，用户名正确

### Q2: 提示 "Authentication failed"
A: 使用Personal Access Token代替密码

### Q3: 文件太大上传失败
A: 使用Git LFS或分批次上传

### Q4: 网络连接问题
A: 检查代理设置或使用VPN

## 📞 支持

如果遇到问题：
1. 检查 `GITHUB_SETUP.md` 文件
2. 参考GitHub文档：https://docs.github.com
3. 查看Git错误信息

## 🎉 成功标志

上传成功后，访问：
```
https://github.com/你的用户名/python-web-crawlers
```

应该看到：
- 50个爬虫文件
- 完整的项目结构
- 详细的README文档

---

**祝上传顺利！** 🚀