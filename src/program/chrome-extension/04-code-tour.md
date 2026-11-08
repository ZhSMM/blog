# 代码导读与项目结构

video-sniffer 的代码摊开来看不小：一份 MV3 清单、两个内容脚本、后台 Service Worker、offscreen 文档、ffmpeg 封装层，再加一整层能在 Node 里裸跑的纯逻辑模块。这一页按「目录 → 文件 → 函数」的顺序把整棵代码树铺开：先给完整目录结构和每个文件的职责，再逐层说清每个文件在干什么、关键数据结构长什么样，最后附上消息协议全表和资源登记表的数据模型。

这一页是 [扩展架构](03-architecture.md) 的下半场。[扩展架构](03-architecture.md) 回答的是「五个执行上下文怎么协作、一条数据怎么流过整条链路」，本页回答的是「这个仓库里有哪些文件、每个文件负责什么、关键函数在第几行」。要动手改代码，先读本页；想知道为什么这么设计，回头看 [扩展架构](03-architecture.md)；想知道怎么跑测试、怎么调、怎么改完验证，去 [开发与调试指南](10-dev-guide.md)。

本页出现的 `src/common/dash.js:91`、`src/content/page-hook.js:1656` 这类写法，**指的是 video-sniffer 项目里的文件与行号**，不是本章的页面。整章的阅读路线见 [章节总览](00-summary.md)。

* auto-gen TOC;
{:toc}

---

## 项目目录结构

```
video-sniffer/
├── manifest.json                 MV3 清单：权限、双内容脚本、CSP
├── icons/                        16/32/48/128 PNG（tools/make_icons.py 生成）
├── src/
│   ├── common/                   ← 纯逻辑，无 DOM / 无 chrome API，可单测
│   │   ├── constants.js          MSG 协议表、KIND 分类、默认设置
│   │   ├── mime.js               URL/MIME 分类、格式化工具
│   │   ├── filename.js           文件名生成（标题清洗 + 画质后缀）
│   │   ├── hls.js                m3u8 解析（主/子列表、AES-128、EXT-X-MAP）
│   │   ├── playlist.js           播放清单/分片清单识别（v1.4.0）
│   │   ├── dash.js               DASH 清单的通用定位与解析（v1.4.1）
│   │   ├── download-check.js     下载结果校验（错误页 / 非媒体 / 被截断）（v1.4.2）
│   │   └── ffmpeg-args.js        ffmpeg 命令行构造
│   ├── content/                  ← 页面侧
│   │   ├── page-hook.js          MAIN world：挂钩 + JSON 解析 + 分片捕获
│   │   └── bridge.js             ISOLATED world：消息中继 + DOM 兜底扫描 + 代取接口
│   ├── background/               ← 后台
│   │   ├── service-worker.js     总路由、设置、角标、任务状态机
│   │   ├── registry.js           资源登记表（内存 + storage.session 镜像）
│   │   ├── net.js                webRequest.onHeadersReceived 网络嗅探
│   │   ├── referer.js            DNR 注入 Referer
│   │   ├── downloader.js         下载/转码编排（direct/hls/dash/segments/mse 五条路）
│   │   ├── bilibili-alt.js       番剧「备用播放地址」（v1.4.3）
│   │   └── offscreen.js          offscreen 文档生命周期
│   ├── offscreen/                ← 真正干活的地方（扩展页，有 DOM 和 fetch）
│   │   ├── offscreen.html
│   │   ├── offscreen.js          HLS/DASH 管线、ffmpeg 引擎、保存产物
│   │   └── ffmpeg-protocol.js    worker 协议层（被拼进 ffmpeg 核心源码）
│   ├── popup/                    ← 工具栏弹窗
│   └── options/                  ← 设置页
├── test/                         单元测试 + 素材 + ffmpeg 核心启动助手
├── tools/                        CDP 客户端、端到端脚本、打包、图标生成、诊断工具
│   ├── cdp.mjs                   零依赖 CDP 客户端 + Chrome 启动 + 扩展安装
│   ├── smoke-test.mjs            无头 Chrome 端到端
│   ├── bilibili-test.mjs         真实 B 站端到端（投稿页 / 番剧页都能测）
│   ├── dash-diagnose.mjs         浏览器之外复现 DASH 管线（npm run test:dash）
│   ├── diagnose-bangumi.mjs      抓番剧页的 JSON 响应，打印结构与 DASH 位置
│   ├── dump-playurl.mjs          打印 playurl 响应的完整细节（画质/轨道/DRM）
│   ├── diagnose-dash-tracks.mjs  DASH 轨道取证：编码 / 真实体积 / bpp（v1.4.3）
│   ├── diagnose-dash-frames.mjs  DASH 抽帧取证：把画面拍成 PNG（v1.4.3）
│   ├── diagnose-dash-mux.mjs     复现封装的四种 ffmpeg 参数（v1.4.3）
│   ├── dump-boxes.mjs            打印 MP4 盒子结构（pssh/senc/encv）（v1.4.3）
│   ├── scan-drm.mjs              批量检查几集番剧的加密/占位情况（v1.4.3）
│   ├── compare-track-files.mjs   对比两个接口给的是不是同一批文件（v1.4.3）
│   ├── probe-alt-api.mjs         验证普通播放接口能不能拿到未加密的流（v1.4.3）
│   ├── probe-ext-fetch.mjs       在扩展环境里调 B 站接口（v1.4.3）
│   ├── probe-risk-control.mjs    对比不同上下文的接口风控命中率（v1.4.3）
│   ├── probe-isolated-origin.mjs 测隔离世界/主世界的 origin 差异（v1.4.3）
│   ├── capture-request.mjs       抓接口请求的完整形态（方法/请求体/请求头）（v1.4.3）
│   ├── list-page-apis.mjs        列出页面所有含媒体地址的接口（v1.4.3）
│   ├── probe-fetch-json.mjs      测「内容脚本代发接口」这条通道（v1.4.3）
│   ├── probe-track-urls.mjs      对比嗅探到的轨道和接口清单的地址（v1.4.3）
│   ├── probe-quality.mjs         逐档画质实际下载一次
│   ├── probe-title.mjs           列出页面上所有可能的标题来源
│   ├── probe-direct-items.mjs    对比「扩展记录的体积」和「真实体积」
│   ├── probe-referer.mjs         同一个 URL 带/不带 Referer 各请求一次
│   ├── probe-dnr-download.mjs    测 DNR 规则对 chrome.downloads 是否生效
│   ├── repro-track-download.mjs  复现「点直链下载」的完整过程
│   ├── download-ugc.mjs           不装扩展直接下载投稿视频的完整文件（v1.4.4）
│   ├── probe-ugc-playurl.mjs      投稿视频接口诊断：三种 fnval / 每条轨道 / qn 上限（v1.4.4）
│   ├── probe-ugc-durl.mjs         投稿视频 durl 取证（v1.4.4）
│   ├── probe-durl-boxes.mjs       durl 的盒子结构：独立 MP4 还是 fMP4 碎片（v1.4.4）
│   ├── probe-output.mjs           探测下载产物的时长/编码/分辨率（v1.4.4）
│   ├── scan-merged-lines.mjs      扫「两行被粘成一行」的隐患（v1.4.3）
│   ├── strip-bom.mjs              去 UTF-8 BOM（v1.4.3）
│   ├── probe-files.mjs           探测本地媒体文件（npm run probe）
│   ├── package.mjs               零依赖 zip 打包器（npm run package）
│   ├── syntax-check.mjs          ES 模块语法检查（npm run lint）
│   ├── check-doc-refs.mjs        文档代码引用校对（npm run docs:check，v1.4.4）
│   └── make_icons.py / make-fixtures.mjs / test-server.mjs
└── docs/
    ├── DEVELOPMENT.md             本文档
    ├── 新手教程.md                 零基础入门（v1.4.0）
    ├── 从零上手完全指南.md          安装→概念→逐函数导读→动手改→排障（v1.4.4）
    ├── 新站点视频调试手册.md        新站点抓视频的完整调试流程（v1.4.4）
    ├── 番剧DASH接口手册.md          B 站番剧播放地址接口详解（v1.4.3）
    ├── DASH下载异常排查.md          「体积偏小 + 满屏条码」排查记录（v1.4.3）
    └── 普通投稿视频下载分析.md        投稿视频（BV）下载分析 + 三条路线（v1.4.4）
```

**一条判断规则**：`src/common/` 里的文件必须能在 Node 里裸跑（不 import 任何 chrome API）。所有跨层可复用的判断都往这里放，测试也只测这一层 —— 这样绝大多数逻辑不需要开浏览器就能验证。

树里每一行后面的注解是**一句话摘要**，只够让你知道「这个文件大概管什么」。接下来的小节才是逐文件的展开：按 `manifest.json → content/ → background/ → offscreen/ → popup/ → common/` 的顺序走一遍，每个文件给出职责、关键数据结构、关键函数。

其中 `docs/` 目录是项目自己的原始技术文档，本章内容即改写自其中的开发文档与逐函数导读部分；`test/` 和 `tools/` 不在代码运行路径上，属于工程配套，怎么跑它们见 [开发与调试指南](10-dev-guide.md)。

---

## 清单与权限：manifest.json

改 `manifest.json` 之前，先理解三个决策点。

```json
"content_scripts": [
  { "js": ["src/content/page-hook.js"], "world": "MAIN",    "run_at": "document_start" },
  { "js": ["src/content/bridge.js"],  "world": "ISOLATED", "run_at": "document_start" }
]
```

- **`world: "MAIN"`**：Chrome 给内容脚本默认的 isolated world 有**独立的原型链**。在隔离世界里改 `HTMLMediaElement.prototype.src`，页面完全不受影响。所以真正的挂钩必须在主世界。
- **两个脚本分开声明**：不同 world 的内容脚本不能共享变量，主世界那份也不能用 `chrome.runtime`。
- **`run_at: "document_start"`**：必须在播放器创建 `MediaSource` 之前挂钩，否则会漏掉 init segment。

```json
"content_security_policy": {
  "extension_pages": "script-src 'self' 'wasm-unsafe-eval'; object-src 'self';"
}
```

- **没有 `blob:`**：一旦 `script-src` 里出现 `blob:` 或 `https:`，**整个 manifest 校验失败**，扩展直接加载不了。这直接决定了 ffmpeg 的启动方式（见 [开发与调试指南](10-dev-guide.md) 里的 ffmpeg 启动那一节）。
- **`'wasm-unsafe-eval'`**：允许 WebAssembly 编译。少了它 ffmpeg.wasm 起不来。
- **`worker-src` 也不要写**：实测 Chrome 会拒绝 `worker-src 'self' blob:` 这类组合。

---

## 页面侧脚本：src/content/

### `page-hook.js`：主世界的五个挂钩点（MAIN world，约 48 KB）

五个挂钩点，每个都是一个「原函数包一层」：

| 位置 | 钩子 | 拿到什么 |
|---|---|---|
| §1 | `URL.createObjectURL` | 区分 `MediaSource` 和 `Blob`（**Blob 还可能是包装过的播放清单**） |
| §2 | `MediaSource.prototype.addSourceBuffer` | SourceBuffer ↔ MediaSource ↔ 流 URL 的对应关系（**顺便判断这是不是「换源后的新流」**） |
| §3 | `SourceBuffer.prototype.appendBuffer` | 编码后的分片字节 |
| §4 | `HTMLMediaElement.src` / DOM 扫描 | 元素级信息（宽高、时长） |
| §5 | `fetch` / `XMLHttpRequest.send` | 媒体响应头 + **JSON 播放地址** + **播放清单** |

**关键数据结构**（都是 `WeakMap`/`Map`，不影响页面）：

```js
var msInfo        = new WeakMap();  // MediaSource -> { url, type }
var sbInfo        = new WeakMap();  // SourceBuffer -> { ms, mime, streamKey }
var blobUrls      = new Map();      // blob url -> mime
var captures      = new Map();      // streamKey -> Uint8Array[]
var capturedBytes = new Map();      // streamKey -> number（预算控制）
var streams       = new Map();      // streamKey -> { url, mime, isAudio, duration }

// v1.4.0 新增：录制会话（锚定在媒体元素上，而不是 blob URL 上）
var recordSessions = new Map();     // recordToken -> { el, url, streamKeys:Set, hasInit, jobId }
var streamSession  = new Map();     // streamKey -> recordToken
var chunkSeq       = new Map();     // recordToken -> 已发送分片数
var outbox         = new Map();     // recordToken -> 未确认的分片（可靠投递）
var playlistCache  = new Map();     // 播放清单文本 -> 原始 URL
```

**`streamKey` 是分轨的钥匙**：`info.url + '::' + type`。DASH 播放器会把视频和音频塞进同一个 MediaSource 的两个 SourceBuffer，如果只用 blob URL 做键，两者会被合并成一个文件 —— 结果就是「有画面没声音」或反之。

**`recordSessions` 是 v1.4.0 的核心**（机制细节见 [开发与调试指南](10-dev-guide.md)）：一次录制 = 一个媒体元素，播放器重建 MediaSource 时新流会被并进同一个会话，录制因此不会断。

**JSON 解析的预筛**：

```js
var MEDIA_HINT_RE = /(\.m4s|\.mp4|\.webm|\.m3u8|\.mpd|baseUrl|base_url|"dash"|"durl"|"playurl")/i;
function maybeJsonMedia(text) {
  if (!text || text.length > 4 * 1024 * 1024) return false;
  return MEDIA_HINT_RE.test(text);
}
```

页面上每个 JSON 响应都会经过这里。先用正则粗筛（比 `JSON.parse` 便宜几个数量级），命中才真的解析。**加新的站点适配时，第一步就是往这个正则里加关键词**（完整适配流程见 [新站点适配手册](08-new-site-playbook.md)）。

**标题采集**（与文件名强相关）：

- 主世界能读到 `window.__INITIAL_STATE__.videoData.title`（B 站），isolated world 读不到 —— 这是必须放在主世界的原因之一。
- `document.title` 在 `document_start` 时是空的，所以 `report()` 每次都重新读一次。
- `reportJsonMedia` 还会顺手看接口里有没有 `data.title`。

**调试出口**：`window.__vsDebug`（会话 / 已武装的流 / 媒体元素状态 / 未确认分片），用法见 [开发与调试指南](10-dev-guide.md) 的调试章节。

### `bridge.js`：隔离世界的中继站（ISOLATED world，约 14 KB）

四件事：**中继消息、兜底扫 DOM、给条目补齐页面级元数据、把分片直发 offscreen**。

> v1.4.0：分片不再经 Service Worker 中转，而是
> `chrome.runtime.sendMessage({ target: 'offscreen', ... })` 直接投给 offscreen 文档。
> SW 的监听器遇到 `target === 'offscreen'` 会立刻 `return false`（不响应也不拦截），
> 消息照样送达 —— 这是「分片绕过 SW」能成立的关键（机制细节见 [开发与调试指南](10-dev-guide.md)）。

**跨 world 通信的 token 机制**：

```js
// page-hook.js 侧：随机 16 字节
var token = Array.prototype.map.call(buf, function (b) {
  return ('0' + b.toString(16)).slice(-2);
}).join('');

// bridge.js 侧：第一次收到的 token 就是"合法密钥"
if (!token && data.token) token = data.token;
if (!token || data.token !== token) return;
```

> ⚠️ **不要写 `if (event.source !== window) return;`**。隔离世界的 `window` 和主世界的 `window` 是两个不同的代理对象，这个判断会把所有合法消息全部丢掉。这是本项目最容易踩的坑之一。

**去重与合并**：同一个 URL 可能被多个来源报告（DOM 扫描说它是 blob，页面钩子说它是 mse）。桥接层按 kind 排名保留更具体的那种：

```js
var KIND_RANK = { mse: 5, blob: 4, hls: 3, dash: 3, direct: 2, segment: 1 };
```

同 kind 时，只有「带来了新信息」（mime / duration）才转发 —— 播放器元数据是异步的，时长要能后补。

---

## 后台：src/background/

### `service-worker.js`：只做路由和状态

MV3 的 SW 随时可能被回收，所以它**不做重活**，只做路由和状态：

- `handleMessage(msg, sender)` 是一个大 `switch`，覆盖所有 `MSG.*`。
- `registry.restore()` 在启动时把 `chrome.storage.session` 里的资源表读回来。
- `updateBadge()` 用角标显示当前标签页的资源数量。
- `notifyPopup()` 用回调形式发消息，避免「没有接收端」时抛未捕获的 Promise 拒绝。

**任务状态机**：`queued → running → done / error / cancelled`，全部存在 `registry` 的 `jobs` Map 里，popup 靠它画进度条。

> v1.4.0：`onMessage` 里会先 `await ensureBoot()` 再处理消息。
> SW 刚被回收醒来时内存是空的，不等 `registry.restore()` 完成就处理消息，
> 会把「恢复资源表」之前到达的请求全部丢掉（症状：过一会儿插件就不灵了）。

### `registry.js`：资源登记表

内存是权威，`storage.session` 只是镜像（SW 被回收后能恢复）。

- `itemKey(item)`：普通资源用 URL，MSE 用 `streamKey`。
- `mergeItem(prev, next)`：空值不覆盖旧值（`if (v === null || v === undefined || v === '') continue;`）。
- `linkDashTracks(map)`：**把单条轨道和 DASH 完整条目关联起来**。DASH 的视频轨/音频轨在网络层看起来就是两个普通媒体文件，用户很容易点错，关联之后 popup 才能提示「这条没有声音」。
- `upsert` 的双入口：带 `url` 是「发现新资源」，只带 `id` 是「更新状态」（下载完成后回写 `status: 'done'`）。
- **v1.4.0**：任务表（`jobs`）也落盘到 `vs:jobs` 键，SW 重启后能找回「正在进行的录制」。
  录制任务还带 `recordToken`（录制会话号），后台靠它把页面传来的消息对上号 ——
  不再依赖内存里的 URL → jobId 映射。

### `net.js`：网络层嗅探

`chrome.webRequest.onHeadersReceived` + `['responseHeaders']` 权限，拿到响应头后按 MIME/扩展名分类。

```js
export function classify({ mime = '', url = '', contentLength = null } = {}) { ... }
```

分类结果 → `kind` 映射：`playlist → hls/dash`、`segment → segment`、`video/audio → direct`。

同时会跳过扩展自己发起的请求（`initiator.startsWith('chrome-extension://')`），否则扩展的下载会被自己嗅探到。

### `referer.js`：用 DNR 注入 Referer

**`Referer` 是 fetch 的禁止头**，扩展页面设不了；扩展发起的请求默认也不带可用的 Referer。B 站 CDN 没有 Referer 直接 403。

解决办法是 DNR 会话规则：

```js
await chrome.declarativeNetRequest.updateSessionRules({
  addRules: [{
    id, priority: 1,
    action: {
      type: 'modifyHeaders',                                  // ← 必须是字符串
      requestHeaders: [{ header: 'Referer', operation: 'set', value: referer }],
    },
    condition: { urlFilter: `||${host}^`, resourceTypes: ['xmlhttprequest', 'media', 'other'] },
  }],
});
```

> ⚠️ `action.type` 必须是字符串 `'modifyHeaders'`。写成 `chrome.declarativeNetRequest.RuleActionType.MODIFY_HEADERS`（带命名空间的常量）在某些版本里会校验失败。

规则按 host 去重，任务结束由 `releaseReferers` 卸载。

### `downloader.js`：下载与转码的编排

四条下载路径的统一编排：

| kind | 路径 | 做什么 |
|---|---|---|
| `direct` | `downloadDirect` | 先用 `chrome.downloads` 直下；403/中断则回退到带 Referer 的 fetch |
| `hls` | `convertHls` | 下播放列表 → 下分片 → AES-128 解密 → 合并 → ffmpeg |
| `dash` | `convertDash` | 下视频轨 + 音频轨 → ffmpeg 封装成单个 MP4 |
| `segments` | `convertSegments` | **v1.4.0**：下整组分片（并发 6 路）→ 按序拼接 → ffmpeg |
| `mse` / `blob` | `convertCaptured` | 从页面把已缓冲的分片拉出来 → ffmpeg 封装 |

**v1.4.0：任务立刻返回 jobId，实际工作放到后台跑。**

```js
const runner = downloadRunner(item, settings, job, type === 'convert');
runner().then(ok, err);   // 后台跑，消息不等它
return { ok: true, jobId: job.id };
```

原因：一次下载可能几分钟到几十分钟，让一条消息挂这么久，弹窗会被卡住、用户一关弹窗消息就丢了；MV3 的 SW 回收后，长时间挂着的消息回调也没人接，任务状态反而丢失。

**命名**（v1.2.0 起）：文件名不再是 CDN 的随机串。

```js
function buildFilename(item, settings, extension, suffix = '') {
  return buildDownloadFilename({
    title: item.mediaTitle || item.title || '',   // 视频原名
    pageTitle: item.pageTitle || '',              // 页面标题
    url: item.url, mime: item.mime || '',
    extension, suffix, dir: settings.downloadDir || '',
  });
}
```

后缀规则：DASH → `_480p`（按实际选中的轨道）；单条轨道 → `_视频轨_480p` / `_音频轨`；MSE 录制 → `_录制片段`。

### 另外两个后台文件

- `bilibili-alt.js`：番剧「备用播放地址」（v1.4.3）。
- `offscreen.js`：offscreen 文档的生命周期管理。

---

## 真正干活的地方：src/offscreen/

### `offscreen.js`：三条管线 + 一个引擎（约 25 KB）

**HLS 管线**：`collectHls` 解析主列表（选清晰度）→ 下媒体列表 → 并发下分片（`mapLimit(segments, 6, …)`）→ AES-128 解密 → 按播放清单顺序拼接（`EXT-X-MAP` 的 init segment 放最前）。

**DASH 管线**：`fetchTrack` 下载轨道（**带截断检测**：实收字节 ≠ `Content-Length` 就判定失败，换备用地址重试）→ `runFfmpegDash` 封装。

四级回退（每一级失败就试下一级）：

```js
attempts.push(['-c', 'copy', …]);                      // 1. 直接封装
attempts.push(['-c:v', 'copy', '-c:a', 'aac', …]);      // 2. 视频 copy + 音频重编码
attempts.push(['-i', 'video.m4s', '-c', 'copy', …]);    // 3. 只要视频
attempts.push(buildTranscodeArgs(…));                  // 4. 全部重编码
```

**时长校验**（v1.2.0 新增）：封装完不删文件，先反查一次时长：

```js
async probeDuration(path) {
  // ffmpeg -i <file> 会把 "Duration: 00:03:32.31" 打到 stderr，
  // 因为没给输出文件所以退出码非 0 —— 这是预期行为。
}
```

拿到实际时长后和 `spec.expectedDuration` 比对，短了就生成警告文案，随 `OFFSCREEN_DONE` 一起回传。

配套的 `offscreen.html` 是这个扩展页的入口 —— 它是扩展页面（有 DOM 和 `fetch`），和后台 Service Worker 是两个不同的运行环境。

### `ffmpeg-protocol.js`：被拼进 ffmpeg 核心的协议层

一段**不会被当普通脚本加载**的代码。它的源码被 offscreen 文档 fetch 出来，拼在 ffmpeg 核心源码后面，整体做成 Blob 再用 `new Worker(blobURL)` 启动。

协议就五个动作：`LOAD` / `EXEC` / `WRITE_FILE` / `READ_FILE` / `DELETE_FILE`，外加 `LOG` 和 `PROGRESS` 两个上行通道。

---

## 界面层：src/popup/ 与 src/options/

### `popup.js`：弹窗怎么渲染

- `renderMediaTitle()`：顶部显示识别到的**视频原名**。
- `renderCard()`：badge（类型）+ 标题 + 元信息 + URL + 操作按钮 + 警告行。
- 轨道条目额外挂一个 `.tag-video` / `.tag-audio` 标签，并显示 `item.note`（如「DASH 的单条视频轨（480p），没有声音」）。
- `renderJobStatus()`：进度条 + 状态文案；任务带 `warning` 时文案转黄。

`src/options/` 是设置页，对应 `constants.js` 里的 `DEFAULTS` 与 `getSettings()` 的合并结果。

---

## 纯逻辑层：src/common/

这一层最重要，也最好读：不碰 DOM、不碰 `chrome.*` API，全是纯函数。所以在 Node 里可以直接跑单元测试，不用开浏览器。

> **一条铁律**：`src/common/` 里的文件必须能在 Node 里裸跑。
> 所有跨层可复用的判断都往这里放。

下面按文件列出每个模块的导出、关键函数和行号。约定：`文件名:行号` 都能直接跳到源码对应位置；`export` 表示可以从别的文件 import。

### `constants.js`（110 行）

整个扩展的「词汇表」。

| 导出 | 内容 |
|---|---|
| `MSG` | 所有消息类型的常量表。`MSG.FOUND = 'vs:found'` 这样 |
| `TARGET` | `TARGET.OFFSCREEN = 'offscreen'`、`TARGET.SW = 'sw'`。消息靠它区分发给谁 |
| `KIND` | 媒体种类：`DIRECT` / `HLS` / `DASH` / `MSE` / `BLOB` / `SEGMENT` / `SEGMENTS` |
| `ORIGIN` | 发现来源：`NETWORK` / `DOM` / `MSE` / `BLOB` |
| `JOB_STATUS` | 任务状态：`IDLE` / `QUEUED` / `RUNNING` / `DONE` / `ERROR` / `CANCELLED` |
| `DEFAULTS` | 所有设置的默认值。`getSettings()` 会把它和用户设置合并 |

**为什么用常量不用字符串字面量**：拼错了编译器不会报错，但运行时消息就路由不到。

这个文件也是后面「消息协议全表」里所有常量的定义处。

### `mime.js`（215 行）

**「这个资源是什么类型」的判断中心。**

| 函数 | 作用 |
|---|---|
| `extFromUrl(url)` `:89` | 取 URL 路径的后缀（去掉 `?query` 和 `#hash`）。`blob:`/`data:` 开头的返回空串 |
| `mimeFromUrl(url)` `:103` | 从后缀推 MIME 类型（用 `EXT_TO_MIME` 表） |
| `extFromMime(mime)` `:205` | 从 MIME 推后缀（用 `MIME_TO_EXT` 表）。`video/*` 拿不到具体类型时默认 `mp4` |
| `classify({mime,url})` `:124` | **核心**：返回 `'video'\|'audio'\|'playlist'\|'segment'\|''` |
| `isMediaLike({mime,url})` `:150` | 是不是我们关心的媒体（video/audio/playlist/segment） |
| `humanSize(bytes)` `:156` | `1536` → `'1.5 KB'` |
| `humanDuration(seconds)` `:172` | `417` → `'6:57'`；超过一小时 → `'1:06:57'` |
| `qualityLabel(w,h)` `:183` | `1080` → `'1080p'`；`2160` → `'4K'` |
| `guessFilename(url,mime,fallback)` `:195` | 没标题时，从 URL 里猜文件名 |
| `durationWarning(actual,expected)` `:223` | **比成品时长和页面声明的时长**，返回警告文案或 null |

**`classify()` 的判断顺序**（重要）：

```
1. MIME 是播放列表类型？      → 'playlist'
2. MIME 是 MPEG-TS？          → 'segment'
3. MIME 是 video/*？          → 'video'
4. MIME 是 audio/*？          → 'audio'
5. 后缀是 m3u8/m3u/mpd？      → 'playlist'
6. 后缀是 ts/m2ts/mts/m4s？   → 'segment'
7. 后缀在 VIDEO_EXT 里？       → 'video' 或 'audio'
8. 都不是                      → ''（不是媒体，忽略）
```

**`durationWarning()` 的三档**：

| 比例 | 返回 |
|---|---|
| ≥ 98% | `null`（没问题） |
| ≥ 90% | `成品时长 400.0s / 预期 417.0s，可能有 4% 未下载完整` |
| < 90% | `成品时长只有 100.0s（预期 417.0s，缺 76%），文件不完整` |

> **为什么必须有这个**：以前「下到一半」是**静默失败**的 ——
> 文件存下来了，用户以为成功了，播放才发现只有开头。
> 加了这个判断，任务里会直接写明缺了多少。

### `filename.js`（168 行）

**「文件该叫什么名」的全部逻辑。**

| 函数 | 作用 |
|---|---|
| `cleanMediaTitle(raw)` `:49` | 去掉站点后缀。`"没有肉车，只有怂人！_哔哩哔哩_bilibili"` → `"没有肉车，只有怂人！"`。循环剥离，因为它可能叠了好几层 |
| `sanitizeFileStem(raw,maxLength=80)` `:80` | 变成合法文件名主名：`/\:*?"<>|` 全换成 `_`，去掉首尾的点和空格，长度截断 |
| `qualitySuffix(height)` `:96` | `1080` → `'1080p'` |
| `sanitizeDownloadDir(dir)` `:108` | `D:\Videos` → `Videos`（**相对路径**） |
| `buildDownloadFilename({...})` `:136` | **最终组装** |

**`buildDownloadFilename()` 的标题优先级**：

```
item.mediaTitle（视频原名，最可信）
  → item.title
  → item.pageTitle（页面标题）
  → URL 里的 CDN 文件名
  → 'video'（兜底）
```

**为什么要 `sanitizeDownloadDir()`**：
`chrome.downloads` **只接受相对于下载目录的路径**，
传绝对路径（`D:\Videos`）会直接抛错。

### `playlist.js`（232 行）

**「播放清单 / 分片清单」的识别与解析**（v1.4.0 新增；v1.4.1 收紧了 `collectSegmentArray` 的判定：必须有强信号，且跳过整个 DASH 子树）。

| 函数 | 作用 |
|---|---|
| `playlistKind({mime,url})` `:28` | 返回 `'hls'\|'dash'\|''` |
| `looksLikePlaylist(text)` `:45` | 看文本内容判断：`#EXTM3U` → HLS；`<MPD` → DASH；`<SmoothStreamingMedia` → MSS |
| `collectSegmentArray(root)` `:79` | **在 JSON 树里找「整集分片数组」** |
| `segmentsFromPlaylistText(text,baseUrl)` `:188` | 把播放列表文本解析成分片地址 + init 段 |

**`collectSegmentArray()` 的四条硬性要求**（缺一不可）：

```
1. 数组至少 3 个元素
2. 每个元素都能取到一个 URL 字符串
3. 所有 URL 同源
4. 必须有一个「强信号」：
   ① 数组名像分片数组（urlList / segList / segments / chunkList …）
   ② 或者半数以上的 URL 带媒体后缀（.ts / .m4s / .mp4 / .webm …）
```

**另外还会跳过整棵 DASH 子树** —— DASH 的 `video[]`/`audio[]` 是
「不同画质的完整轨道」，不是「同一条视频的先后分片」，拼起来只会得到乱码。

> **这个保守是有血的教训的**：v1.4.0 只要求「≥3 个同源 URL」，
> 结果 B 站番剧页的「相关推荐」列表（20 个剧集链接）被当成了整集分片，
> popup 里冒出一条假的「分片清单（20 片）」——
> 用户点「下载整集」拿回来的是 20 个网页。
>
> **宁可漏判也不能误判**：漏判只是少一个入口，误判会让用户下载一堆垃圾。

**`segmentsFromPlaylistText()` 处理的行**：

| 行 | 处理 |
|---|---|
| `#EXT-X-MAP:URI="..."` | 记为 init 段（fMP4 的初始化数据） |
| `#EXTINF:9.9,` | 记住这一段的时长 |
| `#EXT-X-KEY:...` | 加密信息（这里只记录，不解密） |
| `#` 开头 | 其它注释，忽略 |
| 其它非空行 | **这就是一个分片地址** |

### `dash.js`（560 行）

DASH 的识别、解析、选轨、体检。是本项目技术含量最高的公共模块（v1.4.1 起改为在 JSON 树里通用定位 DASH）。

**识别部分**

| 函数 | 作用 |
|---|---|
| `pickTrackUrl(track)` `:55` | 从轨道对象取地址。认 `baseUrl`/`base_url`/`url`/`src`/`main_url`/`mainUrl`（驼峰、下划线两种拼写都认） |
| `pickTrackBackups(track)` `:74` | 取备用镜像地址列表 |
| `looksLikeDash(node)` `:91` | **判断这个对象是不是 DASH 清单** |
| `findDash(root,maxDepth=8)` `:123` | 在 JSON 树里通用定位 DASH 清单 |
| `findDashContext(root)` `:292` | 找 DASH 清单，**并且把它的父对象也带出来** |
| `findNumberField(root,key)` `:164` | 在 JSON 树里找某个数字字段 |
| `findArrayField(root,key)` `:194` | 在 JSON 树里找某个数组字段（比如 `durl`） |

**`looksLikeDash()` 的三个条件**（全部满足才算）：

```
1. 自己带一个 video 数组
2. 数组里第一个元素是**对象**（不是裸字符串），而且能取到地址
3. 还带 DASH 的标志字段：audio 数组 / duration / min_buffer_time
```

> **为什么不能写死路径？**
> 同一个站点不同页面的结构完全不一样：
>
> ```
> 投稿页   data.dash
> 番剧页   data.video_info.dash
> PGC      result.video.dash
> ```
>
> v1.4.0 只认 `data.dash`，于是在番剧页上**一条 DASH 都识别不出来** ——
> 页面能正常播放，但插件只看到零散的 `.m4s` 单轨（没有声音）。

**`findDashContext()` 为什么还要「父对象」**：
`quality`（当前授权画质）、`drm_type` 不是写在 `dash` 里面，
而是和 `dash` **平级**的：

```
data: {
  quality: 32,          ← 在这
  dash: { ... }         ← 在这
}
```

**解析部分**

`extractDash(root)` `:226` 返回：

```javascript
{
  videos: [{ url, backups, width, height, bandwidth, codecs, id, encrypted }],
  audios: [{ url, backups, bandwidth, codecs, id, encrypted }],
  duration: 417,        // 秒
  quality: 32,          // 站点当前给这个访客播放的画质
  drmType: '',          // DRM 类型
}
```

**`isEncryptedTrack(track)`** `:334`：
B 站在每条轨道上带一个 `widevine_pssh` 字段。
有值 = 这条流是 Widevine 加密的（文件里会有 `pssh`/`senc` 盒子，画面数据是密文）。

**选轨部分**

| 函数 | 作用 |
|---|---|
| `codecRank(codecs)` `:355` | 编码兼容度排名：`avc1`=0（最好）、`hvc1`=1、`av01`=2、`vp9`=3、其它=4 |
| `bitsPerPixel(track,fps=25)` `:374` | **bpp** = 每像素每帧多少比特 |
| `isPlaceholderTrack(track)` `:396` | bpp < `PLACEHOLDER_BPP`（0.01）就是占位流 |
| `isPlaceholderByBytes(bytes,duration,height)` `:413` | 用**实际下载到的字节数**再判一次 |
| `pickVideoTracks(videos,opts)` `:438` | **选轨策略** |
| `classifyTracks(videos)` `:476` | 这批轨道是不是全都不正常 |

**bpp 的实际数值**（判断占位流的关键）：

| 类型 | 码率 | bpp |
|---|---|---|
| 正常 1080P | 2~6 Mbps | 0.04 ~ 0.10 |
| 正常 360P | 0.3~0.8 Mbps | 0.05 ~ 0.12 |
| **占位流** | ~100 kbps | **~0.002**（差两个数量级） |

**`pickVideoTracks()` 的五步顺序**：

```
1. 先剔掉「占位流」和「DRM 加密流」
   —— 这两种下载下来都是废的
   —— 全被剔光了就退回全部轨道（宁可给个坏文件并警告，也别一声不吭）
2. 应用高度上限（用户在设置里选了「最高 720p」之类）
3. 画质高的优先
4. 同画质时：站点正在播的那一档优先（那是访客真正有权看的那一档）
5. 同画质同授权时：H.264 优先（兼容性最好）→ 码率高的优先
```

> **为什么不能「码率最高的优先」**：
> B 站恰恰把没权限的那一档标成了「码率最高」。
> 所以必须先剔掉占位流。

**体检部分**

`inspectTrackBytes(bytes, entry, durationSeconds)` `:507`：

```javascript
{
  encrypted: false,    // 文件头里有 pssh/encv/enca/senc 盒子
  placeholder: false,  // 实际字节数算出来的 bpp 太低
  kbps: 878,           // 实际码率
  bpp: 0.045,
}
```

> **为什么要看文件而不只看清单**：
> B 站的**音轨**没有 `widevine_pssh` 字段，可文件里照样有 `enca`/`senc`。
> 只看清单会漏判。

**改动注意**：page-hook.js 里有一份 `dash.js` 的内联镜像，`test/dash.test.mjs` 会比对两边防止漂移 —— 改了这个文件，镜像和测试要一起改。

### `hls.js`（208 行）

m3u8 解析（主列表 / 媒体列表、AES-128、EXT-X-MAP）。

| 函数 | 作用 |
|---|---|
| `parseMasterPlaylist(text,baseUrl)` `:30` | 解析**主播放列表**（列了几档清晰度） |
| `parseMediaPlaylist(text,baseUrl)` `:83` | 解析**媒体播放列表**（真正的分片列表） |
| `parseIv(ivString,sequence)` `:170` | 解析 AES-128 的 IV（初始向量） |
| `pickVariant(variants,{maxHeight})` `:191` | 从主列表里挑一档（按 `码率 + 高度×1000` 打分） |
| `isMasterPlaylist(text)` `:206` | 有 `#EXT-X-STREAM-INF:` 就是主列表 |

**`parseMediaPlaylist()` 认识的标签**：

| 标签 | 处理 |
|---|---|
| `#EXT-X-TARGETDURATION:` | 记下来（不参与播放） |
| `#EXT-X-MEDIA-SEQUENCE:` | 第一个分片的序号 |
| `#EXTINF:9.9,` | 这一段的时长 |
| `#EXT-X-BYTERANGE:` | 这一段是文件的一部分 |
| `#EXT-X-KEY:` | 加密方式 + 密钥地址 + IV |
| `#EXT-X-MAP:` | init 段（fMP4 用） |
| `#EXT-X-ENDLIST` | 播放列表结束 |
| 其它非 `#` 行 | 一个分片地址 |

**`parseIv()` 的两个分支**：

- 给了 IV 字符串 → 解析成 16 字节数组；
- 没给 → **用分片序号当 IV**（`BigInt` 位运算，注意字节序是倒着填的）。

### `download-check.js`（102 行）

下载结果校验（错误页 / 非媒体 / 被截断）。

| 函数 | 作用 |
|---|---|
| `describeBadDownload({mime,size,expectedSize})` `:38` | 判断这次下载是不是「拿到了错误页」 |
| `looksLikeStandaloneMp4(bytes)` `:79` | 判断这些分片是「独立完整 MP4」还是「fMP4 碎片」 |

**`describeBadDownload()` 的三种判坏**：

```
1. MIME 是 text/html          → 「服务器返回的是网页，多半是 403/404 错误页」
2. 体积 < 4096 字节           → 「只拿到 N 字节，不是有效的媒体文件」
3. 实际 < 预期的一半           → 「只拿到 N 字节，预期 M 字节」
```

> **为什么必须有它**：`chrome.downloads` 只负责把**服务器返回的正文**存成文件，
> 它**不看 HTTP 状态码**。两种结局：
> - CDN 用 `text/html` 回应 → Chrome 标成 interrupted → 旧代码能捕获
> - CDN 用 `application/octet-stream` 回应 → Chrome 以为正常，**报「完成」**
>   → 用户拿到一个几百字节的假 mp4

**`looksLikeStandaloneMp4()` 的判据**：

```
扫前 24 个盒子：
  ftyp + moov + mdat，且没有 moof/styp  → true（独立完整 MP4）
  出现 moof 或 styp                    → false（fMP4 碎片）
```

### `ffmpeg-args.js`（61 行）

ffmpeg 命令行构造。

| 函数 | 作用 |
|---|---|
| `qualityToHeight(quality)` `:8` | `'source'` → 0（不限制）；`'1080'` → 1080 |
| `buildArgs(inputName,outputName,options)` `:20` | **生成 ffmpeg 参数** |
| `buildTranscodeArgs(...)` `:43` | 兜底的全量重编码参数 |
| `isMpegTs(name)` `:56` | 按扩展名判断是不是 MPEG-TS |

**`buildArgs()` 的两种模式**：

```javascript
// quality === 'source'（默认）→ 直接复制流，不重新编码
['-hide_banner', '-y', '-i', inputName,
'-c', 'copy',
// 如果输入是 .ts/.m2ts/.mts，额外加这一条
'-bsf:a', 'aac_adtstoasc',
'-movflags', '+faststart', outputName]
```

> **`-bsf:a aac_adtstoasc` 是干什么的**：
> MPEG-TS 里的 AAC 是 ADTS 格式（每个帧自带头），
> 直接塞进 MP4 播不了，要转成 ASC（裸帧）。这一条就是干这个的。

```javascript
// quality 是具体数值 → 重新编码
['-hide_banner', '-y', '-i', inputName,
'-c:v', 'libx264', '-preset', preset, '-crf', String(crf),
'-vf', `scale=-2:min(${height}\,ih)`,     // -2 = 宽度按比例取偶数
'-c:a', 'aac', '-b:a', '128k',
'-movflags', '+faststart', outputName]
```

> **`-movflags +faststart`**：把索引（`moov`）放到文件头，这样**边下边播**。

---

## 消息协议全表

定义在 `src/common/constants.js`。消息统一带 `target: 'sw' | 'offscreen'`，后台和 offscreen 各自只处理属于自己的那份。

### 内容脚本 → 后台

| 常量 | 值 | 载荷 | 用途 |
|---|---|---|---|
| `MSG.FOUND` | `vs:found` | `{ item }` | 发现一条媒体资源 |
| `MSG.PAGE_INFO` | `vs:page-info` | `{ pageUrl, title }` | 页面元信息 |
| `MSG.STREAM_CHUNK` | `vs:stream-chunk` | `{ url, streamKey, index, total, data }` | MSE 分片（base64） |
| `MSG.STREAM_DONE` | `vs:stream-done` | `{ url, streamKey, total }` | 分片传完 |
| `MSG.STREAM_ERROR` | `vs:stream-error` | `{ message }` | 抓取失败 |
| `MSG.STREAM_ARMED` | `vs:stream-armed` | `{ url, streamKey, recordToken }` | 页面已进入录制模式 |
| `MSG.STREAM_DISARMED` | `vs:stream-disarmed` | `{ url, streamKey, recordToken, sent }` | 页面停止推送（`sent` = 已发分片数） |
| `MSG.STREAM_PROGRESS` | `vs:stream-progress` | `{ url, streamKey, recordToken, buffered, duration, ended, currentTime, sent }` | 播放进度 |
| `MSG.STREAM_MIGRATED` | `vs:stream-migrated` | `{ url, streamKey, recordToken, jobId }` | **v1.4.0**：播放器重建 MediaSource，新流并入正在进行的录制 |
| `MSG.JSON_MANIFEST` | `vs:json-manifest` | `{ url, text }` | **v1.4.0**：JSON 接口原文，后台用来找「整集分片数组」 |

> **v1.4.0 的分片通道变了**：分片不再经过 Service Worker，
> 而是 `页面 → 隔离世界 → offscreen` 直发（机制细节见 [开发与调试指南](10-dev-guide.md)）。
> 上表里的 `MSG.STREAM_CHUNK` 只为兼容旧版页面脚本保留。

### popup / options → 后台

| 常量 | 值 | 载荷 |
|---|---|---|
| `MSG.GET_MEDIA` | `vs:get-media` | `{ tabId }` |
| `MSG.GET_SETTINGS` | `vs:get-settings` | — |
| `MSG.SAVE_SETTINGS` | `vs:save-settings` | `{ tabId, patch }` |
| `MSG.DOWNLOAD` | `vs:download` | `{ tabId, id }` |
| `MSG.CONVERT` | `vs:convert` | `{ tabId, id }` |
| `MSG.CONVERT_CANCEL` | `vs:convert-cancel` | — |
| `MSG.CLEAR_MEDIA` | `vs:clear-media` | `{ tabId }` |
| `MSG.RESNIFF` | `vs:resniff` | `{ tabId }` |
| `MSG.DELETE_ITEM` | `vs:delete-item` | `{ tabId, id }` |
| `MSG.CAPTURE_RESET` | `vs:capture-reset` | `{ tabId, id }` |
| `MSG.CAPTURE_RECORD` | `vs:capture-record` | `{ tabId, id }` 开始边播边录 |
| `MSG.CAPTURE_STOP` | `vs:capture-stop` | `{ tabId, id }` 停止录制并保存 |
| `vs:download-full` | `vs:download-full` | `{ tabId }` **v1.4.0**：一键下载完整视频（后台自动挑能整段下载的条目） |

### 后台 → popup（推送）

| 常量 | 值 | 载荷 |
|---|---|---|
| `MSG.MEDIA_UPDATED` | `vs:media-updated` | `{ tabId }` |
| `MSG.JOB_UPDATED` | `vs:job-updated` | `{ tabId }` |

### 后台 ⇄ offscreen

| 常量 | 值 | 方向 | 载荷 |
|---|---|---|---|
| `MSG.OFFSCREEN_JOB` | `vs:offscreen-job` | → | `{ jobId, spec }` |
| `MSG.OFFSCREEN_CHUNK` | `vs:offscreen-chunk` | → | `{ jobId, data }` |
| `MSG.OFFSCREEN_CHUNK_END` | `vs:offscreen-chunk-end` | → | `{ jobId }` |
| `MSG.OFFSCREEN_CLEAR_CACHE` | `vs:offscreen-clear-cache` | → | — |
| `MSG.OFFSCREEN_CORE_STATUS` | `vs:offscreen-core-status` | → | — |
| `MSG.OFFSCREEN_READY` | `vs:offscreen-ready` | ← | — |
| `MSG.OFFSCREEN_PROGRESS` | `vs:offscreen-progress` | ← | `{ jobId, progress, phase }` |
| `MSG.OFFSCREEN_DONE` | `vs:offscreen-done` | ← | `{ jobId, filename, size, duration, warning }` |
| `MSG.OFFSCREEN_ERROR` | `vs:offscreen-error` | ← | `{ jobId, message }` |
| `MSG.OFFSCREEN_LOG` | `vs:offscreen-log` | ← | `{ jobId, message }` |

---

## 资源登记表的数据模型

一条资源的完整字段：

```ts
{
  id: string,            // hashId(kind + streamKey|url)
  tabId: number,
  frameId: number,
  kind: 'direct'|'hls'|'dash'|'mse'|'blob'|'segment',
  url: string,
  streamKey?: string,    // 仅 MSE：blobUrl + '::' + mime
  mime: string,
  ext: string,
  size: number|null,
  width: number|null,
  height: number|null,
  duration: number|null, // 期望时长（接口/元素提供）
  label: string,         // 人类可读描述
  origin: 'network'|'dom'|'mse'|'blob'|'json',
  origins: string[],     // 见过这个 URL 的所有来源
  pageUrl: string,       // 页面地址（Referer 用）
  pageTitle: string,     // 页面标题
  mediaTitle?: string,   // 视频原名
  sourceUrl?: string,    // 解析出它的接口地址

  // DASH 专属
  videoUrls?: { url, backups[], width, height, bandwidth, codecs, id }[],
  audioUrls?: { url, backups[], bandwidth, codecs, id }[],

  // DASH 轨道关联（v1.2.0）
  trackType?: 'video'|'audio',   // 这是 DASH 的单条轨道
  trackHeight?: number,
  dashId?: string,               // 归属的 DASH 条目 id
  complete?: boolean,            // true = 完整视频
  note?: string,                 // 给人看的提示

  status: 'new'|'downloading'|'converting'|'done'|'error',
  progress: number,
  error: string|null,
  warning?: string,
  ts: number,
}
```

这张表就是 `registry.js` 内存里的条目结构，`storage.session` 里的镜像也是它。字段怎么被填、被合并，见前面「`registry.js`：资源登记表」一节；字段怎么被渲染成弹窗里的卡片，见「`popup.js`：弹窗怎么渲染」一节。
