@echo off
setlocal enabledelayedexpansion
chcp 65001

:: 检查是否在Git仓库中
git rev-parse --is-inside-work-tree >nul 2>&1
if not %errorlevel% equ 0 (
    echo 错误：当前目录不是Git仓库！
    pause
    exit /b 1
)

:: 拉取远程最新代码（避免冲突）
echo 正在拉取远程最新代码...
git pull
if not %errorlevel% equ 0 (
    echo 拉取代码失败，请手动解决冲突后重试
    pause
    exit /b 1
)

:: 检查是否有修改
git status --porcelain
if %errorlevel% equ 0 (
    set "changes="
    for /f "delims=" %%i in ('git status --porcelain') do (
        set "changes=1"
    )
    if not defined changes (
        echo 没有需要提交的修改
        pause
        exit /b 0
    )
)

:: 添加所有修改
echo 正在添加所有修改...
git add .
if not %errorlevel% equ 0 (
    echo 添加文件失败
    pause
    exit /b 1
)

:: 获取提交信息
set /p commit_msg=请输入提交信息:
if "!commit_msg!"=="" (
    set commit_msg=自动提交: %date% %time%
    echo 未输入提交信息，使用默认信息: !commit_msg!
)

:: 提交修改
echo 正在提交修改...
git commit -m "!commit_msg!"
if not %errorlevel% equ 0 (
    echo 提交失败
    pause
    exit /b 1
)

:: 推送到远程仓库
echo 正在推送到远程仓库...
git push origin main
:: 如果你的主分支是master，请将上面的main改为master
if not %errorlevel% equ 0 (
    echo 推送失败
    pause
    exit /b 1
)

echo 操作完成：提交和推送成功！
pause
endlocal
