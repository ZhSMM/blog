

#### 安装wsl

官方文档：[https://learn.microsoft.com/zh-cn/windows/wsl/install](https://learn.microsoft.com/zh-cn/windows/wsl/install)

```
# 安装发行版
wsl --install <Distribution Name>

# 列出可用的发行版
wsl --list --online

# 列出已安装的发行版
# --all：所有分发版
# --running：运行中的
# --quiet：仅显示发行版名称
wsl --list --verbose

# 设置默认的发行版
wsl --set-default <Distribution Name>

# 运行特定的发行版
wsl --distribution <Distribution Name> --user <User Name>

# 更新wsl
wsl --update
```

#### wsl2子系统重置密码

```
# Win + R 打开运行，输入cmd回车进入控制台
# 如果为默认分发版，使用如下分支进入根目录
wsl --user root

# 非默认分发版
wsl --list
wsl -d Debian -u root

# 修改root密码
passwd root

# 修改用户密码
passwd username
```

