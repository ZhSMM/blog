@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: 检查是否安装了 Git
git --version >nul 2>&1
if errorlevel 1 (
    echo Git 未安装或未正确配置，请先安装 Git。
    pause
    exit /b 1
)

:: 检查当前目录是否是 Git 仓库
if not exist ".git" (
    echo 当前目录不是 Git 仓库。
    pause
    exit /b 1
)

:: 提示输入提交信息
set /p commit_msg="请输入提交信息: "
if "!commit_msg!"=="" (
    echo 提交信息不能为空。
    pause
    exit /b 1
)

:: 执行 Git 操作
echo 正在添加所有更改...
git add --all >nul 2>&1
if !errorlevel! neq 0 (
    echo 添加文件时出错。
    pause
    exit /b 1
)

echo 正在提交更改...
git commit -m "!commit_msg!" >nul 2>&1
if !errorlevel! neq 0 (
    echo 提交更改时出错。
    pause
    exit /b 1
)

echo 正在推送到远程仓库...
git push >nul 2>&1
if !errorlevel! neq 0 (
    echo 推送更改时出错。
    pause
    exit /b 1
)

echo 操作完成！
pause