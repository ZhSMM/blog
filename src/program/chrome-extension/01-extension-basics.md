# Chrome 扩展开发入门

* auto-gen TOC;
{:toc}

浏览器扩展听着像个「黑科技」，其实本质就是**几个普通文件打包在一起**，再写一份 `manifest.json` 告诉浏览器「我是谁、我能做什么」。这一页带你从零做出一个能点的空壳扩展，再一步步把 Popup、Content Script、Service Worker 三个零件串起来，把权限、存储、通信、调试这些以后天天要用的东西一次讲透。

本页是整章的**第 01 页**，是唯一的零基础起点：没写过扩展的人从这儿入门，然后按 [章节总览](00-summary.md) 给的阅读路线继续走。想先弄清「视频文件到底是个什么东西」再动手，去看 [音视频基础](02-media-fundamentals.md)；想知道这几个零件在真实项目里怎么分层、Service Worker 生命周期到底有多反直觉，去看 [扩展架构](03-architecture.md)；等本页的最小认知够了，再进 [代码导读](04-code-tour.md) 读 video-sniffer 的实际实现。

---

## 四个主要零件

### 核心概念地图

浏览器插件本质上是**几个普通文件打包在一起**，通过一个叫 `manifest.json` 的配置文件告诉浏览器「我是谁、我能做什么」。

插件有四个主要「零件」，各司其职：

| 零件               | 通俗叫法           | 能干什么                       | 不能干什么               |
| ------------------ | ------------------ | ------------------------------ | ------------------------ |
| **Popup**          | 点图标弹出的小窗口 | 画按钮、输入框，响应用户点击   | 关掉就销毁，不能一直跑   |
| **Content Script** | 潜入网页的脚本     | 读写当前网页（改文字、加按钮） | 不能直接用全部浏览器 API |
| **Service Worker** | 后台调度员         | 监听事件、存数据、收消息       | 不能操作网页 DOM，会睡着 |
| **manifest.json**  | 插件身份证         | 声明权限、注册上面三个零件     | 本身不写逻辑             |

> 💡 一句话总结：Popup 管界面，Content Script 管网页，Service Worker 管后台，manifest 把它们串起来。

---

## 做出一个「能点的空壳」扩展

### 第一步：新建文件夹

在桌面创建一个文件夹，比如 `my-first-extension`，然后在里面创建三个文件。

### 文件 1：`manifest.json`（必须，相当于户口本）

```json
{
  "manifest_version": 3,
  "name": "我的第一个插件",
  "version": "1.0",
  "description": "用来学习的第一个插件",
  "action": {
    "default_popup": "popup.html"
  }
}
```

- `manifest_version: 3`：目前必须用 V3（V2 已淘汰）
- `name` / `version` / `description`：在插件管理页显示的信息
- `action.default_popup`：点工具栏图标时弹出的页面

### 文件 2：`popup.html`（弹窗长什么样）

```html
<!DOCTYPE html>
<html>
  <body>
    <h1>你好呀 👋</h1>
    <p>这是我的第一个插件</p>
    <button id="btn">点我</button>
    <script src="popup.js"></script>
  </body>
</html>
```

### 文件 3：`popup.js`（点击后的反应）

```javascript
document.getElementById('btn').addEventListener('click', () => {
  alert('插件跑起来了！');
});
```

> ⚠️ **MV3 铁律**：不能写 `<script>alert()</script>` 这种内联代码，必须拆成单独的 `.js` 文件。

### 第三步：把插件装进浏览器

1. 浏览器地址栏输入 `chrome://extensions`（Edge 同理）
2. 右上角打开 **「开发者模式」** 开关
3. 点 **「加载已解压的扩展程序」**
4. 选中刚才创建的文件夹
5. 工具栏点拼图图标，把插件「固定」到工具栏

现在点图标→看到弹窗→点按钮→弹出 alert 🎉

**你已经完成了 80% 的入门。**

---

## 改完代码怎么看效果

| 你改了什么                     | 要不要重新加载           |
| ------------------------------ | ------------------------ |
| `manifest.json`                | ✅ 必须点刷新             |
| `popup.html` / `popup.js`      | ❌ 不用，关掉弹窗重开即可 |
| `content.js` / `background.js` | ✅ 刷新插件 + 刷新网页    |

刷新方法：回到 `chrome://extensions` 页面，点你插件卡片上的 🔄 圆形箭头。

---

## 让插件「真正有用」：读取当前网页

做一个字数统计工具。

### 升级 manifest，加两个权限

```json
{
  "manifest_version": 3,
  "name": "字数统计器",
  "version": "1.0",
  "description": "统计当前网页字数",
  "permissions": ["activeTab", "scripting"],
  "action": {
    "default_popup": "popup.html"
  }
}
```

- `activeTab`：允许插件临时访问你正在看的那个标签页
- `scripting`：允许插件往网页里注入代码来读取内容

> 📌 权限原则：能少要就少要，要得越多用户越害怕，上架审核越严。

### 修改 popup.html

```html
<!DOCTYPE html>
<html>
  <body>
    <p>当前网页字数：</p>
    <h1 id="result">—</h1>
    <button id="count">开始统计</button>
    <script src="popup.js"></script>
  </body>
</html>
```

### 修改 popup.js

```javascript
document.getElementById('count').addEventListener('click', async () => {
  // 1. 找到用户正在看的那一个标签页
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  // 2. 往那个网页里塞一段函数，让它数字数
  const [result] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      // 这段代码运行在网页里，能碰到网页的文字
      const text = document.body.innerText;
      const words = text.trim().split(/\s+/);
      return words.length;
    }
  });

  // 3. 把结果显示出来
  document.getElementById('result').textContent = result.result + ' 个字';
});
```

### 🔧 核心 API：`chrome.tabs` —— 「标签页管理员」

```javascript
// 查当前标签页
const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

// 开新标签页
chrome.tabs.create({ url: 'https://example.com' });

// 关掉某个标签
chrome.tabs.remove(tab.id);
```

### 🔧 核心 API：`chrome.scripting` —— 「往网页里派卧底」

```javascript
chrome.scripting.executeScript({
  target: { tabId: tab.id },
  func: () => {
    // 这里的代码运行在网页内部，能读 DOM
  }
});
```

---

## 让插件「记住事情」：存储 API

Popup 关掉就没了，Service Worker 会睡着，数据放哪里？答案是 `chrome.storage`。

### 升级 manifest，加 storage 权限

```json
"permissions": ["activeTab", "scripting", "storage"]
```

### 用法示例

```javascript
// 存
await chrome.storage.local.set({ nickname: '小明' });

// 取
const data = await chrome.storage.local.get('nickname');
console.log(data.nickname); // "小明"

// 删
await chrome.storage.local.remove('nickname');
```

### 三种存储的区别

| 类型      | 存在哪         | 适合放什么               |
| --------- | -------------- | ------------------------ |
| `local`   | 本机           | 缓存、大一点的数据       |
| `sync`    | 跟着账号走     | 设置、偏好（换电脑也在） |
| `session` | 内存，重启清空 | 临时状态                 |

> ⚠️ **别用 `localStorage`**！它是网页用的，插件各个零件之间不互通，Service Worker 里根本用不了。

---

## 三个零件一起用：完整通信模型

场景：Content Script 改网页，Service Worker 管数据。

### `manifest.json`：加入 content_scripts 和 background

```json
{
  "manifest_version": 3,
  "name": "综合示例",
  "version": "1.0",
  "permissions": ["storage"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://*.example.com/*"],
      "js": ["content.js"]
    }
  ],
  "action": {
    "default_popup": "popup.html"
  }
}
```

- `background.service_worker`：指定后台文件
- `content_scripts.matches`：在哪些网站注入脚本（`<all_urls>` 表示全部，但别乱用）

### `content.js`：潜入网页

```javascript
// 网页加载后，往页面顶部插一条横幅
const banner = document.createElement('div');
banner.textContent = '插件已生效 🎉';
banner.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#4285f4;color:white;padding:8px;text-align:center;z-index:99999';
document.body.prepend(banner);

// 发消息给后台
chrome.runtime.sendMessage({ type: 'PAGE_LOADED', url: location.href });
```

### `background.js`：后台调度员

```javascript
// 安装时触发一次
chrome.runtime.onInstalled.addListener(() => {
  console.log('插件装好啦');
});

// 收消息
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'PAGE_LOADED') {
    console.log('网页打开了：', msg.url);
    // 存起来
    chrome.storage.local.set({ lastUrl: msg.url });
  }
});
```

### `popup.js`：弹窗里读数据

```javascript
document.addEventListener('DOMContentLoaded', async () => {
  const data = await chrome.storage.local.get('lastUrl');
  document.body.innerHTML = `上次打开：${data.lastUrl || '暂无'}`;
});
```

### 🔧 `chrome.runtime` —— 「内部对讲机」

```javascript
// 发消息
chrome.runtime.sendMessage({ type: 'XXX' });

// 收消息（任意一方都能写）
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 如果是异步返回，必须 return true
});
```

> ⚠️ **异步坑**：如果你的处理里有 `await` 或 `fetch`，监听器里要 `return true`，否则回复发不出去。

### 🔧 反过来：Popup 发消息给网页里的 Content Script

```javascript
const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
chrome.tabs.sendMessage(tab.id, { type: 'CHANGE_COLOR', color: 'red' });
```

---

## Service Worker 的「睡眠怪癖」

Service Worker 不是一直醒着的：

- 空闲约 30 秒 → 浏览器把它关了
- 有事件来了 → 自动唤醒

所以：

❌ **不要**在全局变量里存重要状态：

```javascript
let count = 0; // 下次醒来，count 又变 0 了
```

✅ **要存就放 `chrome.storage`**：

```javascript
await chrome.storage.local.set({ count: 1 });
```

✅ 事件监听器要写在最外层，别塞进函数里：

```javascript
// ✅ 正确
chrome.runtime.onMessage.addListener(...);

// ❌ 错误：worker 醒来时这段根本没执行
function init() {
  chrome.runtime.onMessage.addListener(...);
}
```

这一条在真实项目里还要再展开一层：video-sniffer 为什么要另开 offscreen 文档来干重活、消息怎么在隔离世界和主世界之间来回传，见 [扩展架构](03-architecture.md) 的执行上下文与生命周期部分。

---

## 调试方法（不用瞎猜）

| 想看哪里的日志   | 怎么做                                                       |
| ---------------- | ------------------------------------------------------------ |
| Popup 的 console | 右键点弹窗 → 「检查」                                        |
| Content Script   | 打开那个网页 → F12 普通开发者工具                            |
| Service Worker   | `chrome://extensions` → 点你插件下的 **「Service Worker」** 蓝色链接 |

报错先在扩展管理页看有没有红色感叹号，点进去能看到具体错误。

要按症状系统地定位问题，配合 [开发与调试指南](10-dev-guide.md) 一起看。

---

## 推荐的项目结构（以后照着建）

```
my-extension/
├── manifest.json        # 必须，身份证
├── popup.html           # 弹窗界面
├── popup.js             # 弹窗逻辑
├── popup.css            # 弹窗样式
├── content.js           # 注入网页的脚本
├── background.js        # 后台服务
├── icons/
│   ├── icon16.png       # 工具栏小图标
│   ├── icon48.png       # 管理页
│   └── icon128.png      # 商店展示
└── options.html         # 设置页（可选）
```

图标不是必须，但上架一定要有，可以用在线工具生成 16/48/128 三张。

---

## 从「能跑」到「能上架」的下一步

1. **别放秘密**：API Key 别写进插件，谁装了都能反编译看到，要走你自己的后端
2. **权限最小化**：能用 `activeTab` 就别用 `<all_urls>`
3. **打包**：把文件夹压缩成 zip（manifest.json 要在根目录）
4. **上架**：去 Chrome Web Store 开发者后台，交一次性注册费，传 zip + 截图 + 说明，等审核

Edge、Brave、360 极速版基本都兼容这套 Manifest V3 写法，加载方式类似。

---

## 可以立刻动手做的小练习

选一个做，做完你就出师了：

1. **划词翻译按钮**：选中文字，旁边浮出「翻译」按钮
2. **网页置顶横幅**：给正在看的网页加一句提醒文字
3. **一键复制当前页标题+链接**：点弹窗按钮，自动复制到剪贴板
4. **暗黑模式开关**：给当前网页强行加 `filter: invert(1)` 反色

---

## 一张速查表（贴墙上）

```javascript
// 查当前标签
await chrome.tabs.query({ active: true, currentWindow: true })

// 注入脚本
chrome.scripting.executeScript({ target: { tabId }, func: () => {} })

// 存/取数据
chrome.storage.local.set({ key: val })
chrome.storage.local.get('key')

// 发/收消息
chrome.runtime.sendMessage({ type: 'X' })
chrome.runtime.onMessage.addListener((req, sender, res) => {})

// 给某网页的 content script 发消息
chrome.tabs.sendMessage(tabId, { type: 'X' })
```

---

**恭喜！你已经掌握了浏览器插件开发的核心知识。接下来就是多写多练，遇到问题查官方文档：https://developer.chrome.com/docs/extensions/**

想把这套能力用到一个真实站点上，去看 [新站点适配手册](08-new-site-playbook.md)；想动手改 video-sniffer 的代码，从 [代码导读](04-code-tour.md) 开始。
