# 基于 GitHub + mdBook 搭建个人笔记

* auto-gen TOC;
{:toc}

### 准备

准备工作如下：

1. 安装版本控制工具 Git：

   + windows：[https://git-scm.com/downloads/win](https://git-scm.com/downloads/win)，安装时勾选「Add Git to PATH」，方便命令行调用。
   + Mac：[https://git-scm.com/download/mac](https://git-scm.com/download/mac) 或 `brew install git`

   验证安装：打开终端输入 `git --version`，显示版本号即成功。

2. 安装mdbook并配置环境变量：

   + 访问 [mdBook Releases 页面](https://github.com/rust-lang/mdBook/releases)，下载对应系统的压缩包（如 Windows 选 `mdbook-v0.4.52-x86_64-pc-windows-msvc.zip`）
   + 解压压缩包，将mdbook.exe（Windows）或mdbook（Mac/Linux）放到系统环境变量目录：
     - Windows：复制到 `C:\Windows\System32` 或自定义目录并添加到 PATH
     - Mac/Linux：复制到 `/usr/local/bin`（命令：`sudo mv mdbook /usr/local/bin/`）

   验证安装：终端输入 `mdbook --version`，显示 `mdbook v0.4.52` 即成功。

3. 注册一个[Github账号](https://github.com/)，并新建一个Repsitory。



### 项目

#### 创建项目

1、创建本地项目目录：打开终端，执行以下命令创建并进入项目文件夹

```bash
# 替换为你的项目名（如 my-tech-notes）
mkdir my-tech-notes && cd my-tech-notes
```

2、执行 `mdbook init` 命令，自动生成基础目录结构，如下：

```plaintext
my-tech-notes/
├── book/               # 构建后生成的静态网页（自动生成，无需手动改）
├── src/                # 笔记核心目录（所有 Markdown 笔记放这里）
│   ├── chapter_1.md    # 示例章节（可删除）
│   └── SUMMARY.md      # 笔记导航目录（关键！定义章节结构）
└── book.toml           # mdBook 配置文件（标题、主题、插件等）
```



#### 配置项目

1、修改book.toml：配置项参考 [官方文档](https://hellowac.github.io/mdbook-doc-zh/zh-cn/format/configuration/renderers.html)

```toml
[book]
title = "我的技术笔记"     # 笔记标题（将显示在网页顶部）
authors = ["Your Name"]  # 作者名
language = "zh-CN"       # 语言（中文）
src = "src"              # 笔记源文件目录（默认无需改）
description = "记录编程、算法、工具使用的学习笔记"  # 站点描述

[output.html]
search = true            # 启用网页搜索功能（支持关键词查找笔记）
favicon = "src/assets/favicon.ico"  # 网站图标（可选，需自行添加）
additional-css = ["src/assets/custom.css"]  # 自定义样式（可选）
theme = "ayu"            # 内置主题（可选：light/dark/ayu，也可自定义）

# （可选）启用数学公式支持（需后续安装插件）
[preprocessor.katex]
no-css = false
include-src = true
```



2、编写导航目录 src/SUMMARY.md：

> `SUMMARY.md` 是笔记的「目录索引」，决定网页左侧导航栏的结构。

```markdown
# 目录

## 基础工具
- [前言](intro.md)          # 笔记介绍页
- [Git 常用命令](tools/git.md)  # 工具类笔记
- [Markdown 语法](tools/markdown.md)

## 编程学习
- [Rust 入门](programming/rust/basics.md)
- [JavaScript 异步编程](programming/js/async.md)

## 数学知识
- [线性代数基础](math/linear-algebra.md)
- [概率论笔记](math/probability.md)

## 附录
- [常见问题](appendix/faq.md)
```

规则说明：

- 目录层级用 `##`/`###` 区分，对应导航栏的折叠层级
- 链接格式：`[章节名](文件路径)`，路径是 `src/` 下的相对路径
- 新增笔记后，必须在 `SUMMARY.md` 中添加条目，否则不会显示在导航中



3、编写与预览笔记：根据 `SUMMARY.md` 的目录结构，在 `src/` 下创建对应 Markdown 文件，如 `src/tools/git.md`

````
# Git 常用命令

## 基础操作
- 初始化仓库：`git init`
- 克隆远程仓库：`git clone https://github.com/your-username/your-repo.git`
- 查看状态：`git status`

## 提交代码
```bash
git add .  # 添加所有修改
git commit -m "新增 Git 常用命令笔记"  # 提交说明
git push origin main  # 推送到远程
```
````



4、在 `src/` 下创建 `assets/` 文件夹，用于存放图片、附件等：

> 引用图片时用 **相对路径**（如 `../assets/git-workflow.png`），避免依赖外部图床（防止失效）

```plaintext
src/
└── assets/
    ├── git-workflow.png  # 笔记中引用的图片
    └── custom.css        # 自定义样式文件
```



5、笔记预览：执行 `mdbook serve` 命令启动本地服务器，实时预览笔记效果，终端会输出访问地址（默认 [http://localhost:3000](http://localhost:3000)），打开浏览器即可查看

+ 左侧是 `SUMMARY.md` 定义的导航栏
+ 右侧是 Markdown 渲染后的内容
+ 修改笔记后，网页会自动刷新（无需重启命令）



#### 关联Github仓库

1、初始化本地Git仓库：在项目根目录执行

```bash
git init  # 初始化 Git 仓库
git add .  # 添加所有文件到暂存区
git commit -m "初始化 mdBook 笔记项目"  # 提交第一版
```

2、关联远程仓库：

```bash
# 替换为你的仓库地址
git remote add origin https://github.com/your-username/my-tech-notes.git
# 推送到 GitHub（首次推送需输入 GitHub 账号密码或 Token）
git push -u origin main
```

3、在项目根目录创建 .gitignore，避免提交无关文件：

```.gitignore
# 忽略 mdBook 构建产物
book/
# 忽略 IDE 配置文件
.idea/
.vscode/
# 忽略系统临时文件
.DS_Store
Thumbs.db
# 忽略缓存文件
.mdbook-cache/
```



#### Github自动部署

通过 **GitHub Actions** 实现「推送代码后自动构建并部署到 GitHub Pages」，无需手动操作。

1、创建 GitHub Actions 工作流文件：在项目根目录创建 `.github/workflows/deploy.yml` 文件，内容如下

```yaml
name: Deploy mdBook to GitHub Pages

# 触发条件：仅当 main 分支的 src/、book.toml、工作流文件变更时触发
on:
  push:
    branches: ["main"]
    paths:
      - "src/**"
      - "book.toml"
      - ".github/workflows/deploy.yml"
  # 允许手动触发（在 GitHub Actions 页面点击「Run workflow」）
  workflow_dispatch:

# 权限配置（确保能部署到 Pages）
permissions:
  contents: read
  pages: write
  id-token: write

# 并发控制：避免同时部署多个版本
concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  # 构建阶段：生成静态网页
  build:
    runs-on: ubuntu-latest
    env:
      MDBOOK_VERSION: 0.4.36  # 固定 mdBook 版本，避免兼容性问题
    steps:
      - name: 拉取 GitHub 代码
        uses: actions/checkout@v4

      - name: 安装 mdBook（预编译二进制，快速）
        run: |
          curl -L https://github.com/rust-lang/mdBook/releases/download/v${MDBOOK_VERSION}/mdbook-v${MDBOOK_VERSION}-x86_64-unknown-linux-gnu.tar.gz | tar xzf -
          sudo mv mdbook /usr/local/bin/

      - name: 安装数学公式插件（可选，若启用了 katex）
        run: cargo install mdbook-katex

      - name: 构建 mdBook 静态网页
        run: mdbook build  # 生成的文件在 book/ 目录

      - name: 上传构建产物（供部署使用）
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./book  # 上传 book/ 目录下的所有文件

  # 部署阶段：将构建产物推送到 GitHub Pages
  deploy:
    needs: build  # 依赖 build 阶段完成后才执行
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}  # 部署后显示访问地址
    steps:
      - name: 部署到 GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

2、推送工作流文件到 GitHub：

```
git add .github/workflows/deploy.yml
git commit -m "添加 GitHub Actions 自动部署配置"
git push
```

3、配置 GitHub Pages：

- 打开 GitHub 仓库 → 点击顶部「Settings」→ 左侧「Pages」
- 在「Source」中选择「Deploy from a branch」→ 分支选择 `gh-pages`（由 GitHub Actions 自动创建）
- 点击「Save」，等待 1-2 分钟，页面会显示访问地址（如 `https://your-username.github.io/my-tech-notes/`）


```mermaid
graph TD;
    A[开始] --> B{判断};
    B -->|是| C[执行操作];
    B -->|否| D[结束];
    C --> D;
```






#### 支持数学公式

mdbook 本身不支持数学公式渲染，需要通过插件扩展，如 `mdbook-katex`（基于 KaTeX 引擎，轻量快速）或 `mdbook-mathjax`（基于 MathJax 引擎，兼容性强）。

- Markdown 语法无数学公式标准，需通过 LaTeX 语法（如 `$E=mc^2$`）编写公式，再由引擎（KaTeX/MathJax）渲染为可视化效果。
- mdBook 不内置公式引擎，需通过 **预处理器插件（Preprocessor）** 在构建阶段（`mdbook build`）自动识别 LaTeX 公式语法，调用引擎渲染为 HTML 可识别的代码（如 SVG/HTML 元素）。
- `mdbook-katex` 是 mdBook 生态中最成熟的公式插件，支持行内公式（`$...$`）、块级公式（`$$...$$`）、公式编号、宏定义等核心功能，且渲染速度远快于 MathJax。



1、使用cargo安装mdbook-katex：

```shell
# 安装mdbook-katex
cargo install mdbook-katex

# 验证
mdbook-katex --version
```

2、基础配置：在 `book.toml` 中添加 `[preprocessor.katex]` 段落，启用插件并配置核心功能

```toml
# 启用 mdbook-katex 预处理器（核心）
[preprocessor.katex]
# 允许行内公式（$...$），默认开启
allow-inline = true
# 允许块级公式（$$...$$），默认开启
allow-block = true
# 自动为块级公式生成编号（如 (1.1)），按需开启
auto-number = true
# 公式编号格式（{chapter}.{section}.{equation}）
number-format = "{chapter}.{section}.{equation}"
# 加载 KaTeX 扩展（如支持化学公式、流程图，按需添加）
extensions = ["mhchem", "tikz"]  # mhchem 支持化学公式（如 \ce{H2O}），tikz 支持简单绘图
```

3、进行宏定义，如常用公式可在book.toml中添加，避免重复编写：

```toml
[preprocessor.katex.macros]
# 定义宏：\mat{a}{b}{c}{d} 生成 2x2 矩阵
"\\mat{#1}{#2}{#3}{#4}" = "\\begin{pmatrix} #1 & #2 \\\\ #3 & #4 \\end{pmatrix}"
# 定义宏：\intf 生成 ∫f(x)dx
"\\intf" = "\\int f(x) \\, dx"
```

4、自定义Katex样式：在  `src/css/custom.css` 中添加样式

```css
/* src/css/custom.css */
/* 行内公式样式：蓝色、稍大 */
.katex-inline {
  color: #2563eb;
  font-size: 1.05em;
}

/* 块级公式样式：居中、添加灰色背景 */
.katex-display {
  margin: 1em auto;
  padding: 0.5em;
  background-color: #f9fafb;
  border-radius: 4px;
}
```

5、验证公式效果：

5.1 行内公式：爱因斯坦质能方程：$E=mc^2$，其中 $m$ 为质量，$c$ 为光速（$c \approx 3 \times 10^8 \, \text{m/s}$）

5.2 块级公式（带编号）
欧拉公式（复数领域核心公式）：

$$
\begin{pmatrix}
   a & b \\
   c & d
\end{pmatrix}
$$

5.3 宏定义测试：使用自定义宏 $\mat{a}{b}{c}{d}$ 生成 2x2 矩阵，使用 \(\intf\) 生成积分公式

5.4 扩展功能测试（化学公式）：水的化学式：\(\ce{H2O}\)，盐酸与氢氧化钠反应：\(\ce{HCl + NaOH -> NaCl + H2O}\)

$$
\test
$$

\# 简化测试 

1. 宏定义简化测试：\(\mat{1}{0}{0}{1}\)（单位矩阵） 
1. 化学公式简化测试：\(\ce{CO2}\)（二氧化碳）
