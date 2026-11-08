# YouTube 视频抓取

* auto-gen TOC;
{:toc}

这一页讲 YouTube 在 video-sniffer 里的完整实现：它是**怎么把视频送过来的**、为什么原来的扩展**只抓得到声音**、为此**代码改了哪些地方**，以及这些结论**怎么自己复现**。

在整章里的位置：这是 [章节总览](00-summary.md) 里的第 07 页，属于阅读路线 C（某个站点下不动）里的 YouTube 分支。前面 [音视频基础](02-media-fundamentals.md) 讲过 MSE 和 Blob URL 这些基本概念，[扩展架构：五个执行上下文](03-architecture.md) 讲过分片怎么从页面钩到 offscreen，本页只聚焦 YouTube 这条特殊路径；逐文件的职责对照见 [代码导读](04-code-tour.md)，想把同一套 UMP 判定逻辑搬到别的站点上，见 [新站点适配手册](08-new-site-playbook.md)。

> 本页出现的 `` `src/common/youtube.js:213` `` 这类写法，指的是 **video-sniffer 项目里的文件与行号**，不是本章的页面位置。

> **案例**：`https://www.youtube.com/watch?v=rfwe5weNpLw`
> 标题《The Surprising Origins of Vanilla | Delishtory》
> 时长 422 秒（7 分 02 秒）
>
> **起因**：扩展在 YouTube 上只能抓到一条音频流，视频轨整个不见了。
>
> **本页回答四件事**：
> 1. YouTube 的视频**到底是怎么送过来的**？（全部是实测，没有推测）
> 2. 为什么原来的扩展**抓不到视频**？
> 3. 为了修好它，**代码改了什么**？（逐文件、逐处、说明理由）
> 4. 怎么**自己复现**这些结论？
>
> 面向零基础。文中每个数字都来自真实 Chrome 的抓取记录。
> 复现命令在「自己复现」一节。

---

## 先说结论

1. **YouTube 走 MSE，不走直链。**
   `<video>` 的 `currentSrc` 是 `blob:https://www.youtube.com/<uuid>`，
   说明浏览器端用的是 **MSE**（MediaSource Extensions）。
   网络上的媒体请求是 `POST .../videoplayback`，
   **不能改写成 GET 直接下载**（实测会返回 31 字节的 `sabr.malformed_config`）。

2. **YouTube 把音视频拆成两条独立的流。**
   同一个 `MediaSource` 上挂着两个 `SourceBuffer`：
   视频是 **fMP4 / AV1**，音频是 **WebM / Opus**。
   **两个容器格式都不一样**，字节混在一起 ffmpeg 直接认不出来，必须分轨处理再合成。

3. **两个 SourceBuffer 共用同一个 blob URL。**
   `URL.createObjectURL` 只被调用了 **1 次**。
   扩展原来靠 URL 区分条目，于是**视频轨被音频轨覆盖掉了**——
   这就是「只看到音频」的直接原因。

4. **改完之后实测产物**（2026-11）：

   | 项目 | 结果 |
   |---|---|
   | 产物 | **单个 `.mp4`** |
   | 大小 | 5.33 MB |
   | 时长 | 64.69 秒（录制 12 秒 + 起播时已缓冲的部分） |
   | 画面 | `Video: av1 (Main) 854x480 / 640x360, 23.98 fps` |
   | 声音 | `Audio: opus, 48000 Hz, stereo` |

   两条轨都在、都能播、起点对齐。

---

## 抓取环境

| 项目 | 值 |
|---|---|
| 浏览器 | Google Chrome 156（headless=new） |
| 扩展安装方式 | CDP `Extensions.loadUnpacked`（见「自己复现」一节） |
| 操作系统 | Windows 11 |
| Node.js | v25.3.0 |
| 录制时长 | 12 秒 |

> **为什么不能用 `--load-extension`？**
> 品牌版 Chrome 从 137 开始禁用了这个命令行开关。
> 必须通过 DevTools 协议的 `Extensions.loadUnpacked` 加载未打包扩展。
> 本仓库的 `tools/cdp.mjs` 里 `installExtension()` 就是干这个的。

---

## YouTube 的播放链路（实测）

### 整体流程

```
  ┌───────────────────────────────────────────────────────────────┐
  │  <video src="blob:https://www.youtube.com/<uuid>">           │
  │         ▲                                                    │
  │         │  URL.createObjectURL() —— 全程只调用了 1 次          │
  │         │                                                    │
  │  ┌──────┴──────────────────────────────────────────────────┐  │
  │  │ MediaSource                                            │  │
  │  │   ├── SourceBuffer  type="video/mp4; codecs=av01..."    │  │
  │  │   └── SourceBuffer  type="audio/webm; codecs=opus"     │  │
  │  └──────────▲───────────────────────────┬─────────────────┘  │
  │             │                           │                    │
  │      appendBuffer(fMP4)         appendBuffer(WebM)           │
  │             │                           │                    │
  └─────────────┼───────────────────────────┼────────────────────┘
                │                           │
                ▼                           ▼
   POST https://rr3---sn-xxx.googlevideo.com/videoplayback
   Content-Type: application/vnd.yt-ump
   响应体 = [protobuf 头(变长)] + [标准 ISO-BMFF / WebM 字节流]
```

### 关键实测数据

| 观测点 | 实测值 |
|---|---|
| `<video>.currentSrc` | `blob:https://www.youtube.com/<uuid>` |
| `URL.createObjectURL` 调用次数 | **1 次**（两个 SourceBuffer 共用） |
| SourceBuffer 数量 | 2（`audio/webm; codecs="opus"` + `video/mp4; codecs="av01.0.01M.08"`） |
| 媒体请求方法 | `POST`（不是 GET） |
| 媒体响应 Content-Type | `application/vnd.yt-ump` |
| UMP 响应体结构 | protobuf 头 + 标准 ISO-BMFF |
| protobuf 头长度 | **变长**：实测 227 / 294 / 330 / 1479 字节 |
| 音频轨容器 | `EBML`（WebM） |
| 视频轨容器 | `ftyp → moov → sidx → moof/mdat` |

### 为什么不能直接下载

`videoplayback` 需要 **POST + protobuf 请求体**。
把同一个地址改成 GET 再请求，实测返回 **31 字节**，内容是：

```
sabr.malformed_config
```

也就是说：**YouTube 上没有可以直接 `curl` 下来的视频直链**，
只有播放器自己发起的、带签名的分段请求。
所以本扩展在 YouTube 上的正确姿势是 **「录制 MSE」**，而不是「下载直链」。

### UMP 头怎么剥

UMP 响应体的开头是一段 protobuf 头，后面才是真正的媒体数据。
**头部长度是变长的**（见上表），所以**不能硬编码偏移**。

可靠规则是：**往后扫，直到遇到第一个合法的 ISO-BMFF 盒为止**。
`ftyp`（文件类型盒）一定在最前面，所以扫描终点就是 UMP 头的末尾。

这条规则在 `src/common/youtube.js:213` 的 `findFirstBox` 里实现，
`src/common/youtube.js:245` 的 `stripUmpHeader` 用它剥头。

---

## 原来的扩展为什么抓不到视频

装上扩展（修复前）在 YouTube 页面上，popup 里只有 5 条：

```
  [mse]     MSE 音频流（录制片段）    audio/webm; codecs="opus"
  [direct]  网络视频                  audio/mpeg      ← 搜索提示音，噪音
  [direct]  网络视频                  audio/mpeg
  [direct]  网络视频                  audio/mpeg
  [direct]  网络视频                  audio/mpeg
```

**视频轨一条都没有。** 三个原因叠在一起：

### 原因一：两条流共用 blob URL，视频轨被覆盖

扩展在 `src/content/bridge.js:443` 的 `itemKeyOf()` 里决定「一条流用什么做键」：

```js
function itemKeyOf(item) {
  return item.streamKey ? item.streamKey : item.url;
}
```

看起来有 `streamKey` 就该分开了——但**修复前这个键只有 `url`**。
YouTube 的两个 SourceBuffer 共用同一个 blob URL，
于是视频轨和音频轨算出**同一个键**，
`reported` 集合认为「这条已经报过了」，视频轨被当成重复项丢掉。

> **症状特征**：列表里剩下的是**音频**而不是视频。
> 因为音频轨后上报，把视频轨挤掉了。

### 原因二：后台 upsert 又按 URL 覆盖了一次

即使前端区分开了，后台 `src/background/registry.js:65` 的 `upsert()`
还会拿 URL 再匹配一次已有条目，一样会把两条流合并成一条。

### 原因三：网络嗅探认不出 UMP

`src/common/mime.js` 的 `classify()` 只看 Content-Type 和文件后缀。
YouTube 返回的是 `application/vnd.yt-ump`，
既不是 `video/*` 也不是已知的音频类型，**直接被丢掉**。

> 顺带一提：列表里那 4 条 `audio/mpeg` 是 YouTube 搜索框的提示音，
> 是**噪音**，不是视频。

---

## 修复方案总览

```
  ┌──────────────┐   appendBuffer    ┌──────────────┐
  │  YouTube 页面  │ ───────────────▶ │  page-hook   │
  │  (主世界)      │                  │  拦截分片     │
  └──────────────┘                   └──────┬───────┘
                                             │ chunk { streamKey, index, data }
                                             ▼
                                    ┌────────────────┐
                                    │    bridge      │  ← 补上 streamKey
                                    └───────┬────────┘
                                             ▼
                                    ┌────────────────┐
                                    │  service-worker│
                                    └───────┬────────┘
                                             ▼
                                    ┌────────────────┐
                                    │   registry     │  ← 按 streamKey 匹配
                                    └───────┬────────┘
                                             ▼
                                    ┌────────────────┐
                                    │   offscreen    │  ← 按 streamKey::index 去重
                                    │                │     分轨 → ffmpeg 合成
                                    └───────┬────────┘
                                             ▼
                                    ┌────────────────┐
                                    │  ffmpeg.wasm   │  -c copy 重封装
                                    └───────┬────────┘
                                             ▼
                                          单个 .mp4
```

**一句话概括**：**从「按 URL 分流」改成「按 streamKey 分流」**，
然后在最后一步把两条轨重新合到一起。

---

## 逐文件代码修改

这一节按文件逐处说明改动理由。每一处改动在 video-sniffer 里的位置见 [代码导读](04-code-tour.md)。

### 新增 `src/common/youtube.js`

一个纯函数模块，专门放 YouTube 相关的判定逻辑。
**没有副作用，可以直接在 Node 里跑**，所以能写单元测试。

| 函数 | 作用 |
|---|---|
| `src/common/youtube.js:90` 的 `isYouTubeMediaUrl` | 认出 `*.googlevideo.com/videoplayback` 地址 |
| `src/common/youtube.js:107` 的 `isYouTubePageUrl` | 认出 watch / shorts / embed / live / youtu.be 页面 |
| `src/common/youtube.js:139` 的 `videoIdFromPageUrl` | 从各种页面地址里取出视频 ID |
| `src/common/youtube.js:171` 的 `isYouTubeUmpMime` | 认出 `application/vnd.yt-ump` |
| `src/common/youtube.js:190` 的 `trackKindFromUrl` | 从 URL 的 `mime` 参数判断视频轨 / 音频轨 |
| `src/common/youtube.js:213` 的 `findFirstBox` | 在字节流里找第一个合法的 ISO-BMFF 盒 |
| `src/common/youtube.js:245` 的 `stripUmpHeader` | 剥掉 UMP 的 protobuf 头 |
| `src/common/youtube.js:268` 的 `sniffTrackKind` | 只看字节判断视频轨 / 音频轨 |
| `src/common/youtube.js:327` 的 `extractMediaPayload` | 从 UMP 响应体里取出「能喂给 ffmpeg 的字节」 |

**`sniffTrackKind` 的兜底规则值得单独说**（`src/common/youtube.js:268`）：

| 判据 | 结论 |
|---|---|
| 开头是 `1A 45 DF A3`（EBML） | 音频（YouTube 的音频是 WebM/Opus） |
| moov 盒里有 `av01`/`vp09`/`hvc1`/`avc1` … | 视频 |
| moov 盒里有 `Opus`/`mp4a`/`ac-3`/`fLaC` | 音频 |
| ftyp 的 brand 是 `M4A`/`M4B` | 音频 |
| ftyp 的 brand 是 `isom`/`mp42`/`avc1`… | 视频 |
| **都认不出来** | **按视频兜底** |

最后那条兜底是实测逼出来的：
**续传片段里只有 `moof`/`mdat`，没有 `moov`**，所以认不出编码。
不兜底的话，只有续传片段的用户就永远拿不到完整视频。

### 改 `src/content/bridge.js`

**改动 1：条目的去重键带上 `streamKey`**（`src/content/bridge.js:443`）

```js
// 修复前：只用 url
// const key = item.url;
// 修复后：
function itemKeyOf(item) {
  return item.streamKey ? item.streamKey : item.url;
}
```

**改动 2：转发分片时补上 `streamKey`**（`src/content/bridge.js:233`）

```js
streamKey: data.streamKey || '',
```

> ⚠️ **这一处是最容易漏、也最致命的一处。**
> 少了它，offscreen 收到的分片就没有流标识，
> 视频轨和音频轨的「第 0 块」会撞在一起互相覆盖，
> 表现是「录出来只有声音没有画面」，**而且不报任何错**。
> 排查这种「静默失败」花的时间比写代码多十倍。

### 改 `src/background/registry.js`

**改动：`upsert()` 先按 `streamKey` 精确匹配，再按 URL 兜底**（`src/background/registry.js:65`）

```js
let existingId = null;
if (incoming.streamKey) {
  for (const [key, item] of map) {
    if (item.streamKey === incoming.streamKey) {
      existingId = key;
      break;
    }
  }
}
// 找不到再退回按 URL 匹配
```

道理和前面 `bridge.js` 的改动 1 一样：YouTube 的两条流共用一个 blob URL，
**必须先按流标识认人**。

### 改 `src/content/page-hook.js`

这一层改了三处，是整个修复里最绕的部分。

**改动 A：分片编号按流独立**

`src/content/page-hook.js:575` 的 `sendChunk()` 里，编号的键从
`recordToken` 改成 `recordToken + '::' + streamKey`：

```js
var seqKey = recordToken + '::' + streamKey;
```

武装时也要分别初始化（`src/content/page-hook.js:1512` 和 `src/content/page-hook.js:1531`）：

```js
chunkSeq.set(armToken + '::' + armKey, 0);
chunkSeq.set(armToken + '::' + otherKey, 0);
```

> 为什么要改：两条流各自从 0 开始编号。
> 编号共用一套的话，音频的第 0 块和视频的第 0 块序号一样，
> 到 offscreen 去重时就会互相顶掉。

**改动 B：武装时把同一媒体元素上的其他轨也一起录**

`src/content/page-hook.js:1514` 起的那段：

```js
streams.forEach(function (meta, otherKey) {
  if (otherKey === armKey) return;
  if (meta.url !== data.url) return;      // 不是同一个媒体元素
  if (armed.has(otherKey)) return;         // 已经录着了
  session.streamKeys.add(otherKey);
  streamSession.set(otherKey, armToken);
  armed.add(otherKey);
  chunkSeq.set(armToken + '::' + otherKey, 0);
  // 已经缓冲在页面里的分片也补发出去
  ...
});
```

> 为什么要改：用户点「录视频」时想要的是「有画面也有声音」。
> 以前只录用户点的那一条，
> 于是 YouTube 上录出来**永远没声音**（因为用户通常点到的是视频那条）。

**改动 C：重复出现的 init 段要裁掉，不是整块丢弃**

这是本轮最难查的一个 bug，表现是：
**产物 mp4 里出现两份 `moov`，ffprobe 报「时长 ?，无画面无声音」**。

原来的判定是：

```js
// 修复前：开头是 ftyp，且前 64KB 里没有 moof  -> 当成纯 init 段，重复就整块丢掉
function isInitSegment(bytes) { ... }
```

**问题在于 YouTube 的块结构是 `ftyp + moov + moof + mdat` 合并成一块**，
`moof` 就在 64KB 内（实测 @700），
于是被判成「不是 init 段」→ 重复的 init 段**没被处理** → 成品里两份 `moov`。

新做法是**不再猜「是不是纯 init」，而是直接把重复的 `ftyp+moov` 裁掉**：

| 新函数 | 位置 | 作用 |
|---|---|---|
| `isInitLike(bytes)` | `src/content/page-hook.js:513` | 只判断「开头是不是 ftyp 盒」 |
| `initEndOffset(bytes)` | `src/content/page-hook.js:525` | 算出 `ftyp + moov` 结束在哪 |
| `markInitSeen(session, streamKey)` | `src/content/page-hook.js:552` | 记录「这条流见过 init 段没有」 |

裁剪逻辑（`captureSegment` 里）：

```js
if (session && isInitLike(bytes)) {
  if (markInitSeen(session, meta.streamKey)) {
    var cut = initEndOffset(bytes);
    if (cut > 0) {
      if (cut >= bytes.length) return;       // 纯 init 段，整块丢掉
      bytes = bytes.subarray(cut);            // 裁掉 ftyp+moov，只留媒体
    }
  }
}
```

> **为什么是「按流记」而不是一个布尔值？**
> 一次录制会话里可能有两条 fMP4 轨（理论上）。
> 如果 init 标记是会话级的，第二条轨的**第一次** init 会被误当成「重复的」裁掉，
> 那条轨就废了。所以 `markInitSeen` 用 `streamKey` 做键。

### 改 `src/offscreen/offscreen.js`

**改动 A：去重键加上 `streamKey`**（`src/offscreen/offscreen.js:1380`）

```js
// 修复前：const key = index;
// 修复后：
const key = streamKey + '::' + index;
```

**改动 B：分轨合并**（`src/offscreen/offscreen.js:753` 的 `mergeChunkTracks`）

按 `streamKey` 分组 → 组内按 `index` 排序 → 每组拼成一条完整流。

**改动 C：识别轨道类型**（`src/offscreen/offscreen.js:870` 的 `trackKindOf`）

`streamKey` 形如 `blob:xxx::video/mp4; codecs="av01"`，
取冒号后面那段的 MIME 前缀就行。

**改动 D：合成**（`src/offscreen/offscreen.js:901` 的 `finishMultiTrack`）

把两条轨写成两个文件，再用 ffmpeg 两条 `-i` 合成。
降级顺序和 DASH 路径（`runFfmpegDash`）保持一致：

| 顺序 | 做法 | 说明 |
|---|---|---|
| 1 | `-c copy` | 编码能进 MP4 时最快，画质无损 |
| 2 | `-c:v copy -c:a aac` | 音频转 AAC，兼容性最好 |
| 2b | `-c:v libx264` + `-c:a aac` | 视频重编码（**AV1 轨会跳过这条**） |
| 3 | 只留视频 | |
| 4 | 只留音频 | |
| 5 | 全部重编码 | 最慢，但最兼容 |

> ⚠️ **AV1 的重编码退路是走不通的**（内置引擎没有 AV1 **解码器**）。
> 所以遇到 AV1 时会**跳过 2b（libx264）**，
> 只靠上面两条 remux 方案出片；
> 万一连它们都失败，最后的兜底是「把两轨原样存成两个文件」。
> 详见下面的「坑二」一节。

### 改 `src/common/mime.js` 和 `src/background/net.js`

`src/common/mime.js:24` 新增：

```js
export const YOUTUBE_UMP_MIME_RE = /^application\/vnd\.yt-ump$/i;
```

并在分类（`src/common/mime.js:137`）和取扩展名（`src/common/mime.js:116`）里认它。

`src/background/net.js:128` 给条目打上 `isUmp` 标记，
`src/background/net.js:139` 决定列表里显示的标签：

```
YouTube 媒体流（UMP）
```

> 这个标签只是**提示**。UMP 那几条流**不能直接下载**
> （响应体前面还包着 protobuf 头），
> 真正能用的还是下面那两条 **MSE** 条目。
> 保留标签是为了让用户知道「网络层确实看到了媒体请求」，
> 排查问题时有用。

### 新增 `tools/check-identifiers.mjs`

这次开发踩了一个**静默失败**的坑：

```js
const GOGOGLEVIDEO_HOST_RE = /\.googlevideo\.com$/i;   // 写成了 GOGOGLEVIDEO
```

拼错一个字母 → 语法检查通过 → 运行时 `RegExp.test(undefined)` **永远返回 false** →
**不报错，只是那个功能一直没生效**。排查花了半小时。

所以加了这个工具：把源文件里的字符串、注释剥掉，
再检查每个标识符引用是否真的存在。已接入 `npm run lint`。

```
$ npm run lint
22/22 个文件语法正确
22/22 个文件标识符检查通过
```

### 新增 `test/youtube.test.mjs`

14 个单元测试，覆盖 URL 判定、UMP 剥头、轨道识别：

```
$ npm test
ℹ tests 122
ℹ pass 122
ℹ fail 0
```

---

## 踩过的四个坑

这一节记录**排查过程中走过的弯路**，每一条都花了时间。

### 坑一：产物里有两份 `moov`

**现象**：ffprobe 报「时长 ?，无画面无声音」。

**原因**：YouTube 的块是 `ftyp+moov+moof+mdat` 合并的，
而原来的「是不是纯 init 段」判定扫前 64KB 找 `moof`，
`moof` 在 64KB 内 → 判定为「不是 init」 → 重复 init 没被裁 → 两份 `moov`。

**修法**：见上面「`page-hook.js` 改动 C：重复出现的 init 段要裁掉」。

### 坑二：（**结论是错的**）「ffmpeg.wasm 不支持 AV1」

**当时的结论**：
> 内置的 ffmpeg 引擎（`@ffmpeg/core` 0.12.10）没有 AV1 支持，
> `-c copy` 会报 `Could not find codec parameters for stream 0 (Video: av1 ...)`，
> 所以碰到 AV1 就只能把两轨原样存成两个文件。

**这个结论错在哪**：
那句报错**是警告，不是致命错误** —— ffmpeg 的**退出码其实是 0**。
更关键的是，当时喂进去的 mp4 **本身是坏的**（坑一的两份 `moov`），
mov 解封装器读到第二个 `moov` 就乱了，才报「找不到 codec 参数」。

**用合法文件重测的结果**：

| 做法 | 退出码 | 产物 |
|---|---|---|
| `-c copy` | 0 | av01 视频轨 + opus 音频轨，**都在** |
| `-c:v copy -c:a aac` | 0 | av01 视频轨 + aac 音频轨，都在 |
| `-c:v libx264`（重编码） | 失败 | 内置引擎没有 AV1 **解码器** |

**修法**：
把「AV1 → 分开存两份文件」从**默认行为**降级成**兜底行为**
（只有所有合成方式都失败时才走），
并把那条错误的注释改掉（见 `src/offscreen/offscreen.js:803` 的 `isAv1Track`）。

> **教训**：看到一条报错，先确认**退出码**和**产物**，
> 不要只看日志里有没有 `error` 字样。

### 坑三：测试脚本把视频点停了

**现象**：端到端录制跑两次，产物**字节完全相同**（1,665,645 字节），
而且长度恰好等于 YouTube 初始预缓冲的 23.52 秒。

**原因**：测试脚本这样起播：

```js
const b = document.querySelector('button.ytp-large-play-button');
if (b) b.click();
v.play();
```

视频**已经在播**的时候（大播放按钮虽然不可见但还在 DOM 里），
再 `click()` 一下等于**切换成暂停**。
于是整个录制窗口都停在初始缓冲上，产物当然每次都一样。

**修法**：改用 YouTube 官方 player API：

```js
const player = document.getElementById('movie_player');
if (player && typeof player.playVideo === 'function') {
  player.mute();
  player.playVideo();
}
```

> **教训**：自动化测试里**不要用「切换型」操作**（toggle），
> 要用「幂等型」操作（playVideo 而不是点播放键）。

修好之后重测，产物长度从 23.52 秒变成 **64.69 秒**，
而且 `sent` 计数在录制窗口里持续增长（视频 44 → 200，音频 14 → 45）。

### 坑四：`Set` 没有 `reduce`

写调试输出时顺手加了个「每条流发了多少块」的统计：

```js
sent: s.streamKeys.reduce(...)   // ❌ streamKeys 是 Set
```

页面控制台直接报 `s.streamKeys.reduce is not a function`。

**修法**：`Array.from(s.streamKeys).reduce(...)`。

---

## 怎么用（面向使用者）

### 基本操作

1. 装好扩展，打开 YouTube 视频页
2. **先点播放**，让播放器缓冲几秒（缓冲区越满，录到的前缀越长）
3. 点扩展图标 → 列表里找到 **`[mse] MSE 视频流（录制片段）`**
4. 点「录制」
5. 播多久录多久，点「停止」
6. 产物是一个 **带画面带声音的 `.mp4`**

> **要选 MSE 那两条，不要选 UMP 那几条。**
> UMP 的响应体前面包着 protobuf 头，下载下来不能直接播。

### 想要 H.264 怎么办

YouTube 默认给 **AV1**。AV1 虽然是正规格式，
但**老一点的播放器和剪辑软件可能不支持**。

想要 H.264：

> 播放器右下角 **齿轮 → 画质 → 选带 "H.264" 字样的那档**（通常 360p/480p）
> → **重新加载页面** → 再录。

这样产出的 mp4 就是 `avc1`（H.264）+ Opus，兼容性最好。

### 已知的行为特点

| 现象 | 原因 | 是不是 bug |
|---|---|---|
| 录出来的长度 = 录制时长 + 初始缓冲 | 武装时会补发页面里已经缓冲的分片 | 不是 |
| 画面轨和声音轨长度可能差几秒 | 两条轨的缓冲区深度不同 | 不是 |
| 提示「成品时长只有 X 秒，缺 Y%」 | 整集比录的长，正常 | 不是 |
| 清晰度切换后画面可能断一下 | YouTube 的 ABR 换档会重建 MediaSource | 是已知限制 |

---

## 自己复现

### 复现「YouTube 走 MSE、两轨共用一个 blob URL」

```powershell
node tools/probe-youtube.mjs
node tools/probe-youtube-deep.mjs
node tools/probe-youtube-headers.mjs
```

### 复现「UMP 响应体 = protobuf 头 + ISO-BMFF」

```powershell
node tools/probe-yt-ump.mjs
node tools/probe-yt-body.mjs
node tools/probe-yt-ump-boundary.mjs
```

### 复现「端到端录制 + 产物探测」

```powershell
# 录 12 秒，并把产物拷到当前目录
node tools/probe-youtube-file.mjs "https://www.youtube.com/watch?v=rfwe5weNpLw" 12 8

# 看产物的音视频轨
node tools/probe-output.mjs "<产物路径>"

# 数真实包数量（别只看元数据时长）
node tools/probe-yt-duration.mjs "<产物路径>"
```

### 复现「录制期间分片在流动」

```powershell
node tools/probe-yt-rec.mjs "https://www.youtube.com/watch?v=rfwe5weNpLw" 8 14
```

它会逐秒打印：

```
t+1s: sent = { "…::video/mp4; codecs=av01…": 44, "…::audio/webm; codecs=opus": 14 }
t+6s: sent = { "…::video/mp4; codecs=av01…": 85, "…::audio/webm; codecs=opus": 25 }
t+7s: sent = { "…::video/mp4; codecs=av01…": 137, "…::audio/webm; codecs=opus": 36 }
```

**这两个数字在涨，就说明录制是活的。**

### 在浏览器里手动看

页面控制台（**不是**扩展的 DevTools，是网页自己的控制台）：

```js
__vsDebug.sessions()   // 当前录制会话（含每条流已发块数 sent）
__vsDebug.armed()      // 正在录制的流（streamKey）
__vsDebug.streams()    // 已知的全部流
__vsDebug.elements()   // 页面上每个媒体元素的 src / currentSrc / buffered
__vsDebug.outbox()     // 还没收到确认的分片数
```

---

## 边界与合规

本扩展在 YouTube 上的实现**只使用站点自己提供的、当前账号有权观看的普通播放地址**：

- **不**提取、**不**伪造、**不**绕过任何签名或密钥
- **不**解密 DRM 内容
- **不**修改播放器行为
- **不**规避 YouTube 的任何限制

它做的事和 B 站那条路径是同一件事（见 [B 站投稿视频下载](06-bilibili-ugc.md)）：
**在浏览器已经把媒体数据取到手之后，从 MSE 缓冲里把数据收下来**。

> 如果你所在的地区/账号本来就看不到这个视频，
> 扩展也**不会**让它变得可见——它只是把你**已经能看**的内容保存成文件。

---

## 附录：本轮改动文件清单

| 文件 | 类型 | 改动 |
|---|---|---|
| `src/common/youtube.js` | 新增 | UMP 剥头、轨道识别、URL 判定 |
| `test/youtube.test.mjs` | 新增 | 14 个单元测试 |
| `tools/check-identifiers.mjs` | 新增 | 标识符拼写检查，已接入 `npm run lint` |
| `src/content/bridge.js` | 修改 | 条目键带 `streamKey`；转发分片补 `streamKey` |
| `src/background/registry.js` | 修改 | `upsert()` 先按 `streamKey` 匹配 |
| `src/content/page-hook.js` | 修改 | 编号按流独立；武装时多轨同录；重复 init 裁剪 |
| `src/offscreen/offscreen.js` | 修改 | 去重键 `streamKey::index`；分轨合成；AV1 兜底降级 |
| `src/common/mime.js` | 修改 | 认识 `application/vnd.yt-ump` |
| `src/background/net.js` | 修改 | UMP 条目加标签 |

### 本轮新增的诊断工具

| 工具 | 作用 |
|---|---|
| `tools/probe-youtube.mjs` | 看 `<video>` 的 src、MediaSource、SourceBuffer 形态 |
| `tools/probe-youtube-deep.mjs` | 深挖 SourceBuffer / appendBuffer 调用 |
| `tools/probe-youtube-headers.mjs` | 看媒体请求的响应头 |
| `tools/probe-yt-ump.mjs` | 看 UMP 响应体长什么样 |
| `tools/probe-yt-body.mjs` | 拆 UMP 的 protobuf 头 |
| `tools/probe-yt-ump-boundary.mjs` | 找 UMP 头和 ISO-BMFF 的分界 |
| `tools/probe-yt-play.mjs` | 逐秒采样播放状态和缓冲（可加 `ext` 参数对照装扩展前后） |
| `tools/probe-yt-rec.mjs` | 录制期间逐秒看每条流发了多少块 |
| `tools/probe-youtube-file.mjs` | 端到端：录 → 查 downloads API → 探测产物 |
| `tools/probe-yt-duration.mjs` | 数真实包数量（别只看元数据时长） |
| `tools/probe-yt-av1.mjs` | 验证 ffmpeg.wasm 能不能封装 AV1 |
| `tools/probe-output.mjs` | 探测产物的音视频轨 |

## 附录：验证命令速查

测试体系、调试入口和打包流程的完整说明见 [开发与调试指南](10-dev-guide.md)。

```powershell
npm run lint          # 语法 22/22 + 标识符 22/22
npm test              # 单元测试 122/122
npm run docs:check    # 文档引用校对
npm run docs:fix      # 文档引用行号漂移时自动重定位
npm run package       # 打包
npm run verify        # 打包后自检
```
