# 扩展架构：五个执行上下文

* auto-gen TOC;
{:toc}

这一页讲的是本扩展（video-sniffer）的**内部架构**：它被拆成哪几个执行上下文、
这些上下文之间靠什么通信、各自的能力边界在哪，以及一次下载从点击按钮到文件落盘的
完整数据流。

如果你还不了解扩展的四个零件（manifest、内容脚本、Service Worker、popup），
先去 [扩展开发入门](01-extension-basics.md)；如果对「视频轨」「分片」「封装」这些词
还陌生，回头看 [音视频基础](02-media-fundamentals.md)。这一页讲的是**骨架**，
逐行逐函数的细节在 [代码导读](04-code-tour.md)，整章的索引和阅读路线在
[章节总览](00-summary.md)。

> 本页出现的 `` `src/common/dash.js:91` `` 这类写法，指的是 **video-sniffer 项目里的
> 文件与行号**，不是本章的页面位置。

---

## 扩展的零件构成

### 扩展能做什么

一个扩展就是一个装进浏览器的小程序，可以：

- 在每个网页上插自己的代码（内容脚本）
- 在浏览器背后跑一个常驻的调度中心（Service Worker）——它并不真的常驻，
  后面「Service Worker 随时会被杀」一节专门讲这件事
- 弹一个小窗口（popup）
- 调一些浏览器特权 API（下载、改请求头、读写存储）

### 文件布局

```
manifest.json          ← 扩展的「身份证 + 权限申请单」
src/background/…       ← 后台（Service Worker）
src/content/…          ← 注入页面的脚本
src/popup/ src/options/ ← 界面
```

### manifest.json 里最关键的三处

```jsonc
"background": {
  "service_worker": "src/background/service-worker.js",
  "type": "module"                    // ← 允许用 import/export
},
"content_scripts": [
  { "js": ["src/content/page-hook.js"], "world": "MAIN",      // ← 注入页面主世界
    "run_at": "document_start" },                             // ← 越早越好
  { "js": ["src/content/bridge.js"], "world": "ISOLATED" }   // ← 注入隔离世界
],
"content_security_policy": {
  "extension_pages": "script-src 'self' 'wasm-unsafe-eval'; object-src 'self';"
}
```

> **⚠️ CSP 那行是个雷**：`script-src` 里**不允许出现 `blob:` 或 `https:`**。
> 这意味着不能用 `importScripts()` 直接加载外部脚本。
> 后面讲 ffmpeg 时会看到扩展是怎么绕过去的，见 [代码导读](04-code-tour.md)。

注意 `content_scripts` 那两行：**同一个扩展往同一个页面里注入了两份脚本**，
一份在主世界、一份在隔离世界。这是整个架构的地基，原因见下一节。

---

## 五个「房间」，互相隔离

这是读这份代码**最重要**的一课。插件的代码跑在 5 个互不相通的环境里。

### 五个执行上下文

```
┌─────────────────────────────────────────────────────────┐
│ ① 页面主世界（MAIN world）                              │
│    跑在网页里，能碰到网页的一切（DOM、原型、变量）        │
│    ← page-hook.js 在这里                                │
├─────────────────────────────────────────────────────────┤
│ ② 隔离世界（ISOLATED world）                            │
│    跑在网页里，但有自己的「平行宇宙」                     │
│    能用 chrome.* API，不能碰网页的 JS 变量                 │
│    ← bridge.js 在这里                                   │
├─────────────────────────────────────────────────────────┤
│ ③ Service Worker                                        │
│    扩展的「大脑」，管资源表、派任务                       │
│    ← service-worker.js                                  │
├─────────────────────────────────────────────────────────┤
│ ④ offscreen 文档                                        │
│    一个看不见的后台页面，有 DOM / fetch / WebCrypto        │
│    真正下载和跑 ffmpeg 的地方                              │
│    ← offscreen/offscreen.js                              │
├─────────────────────────────────────────────────────────┤
│ ⑤ 扩展页面（popup / options）                           │
│    用户看到的界面                                        │
│    ← popup/popup.js、options/options.js                  │
└─────────────────────────────────────────────────────────┘
```

每个房间具体放哪个文件，图里已经标出来了：① `page-hook.js`，② `bridge.js`，
③ `service-worker.js`，④ `offscreen/offscreen.js`，⑤ `popup/popup.js`、
`options/options.js`。

### 数据在房间之间怎么流动

同一套房间，从「页面打开」到「文件落盘」，走的是下面这条链：

```
   ┌──────────────── 页面主世界 (MAIN world) ─────────────────┐
   │  page-hook.js        ← 唯一能"看到"页面内部的地方          │
   │  能用：页面原型、页面变量、window.postMessage              │
   │  不能用：chrome.* 全部 API                                │
   └───────────────────┬──────────────────────────────────────┘
                       │  window.postMessage（带 token 校验）
   ┌───────────────────▼──────────────────────────────────────┐
   │  bridge.js (隔离世界 ISOLATED)                            │
   │  能用：chrome.runtime、DOM                                │
   │  不能用：页面的原型（不共享！）                            │
   └───────────────────┬──────────────────────────────────────┘
                       │  chrome.runtime.sendMessage
   ┌───────────────────▼──────────────────────────────────────┐
   │  service-worker.js   ← 总调度                             │
   │  能用：webRequest、downloads、storage、DNR                  │
   │  不能用：DOM、window、长时间任务                            │
   └───────────────────┬──────────────────────────────────────┘
                       │  { target:'offscreen' }
   ┌───────────────────▼──────────────────────────────────────┐
   │  offscreen.html   ← 真正下载和转码的地方                    │
   │  能用：DOM、fetch、Worker、downloads                       │
   │  不能用：webRequest                                        │
   └───────────────────┬──────────────────────────────────────┘
                       │
   ┌───────────────────▼──────────────────────────────────────┐
   │  ffmpeg Worker     ← 真正干"把音视频拼起来"的活           │
   │  能用：Emscripten 文件系统、ffmpeg 命令行                    │
   │  不能用：DOM、网络                                          │
   └──────────────────────────────────────────────────────────┘
```

这张图比上面那张多画了一层 **ffmpeg Worker**，并且标出了每一层「能用什么、
不能用什么」——后面几个坑（跨世界通信、SW 被杀、403）全都长在这张图上。

图上的箭头就是跨房间的消息通道：主世界 → 隔离世界走 `window.postMessage`
（带 token 校验），隔离世界 → Service Worker 走 `chrome.runtime.sendMessage`，
Service Worker → offscreen 走 `{ target:'offscreen' }`。

注意 ⑤ 扩展页面（popup / options）没有出现在这张链路图里 —— 它是用户界面层，
和后台的消息往返见后面的「一次完整的下载，数据是怎么流的」。

---

## 主世界与隔离世界：为什么必须分开

### 两个世界的原型不共享

Chrome 给内容脚本（content script）一个**独立世界（isolated world）**。

关键事实：**两个世界各有各的 JavaScript 内置对象原型，彼此不共享。**

```js
// 在隔离世界里做这件事：
HTMLMediaElement.prototype.src = 'https://example.com/x.mp4';

// 页面里的 <video> 元素完全没有任何反应！
```

因为页面里的 `<video>` 用的是**主世界**那份 `HTMLMediaElement.prototype`，
你改的是**隔离世界**那份 —— 改的是另一个世界的同名零件，页面当然不认。

所以：**真正的钩子必须跑在主世界**。

### 要 hook 的东西在主世界，特权 API 在隔离世界

换个角度说同一件事：**要 hook 的东西在主世界，chrome API 在隔离世界。**

比如要拦截 `URL.createObjectURL`：

- 这个函数是**网页自己**在调，你必须**替换掉网页的那一份**才能拦到；
- 隔离世界替换的 `URL` 是**另一个对象**，网页完全不受影响 → 拦不到。

反过来，`chrome.runtime.sendMessage` 只有隔离世界能用，主世界调不了。

而主世界里又没有 `chrome.*` API（扩展的特权 API 只给扩展自己的页面），
所以要一个「信使」把消息从主世界搬到隔离世界 → 这就是 `bridge.js`。

### 两边靠 postMessage 通信

所以两边都要注入脚本，用 `window.postMessage` 通信：

```
页面主世界                      隔离世界                  后台
   │                              │                        │
   │  发现一个视频资源              │                        │
   │──── postMessage('found') ───▶│                        │
   │                              │─── chrome.runtime ────▶│
   │                              │      .sendMessage      │
   │◀───── postMessage('ack') ────│◀── 回执 ───────────────│
```

---

## 跨世界通信的一个坑：不能用 `event.source` 判断来源

### 直觉写法在跨世界时会失效

直觉写法：

```js
window.addEventListener('message', (e) => {
  if (e.source !== window) return;   // ❌ 在跨世界场景下失效
});
```

隔离世界和主世界**各有自己的 `window` 代理**，所以在同一个世界里这没问题，
但跨世界时，隔离世界看到的 `window` 和主世界发出的消息里的
`window` **不是同一个对象代理**，判断结果不符合预期。实际表现是
**永远为 true，每条消息都会被丢掉**。

### 改用随机 token 当凭证

插件的做法是**用一个随机 token**：页面主世界生成一个随机串，告诉隔离世界，
之后每条消息都带上它，收到时对不上就丢弃。

```javascript
// ❌ 错误：永远为 true，每条消息都会被丢掉
if (event.source !== window) return;

// ✅ 正确：用随机 token 当凭证
if (data.token !== token) return;
```

具体到实现：

- `page-hook.js:61` 生成 token（16 字节随机数转 hex），
- `bridge.js:175` 采纳**第一条到达的消息**里的 token（因为两个内容脚本是分别注入的，
  第一条 `hello` 可能收不到）；
- 之后每条消息都带上它，收到时对不上就丢弃。

### 握手为什么这么麻烦

> **握手为什么这么麻烦**：`hello` 可能被错过，所以 `page-hook.js:1656` 的
> `helloTimer` **每 500ms 重发一次、最多 20 次**；之后 `slowTimer` **每 2s 重发、最多 90 次**
> —— 合计覆盖约 **190 秒**。

完整的消息协议见 [代码导读](04-code-tour.md) 的消息协议全表。

---

## Service Worker 随时会被杀（v1.4.0 最大的坑）

### MV3 的 SW 没有任何保活保证

MV3 的 Service Worker 不是常驻的。**空闲 30 秒左右 Chrome 就会把它回收**；
更准确地说，它**没有任何保活保证**，浏览器会在你完全没察觉的时候把它回收掉。

回收意味着：**所有存在 JS 变量里的东西全部清零**（内存里的一切都没了）。

**症状**：「用一会儿插件就不灵了」「录着录着任务不见了」。

### 历史上踩过的坑：状态存在内存变量里

v1.4.0 之前，录制用的状态就存在内存变量里：

```js
const captureJobs = new Map();   // ← SW 一被回收，这里就没了
```

结果：录制播到一半，SW 被回收 → 分片全丢 → 录制中断。

### 本项目的三道防线

| 防线 | 在哪 | 干什么 |
|---|---|---|
| 资源表落盘 | `registry.js:393` 的 `flush()` | 存进 `chrome.storage.session` |
| 任务表落盘 | `registry.js:339` 的 `updateJob()` | 状态变了才写（不是每次进度都写） |
| 分片绕过 SW | `bridge.js:210` | 分片**直接**发给 offscreen，不经过 SW |

第 3 条最重要：媒体数据走「页面 → 隔离世界 → offscreen」直连，
SW 只在「开始 / 停止 / 完成」这几个节点参与。

### 为什么「分片不走 SW」是可行的

v1.4.0 的解法有两条：**分片不走 SW**，**任务表落盘**。

第一条之所以成立，是因为 **`chrome.runtime.sendMessage` 是广播给扩展内所有上下文的**：
SW 收到后 `return false` 不响应也不拦截，offscreen 照样收得到。

第二条则是把需要长期存活的状态写进 `chrome.storage.session`
（浏览器关闭前一直在的临时存储）。

---

## Referer：为什么下载会 403

### Referer 是 fetch 的禁止头

很多 CDN（尤其是 B 站）会检查请求头里的 `Referer`（「我是从哪个页面来的」），
没有就返回 403。

问题是：**`Referer` 是 fetch 的「禁止头」** —— 网页 JavaScript 不能设置它，
这是防跨站攻击的安全机制。扩展页面**也没法设置**它，扩展发起的请求也带不上有用的 Referer。

而且 `chrome.downloads.download()` 发出的请求也**不带 Referer**，
`declarativeNetRequest` 的规则同样覆盖不到下载请求（实测三种写法全部无效）。

结果：B 站 CDN 返回 403 + 一个几百字节的 HTML 错误页。
Chrome 还把它当「下载完成」存成了 `.mp4`。

### 解法：在网络层改写请求头

解法是 `declarativeNetRequest`（DNR）：一个**在网络层改写请求头**的规则引擎。

本项目的解法在 `src/background/referer.js`：用 DNR 在**网络层**改写请求头。
任务开始时装规则，结束时装掉。

```js
chrome.declarativeNetRequest.updateSessionRules({
  addRules: [{
    id, priority: 1,
    action: {
      type: 'modifyHeaders',                     // ← 必须是这个字符串
      requestHeaders: [{ header: 'Referer', operation: 'set', value: referer }],
    },
    condition: {
      urlFilter: `||${host}^`,                   // 只影响这一个域名
      resourceTypes: ['xmlhttprequest', 'media', 'other'],
    },
  }],
});
```

> 坑：`action.type` 必须写**字符串** `'modifyHeaders'`。
> 如果你图省事写了个带命名空间的常量，规则会**静默不生效**，不报错，就是不工作。

---

## 嗅探阶段：从页面打开到资源入库

以「在 B 站番剧页下载一集」为例，走一遍全流程。

### 挂钩：比页面自己的代码还早

第 1 步是挂钩。`page-hook.js` 在 `document_start` 时机运行 —— **比页面自己的代码还早**。
晚了就来不及拦截了。

它把几个关键函数「包一层」（保存原函数，包一层新的，调新的时先做记录再调原来的）：

```js
// src/content/page-hook.js
const nativeFetch = window.fetch;
window.fetch = function (input) {
  const p = nativeFetch.apply(this, arguments);   // 先正常发请求
  p.then((res) => {
    // 请求回来了，看看是不是我们关心的
    res.clone().text().then((text) => { /* 解析 JSON */ });
  });
  return p;                                        // 把原样的 Promise 还给页面
};
```

被包的函数有：

| 包了什么 | 用来干嘛 |
|---|---|
| `URL.createObjectURL` | 认出 Blob / MediaSource |
| `MediaSource.prototype.addSourceBuffer` | 知道「哪条流属于哪个 MediaSource」 |
| `SourceBuffer.prototype.appendBuffer` | **抓取视频分片的字节**（边播边录靠它） |
| `window.fetch` | 抓媒体响应 + JSON 播放地址 |
| `XMLHttpRequest.prototype.send` | 同上（B 站走的是 XHR） |

> `res.clone()` 这一步很关键：响应体一旦被读掉，页面自己就读不到了。
> `clone()` 相当于**复印一份**给插件看，原件还给页面。

### 发现：JSON 播放地址

第 2 步是发现。页面开始播放，B 站向 `api.bilibili.com/ogv/player/pre/check/drm` 发请求。

XHR 钩子在 `load` 事件里读响应：

```js
self.addEventListener('load', function () {
  const ct = self.getResponseHeader('content-type');   // 'application/json'
  if (ct.indexOf('json') !== -1) {
    const json = self.responseType === 'json' ? self.response : JSON.parse(self.responseText);
    reportJsonMedia(json, abs);      // ← 关键一步
  }
});
```

### 识别：在 JSON 树里找 DASH

第 3 步是识别。`reportJsonMedia` 负责从一大坨 JSON 里找出「这里头有视频地址」。

**v1.4.0 的写法（番剧页失效的根因）：**

```js
var data = (root.data && typeof root.data === 'object') ? root.data : root;

if (data.dash && Array.isArray(data.dash.video) && data.dash.video.length) {
  // ← 只会命中 data.dash
}
```

番剧页返回的是 `data.video_info.dash`，`data.dash` 是 `undefined` → **整个分支被跳过**。

**v1.4.1 的写法（不再猜路径）：**

```js
// src/common/dash.js
export function looksLikeDash(node) {
  if (!node || typeof node !== 'object' || Array.isArray(node)) return false;

  const tracks = node.video;                       // ① 要有 video 数组
  if (!Array.isArray(tracks) || tracks.length === 0) return false;

  const first = tracks[0];                        // ② 元素得是对象（不能是裸字符串）
  if (!first || typeof first !== 'object' || Array.isArray(first)) return false;
  if (!pickTrackUrl(first)) return false;          // ③ 轨道里必须真有地址

  // ④ 还要有 DASH 的标志字段
  return Array.isArray(node.audio)
    || typeof node.duration === 'number'
    || typeof node.min_buffer_time === 'number'
    || typeof node.minBufferTime === 'number';
}

export function findDash(root, maxDepth = 8) {
  if (looksLikeDash(root)) return root;            // 自己就是
  return findDashIn(root, 0, maxDepth);           // 在树里找
}

function findDashIn(node, depth, maxDepth) {
  if (!node || typeof node !== 'object' || depth > maxDepth) return null;

  if (Array.isArray(node)) { /* 数组里逐个找 */ }

  const values = Object.values(node);
  // 第一轮：直接的孩子里有没有 DASH
  for (const value of values) {
    if (value && typeof value === 'object' && looksLikeDash(value)) return value;
  }
  // 第二轮：再往下钻一层
  for (const value of values) {
    if (!value || typeof value !== 'object') continue;
    const hit = findDashIn(value, depth + 1, maxDepth);
    if (hit) return hit;
  }
  return null;
}
```

**用大白话讲这个算法**：

> 拿到一个 JSON 树，从最外层开始「扒开」每一层。
> 每到一层就问自己：**我手上这一堆对象里，有没有哪个长得像一份 DASH 清单？**
> 「像」的标准是：它有一组视频轨、每条轨有地址、而且还有音频轨或者时长这种 DASH 独有的标志。
> 找到就停。

于是三种结构都能命中：

| 页面 | 接口 | DASH 在哪一层 | 会被第几轮扒到 |
|---|---|---|---|
| 投稿页 | `x/player/playurl` | `data.dash` | 第 1 轮（扒开 `data`） |
| **番剧页** | `ogv/player/pre/check/drm` | `data.video_info.dash` | 第 2 轮（扒开 `data` → `video_info`） |
| PGC | `pgc/player/web/playurl` | `result.video.dash` | 第 3 轮 |

投稿页与番剧页的差异分别见 [06 B 站投稿视频下载](06-bilibili-ugc.md) 和
[05 B 站番剧 DASH 接口](05-bilibili-bangumi.md)。

### 上报与入库：资源登记表做了什么

第 4 步是上报与入库：

页面主世界 → `window.postMessage` → `bridge.js` → `chrome.runtime.sendMessage` →
`service-worker.js` → `registry.upsert()`。

`registry`（资源登记表）会做几件事：

- **按 URL 合并**：同一个地址只留一条，不会刷屏；
- **打标签**：网络层看到的那些 `.m4s` 单条轨道，会被关联到对应的 DASH 条目上，
  并打上「视频轨（1080p），没有声音」的提示 —— 免得用户下错；
- **持久化**：任务状态写进 `chrome.storage.session`，SW 被回收也不丢。

### popup 展示

第 5 步是 popup 展示。popup 打开时问后台：「这个标签页都发现了什么？」

后台返回条目列表，popup 渲染成卡片：

```
┌─────────────────────────────────────────┐
│ 凡人修仙传第178集              [完整视频] │   ← 顶部横幅：一键下载完整视频
├─────────────────────────────────────────┤
│ [DASH] DASH 视频+音频                    │
│        1920×1080 · 24分01秒 · 5档画质 · 3条音轨 │
│        [下载] [转 MP4] [复制链接]          │
├─────────────────────────────────────────┤
│ [直链] 40394753402-1-100026.m4s          │
│        [视频轨] DASH 的单条视频轨（1080p），没有声音 │
├─────────────────────────────────────────┤
│ [直链] 40394753402-1-100008.m4s          │
│        [音频轨] DASH 的单条音频轨，没有画面 │
└─────────────────────────────────────────┘
```

---

## 下载阶段：一次完整的下载，数据是怎么流的

以「点 DASH 条目的下载按钮」为例，走一遍全流程。

```
① popup 点「下载」
   │  chrome.runtime.sendMessage({type:'vs:download', tabId, id})
   ▼
② service-worker.js  handleMessage() 找到 MSG.DOWNLOAD 分支
   │  registry.get(tabId, id) 取出条目
   ▼
③ downloader.js  startDownload() → startJob()
   │  registry.createJob()  建任务，返回 jobId（**立刻返回，不等下载完**）
   │  downloader.installReferers()  装 Referer 规则
   ▼
④ downloader.js  downloadRunner()  决定走哪条路
   │
   ├─ 直链 → downloadDirect()      → chrome.downloads.download()
   ├─ HLS  → convertHls()          → 发给 offscreen
   ├─ DASH → convertDash()         → 发给 offscreen
   ├─ 分片 → convertSegments()      → 发给 offscreen
   └─ MSE  → convertCaptured()     → 发给 offscreen
   ▼
⑤ offscreen.js  runJob()  按 spec.mode 分派
   │  下载轨道（带 Referer/Origin/Cookie）
   │  选轨（画质 → 编码 → 码率）
   ▼
⑥ offscreen.js  runFfmpegDash()  合成
   │  ffmpeg -i video.m4s -i audio.m4s -c copy out.mp4
   ▼
⑦ saveBytes()  存文件
   │  new Blob → createObjectURL → chrome.downloads.download()
   ▼
⑧ 回推给 SW：MSG.OFFSCREEN_DONE
   │  registry.updateJob(status='done') + updateBadge + notifyPopup
   ▼
⑨ popup 收到 MSG.JOB_UPDATED → refresh() → 重新渲染列表
```

**几个值得注意的点**：

1. **第 ③ 步立刻返回 jobId**。
   为什么不等？因为一次下载可能几十分钟，一直挂着消息回调的话，
   弹窗一关消息就丢；而且 SW 随时被回收，回调没了就没人接，任务状态反而丢失。

2. **第 ⑥ 步的四级降级**：见 [音视频基础](02-media-fundamentals.md)。

3. **第 ⑧ 步才是「完成」的真正来源**，不是第 ③ 步返回的时候。

4. **直链走的是 Chrome 原生下载器**（第 ④ 步第一条分支），
   其它都走 offscreen 自己的 fetch 引擎 —— 因为只有后者能带 Referer。

### 下载与合成：downloader → offscreen → ffmpeg

对应上面流程的第 6 步，展开说是这么几步：

点「下载」→ 后台 `downloader.convertDash()` →

1. 按设置挑画质（默认「原画」= 最高）；
2. 给目标 CDN 装 Referer 规则；
3. 把任务交给 offscreen 文档；
4. offscreen 下载视频轨 + 音频轨；
5. 交给 ffmpeg.wasm 封装成 MP4；
6. `chrome.downloads.download()` 保存。

### 完整性校验：防止「下到一半」

封装完不直接交差，先用 ffmpeg 反查产物时长：

```js
const duration = await engineInstance.probeDuration(spec.outputName);
const warning = durationWarning(duration, spec.expectedDuration);
```

如果成品只有 55 秒、预期 1167 秒，任务状态里会明确写：

```
成品时长只有 55.0s（预期 1167.0s，缺 95%），文件不完整
```

这一步很重要 —— 它能把「悄悄下了个残次品」变成「明确告诉你出问题了」。

---

## 下一步

架构讲完了，接下来往哪儿走：

- 想看每个文件的职责、消息协议全表 → [代码导读](04-code-tour.md)
- 想知道 DASH 的合并为什么要「四级降级」 → [音视频基础](02-media-fundamentals.md)
- 实际下载时体积不对、满屏条码、403 → [DASH 下载异常排查](09-troubleshooting.md)
- 准备动手改代码 → [开发与调试指南](10-dev-guide.md)
