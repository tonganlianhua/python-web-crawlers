Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub上传脚本 (PowerShell版本)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 请将 YOUR_GITHUB_USERNAME 替换为你的GitHub用户名
$GITHUB_USER = "YOUR_GITHUB_USERNAME"
$REPO_NAME = "python-web-crawlers"

Write-Host "1. 设置远程仓库..." -ForegroundColor Yellow
git remote remove origin
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

Write-Host ""
Write-Host "2. 重命名分支..." -ForegroundColor Yellow
git branch -M main

Write-Host ""
Write-Host "3. 推送到GitHub..." -ForegroundColor Yellow
Write-Host ""
Write-Host "注意：可能需要输入GitHub用户名和密码" -ForegroundColor Magenta
Write-Host "密码可以使用Personal Access Token" -ForegroundColor Magenta
Write-Host ""
git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 上传成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "请访问：https://github.com/$GITHUB_USER/$REPO_NAME" -ForegroundColor Green
} else {
    Write-Host "❌ 上传失败，请检查：" -ForegroundColor Red
    Write-Host "1. GitHub用户名是否正确" -ForegroundColor Red
    Write-Host "2. 仓库是否已创建" -ForegroundColor Red
    Write-Host "3. 网络连接是否正常" -ForegroundColor Red
    Write-Host "4. 是否需要使用Personal Access Token" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Read-Host "按回车键继续"