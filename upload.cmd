@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: 配置项 - 可根据需要修改默认分支
set "default_branch=main"

:: 检查是否安装了 Git
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未检测到 Git 安装。
    echo    请先安装 Git 并确保已添加到系统环境变量。
    pause
    exit /b 1
)

:: 检查当前目录是否是 Git 仓库
if not exist ".git" (
    echo ❌ 错误：当前目录不是 Git 仓库。
    echo    请在 Git 仓库根目录运行此脚本。
    pause
    exit /b 1
)

:: 拉取远程最新代码，避免冲突
echo 🔄 正在拉取远程最新代码...
git pull origin !default_branch!
if !errorlevel! neq 0 (
    echo ❌ 错误：拉取代码失败。
    echo    可能原因：网络问题、权限不足或存在合并冲突。
    echo    请手动解决后重试。
    pause
    exit /b 1
)

:: 检查是否有需要提交的更改
echo 🔍 检查是否有修改...
git status --porcelain >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ 错误：检查文件状态失败。
    pause
    exit /b 1
)

set "has_changes="
for /f "delims=" %%i in ('git status --porcelain') do (
    set "has_changes=1"
)
if not defined has_changes (
    echo ℹ️ 提示：没有需要提交的修改。
    pause
    exit /b 0
)

:: 提示输入提交信息
:input_msg
set /p commit_msg="✏️ 请输入提交信息: "
if "!commit_msg!"=="" (
    echo ⚠️ 警告：提交信息不能为空，请重新输入。
    goto input_msg
)

:: 执行 Git 提交操作
echo ➕ 正在添加所有更改...
git add --all
if !errorlevel! neq 0 (
    echo ❌ 错误：添加文件失败。
    pause
    exit /b 1
)

echo 📝 正在提交更改...
git commit -m "!commit_msg!"
if !errorlevel! neq 0 (
    echo ❌ 错误：提交更改失败。
    echo    可能原因：提交信息不符合规范或存在配置问题。
    pause
    exit /b 1
)

echo 🚀 正在推送到远程仓库...
git push origin !default_branch!
if !errorlevel! neq 0 (
    echo ❌ 错误：推送更改失败。
    echo    可能原因：网络问题、权限不足或分支不存在。
    pause
    exit /b 1
)

echo ✅ 操作完成！所有更改已成功提交并推送。
pause
