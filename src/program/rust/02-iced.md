# Iced

github地址：[https://github.com/iced-rs/iced](https://github.com/iced-rs/iced)

#### 添加依赖

```
# 通过cargo命令
cargo add iced

# 手动在Cargo.toml中添加
[dependencies]
iced = "0.13.1"
```



#### 计数器示例

```rust
use iced::{
    Font, Result, application,
    widget::{Column, button, column, text},
};

fn main() -> Result {
    application("计数器", Counter::update, Counter::view)
        .default_font(Font::with_name("微软雅黑"))
        .run()
}

#[derive(Default)]
struct Counter {
    value: i64,
}

#[derive(Debug, Clone, Copy)]
pub enum Message {
    Increment,
    Decrement,
}

impl Counter {
    pub fn view(&self) -> Column<Message> {
        column!(
            button("加一").on_press(Message::Increment),
            text(self.value).size(50),
            button("减一").on_press(Message::Decrement),
        )
    }

    pub fn update(&mut self, message: Message) {
        match message {
            Message::Increment => self.value += 1,
            Message::Decrement => self.value -= 1,
        }
    }
}
```

#### 字体

iced默认不支持中文，如果需要使用中文，可以使用text组件的fallback系统字体：

```rust
use iced::widget::text;

text("中文").shaping(text::Shaping::Advanced)
```

或者使用windows默认的微软雅黑字体：

```rust
application("计数器", Counter::update, Counter::view)
    .default_font(Font::with_name("微软雅黑"))
    .run()
```

或者加载自定义的字体，如使用思源黑体 [Region Specific Subset OTFs Simplified Chinese (简体中文)](https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansCN.zip)，解压后选择Regular版本的字体（其他格式无法正常加载）：

```rust
use iced::{
    Font, Result, application,
    widget::{Column, button, column, text},
};

application("计数器", Counter::update, Counter::view)
    .font(include_bytes!("../res/SourceHanSansCN-Regular.otf"))
    .default_font(Font::with_name("思源黑体 CN"))
    .run()
```

#### 图标

图标主要包括窗口icon和程序icon：

+ 窗口icon：支持jpg、png等
+ 程序icon：必须使用icon格式

下载icon：[https://icon-icons.com/zh/](https://icon-icons.com/zh/)

iced默认不支持从文件载入icon，需要开启image feature：

```
# 使用cargo命令添加
cargo add iced -F image

# 直接修改Cargo.toml
[dependencies]
iced = { version = "0.13.1", features = ["image"] }
```

设置窗口Icon：

```rust
use iced::{
    application, widget::{button, column, text, Column}, 
    window::{icon, Icon, Settings}, Font, Result
};

application("计数器", Counter::update, Counter::view)
    .font(include_bytes!("../res/SourceHanSansCN-Regular.otf"))
    .default_font(Font::with_name("思源黑体 CN"))
    .window(Settings {
        // 设置窗口Icon
        icon: Some(Icon::from(icon::from_file_data(include_bytes!("../res/chatgpt.ico"), None).unwrap())),
        // 其余窗口设置保持默认
        ..Default::default()
    })
    .run()
```

程序icon设置：

1、增加winres包：

```
# 修改Cargo.toml文件
[package]
build = "build.rs"

# 增加模块
[build-dependencies]
winres = "0.1"
```

2、在项目根目录下创建build.rs：

```rust
extern crate winres;

fn main() {
    if cfg!(target_os = "windows") {
        let mut res = winres::WindowsResource::new();
        res.set_icon("res/chatgpt.ico");
        res.compile().unwrap();
    }
}
```

