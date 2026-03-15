@echo off
echo ========================================
echo GitHub上传脚本
echo ========================================
echo.

REM 请将 YOUR_GITHUB_USERNAME 替换为你的GitHub用户名
set GITHUB_USER=YOUR_GITHUB_USERNAME
set REPO_NAME=python-web-crawlers

echo 1. 设置远程仓库...
git remote remove origin
git remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git

echo.
echo 2. 重命名分支...
git branch -M main

echo.
echo 3. 推送到GitHub...
echo.
echo 注意：可能需要输入GitHub用户名和密码
echo 密码可以使用Personal Access Token
echo.
git push -u origin main

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo ✅ 上传成功！
    echo.
    echo 请访问：https://github.com/%GITHUB_USER%/%REPO_NAME%
) else (
    echo ❌ 上传失败，请检查：
    echo 1. GitHub用户名是否正确
    echo 2. 仓库是否已创建
    echo 3. 网络连接是否正常
    echo 4. 是否需要使用Personal Access Token
)
echo ========================================
pause