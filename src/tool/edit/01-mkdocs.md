# MkDocs快速入门

MkDocs官方文档：[https://www.mkdocs.org/user-guide/](https://www.mkdocs.org/user-guide/)

#### 安装MkDocs

MkDocs需要Python和Python package manager pip，可以使用pip进行安装：

```
# 安装mkdocs
pip install mkdocs

# 检查安装
mkdocs -V

# 显示帮助
mkdocs -h
```



#### 创建项目

切换到指定目录，执行如下命令创建项目：

```shell
mkdocs new blog
```

执行成功后，会在对应目录生成blog文件夹，文件夹下有如下内容：

+ mkdocs.yml：配置文件，文档结构与主题设置
+ docs：撰写的Markdown文档
+ index.md：默认首页

MkDocs包含了一个内建的服务器，可以在本地预览当前文档。在项目文件夹下打开命令提示符，执行如下命令启动服务：

```shell
mkdocs serve
```

执行成功后，在浏览器打开 [http://127.0.0.1:8000/](http://127.0.0.1:8000/) 进行访问。



#### 配置

MkDocs官方配置文档： [https://www.mkdocs.org/user-guide/configuration/](https://www.mkdocs.org/user-guide/configuration/)

站点配置：

```
# 站点名称
site_name: "My Notes"
# 站点URL
site_url: "http://<domain>:<port>/<project>"
# 站点作者
site_author: ""
# 站点描述
site_description: ""
# 版权信息
copyright: ""
# 站点仓库URL
repo_url: ""
```

配置文档结构：

```yaml
# 默认基于docs目录，只需要填写相对路径
# 如果不想使用默认目录，可以使用docs_dir来指定对应的文件夹名称
nav:
  - "index.md"
  - Python:
    - 环境搭建: "python/install.md"
    - 镜像配置: "python/pip.md"
  - "about.md"
  - "license.md"
```

主题配置：第三方主题 [https://github.com/mkdocs/mkdocs/wiki/MkDocs-Themes](https://github.com/mkdocs/mkdocs/wiki/MkDocs-Themes)

```
# MkDocs内置主题：mkdocs、readthedocs
theme: readthedocs

# 使用第三方主题
# 1. 下载主题
pip install mkdocs-rtd-dropdown
# 2. 在mkdocs.yml中配置
theme: rtd-dropdown
```



#### 扩展

MkDocs 使用 [Python-Markdown](https://github.com/Python-Markdown/markdown) 库（Markdown 规范的 Python 实现）来渲染 Markdown 内容，因此 MkDocs 中对于 Markdown 内容渲染的扩展也是来自于此。我们可以在 Python-Markdown 的 [官方文档](https://python-markdown.github.io/extensions/) 中浏览到目前所支持的 Markdown 扩展有哪些。

如使用下面配置开启对于 Markdown 内容标题的固定标识符、脚注以及表格：

```yaml
markdown_extensions:
  - toc:
      permalink: True
  - footnotes
  - tables
```



#### 站点发布

使用Github Pages发布站点：

1、在Github新建仓库

2、在本地MkDocs项目中初始化：

```shell
# 初始化
git init

# 将项目文件添加到暂存区
git add .

# 提交
git commit -m "first commit"

# 创建分支
git branch -M main

# 添加远端仓库
git remote add origin git@github.com:ZhSMM/note.git

# 推送
git push -u origin main
```

3、部署，在项目根路径执行如下命令：

```
mkdocs gh-deploy
```