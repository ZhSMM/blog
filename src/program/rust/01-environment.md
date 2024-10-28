# 环境搭建

#### Windows环境搭建

环境搭建：

1、配置rustup和cargo目录：

```
RUSTUP_HOME D:\rust\rustup_home
CARGO_HOME D:\rust\cargo_home
```

2、配置加速安装地址：

```
# 使用清华大学镜像源
RUSTUP_DIST_SERVER https://mirrors.tuna.tsinghua.edu.cn/rustup
RUSTUP_UPDATE_ROOT https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup

# 或者指定其他的镜像源
# 字节跳动
RUSTUP_DIST_SERVER=https://rsproxy.cn
RUSTUP_UPDATE_ROOT=https://rsproxy.cn/rustup

# 中国科学技术大学
RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static
RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup

# 上海交通大学
RUSTUP_DIST_SERVER=https://mirrors.sjtug.sjtu.edu.cn/rust-static/
```

或者cmd设置临时环境变量：

```
SET RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static
```

3、配置cargo库镜像：在`%homepath%\.cargo\`或`%CARGO_HOME%`下创建config文件

```
[source.crates-io]
registry = “https://github.com/rust-lang/crates.io-index”
# 指定镜像
replace-with = ‘tuna’

# 中国科技大学
[source.ustc]
registry = "git://mirrors.ustc.edu.cn/crates.io-index"

# 清华大学
[source.tuna]
registry = "https://mirrors.tuna.tsinghua.edu.cn/git/crates.io-index.git"

# 上海交通大学
[source.sjtu]
registry = "https://mirrors.sjtug.sjtu.edu.cn/git/crates.io-index"

# rustcc社区
[source.rustcc]
registry = "https://code.aliyun.com/rustcc/crates.io-index.git"
```

4、下载安装程序后安装即可，支持两种工具链，选择msvc即可：[https://www.rust-lang.org/zh-CN/](https://www.rust-lang.org/zh-CN/)

5、安装后检查：

```
rustc --version
cargo --version
```

6、打开本地文档服务：

```
rustup doc
```

7、Vscode安装rust开发插件：

+ Rust原因插件：rust-analyzer
+ TOML文件：Even Better TOML
+ 错误展示：Error Lens
+ Debugger程序：CodeLLDB

8、卸载环境：

```
rustup self uninstall
```

#### 项目创建

1、使用cargo创建项目：

```
cargo new hello
cd hello
code .
```

2、项目运行：

```
# 编译生成lib或可执行文件，支持release和debug模式
cargo build [--release|--debug]

# 检测代码是否能通过编译
cargo check

# 运行，等效于crago build && ./xx.exe
cargo run [--release|--debug]
```
