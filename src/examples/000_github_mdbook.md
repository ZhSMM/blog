# 基于 GitHub + mdBook 搭建个人笔记工具

### 工具安装

#### 安装Git（版本控制工具）

- Windows：下载 [Git 官方安装包](https://git-scm.com/downloads/win)，安装时勾选「Add Git to PATH」（方便命令行调用）
- **Mac**：
  - 通过 Homebrew 安装：`brew install git`
  - 直接下载 [官方包](https://git-scm.com/download/mac)
- **Linux（Ubuntu/Debian）**：`sudo apt update && sudo apt install git`

验证安装：打开终端输入 `git --version`，显示版本号即成功。



#### 安装 mdBook（静态站点生成器）

推荐用 **预编译二进制** 安装（比 `cargo install` 快 10 倍以上）：

1. 访问 [mdBook Releases 页面](https://github.com/rust-lang/mdBook/releases)，下载对应系统的压缩包（如 Windows 选 `mdbook-v0.4.52-x86_64-pc-windows-msvc.zip`）
2. 解压压缩包，将mdbook.exe（Windows）或mdbook（Mac/Linux）放到系统环境变量目录：
   - Windows：复制到 `C:\Windows\System32` 或自定义目录并添加到 PATH
   - Mac/Linux：复制到 `/usr/local/bin`（命令：`sudo mv mdbook /usr/local/bin/`）

验证安装：终端输入 `mdbook --version`，显示 `mdbook v0.4.52` 即成功。



#### 准备Github账号

- 访问 [GitHub 注册页](https://github.com/)，创建账号（已有账号可跳过）
- 新建一个 **公开 / 私有仓库**（仓库名建议为 `username-notes` 或 `username.github.io`，后者可直接用域名访问）



### 初始化 mdbook 笔记

#### 创建本地项目目录

打开终端，执行以下命令创建并进入项目文件夹：

```bash
# 替换为你的项目名（如 my-tech-notes）
mkdir my-tech-notes && cd my-tech-notes
```