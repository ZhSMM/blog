# 开发与调试指南

这一页是动手改 video-sniffer 时的操作手册。前面几页讲「它是什么、为什么这么设计」，这一页讲「怎么动它」：先把环境跑起来，再按步骤改代码，然后用三层测试验证，接着照着症状表调试，最后按发布清单打包上线。

在整章里的分工是这样的：

- [章节总览](00-summary.md) 给出全章地图和四条阅读路线。想先知道每一页讲什么，从那里进。
- [代码导读](04-code-tour.md) 讲每个文件负责什么、关键函数在第几行、消息协议全表和资源登记表的数据模型。本页只讲**怎么改**，不重复文件职责。
- [扩展架构](03-architecture.md) 讲五个执行上下文怎么协作、一条数据怎么流过整条链路。改代码之前如果还不懂「为什么这么分层」，先去那里。
- 站点侧的问题分别看 [B 站番剧 DASH 接口](05-bilibili-bangumi.md)、[B 站投稿视频下载](06-bilibili-ugc.md)、[YouTube 视频抓取](07-youtube.md)。
- 要把这套做法搬到一个新站点，看 [新站点适配手册](08-new-site-playbook.md)；下载结果不对（体积偏小、满屏条码、403），看 [DASH 下载异常排查](09-troubleshooting.md)。

本页出现的 `src/offscreen/offscreen.js`、`tools/package.mjs`、`test/filename.test.mjs` 这类写法，**指的是 video-sniffer 项目里的文件与行号**，不是本章的页面。

* auto-gen TOC;
{:toc}

---

## 三十秒上手

### 常用命令

```bash
npm install          # 只有测试需要（@ffmpeg/core），扩展本体零依赖
npm test             # 单元测试：mime 分类 / HLS 解析 / 播放清单识别 / ffmpeg 参数 / 文件命名
npm run lint         # 语法检查：把 src/ 下每个 ES 模块解析一遍（不执行）
npm run docs:check   # 文档校对：检查文档里所有 `文件:行号` 引用是否还对得上代码
npm run smoke        # 端到端：无头 Chrome + 真实 ffmpeg.wasm 转码
npm run test:bili    # 线上：真实 B 站页面 → 真实下载 → 真实封装
npm run serve        # 本地测试页 http://127.0.0.1:8765/
node tools/debug-rebuild.mjs   # 调试：复现「播放器重建 MediaSource」并打印内部状态
```

### 手动加载扩展

`chrome://extensions/` → 开发者模式 → 加载已解压的扩展程序 → 选 `video-sniffer/` 目录。

### 看代码的推荐顺序

由外向内，每一层都能独立跑通：

```
manifest.json
  → src/content/page-hook.js      页面里发生了什么
  → src/content/bridge.js         怎么把消息递出去
  → src/background/service-worker.js  总路由
  → src/background/registry.js     资源长什么样、怎么合并
  → src/background/downloader.js   下载/转码怎么编排
  → src/offscreen/offscreen.js     真正干活的地方
  → src/offscreen/ffmpeg-protocol.js  ffmpeg 怎么在 CSP 下跑起来
```

这条顺序对应的逐文件职责说明在 [代码导读](04-code-tour.md)；为什么必须分这么多层，见 [扩展架构](03-architecture.md)。

---

## 改代码

### 改扩展代码

1. 改文件 → `chrome://extensions/` → 点扩展卡片上的**刷新**按钮。
2. 刷新后**已经打开的页面不会自动重新注入**内容脚本，需要刷新那个页面。
3. Service Worker 改动后，先点扩展卡片上的「Service Worker」链接打开 DevTools，再点刷新 —— 否则会看到旧代码。

### 加一个新站点的适配

> **完全新手先看 [新站点适配手册](08-new-site-playbook.md)** —— 那一页把 DevTools 每一步怎么点、6 种视频形态怎么认、「四道关」怎么过、5 种接入改法怎么选，全部写成了可照做的步骤。下面是给已经熟悉本项目的人看的速查版。

按这个顺序排查：

1. **打开 DevTools → Network**，找媒体请求的 URL 形态。
   - 是媒体响应？→ `net.js` 的 `classify` 应该已经能分类，检查 MIME / 扩展名是否在表里。
   - 是 JSON？→ 往 `page-hook.js` 的 `MEDIA_HINT_RE` 加关键词，然后扩展 `reportJsonMedia`。
2. **JSON 形态是 `data.dash.*`** → 现有的 DASH 管线直接能用，只要字段名对上（`baseUrl` / `base_url` / `backupUrl` / `url` / `src`，`pickUrl` 已经都兼容）。
3. **JSON 形态是别的** → 在 `reportJsonMedia` 里加分支，产出 `{ url, kind, videoUrls, audioUrls, duration }`。
4. **需要 Referer** → 扩展已经自动注入，通常不用管。
5. **写一个线上测试**：仿照 `tools/bilibili-test.mjs`，换 URL 即可。

### 加一种新的媒体类型

1. 在 `src/common/constants.js` 的 `KIND` 里加类型。
2. 在 `src/background/registry.js` 的 `KIND_RANK` 里给排名（**越具体排名越高**）。
3. 在 `src/background/downloader.js` 的 `startDownload` / `startConvert` 里加路由分支。
4. 在 `src/offscreen/offscreen.js` 的 `runJob` 里加 `spec.mode` 分支。
5. 在 `src/popup/popup.js` 的 `KIND_LABEL` 和 `metaLine` 里加显示。

### 改 ffmpeg 参数

**不要**直接改 `src/offscreen/offscreen.js` 里的裸数组 —— 参数构造集中在 `src/common/ffmpeg-args.js`，那里的逻辑有单元测试（`test/ffmpeg-args.test.mjs`，见本页[单元测试](#单元测试)），而且会拿**真实的 ffmpeg** 跑一遍验证参数合法。

### 改文件名规则

只改 `src/common/filename.js`，然后补 `test/filename.test.mjs`（见本页[单元测试](#单元测试)）。这个模块是纯函数，改起来最安全。

---

## 测试体系

三层，从快到慢。

### 单元测试

```bash
node --test "test/*.test.mjs"
```

> Node 25 **不接受目录参数**，必须写 glob。

| 文件 | 覆盖 |
|---|---|
| `test/mime.test.mjs` | MIME/URL 分类、格式化 |
| `test/hls.test.mjs` | m3u8 主/子列表、AES-128 key/IV、EXT-X-MAP |
| `test/playlist.test.mjs` | **v1.4.0**：播放清单识别、分片数组提取、清单文本解析；**v1.4.1** 追加「B 站相关推荐列表不能当分片」「DASH 轨道数组不能当分片」两条回归 |
| `test/dash.test.mjs` | **v1.4.1**：DASH 清单的通用定位（投稿页 `data.dash` / 番剧页 `data.video_info.dash` / PGC `result.video.dash`）、驼峰+下划线字段名、**镜像与正式模块的防漂移比对** |
| `test/dash-tracks.test.mjs` | **v1.4.3**：选轨策略（跳过占位流/加密流、同画质优先 H.264、画质上限、授权画质优先）、bpp 占位流判定、下载后体检（认 `pssh`/`encv`） |
| `test/bilibili-alt.test.mjs` | **v1.4.3**：番剧备用地址逻辑（从页面地址取 ep_id、在 `ep/page` 响应里找 cid/bvid、只认 B 站域名）；**v1.4.3 收尾**：番剧轨道判定、接口撞风控时的重试、备用清单的缓存；**v1.4.4**：投稿视频补抓（`bvidFromPageUrl`、`findDurl`、`fetchUgcManifest`） |
| `test/download-check.test.mjs` | **v1.4.2**：下载结果校验（403 错误页识别、体积异常识别）；**v1.4.4**：`looksLikeStandaloneMp4()`（区分独立 MP4 和 fMP4 碎片） |
| `test/net.test.mjs` | **v1.4.2**：`Content-Range` 解析出整个文件的大小 |
| `test/ffmpeg-args.test.mjs` | 参数构造 + **真实 ffmpeg 验证参数合法** |
| `test/filename.test.mjs` | 标题清洗、文件名合法性、后缀 |

### 文档引用校验

```bash
node tools/check-doc-refs.mjs
```

把文档里所有 `文件:行号` 引用抽出来核对：行号不能越界，行号附近必须能找到文档写的那个函数名。脚本在项目目录里的位置见 [代码导读](04-code-tour.md) 的项目目录结构一节（`tools/check-doc-refs.mjs`）。

### 语法检查

```bash
node --experimental-vm-modules tools/syntax-check.mjs
```

Service Worker / popup / offscreen 都有 `chrome.*` 的顶层调用，在 Node 里直接 import 会因为
`chrome is not defined` 而报错，掩盖真正的语法错误。
`tools/syntax-check.mjs` 用 `vm.SourceTextModule` **只解析不执行**，能把语法/结构问题全部暴露出来。

### 端到端冒烟

启动无头 Chrome → 用 CDP 安装扩展 → 打开本地测试页 → 断言嗅探到 4 类资源 → 触发下载/转码 → 用**真实 ffmpeg 核心**解码产物，验证是 h264 + 有音轨。

v1.4.0 新增了两个关键用例（对应用户的两个问题）：

| 用例 | 验证什么 |
|---|---|
| `live recording keeps running instead of finishing immediately` | **录制不能一开始就自动收尾**（旧逻辑用 `buffered >= duration` 判定完成，录制刚开始就结束了） |
| `the rebuild recording contains the segments from BOTH sources` | **播放器重建 MediaSource 后录制要自动接上**：测试页会真的重建一次 MediaSource，成品时长必须接近完整素材（≥ 95%） |

测试页 `test/demo.html` 里有 5 个媒体元素，其中第 5 个专门用来模拟「播放器换源」：
`window.__rebuildNow()` 会新建一个 MediaSource、换掉 `video.src`、再喂剩下的分片。

> ⚠️ 播放器重建 MediaSource 时会**再 append 一次 init 段**，
> 两段 init 直接拼起来中间会插进一个 `moov`，成品就废了。
> 扩展靠「init 段以 `ftyp` 开头」这个特征识别并丢掉重复的那一份。

`test/helpers/core.mjs` 里的 `bootCore()` 是关键：在 Node 里跑 ffmpeg.wasm 需要两个 polyfill：

```js
globalThis.self = globalThis;                                   // worker 全局
globalThis.location = { href: 'http://127.0.0.1:<port>/' };    // 核心用它定位 wasm
```

wasm 通过本地 HTTP 服务提供 —— Node 的 `fetch` 读不了 `file://`。

### 线上测试

真实 B 站页面 → 真实 playurl 接口 → 真实 CDN 下载 → 真实封装 → 解码校验时长与音视频轨。

```bash
npm run test:bili                                              # 投稿页（默认 BV1GJ411x7h7）
npm run test:bili -- 'https://www.bilibili.com/bangumi/play/ep3854802'   # 番剧页
npm run test:bili -- 'https://www.bilibili.com/video/BV11HHq6uEdp/'     # 另一个投稿页
```

三种页面的 playurl 接口结构不同（投稿页 `data.dash`、番剧页 `data.video_info.dash`），
所以脚本三种都能测 —— 它会轮询等 DASH 条目出现，再下载、封装、解码校验。

**v1.4.2 新增的回归用例**（对应「点直链拿到假视频」那个问题）：

| 用例 | 验证什么 |
|---|---|
| `a single DASH track is labelled as a track` | 单条轨道被识别出来并打上标签（`direct` 和 `segment` 两种 kind 都算） |
| `clicking a single track yields a complete video` | **点「直链」必须拿到完整视频**（而不是几百字节的 403 错误页） |
| `… (from a single track) decodes with video AND audio` | 产物必须**同时有画面和声音** |
| `… (from a single track) is complete (416.82s vs 417s)` | 时长要跟接口声明的一致 |

v1.4.1 对番剧页（ep3854802）的实测结果：

```
detected title: 凡人修仙传第178集
video 1920x1080, 5 qualities, 3 audio tracks
downloaded: 凡人修仙传第178集_1080p.mp4
凡人修仙传第178集_1080p.mp4 decodes with video AND audio
凡人修仙传第178集_1080p.mp4 duration matches the API (1440.04s vs 1441s)
```

v1.4.2 对投稿页（BV11HHq6uEdp）的实测结果：

```
track label: video 350 - DASH 的单条视频轨（350p，AV01），本身没有声音；点「下载」会自动配上音轨
track download: 没有肉车，只有怂人！_350p.mp4
没有肉车，只有怂人！_350p.mp4 (from a single track) decodes with video AND audio
没有肉车，只有怂人！_350p.mp4 (from a single track) is complete (416.82s vs 417s)
```

---

## 调试手册：按症状排查

### 怎么看各上下文的日志

| 目标 | 打开方式 |
|---|---|
| Service Worker | `chrome://extensions/` → 扩展卡片 →「Service Worker」链接 |
| Offscreen 文档 | Service Worker DevTools → 目标下拉选 `offscreen.html` |
| popup / options | 右键弹窗 → 检查 |
| 内容脚本（隔离世界） | 页面 DevTools → Sources → Content scripts |
| 内容脚本（主世界） | 页面 DevTools → Console，勾选顶部的「选择上下文」下拉 → `video-sniffer` |
| 页面自己的报错 | 页面 DevTools → Console |

> **主世界日志看不到？** 内容脚本默认在页面控制台里带 `(index.js)` 前缀，容易和页面代码混在一起。用 DevTools 的**上下文下拉框**切到 `video-sniffer` 就能单独过滤。

**设置页 → 调试 → 调试日志**打开后，Service Worker 控制台会输出：

```
[Video Sniffer] 发现资源 [dash] https://…/137649199_da2-1-30032.m4s 原名: 【官方 MV】Never Gonna Give You Up - Rick Astley 页面标题: 【官方 MV】… - 哔哩哔哩_bilibili
[Video Sniffer] 网络嗅探 [direct] https://…/137649199_da2-1-30216.m4s
[Video Sniffer] [ffmpeg] job_xxx Input #0, mov,…  Duration: 00:03:32.31
[Video Sniffer] 任务 job_xxx 完成但有告警: 成品时长只有 30.0s（预期 213.0s，缺 86%），文件不完整
```

这四行分别对应：**资源来源**、**网络层嗅探**、**ffmpeg 输出**、**完整性告警** —— 排查时先看它们。

### 命令行诊断工具

在动浏览器之前，先用命令行把问题定位到一半：

```bash
# 在浏览器之外复现 DASH 下载 + 封装，逐项对比时长
npm run test:dash

# 用真实 ffmpeg 探测本地媒体文件（时长/编码/分辨率/帧数）
npm run probe test/downloads/xxx.mp4
```

`npm run test:dash` 会打印：接口声明的时长、轨道各自的时长、封装后的时长、三者是否一致。
如果**这里**的时长就是对的，那问题不在封装环节，而在扩展的选轨或传输环节 —— 这能一刀切掉一半的排查范围。

### 症状速查表

| 症状 | 最可能的原因 | 怎么确认 |
|---|---|---|
| 弹窗里一条资源都没有 | 内容脚本没注入 / 站点是 DRM / `enabled` 关了 | DevTools Sources 看有没有 `page-hook.js`；检查设置页开关 |
| 只有「直链」，没有 DASH | JSON 预筛没命中 | Network 里找 JSON 响应，把响应里的关键词加进 `MEDIA_HINT_RE` |
| 下载 403 | CDN 校验 Referer | Network 看请求头有没有 `Referer`；检查 DNR 规则是否装上 |
| 下载下来了但没声音 | 点的是 DASH 的**单条视频轨** | popup 上看有没有「视频轨」标签；有就改下 **DASH** 条目 |
| 下载下来的视频长度不够 | 下的是 MSE 条目（只有已缓冲的部分），或下载被截断 | 看任务消息里的时长警告；MSE 条目改用「边播边录」，或下载 HLS/DASH 完整条目 |
| 文件名是 `137649199_da2-1-30032.mp4` | 没拿到视频原名 | 检查 `mediaTitle` / `pageTitle` 是否有值（见本页[专门排查文件名不对](#专门排查文件名不对)） |
| 「边播边录」不自动结束 | 播放器的 `<video>` 没上报 `ended` / `buffered` | 手动点「停止并保存」；或确认播放器真的有 `<video>` 元素 |
| 「转 MP4」卡在下载核心 | unpkg 不通 | 设置页换「核心下载地址」为镜像 |
| HLS 报「不支持的加密方式」 | `SAMPLE-AES` / `cbcs` | 属于 DRM 范畴，本扩展不做绕过 |
| **番剧文件特别小 / 播放满屏条码**（v1.4.3 前） | 番剧页的 DRM 接口给的是占位清单/加密流 | 已修：番剧改走普通播放接口 + 下载后体检（见 [DASH 下载异常排查](09-troubleshooting.md)） |
| **番剧清晰度比网页上低**（v1.4.3 后） | 番剧现在拿的是「免会员版」地址，清晰度按账号权限给 | 登录大会员账号即可；这是刻意的（不伪造权限）（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md) 的「三个必须知道的坑」） |
| 扩展里调 B 站接口拿到 `v_voucher` | 风控：请求的 origin 是 `chrome-extension://` | 让内容脚本代发（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md) 的「三个必须知道的坑」之风控对照） |
| MSE 条目只有几十秒 | 只录了播放器已缓冲的部分 | 让视频播完再下载，或优先用 DASH 条目 |
| 弹窗不刷新 | `notifyPopup` 的消息没送到 | 看 SW 控制台有没有 `MEDIA_UPDATED` |
| **录制刚开始就自动停止**（v1.4.0 前） | `buffered >= duration` 误判 —— MSE 的 duration 就是缓冲区末端 | 已修：只用 `ended` 判定完成（进度上报字段见 [代码导读](04-code-tour.md) 的消息协议全表 `MSG.STREAM_PROGRESS`） |
| **录制中途断掉、列表多出一条新条目**（v1.4.0 前） | 播放器重建了 MediaSource，录制还盯着旧 blob URL | 已修：录制会话锚定媒体元素，自动迁移（会话与分片编号的改动见 [YouTube 视频抓取](07-youtube.md) 的「改 `src/content/page-hook.js`」） |
| 录制跑着跑着全停了 | Service Worker 被回收，中转的分片丢了 | 已修：分片直发 offscreen，任务落盘（见 [扩展架构](03-architecture.md) 的「Service Worker 随时会被杀」） |
| 播完了但迟迟不自动保存 | 后台标签页的 `setInterval` 被节流到 1 分钟一次 | 已修：改用媒体元素事件（见 [代码导读](04-code-tour.md) 的消息协议全表 `MSG.STREAM_PROGRESS` / `MSG.STREAM_DISARMED`） |
| 下到的 m3u8 是个几十 KB 的文本文件 | 播放清单被当成了普通媒体文件 | 已修：清单单独识别成 HLS/DASH 条目（清单与媒体文件的区分见 [代码导读](04-code-tour.md) 的 `playlist.js`） |
| 清单是 blob URL，找不到原始地址 | 站点把 m3u8 包进了 `new Blob([text])` | 看 popup 有没有「分片清单」条目；有就整组下载（见 [代码导读](04-code-tour.md) 的 `playlist.js`） |
| **番剧页只有单轨、没有 DASH**（v1.4.1 前） | DASH 写死在 `data.dash`，番剧页是 `data.video_info.dash` | 已修：改成在 JSON 树里通用定位（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md) 的「为什么要「树形搜索」而不是写死路径」） |
| **番剧页冒出一条假的「分片清单（20 片）」**（v1.4.1 前） | 「相关推荐」里的剧集列表被当成分片 | 已修：分片清单必须有强信号，且跳过 DASH 子树（见 [代码导读](04-code-tour.md) 的 `playlist.js`） |
| **番剧下载的文件名没有集数**（v1.4.1 前） | og:title 只有剧名，集数在 `document.title` 里 | 已修：og:title 是前缀时补上「第N集」（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md)） |
| 番剧 1080P 下载 403 | 高画质要大会员/登录 | 已修：自动降到下一档画质，文件名同步改（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md) 的画质与选轨说明） |
| **点「直链」下载，拿到几百字节的假视频**（v1.4.2 前） | 网络嗅探条目没有 pageUrl → 没法注入 Referer；`chrome.downloads` 又不带 Referer | 已修：补 pageUrl + 下载结果校验 + 自动改走引擎（见 [代码导读](04-code-tour.md) 的 `download-check.js`） |
| **点「直链」下载，文件没声音**（v1.4.2 前） | DASH 的单条轨道本来就只有一半 | 已修：自动配上配套的另一条轨，合成完整有声视频（见 [DASH 下载异常排查](09-troubleshooting.md)） |
| **列表里显示的文件大小小得离谱**（v1.4.2 前） | 播放器用 Range 分段拉取，记到的是那一段的长度 | 已修：解析 `Content-Range` 取总大小（见 [代码导读](04-code-tour.md) 的 `download-check.js`） |
| **番剧页点「单条轨道」报 403**（v1.4.3 收尾前） | 轨道和清单对不上号 + 只给一条候选 + 镜像漏装 Referer + 风控重试只做了一半 | 已修：四个都改了（见 [DASH 下载异常排查](09-troubleshooting.md) 的修复清单） |
| 扩展里调 B 站接口第一次就拿到 `v_voucher` | 风控是**按次**的，第一次请求就可能被挡 | 退避重试（两条路都重试）；备用清单缓存 5 分钟（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md) 的「三个必须知道的坑」） |
| **投稿页列表里只剩「缓冲片段」** | 页面钩子没抓到 playurl 响应（页面先开着 / 走了 SW / 命中缓存） | 点 popup 的「补抓播放地址」（v1.4.4，见 [B 站投稿视频下载](06-bilibili-ugc.md) 的「坑 1」） |
| **投稿页的 durl 只有 1 项却被当成片段** | 那一项**就是整个视频**（独立完整 MP4） | 扫盒子：有 `moov` 无 `moof` = 独立 MP4（v1.4.4，见 [B 站投稿视频下载](06-bilibili-ugc.md) 的「实证：`durl` 那一项就是整个视频」） |
| **下下来的视频只有开头一小段** | 多段 durl 被按字节拼了（每段都自带 moov） | 用 ffmpeg concat 分离器合并（v1.4.4，见 [B 站投稿视频下载](06-bilibili-ugc.md) 的「坑 4」） |
| **durl 的时长显示成 116 小时** | `durl.length` 的单位是毫秒不是秒 | 毫秒 ÷ 1000（v1.4.4） |

### 专门排查文件名不对

按顺序确认这三个字段（popup 里把鼠标悬停在标题上也能看到）：

1. `item.mediaTitle` —— 视频原名，来自 og:title / `__INITIAL_STATE__.videoData.title` / 接口的 `data.title`。
2. `item.pageTitle` —— 页面标题，来自 `document.title`（**必须实时读**，`document_start` 时是空的）。
3. `item.url` —— 前两个都没有时才用它。

在 SW 控制台里直接查：

```js
// Service Worker 控制台
const items = await chrome.runtime.sendMessage({ type: 'vs:get-media', tabId: <tabId> });
console.table(items.items.map(i => ({ kind: i.kind, mediaTitle: i.mediaTitle, pageTitle: i.pageTitle, url: i.url.slice(0, 60) })));
```

如果 `mediaTitle` 和 `pageTitle` 都是空的 → 标题采集链路断了（页面钩子没装上，或站点用了非标准结构）。

### 用 CDP 手动探查

`tools/cdp.mjs` 是一个零依赖的 CDP 客户端，可以直接拿来用：

```js
import { CDP, launchChrome, installExtension, newTarget } from './tools/cdp.mjs';

const { proc, port } = await launchChrome(userDataDir, []);
const { browser, extId } = await installExtension(port, EXT_DIR);
const target = await newTarget(port, 'https://www.bilibili.com/video/BV.../');
const page = await CDP.connect(target.webSocketDebuggerUrl);
await page.send('Runtime.enable');
const r = await page.eval('document.title');
```

> Chrome 137+ 的正式版**禁用了** `--load-extension`，所以测试脚本统一走 `Extensions.loadUnpacked`。

### 性能与内存

- ffmpeg.wasm 是单线程纯 JS，长视频很慢 → 优先选「原画」（`-c copy`，只封装不重编码）。
- 转码会把整个文件读进内存，默认上限 300 MB（设置页可调）。超限会直接拒绝并提示。
- MSE 抓取预算默认 64 MB，页面内存占用有限。

### 页面侧调试出口（v1.4.0）

录制相关的问题（断线、迁移失败、条目重复）光看 UI 看不出来，
必须能看到页面侧的内部状态。`page-hook.js` 把它们挂到了 `window.__vsDebug`：

在**页面**的 DevTools Console 里直接敲：

```js
__vsDebug.sessions()   // 当前录制会话：token / jobId / 当前 URL / 已收过的流 / 是否有元素
__vsDebug.armed()      // 正在录制的 streamKey 列表
__vsDebug.streams()    // 已知的全部流（URL + mime + 是否音频）
__vsDebug.elements()   // 每个媒体元素的 src / currentSrc / ended / paused / currentTime / buffered
__vsDebug.outbox()     // 还没收到 offscreen 确认的分片数
```

对应的排查脚本：`node tools/debug-rebuild.mjs`
——它会起一个真实的 Chrome，复现「播放器重建 MediaSource」，并把上面这些状态逐步打出来。

> 提醒：调试出口在**页面主世界**（`world: "MAIN"`），
> 要在页面自己的 Console 里敲，不是扩展的 DevTools。

---

## 踩过的坑清单

这些都是本项目**实际踩过**的，改代码前值得扫一眼。

| # | 坑 | 现象 | 正解 |
|---|---|---|---|
| 1 | 扩展 CSP 里写了 `blob:` / `https:` | 整个 manifest 校验失败，扩展根本装不上 | `script-src` 只能有 `'self'` 和 `'wasm-unsafe-eval'`；`worker-src` 同理 |
| 2 | 在 isolated world 里改页面原型 | 页面毫无反应，嗅探不到任何东西 | 挂钩必须在 `world: "MAIN"` |
| 3 | 跨 world 用 `event.source !== window` 判断 | 所有消息被丢弃，页面与扩展彻底断联 | 用随机 token 校验 |
| 4 | 用 `fetch` 设置 `Referer` | 头被浏览器直接丢掉，CDN 返回 403 | 用 `declarativeNetRequest` 在网络层注入 |
| 5 | DNR 的 `action.type` 用了带命名空间的常量 | 规则静默不生效 | 必须写字符串 `'modifyHeaders'` |
| 6 | `document.title` 在 `document_start` 读 | 永远是空字符串 → 文件名退回 CDN 名 | 每次上报都重新读；用 og:title 兜底 |
| 7 | MSE 只按 blob URL 分键 | 视频和音频被合并 → 有画面没声音 | 用 `streamKey = url + '::' + mime` |
| 8 | `FS.writeFile` 传裸 `ArrayBuffer` | 报 `Unsupported data type` | 必须包成 `Uint8Array` |
| 9 | 用 `movflags default_base_is_moof` | ffmpeg 报未知选项 | 改用 `frag_keyframe+empty_moov` |
| 10 | `addSourceBuffer('video/mp4')` | Chrome 直接抛异常 | 必须带 codecs：`video/mp4; codecs="avc1.42E01E"` |
| 11 | 用 PowerShell 的 `Get-Content`/`Set-Content` 改含中文的文件 | UTF-8 被按 ANSI 误读，中文变成 `鎾斁鍒楄〃` | **永远用编辑工具改文件**；改完用 grep 扫一遍可疑字符 |
| 12 | `node --test test/` | Node 25 报参数错误 | 写 glob：`node --test "test/*.test.mjs"` |
| 13 | Node 里跑 ffmpeg 核心报找不到 wasm | `file://` 读不了 | polyfill `globalThis.self` + 用本地 HTTP 服务提供 wasm |
| 14 | `registry.upsert` 只带 `id` 不带 `url` | 状态更新被静默丢弃，条目永远不显示「完成」 | `upsert` 支持 id-only 更新分支 |
| 15 | 直接下载 `.m4s` 单条轨道 | 下到的是没有声音的视频（或纯音频） | 提供 DASH 完整条目，并把单条轨道打标签提示 |
| 16 | MSE 的 init 段里带了 `mfra` / `udta` | SourceBuffer 直接拒收，元素 readyState 永远 0 | init 段只保留 `ftyp` + `moov`（`mvex` 在 `moov` 里） |
| 17 | SourceBuffer 的 codec 串只写了视频 | `audio object type 0x40 does not match what is specified in the mimetype` | 声明完整 codec，例如 `avc1.42c00c,mp4a.40.2` |
| 18 | fMP4 分片用绝对寻址 | `TFHD base-data-offset not allowed by MSE` | 生成时加 `-movflags default_base_moof`（相对寻址） |
| 19 | 用 `buffered >= duration` 判定「录完了」 | **录制刚开始就自动收尾**（用户反馈「只录了几十秒」） | MSE 的 `duration` 就是缓冲区末端；只用 `ended` 判定（录制消息协议见 [代码导读](04-code-tour.md)，分片不走 SW 的原因见 [扩展架构](03-architecture.md)） |
| 20 | 换源后只看 `video.currentSrc` | 判定不出「播放器换源了」→ 录制迁移完全失效 | `currentSrc` 是异步更新的，换源瞬间还指向旧地址；必须同时看 `video.src` 属性 |
| 21 | 分片经 Service Worker 中转 | SW 一回收，录制的分片全丢 | 分片直发 offscreen；任务表落盘到 `storage.session`（见 [扩展架构](03-architecture.md) 的「Service Worker 随时会被杀」） |
| 22 | 播放清单和媒体文件一视同仁 | 下到的 m3u8 是个几十 KB 的文本文件 | 按 content-type / URL 后缀区分，报成 `hls` / `dash` |
| 23 | 播放器重建 MediaSource 后直接拼分片 | 中间插进一个 `moov`，成品播不出来 | init 段以 `ftyp` 开头，识别出来只保留第一个（见 [YouTube 视频抓取](07-youtube.md) 的「坑一：产物里有两份 `moov`」） |
| 24 | 用 `node --check` 检查 ES 模块 | 按 CommonJS 解析，`import` 直接报错 | 用 `npm run lint`（`vm.SourceTextModule` 只解析不执行） |
| 25 | 把 DASH 写死在 `data.dash` | **番剧页一条 DASH 都识别不出来**（只剩没有声音的单轨） | 在 JSON 树里通用定位（`src/common/dash.js`，见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md)） |
| 26 | 只认驼峰 `baseUrl` | 番剧页用下划线 `base_url`，轨道地址取不到 | 两种拼写都列上（`pickTrackUrl` / `pickTrackBackups`） |
| 27 | 「≥3 个同源 URL」就当成分片清单 | B 站「相关推荐」的剧集列表被当成整集分片，下载下来是 20 个网页 | 必须有强信号（键名像分片数组 / 半数带媒体后缀），且跳过整个 DASH 子树 |
| 28 | 把 DASH 的 `video` 数组当成分片 | 把不同画质的完整轨道拼在一起 → 成品是乱码 | DASH 子树整个跳过（`looksLikeDash`） |
| 29 | 只用 og:title 当文件名 | 番剧的 178 集全部存成「凡人修仙传.mp4」 | og:title 是 document.title 前缀时补上「第N集」 |
| 30 | 内容脚本里 `import` ES module | 整个内容脚本不执行 | classic script 只能内联镜像；用测试比对镜像与正式模块防止漂移 |
| 31 | DASH 只下载第一条轨道 | 高画质 403 就整单失败 | 逐档尝试，自动降级，文件名里的画质后缀同步改 |
| 32 | 网络嗅探到的条目不带 `pageUrl` | 没法注入 Referer → CDN 403 → 下载拿到的是错误页 | 嗅探回调里补上页面地址；DASH 轨道再从父条目继承一次 |
| 33 | 以为 `declarativeNetRequest` 能管住 `chrome.downloads` | 规则写了 Referer，下载请求**完全不受影响**（实测三种写法都无效） | 下载结果要校验；CDN 要 Referer 时必须走 fetch 引擎那条路 |
| 34 | 相信 `chrome.downloads` 的「完成」状态 | 服务器返回 403 错误页时它照样存成文件并报「完成」 | 下载后用 `chrome.downloads.search` 查 mime/fileSize，异常就删掉重下 |
| 35 | 用分段响应的 `Content-Length` 当文件大小 | 播放器用 Range 分段拉取，记到的是**那一段**的长度（实测只记到 1.5%） | 解析 `Content-Range` 里的总大小 |
| 36 | 以为「码率最高的」就是「最好的」轨道 | B 站给没权限的那一档标的恰恰是最高码率 | 按「授权画质 + 画质 + 编码兼容」选轨，跳过占位流/加密流 |
| 37 | 只看清单判断有没有加密 | 番剧的**音轨**没有 `widevine_pssh` 字段，可文件里照样有 `enca`/`senc` | 下载后看文件盒子（`pssh`/`encv`/`enca`/`senc`） |
| 38 | 在 Service Worker 里直接调 B 站接口 | 100% 返回 `v_voucher`（人机验证），拿不到播放地址 | 让**内容脚本**代发（origin = 页面地址，实测 0/6 被拦）（见 [B 站番剧 DASH 接口](05-bilibili-bangumi.md)） |
| 39 | 给 fetch 手动加 `Origin` 头绕风控 | `Origin` 是禁止头，浏览器直接忽略，没用 | 要改 origin 就得换上下文（内容脚本 / 主世界） |
| 40 | 只给单轨条目一条候选地址 | 那一档签名过期 403 了就没第二次机会（实测「所有画质都下载失败」） | 把所有画质都带上，逐档尝试 |
| 41 | 用 PowerShell 的 `Get-Content`/`Set-Content` 改中文文件 | 按 ANSI 误读再写回，UTF-8 被改坏（`鐢婚潰鍙栬瘉`） | 用编辑器类工具改；改完扫一遍 `\uFFFD` |
| 42 | 靠「地址完全相同」关联单轨和 DASH 清单 | 番剧页上页面真正下载的轨道关联不上（cid、签名、文件名编号全不同）→ 点它就 403 | 番剧页上凡是 `.m4s` 轨道都按轨道处理（`isBangumiTrackItem`） |
| 43 | 只给轨道的主地址装 Referer 规则 | 备用镜像（`backupUrl`）在别的域名上，一用就 403 | `v.url` 和 `v.backups` 一起装规则 |
| 44 | 接口重试只做了一半 | 内容脚本这条路被风控挡一次就直接掉到后台自取（100% 撞风控） | 风控是**按次**的，两条路都要退避重试；备用清单按「标签页+集号」缓存 |
| 45 | 报错只给状态码 | 只有一个「403」，根本不知道是哪个地址挂了 | 报错里带上「主机名/…/文件名」 |
| 46 | 以为 `fnval=0` 和 `fnval=4048` 给的是同一批地址 | `fnval` 决定返回形态：0 给 `durl`（整段 MP4），16/4048 给 DASH 清单 | 分别请求，按返回形态分别处理（见 [B 站投稿视频下载](06-bilibili-ugc.md) 的 `fnval` 表） |
| 47 | 把 `durl[].length` 当秒 | 单位是毫秒（416816 = 416.8 秒），时长会放大 1000 倍 | 毫秒 ÷ 1000 |
| 48 | 以为 `durl` 多段可以按字节拼 | 每段都自带 `moov`，拼起来播放器只读第一段 | 用 `looksLikeStandaloneMp4()` 区分，独立的走 ffmpeg concat |
| 49 | 只靠页面钩子拿播放清单 | 页面先开着 / 走了 SW / 命中缓存时钩子会漏，列表只剩缓冲片段 | 加「补抓播放地址」：扩展自己去接口要一份（见 [B 站投稿视频下载](06-bilibili-ugc.md)） |
| 50 | 在 Node 里 `require('@ffmpeg/core')` 就能用 | 核心按 Worker 编译，要 `globalThis.self` + `wasmBinary` 两块垫片；`exec` 参数要展开传 | 见 [B 站投稿视频下载](06-bilibili-ugc.md) 的「自己写脚本下载」一节 |

---

## 打包与发布

### 打包命令

```bash
# 1. 改版本号（manifest.json 与 package.json 必须一致，脚本会校验）
# 2. 自检
npm test && npm run lint && npm run docs:check && npm run smoke
# 3. 打包
npm run package        # → video-sniffer-v1.2.0.zip
# 4. 验证发布包（解压 → CDP 安装 → 确认 SW 启动、popup 正常）
npm run verify
```

### 打包器与包内容

`tools/package.mjs` 是一个零依赖的 zip 写入器（Node 自带 `zlib`），只打包运行时真正需要的文件：

```
video-sniffer/
  manifest.json        ← 加载扩展时选这一层
  icons/
  src/
  README.md
  docs/DEVELOPMENT.md
  docs/新手教程.md
  docs/从零上手完全指南.md
  docs/新站点视频调试手册.md
  docs/番剧DASH接口手册.md
  docs/DASH下载异常排查.md
  docs/普通投稿视频下载分析.md
```

`test/`、`tools/`、`node_modules/` 一律不进包。

### 加载与清单自检

**加载**：解压 → `chrome://extensions/` → 开发者模式 → 加载已解压的扩展程序 → 选解压出来的 `video-sniffer/` 目录（注意是子目录，不是 zip 本身）。

**清单自检**：

- `manifest.json` 的 `version` 与 zip 文件名一致（打包脚本会直接报错）。
- `icons/` 四个尺寸齐全（16/32/48/128）。
- `src/` 下没有 `.map`、测试残留。
- `video-sniffer/` 目录里不含 `node_modules`。
- 加载后 Service Worker 正常启动、popup 能列出资源。

### 许可与合规

- 扩展代码：MIT。
- ffmpeg 核心（`@ffmpeg/core`）：**GPL-2.0-or-later**，运行时下载、缓存于本地，**不随扩展分发**。

**合规提醒**：仅下载你有权保存的内容；不绕过任何 DRM（本扩展不支持 `SAMPLE-AES` / `cbcs` 等 DRM 流）。
