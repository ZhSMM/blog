# 新站点适配手册

* auto-gen TOC;
{:toc}

这一页教你一件事：**遇到一个没见过的网站，怎么判断「它的视频能不能下」、「地址藏在哪里」、以及「怎么让它在本扩展里工作」。**

读者假设：完全不懂音视频、不懂前端，但会用浏览器、知道怎么装扩展。每一节都是「照着做就行」的步骤；遇到陌生的名词，先看本章末尾的「术语表」一节，不必停下来查。

在整章里的位置：这是 [章节总览](00-summary.md) 里路线 B「想给一个新站点做适配」的第二站。前面 [扩展架构](03-architecture.md) 给你判断依据（扩展在哪些地方拦数据、往哪儿存），本页给你操作步骤，[DASH 下载异常排查](09-troubleshooting.md) 给你兜底（体积不对、满屏条码这类症状的完整排查记录）；真要动手改代码了，看 [代码导读](04-code-tour.md) 和 [开发与调试指南](10-dev-guide.md)。

本章里出现的 `` `src/common/dash.js:91` `` 这类写法，**指的是 video-sniffer 项目里的文件与行号**，不是本章的页面。

---

## 一张图看懂全流程

```
        ┌────────────────────────────────────────────┐
        │  第 1 步：打开 DevTools，看 Network 面板       │
        └───────────────────┬────────────────────────┘
                            ▼
              ┌─────────────────────────┐
              │ 找到「媒体请求」了吗？      │──没有──▶ 看「什么都抓不到 / 只有 MSE 的处理」
              └───────────┬─────────────┘
                          │找到了
                          ▼
        ┌────────────────────────────────────────────┐
        │  第 2 步：判断它属于哪一类（6 种形态之一）    │
        └───────────────────┬────────────────────────┘
                            ▼
        ┌────────────────────────────────────────────┐
        │  第 3 步：如果地址不在请求里，在 JSON 接口里？│
        └───────────────────┬────────────────────────┘
                    ┌───────┴────────┐
                    ▼                ▼
                 是（playurl）      否
                    │                │
                    ▼                ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ 第 4 步：挖地址    │  │ 只有 MSE 的处理   │
        └────────┬─────────┘  └──────────────────┘
                 ▼
        ┌────────────────────────────────────────────┐
        │  第 5 步：过「四道关」——能不能下、是不是加密、│
        │          是不是占位流、下下来完整吗          │
        └───────────────────┬────────────────────────┘
                            ▼
        ┌────────────────────────────────────────────┐
        │  第 6 步：接进扩展（按类型分 5 种改法）      │
        └───────────────────┬────────────────────────┘
                            ▼
        ┌────────────────────────────────────────────┐
        │  第 7 步：验证（改完必须跑的三件事）          │
        └────────────────────────────────────────────┘
```

---

## 网页上的视频有 6 种形态

**这一步最重要。** 后面所有的判断，都是在回答「这是哪一种」。

| # | 形态 | 你在 Network 面板里看到什么 | 地址在哪 | 完整吗 |
|---|---|---|---|---|
| ① | **直链** | 一个大 `.mp4` / `.webm` 响应 | 就在请求 URL 里 | ✅ 完整 |
| ② | **HLS** | 一个 `.m3u8`，里面是一行行分片地址 | 清单里 | ✅ 完整 |
| ③ | **DASH** | 一个 `.mpd`，或者 JSON 里的 `dash` 字段 | 清单里 | ✅ 完整（要合并音视频） |
| ④ | **MSE 分片** | 一堆几百 KB 的小响应，没有清单 | 每个小响应各自的 URL | ❌ **只是缓冲** |
| ⑤ | **Blob** | 根本看不到 HTTP 请求 | 在页面的 JS 变量里 | 看情况 |
| ⑥ | **DRM 加密** | 有请求，但内容是密文 | —— | ❌ **本扩展不做** |

### 逐个讲清楚

**① 直链（最简单）**
整个视频就是一个文件，服务器直接给你。比如 `https://cdn.site.com/video.mp4`。
本扩展**开箱即用**，不用改任何代码。

**② HLS**
一个 `m3u8` 文本文件，里面每行一个分片地址：

```
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXTINF:9.9,
https://cdn.site.com/seg1.ts
#EXTINF:9.9,
https://cdn.site.com/seg2.ts
#EXT-X-ENDLIST
```

只要拿到这个 m3u8，整集就都能下 —— **不用等播放器缓冲**。

**③ DASH**
和 HLS 一样是「清单 + 分片」，但更现代。区别是 DASH 通常把
**画面和声音分成两条独立的轨道**（`.m4s` 文件），下载后要合并。

**④ MSE 分片（最容易误判的一种）**
播放器一边播一边下载，Network 面板里刷出一堆小请求。
**这是正常的网络行为，但它不是「整集地址」**。
只靠这些小分片，你只能拿到「已经缓冲的那一部分」。

> **这就是用户说「只有片段，下不了完整视频」的真正含义。**
> 他们的列表里全是 ④，而真正的 ②/③ 清单没被找到。

**⑤ Blob**
有些播放器把数据先放进内存（`new Blob([...])`），再 `URL.createObjectURL()` 造一个
`blob:https://site.com/xxxx` 的假地址交给 `<video>`。这时候 DevTools 的 Network 面板
可能什么都看不到，得去 Console 里翻页面变量。

**⑥ DRM 加密**
文件本身是密文，浏览器用解密模块（Widevine / PlayReady）在播放时解密。
**密文导出到本地就是一堆乱码。** 本扩展**不绕过**这个（红线见本章末尾的「红线」一节）。

这 6 种形态的通用背景（容器 vs 编码、轨道、清单、分片），见 [音视频基础](02-media-fundamentals.md)。

---

## 准备工具与脚本速查表

### 你已经有的：Chrome DevTools

按 `F12`（或 `Ctrl+Shift+I` / `Cmd+Option+I`）打开。

### 本项目自带的诊断脚本

这些脚本**不需要额外装任何东西**（Node 之外零依赖）。先确认 Node 装好了：

```powershell
node -v
```

应该输出 `v25.x.x` 或更高。如果没有，去 <https://nodejs.org> 下载 LTS 版。

然后在项目目录里：

```powershell
cd C:\Users\19114\Desktop\PROJECT\chrome_plugins\video-sniffer
npm install
```

> `npm install` 只会装一个东西：`@ffmpeg/core`（ffmpeg 的网页版，约 32 MB）。
> 扩展本身**零运行时依赖**，这个只是为了跑测试和诊断脚本。

### 脚本速查表

| 脚本 | 干什么 | 什么时候用 |
|---|---|---|
| `tools/list-page-apis.mjs <页面地址>` | 打开页面，列出**所有** JSON 接口，逐个检查里面有没有 DASH / durl | **第 3 步的主力工具** |
| `tools/probe-files.mjs <文件>` | 用真 ffmpeg 探测本地文件的时长/编码/分辨率/帧数 | 第 5 步「验证完整性」 |
| `tools/dump-boxes.mjs <ep_id>` | 打印 MP4 的完整盒子结构 | 判断「独立 MP4」还是「碎片」 |
| `tools/probe-durl-boxes.mjs <BV号>` | 同上，专门针对 B 站 `durl` | 同上 |
| `tools/probe-ugc-playurl.mjs <BV号>` | 打印 B 站接口的每一条轨道 | B 站专用 |
| `tools/probe-output.mjs <文件>` | 探测产物有没有画面、有没有声音、多长 | 验证下载结果 |
| `tools/smoke-test.mjs` | 无头 Chrome 跑一遍扩展全流程 | 改完代码后跑 |
| `tools/syntax-check.mjs` | 检查每个源文件语法对不对（不执行） | 改完代码先跑这个 |
| `tools/download-ugc.mjs <BV号>` | 不装扩展直接下载 B 站视频 | B 站专用 |

---

## 在 DevTools 里找到媒体请求

### 打开 Network 面板（关键设置）

1. 按 `F12` 打开 DevTools；
2. 点顶部的 **Network**（网络）标签；
3. **勾选 `Preserve log`（保留日志）** —— 不勾的话，页面跳转时记录会被清空；
4. **勾选 `Disable cache`（停用缓存）** —— 不勾的话可能命中缓存，Network 里看不到请求；
5. 点 **🚫（清空）** 按钮把旧记录清干净。

> **⚠️ 顺序很重要**：先设置，再刷新页面。
> 正确顺序是：打开 Network → 勾两个复选框 → 清空 → **刷新页面（F5）** → 播放视频。

### 用筛选按钮缩小范围

Network 面板上方有一排筛选按钮：

| 按钮 | 含义 | 什么时候点它 |
|---|---|---|
| `All` | 全部 | 不知道是什么类型时先看这个 |
| `Doc` | HTML 文档 | 找页面的初始接口 |
| `CSS` `JS` `Img` `Font` `Manifest` | 样式/脚本/图片… | 一般不用 |
| **`XHR`** | XMLHttpRequest | **找 JSON 接口（playurl）** |
| **`Fetch`** | fetch() 调用 | **同上，modern 站点多用这个** |
| **`Media`** | 媒体请求 | **找直链视频 / 分片** |
| `WS` | WebSocket | 直播流 |
| `Other` | 其它 | 兜底 |

**实用技巧**：
- 先点 `Media` 看有没有媒体请求；
- 再点 `XHR` + `Fetch` 一起看（按住 `Ctrl` 可以多选），找 JSON 接口。

### 读懂请求列表的每一列

| 列 | 怎么读 |
|---|---|
| **Name** | 文件名或接口路径。`playurl`、`video`、`master.m3u8` 这些字样很显眼 |
| **Status** | `200` 正常；`206` 部分内容（播放器分段拉取）；`403` 被拒（缺 Referer）；`(failed)` 失败 |
| **Type** | `media` / `xhr` / `fetch` / `script`… |
| **Initiator** | **是哪个脚本发起的**。点这一列会跳到源码 —— 找接口时非常有用 |
| **Size** | ⚠️ **别被骗**。播放器用 Range 分段拉取时，这里显示的是**那一段**的大小，不是整个文件 |
| **Time** | 耗时 |
| **Waterfall** | 时间轴，能看出请求的先后顺序 |

> **关于 Size 的坑（实测）**：
> B 站 `BV11HHq6uEdp` 的真实轨道文件是 17139565 字节，
> 但 Network 面板里显示成 259979 字节（1.5%）。
> 因为播放器是 `bytes=0-1048575`、`bytes=1048576-…` 这样一段段拉的。
> 本扩展专门处理了这个（`src/background/net.js:66` 的 `totalSizeFromContentRange()`，
> 从 `Content-Range: bytes 0-1048575/17139565` 里取斜杠后面的总大小）。

### 打开一个请求，看「响应」标签

选中一个请求 → 右侧（或下方）的 **Response** 标签页：

- 是 JSON → 直接能看到里面的结构（这是找地址的关键）；
- 是文本 → 能看到 m3u8 的内容；
- 是二进制 → 只能看到一堆乱码，但 **Headers 标签页依然有用**。

**Headers 标签页重点看这四个**：

| 头 | 作用 |
|---|---|
| `Content-Type` | 决定这资源是什么类型。`video/mp4` = 直链；`application/dash+xml` = DASH 清单；`application/vnd.apple.mpegurl` = HLS 清单；`application/json` = 接口 |
| `Content-Length` | 文件大小（分段响应时不可信） |
| `Content-Range` | 分段响应时的总大小（斜杠后面） |
| **`Referer`** | 有些站点没有它就 403 |

---

## 判断属于哪一类

### 决策树

```
在 Network 里找到一个疑似媒体的请求
        │
        ├─ 响应是 JSON？
        │   ├─ 里面有 video[] 且每条有 baseUrl/base_url → 「DASH 藏在 JSON 里」一节
        │   ├─ 里面有 durl[] → 「整段 MP4 藏在 JSON 里（durl）」一节
        │   └─ 里面有 urlList[] / segments[] 之类的一组地址 → 「分片清单」一节
        │
        ├─ Content-Type 是 video/* 或 audio/*，且 Size 很大（几 MB 以上）
        │   └─ ① 直链 —— 不用改任何代码
        │
        ├─ URL 以 .m3u8 / .m3u 结尾，或 Content-Type 是 mpegurl
        │   └─ ② HLS —— 不用改任何代码
        │
        ├─ URL 以 .mpd 结尾，或 Content-Type 是 dash+xml
        │   └─ ③ DASH —— 不用改任何代码
        │
        ├─ 响应第一行是 "#EXTM3U"
        │   └─ ② HLS（URL 看不出来，但内容是清单）
        │
        ├─ 响应第一行是 "<MPD"
        │   └─ ③ DASH（同样是内容判断）
        │
        ├─ 一堆几百 KB 的请求，没有清单
        │   └─ ④ MSE 分片 —— 去看「什么都抓不到 / 只有 MSE 的处理」
        │
        └─ Network 里什么都没有，但页面能播
            └─ ⑤ Blob —— 去看「什么都抓不到 / 只有 MSE 的处理」
```

### ① 直链 —— 不用改代码

特征：`Content-Type: video/mp4`，URL 以 `.mp4`/`.webm` 结尾，Size 是几 MB 级别。

**验证**：

1. 右键请求 → **Copy → Copy URL**；
2. 新标签页打开这个 URL；
3. 能直接播放 = 没问题。

**如果打不开（403）**：说明要 Referer。去 Request 标签页看原请求的 `Referer` 是什么，
照着加上就行。（本扩展自动处理这件事，见 `src/background/referer.js`。）

### ③ DASH 藏在 JSON 里（最常见的复杂情况）

**特征**：某个 XHR/Fetch 请求返回 JSON，里面有 `video` 数组，每条元素有 `baseUrl` 或 `base_url`。

**典型结构**（B 站投稿页）：

```json
{
  "code": 0,
  "data": {
    "quality": 32,
    "dash": {
      "duration": 417,
      "video": [
        { "id": 32, "width": 854, "height": 468, "codecs": "avc1.640033",
          "bandwidth": 878020, "baseUrl": "https://cdn.../xxx.m4s",
          "backupUrl": ["https://backup.../xxx.m4s"] }
      ],
      "audio": [
        { "id": 30280, "codecs": "mp4a.40.2", "bandwidth": 148052,
          "baseUrl": "https://cdn.../yyy.m4s" }
      ]
    }
  }
}
```

**注意**：同一份 JSON 里，`quality` 和 `dash` 是**平级**的（都在 `data` 下面）。
有的站点 `dash` 会藏得更深，比如 `data.video_info.dash`（B 站番剧页）。

**本扩展怎么认的**（`src/common/dash.js:91` 的 `looksLikeDash()`）：
三个条件**全部满足**才算 DASH 清单：

1. 自己带一个 `video` 数组；
2. 数组里的元素是**对象**（不是裸字符串），且能取到地址；
3. 还带 DASH 的标志字段：`audio` 数组 / `duration` / `min_buffer_time`。

> **为什么不写死路径？**
> 因为同一站点不同页面的结构完全不一样（投稿页 `data.dash`、番剧页 `data.video_info.dash`、
> PGC `result.video.dash`）。早期版本写死了 `data.dash`，结果番剧页**一条 DASH 都识别不出来**。
> 现在改成「在 JSON 树里找长得像 DASH 的那个对象」。

**怎么快速找到这个接口？** 两种办法：

**办法 A：DevTools 手工找**
1. Network → 点 `Fetch` / `XHR`；
2. 找名字里带 `playurl` / `play` / `video` / `url` / `source` 的请求；
3. 点开 Response 看有没有 `video[]` / `dash` / `durl`。

**办法 B：用本项目的脚本（推荐，快得多）**

```powershell
node tools/list-page-apis.mjs "https://目标网站的视频页地址"
```

这个脚本会自动：开一个无头 Chrome → 打开页面 → 抓下**所有** JSON 响应 →
逐个检查里面有没有 DASH 或 durl → 打印出来。

输出长这样：

```
https://api.bilibili.com/x/player/wbi/playurl
  query: bvid=BV11HHq6uEdp&cid=42431614387&fnver=0&fnval=4048&fourk=1
  DASH: 6 视频轨 / 3 音频轨, 加密轨=0
    id=32 854x468 avc1.640033 bw=878020 encrypted=false size=-
    ...
```

### 整段 MP4 藏在 JSON 里（`durl`）

**特征**：JSON 里有 `durl` 数组。

```json
{
  "data": {
    "quality": 64,
    "durl": [
      { "order": 1, "length": 416816, "size": 48631385,
        "url": "https://cdn.../42431614387-1-16.mp4" }
    ]
  }
}
```

> **⚠️ 三个必须知道的细节**（每一条都踩过坑）：
>
> 1. **`length` 的单位是毫秒**，不是秒。`416816` = 416.8 秒。
>    当成秒用会让时长变成 116 小时。
> 2. **`durl` 通常只有 1 项，而那一项就是整个视频**。
>    实测 `BV11HHq6uEdp` 的 `durl` 只有 1 段，46.4 MB，盒子结构
>    `ftyp(32) moov(517599) free(8) mdat(48113746)` —— 是**独立完整的 MP4**，
>    不是「残缺的片段」。
> 3. **如果真有多段，不能按字节拼**。每段都自带 `moov`，
>    按字节拼起来播放器只会读到**第一段**。必须用 ffmpeg 的 concat 分离器。
>
> 本扩展的处理：`src/common/download-check.js:79` 的 `looksLikeStandaloneMp4()`
> 扫前几个盒子，有 `ftyp+moov+mdat` 且**没有** `moof/styp` → 判为独立 MP4，
> 走 ffmpeg 合并；否则按 fMP4 碎片处理。

**怎么验证「那一项是不是整个视频」**：

```powershell
node tools/probe-durl-boxes.mjs <BV号>
```

会输出：

```
durl 段数 = 1
  [0] order=1 length=416816 (416.8s) size=48631385 (46.4 MB) https://...
第 0 段：HTTP 200  46.38 MB
  盒子结构: ftyp(32) moov(517599) free(8) mdat(48113746)
```

有 `moov` 又有 `mdat`、没有 `moof` → **独立完整 MP4，拿到就是成品**。

`durl` 和 DASH 两条路线的实测对比，见 [B 站投稿视频下载](06-bilibili-ugc.md)。

### 分片清单（接口直接给一组地址）

**特征**：JSON 里有个数组，里面是一组同一域名、带媒体后缀的地址。

```json
{ "data": { "urlList": [
    { "url": "https://cdn.site.com/1.ts" },
    { "url": "https://cdn.site.com/2.ts" }
] } }
```

**本扩展怎么认的**（`src/common/playlist.js:79` 的 `collectSegmentArray()`）——
刻意保守，四条全满足才认：

1. 数组至少 3 个元素；
2. 每个元素都能取到一个 URL 字符串；
3. 所有 URL **同源**；
4. **必须有一个强信号**：数组名像分片数组（`urlList`/`segList`/`segments`/`chunkList`…），
   **或者**半数以上的 URL 带媒体后缀（`.ts`/`.m4s`/`.mp4`/`.webm`…）。

> **为什么这么保守？**
> v1.4.0 只要求「≥3 个同源 URL」，结果 B 站番剧页的「相关推荐」列表
> （`result.season`，20 个剧集链接）被当成了整集分片，
> popup 里冒出一条假的「分片清单（20 片）」—— 用户点「下载整集」拿回来的是 20 个网页。
>
> **宁可漏判也不能误判**：漏判只是少一个入口，误判会让用户下载一堆垃圾。

---

## 过「四道关」

找到地址 ≠ 能下。**这四道关要一道一道过**，每过一关都有明确的验证手段。

### 关 1：地址能不能访问？

很多 CDN 会校验 `Referer` 或 `Cookie`。

**手工验证**：

```powershell
curl -L -o 测试.mp4 "<地址>" -H "Referer: https://目标网站/视频页地址" -H "User-Agent: Mozilla/5.0"
```

- 下到几 MB 的正常文件 → ✅ 通过；
- 下到几百字节的 HTML → ❌ Referer 不对或缺 Cookie；
- 403 → 同上。

**看返回的 Content-Type**：

```powershell
curl -sI "<地址>" -H "Referer: https://目标网站/视频页地址"
```

| 返回 | 含义 |
|---|---|
| `content-type: video/mp4` | 正常 |
| `content-type: text/html` | **错误页**，别存成 mp4 |
| `HTTP/1.1 403` | 被拒 |

> **本扩展踩过的坑**：`chrome.downloads.download()` **不带 Referer**
> （Referer 是 fetch 的禁止头，扩展也没法给下载请求设置它；
> `declarativeNetRequest` 的规则同样覆盖不到下载请求 —— 实测三种规则写法全部无效）。
> 结果 CDN 返回 403 错误页，Chrome 还把它当「下载完成」存成了 `.mp4`。
> 扩展的解法：下载走自己的 fetch 引擎，并用 DNR 在网络层注入 Referer
> （`src/background/referer.js`）。

### 关 2：是不是 DRM 加密流？

**清单层面看**：轨道对象里有没有 `widevine_pssh` 字段（有值 = 加密）。
本扩展：`src/common/dash.js:334` 的 `isEncryptedTrack()`。

**文件层面看**（更可靠）：下载下来扫盒子，看有没有 `pssh` / `encv` / `enca` / `senc`。
本扩展：`src/common/dash.js:507` 的 `inspectTrackBytes()`。

```powershell
node tools/dump-boxes.mjs <ep_id>
```

> **注意**：B 站的**音轨**没有 `widevine_pssh` 字段，可文件里照样有 `enca`/`senc`。
> 所以只看清单会漏判，**一定要看文件**。

**如果确认是加密流 → 停。** 见本章末尾的「红线」一节。

### 关 3：是不是占位流？

「占位流」= 站点给没权限的访客返回的**假流**：时长对、分辨率对、编码对，
但画面是糊的/乱的，码率低得离谱。

**判据是 bpp（bits per pixel per frame，每像素每帧多少比特）**：

| 类型 | 码率 | bpp |
|---|---|---|
| 正常 1080P | 2~6 Mbps | 0.04 ~ 0.10 |
| 正常 360P | 0.3~0.8 Mbps | 0.05 ~ 0.12 |
| **占位流** | ~100 kbps | **~0.002**（差两个数量级） |

阈值：**bpp < 0.01 判为占位流**（`src/common/dash.js:384` 的 `PLACEHOLDER_BPP`）。

```powershell
node tools/probe-files.mjs test\downloads\某个文件.mp4
```

输出里的 `video` 和 `bytes` 就能算出来。

> **为什么不能只看清单？**
> 清单里的 `bandwidth` 是「声明值」，服务器真正发过来的字节数才是事实。
> 所以扩展下载完还会用实际字节数再判一次
> （`src/common/dash.js:413` 的 `isPlaceholderByBytes()`）。

### 关 4：下下来的东西完整吗？

**三个检查一起做**：

```powershell
node tools/probe-files.mjs "test\downloads\下下来的文件.mp4"
```

看输出：

| 字段 | 期望 | 不对说明 |
|---|---|---|
| `duration` | 和页面/API 说的时长接近（差 < 2%） | 短了 = 下到一半或只录了缓冲部分 |
| `video` | 非 null | null = 只有声音没画面（或反之） |
| `audio` | 非 null | null = 只下了视频轨 |
| `frames` | ≈ duration × 帧率 | 差太多 = 缺帧 |

**再扫盒子**：

```powershell
node tools/dump-boxes.mjs <ep_id>
```

| 看到什么 | 含义 |
|---|---|
| `ftyp` + `moov` + `mdat` | ✅ **独立完整 MP4**，可以直接播 |
| 出现 `moof` | ⚠️ fMP4 碎片，需要拼接/合并 |
| `moov` 在**最后** | ⚠️ 文件不完整（moov 没写进去） |

---

## 把新站点接进扩展

### 先判断：真的需要改代码吗？

| 站点情况 | 要改吗 |
|---|---|
| ① 直链 | **不用** |
| ② HLS（`.m3u8`） | **不用** |
| ③ DASH（`.mpd` 文件） | **不用** |
| ③' DASH 藏在 JSON 里，但结构标准 | **通常不用**（扩展会自动在 JSON 树里找） |
| ④ 只有 MSE 分片，没有清单 | **要改**（见「情况 E：只有 MSE 分片」一节） |
| ⑤ Blob | **要改**（见「情况 E：只有 MSE 分片」一节） |
| 接口需要额外参数（如 cid）才能拿到地址 | **要改**（见「情况 F：站点专用接口」一节） |
| 字段名很特殊（不是 `baseUrl`/`base_url`/`url`/`src`…） | **要改**（见「情况 D」一节） |

### 情况 A/B/C：不用改代码

扩展的识别逻辑是**通用的**：

- **直链**：`src/common/mime.js:124` 的 `classify()` 按 Content-Type 和扩展名分类；
- **HLS**：`src/common/playlist.js:28` 的 `playlistKind()` 看 mime 和 `.m3u8` 后缀；
- **DASH**：`src/common/dash.js:123` 的 `findDash()` 在 JSON 树里搜。

**你要做的只是验证**：

1. 装上扩展，打开目标页面，播放视频；
2. 看 popup 里有没有出现对应的条目；
3. 有的话，点「下载」，看产物对不对（过「四道关」那四关）。

**如果没出现**，按「情况 D：改 `page-hook.js` 的字段名识别」往下走。

### 情况 D：改 `page-hook.js` 的字段名识别

**症状**：popup 里只有「缓冲片段」，没有 DASH 条目，但你确信接口返回了 DASH。

**原因**：轨道的地址字段名不在扩展认识的那几个里。

扩展认识这些（`src/common/dash.js:41`）：

```js
const TRACK_URL_KEYS = ['baseUrl', 'base_url', 'url', 'src', 'main_url', 'mainUrl'];
```

备用地址（镜像）认识这些（`src/common/dash.js:44`）：

```js
const TRACK_BACKUP_KEYS = ['backupUrl', 'backup_url', 'backupUrls', 'backup_urls'];
```

**如果你的站点用的是别的名字**（比如 `play_url`、`file_url`、`video_url`）：

**第 1 步**：改 `src/common/dash.js` 的 `TRACK_URL_KEYS`，加上你的字段名。

**第 2 步**：加一条测试，证明改动有效。打开 `test/dash.test.mjs`，加：

```js
test('认得自定义的轨道地址字段', () => {
  const json = {
    data: {
      dash: {
        duration: 100,
        video: [{ id: 32, width: 1280, height: 720, codecs: 'avc1', bandwidth: 1000,
                   play_url: 'https://cdn.site.com/v.m4s' }],
        audio: [{ id: 30280, codecs: 'mp4a.40.2', bandwidth: 128,
                  play_url: 'https://cdn.site.com/a.m4s' }],
      },
    },
  };
  const dash = findDash(json);
  assert.ok(dash, '应该能找到 DASH');
  assert.equal(dash.videos[0].url, 'https://cdn.site.com/v.m4s');
});
```

**第 3 步**：跑测试确认通过。

```powershell
npm test
```

> ⚠️ **重要**：`src/content/page-hook.js` 是 **classic script**（不能 import ES module），
> 所以它里面有一份**内联镜像**的同样逻辑。
> 改了 `src/common/dash.js` 之后，**必须同步改镜像**，否则页面钩子那边不生效。
> 改完跑 `npm test` —— 里面有一条**防漂移比对**的测试会帮你抓住不同步。

### 情况 E：只有 MSE 分片 —— 做一个「补抓清单」的入口

**症状**：页面在放视频，Network 里只有一堆小分片，没有清单接口。
但你能在 DevTools 里找到一个接口，返回 JSON 里有 `video[]`/`durl`。

**思路**：让扩展**自己**去问那个接口要一份清单，插回列表。

**参照实现**：`src/background/bilibili-alt.js` 的 `fetchUgcManifest()`
（`src/background/service-worker.js:425` 处理 `MSG.FETCH_MANIFEST`）。

**要改 4 个地方**：

| # | 文件 | 改什么 |
|---|---|---|
| 1 | `src/common/constants.js` | 加一条 `MSG.FETCH_MANIFEST = 'vs:fetch-manifest'` |
| 2 | `src/background/xxx.js` | 写一个 `fetchManifest(pageUrl, log, tabId)`：调接口 → 解析 → 返回清单 |
| 3 | `src/background/service-worker.js` | 加一个 `case MSG.FETCH_MANIFEST:` 分支，把清单插进 registry |
| 4 | `src/popup/popup.html` + `popup.js` | 加一个按钮，点了就发 `MSG.FETCH_MANIFEST` |

**关键的三个细节**：

1. **请求要走「内容脚本代发」这条路**。
   实测：B 站接口在扩展页面 / Service Worker 里发 → **6/6 被风控挡**（返回 `v_voucher`）；
   在内容脚本（ISOLATED world）里发 → **0/6 被挡**。
   原因是内容脚本的 origin 就是**页面自己的地址**，请求发出去和站点自己的 XHR 长得一样。

2. **要带 `Referer`**，还要**退避重试**。风控是**按次**的，不是永久的。

3. **接口需要额外参数时要先补齐**。
   比如 B 站的播放地址接口必须带 `cid`（只给 `bvid` 报 `code=-400 请求错误`），
   所以流程是：`bvid` → 查详情接口拿 `cid` → 再去要播放地址。

### 情况 F：站点专用接口 —— 单独写一个模块

如果某个站点需要「查详情 → 拿 cid → 取地址」这种多步流程，
**别塞进 `page-hook.js`**，单独开一个文件（比如 `src/background/xxx-alt.js`）。

**为什么**：
- `page-hook.js` 是 classic script，不能 import，写长了很难维护；
- 站点专用逻辑和通用逻辑混在一起，改通用逻辑时容易碰坏站点专用逻辑。

**照着 `src/background/bilibili-alt.js` 的结构写**：
- 纯函数放 `src/common/`（能单测）；
- 网络调用放 `src/background/`；
- 在 `src/background/service-worker.js` 里 import 并加消息分支。

**必须写单元测试**，照着 `test/bilibili-alt.test.mjs` 的结构：

```js
test('从页面地址取 BV 号', () => {
  assert.equal(bvidFromPageUrl('https://www.bilibili.com/video/BV11HHq6uEdp/'), 'BV11HHq6uEdp');
});

test('在 JSON 树里找 durl', () => {
  const durl = findDurl({ data: { durl: [{ url: 'https://x/1.mp4' }] } });
  assert.equal(durl.length, 1);
});
```

> **⚠️ 单测里千万别真的联网**！
> `test/bilibili-alt.test.mjs` 里的 `fakeContentScript()` 专门把 `globalThis.fetch` 打掉，
> 就是为了防止单测偷偷去请求真实接口（网络一慢，测试就超时；接口一变，测试就假失败）。
> 你写新测试时也要这么干。

各文件之间的职责划分，见 [代码导读与项目结构](04-code-tour.md)；日常改代码的完整流程，见 [开发与调试指南](10-dev-guide.md)。

---

## 验证（改完必须做的三件事）

### 第一件事：语法检查（秒级）

```powershell
npm run lint
```

期望输出：`21/21 个文件语法正确`。

> **⚠️ 为什么必须先跑这个？**
> 这个项目踩过一个非常隐蔽的坑：编辑工具在长文件上偶尔会把两行粘成一行
> （比如 `renderFullDownload(visible)` 变成 `renderFullDownloadvisible)`）。
> **这种错误语法是合法的**，lint 查不出来，运行时才炸。
> 所以项目另有一个专门的扫描器：

```powershell
node tools/scan-merged-lines.mjs
```

### 第二件事：单元测试（秒级）

```powershell
npm test
```

期望：`tests 108 / pass 108 / fail 0`。

### 第三件事：端到端（分钟级，真开浏览器真下载）

```powershell
npm run smoke
```

或者针对具体站点：

```powershell
npm run test:bili -- "https://www.bilibili.com/video/BV11HHq6uEdp/"
```

期望看到这样的输出：

```
PASS  a mp4 was produced
PASS  没有肉车，只有怂人！_468p.mp4 decodes with video AND audio
PASS  没有肉车，只有怂人！_468p.mp4 duration matches the API (416.82s vs 417s)
```

**只有这三步全绿，才算改完。**

---

## 什么都抓不到 / 只有 MSE 的处理

### 情况：Network 面板里什么都没有

**检查 1：是不是缓存？**
勾上 `Disable cache`，刷新页面。

**检查 2：是不是在 Service Worker 里发的请求？**
DevTools → Application → Service Workers → 勾上 **「Bypass for network」**，
或者在 Service Worker 的调试窗口里看 Network 标签页。

**检查 3：是不是 WebSocket 传的？**
Network → 点 `WS` 标签 → 看 Messages 面板里有没有二进制数据流。

**检查 4：是不是 WebAssembly 加密了？**
有些站点用 WASM 做混淆，地址是运行时算出来的。这时候：
- 看 `Initiator` 列，能找到算地址的那个脚本；
- 在 Sources → `{}` (Sources) 里打断点，或者用 `debugger` 语句。

### 情况：只有 blob 地址

在 Console 里执行：

```javascript
// 列出页面里所有的 <video> 和 <audio> 元素
document.querySelectorAll('video, audio').forEach((el, i) => {
  console.log(i, el.src, el.currentSrc);
});
```

如果 `src` 是 `blob:...`，说明数据在内存里。

**再试**：把 `URL.createObjectURL` 打个补丁，在它被调用时把 Blob 存下来：

```javascript
// 在 Console 里粘贴执行（要在页面加载前执行效果最好）
// → DevTools 打开时，Console 会提示 "Warning: Don't paste code you don't understand"
const _orig = URL.createObjectURL.bind(URL);
window.__blobs = [];
URL.createObjectURL = (obj) => {
  if (obj instanceof Blob) {
    window.__blobs.push(obj);
    console.log('捕获 Blob:', obj.size, '字节', obj.type);
  }
  return _orig(obj);
};
```

然后刷新页面、播放视频，再执行：

```javascript
window.__blobs.forEach((b, i) => {
  console.log(i, b.type, b.size);
  // 文本类型（m3u8/mpd）可以直接读出来
  if (b.type.includes('mpegurl') || b.type.includes('dash') || b.type.includes('text')) {
    b.text().then((t) => console.log(t.slice(0, 2000)));
  }
});
```

> **本扩展怎么处理的**：`src/content/page-hook.js` 会在 `URL.createObjectURL` 被调用时
> 拦截 Blob；如果是文本类型，就用 `segmentsFromPlaylistText()`
> （`src/common/playlist.js:188`）把里面的分片地址解析出来。
> 这就是为什么有些站点的视频 popup 里能直接看到「HLS」条目。

### 情况：找到了清单，但下载下来是乱的

按顺序排查：

1. **是不是有加密**（「四道关」里的关 2）；
2. **是不是编码不兼容**（HEVC / AV1 塞进 MP4 后老播放器显示满屏条码）；
3. **是不是 durl 多段被按字节拼了**（见「整段 MP4 藏在 JSON 里（`durl`）」一节的细节 3）；
4. **是不是 Referer 缺失**（「四道关」里的关 1）。

---

## 调试小抄

### 打开扩展的调试开关

**设置页** → 勾上「调试日志」。

之后：

- popup 右下角会显示 ffmpeg 核心的状态；
- Service Worker 的 console 会有详细日志。

**Chrome 里怎么看 Service Worker 的 console**：
`chrome://extensions/` → 找到本扩展 → 点「Service Worker」链接 → 打开的是 DevTools。

### 页面主世界的调试入口

在视频页面的 **Console** 里：

```javascript
__vsDebug.sessions()   // 当前的 MediaSource 会话
__vsDebug.armed()      // 哪些流正在录制
__vsDebug.streams()    // 发现的所有流
__vsDebug.elements()   // 页面上的 video/audio 元素
__vsDebug.outbox()     // 待上报的消息队列
```

### 症状速查表

| 症状 | 最可能的原因 | 怎么确认 |
|---|---|---|
| popup 完全空 | 扩展没装上 / 没启用 | `chrome://extensions/` 看状态 |
| 只有「缓冲片段」 | 没抓到清单接口 | 用 `tools/list-page-apis.mjs` 确认接口存在 |
| 有 DASH 条目但下载没声音 | 只下了视频轨 | 看条目是不是「单条轨道」而不是「DASH 视频+音频」 |
| 文件几百字节 | CDN 返回了 403 错误页 | curl 加 Referer 试 |
| 文件只有几 MB，时长却很长 | 占位流 | 算 bpp |
| 播放满屏条码 | 加密流 或 HEVC/AV1 不兼容 | 扫盒子看有没有 `pssh`/`encv` |
| 视频只有开头一小段 | 多段 durl 被按字节拼了 | 扫盒子看有没有 `moof` |
| 时长显示成 116 小时 | `durl.length` 当成秒了 | 毫秒 ÷ 1000 |
| 番剧页点单轨报 403 | 轨道和清单对不上号 | 见 [DASH 下载异常排查 · 番剧页「点单轨下载 403」的四个根因](09-troubleshooting.md) |
| 接口返回 `v_voucher` | B 站风控 | 改用内容脚本代发 + 退避重试 |

更细的按症状调试方法，见 [开发与调试指南](10-dev-guide.md)。

---

## 红线

这几件事**本扩展不做，也不要做**：

| ❌ 不做 | 为什么 |
|---|---|
| 绕过 DRM / 提取解密密钥 | 涉及版权保护机制，绕过属于侵权行为 |
| 伪造/提升账号权限 | 清晰度本来就按账号给，扩展只是如实使用 |
| 修改播放器行为 | 一改就可能破坏站点的正常功能 |
| 绕过付费墙 | 同上 |

**扩展做的**：只使用站点自己提供的、**当前登录账号有权观看**的普通播放地址。
遇到加密流就明确告诉用户「这是加密流，下载下来播不了」，而不是想办法破解。

---

## 术语表

| 词 | 白话解释 |
|---|---|
| **轨道（track）** | 一条独立的流。视频轨只有画面，音频轨只有声音 |
| **DASH** | 一种把画面和声音分开放的流媒体格式。`.mpd` 是它的清单 |
| **HLS** | 苹果的流媒体格式。`.m3u8` 是它的清单 |
| **MSE** | Media Source Extensions。浏览器边播边下用的机制 |
| **清单（manifest/playlist）** | 写明了整集所有流地址的文件。**有清单就能整集下载** |
| **分片（segment）** | 一小段数据。`.ts` / `.m4s` |
| **fMP4** | 分片版 MP4。特征是文件里有 `moof` 盒子，必须拼起来才能播 |
| **独立 MP4** | 自带 `moov`（索引）的完整 MP4。**拿到就能播** |
| **moov / mdat / ftyp** | MP4 的三种盒子。`moov`=索引，`mdat`=数据，`ftyp`=文件类型 |
| **Referer** | 告诉服务器「你是从哪个页面过来的」。很多 CDN 强制要求 |
| **DRM / Widevine** | 数字版权保护。浏览器在播放时解密，导出来是密文 |
| **占位流** | 站点给没权限的人返回的假流。参数都对但画面是糊的 |
| **bpp** | 每像素每帧多少比特。判断占位流的关键指标（< 0.01 就是占位流） |
| **v_voucher** | B 站风控返回的人机验证凭证。看到了就要退避重试 |
| **cid / bvid** | B 站给视频/每一集分配的内部编号。播放地址接口必须带 cid |

更完整的名词解释，见 [音视频基础](02-media-fundamentals.md)。

---

## 命令速查

```powershell
# ---- 环境 ----
node -v                                   # 确认 Node 装好了
npm install                               # 装 @ffmpeg/core（只有测试/诊断需要）
cd C:\Users\19114\Desktop\PROJECT\chrome_plugins\video-sniffer

# ---- 诊断新站点 ----
node tools/list-page-apis.mjs "https://目标页面"      # 列出页面所有 JSON 接口，找出 DASH/durl
node tools/probe-files.mjs <文件>                    # 探测产物的时长/编码/分辨率/帧数
node tools/dump-boxes.mjs <ep_id>                    # 打印 MP4 盒子结构

# ---- B 站专用 ----
node tools/probe-ugc-playurl.mjs BV11HHq6uEdp       # 三种 fnval + 每条轨道 + qn 上限
node tools/probe-durl-boxes.mjs BV11HHq6uEdp         # durl 的盒子结构
node tools/download-ugc.mjs BV11HHq6uEdp            # 不装扩展直接下载（整段 MP4）
node tools/download-ugc.mjs BV11HHq6uEdp --mode dash # DASH 模式
node tools/download-ugc.mjs BV11HHq6uEdp --dry-run   # 只看清单不下

# ---- 改完代码的三道验证 ----
npm run lint                              # 语法检查（21/21）
npm test                                  # 单元测试（108/108）
node tools/scan-merged-lines.mjs          # 扫「两行粘成一行」
npm run smoke                             # 端到端
npm run test:bili -- "<页面地址>"          # 针对具体站点

# ---- 打包 ----
npm run package                           # 生成 video-sniffer-vX.Y.Z.zip
npm run verify                            # 解压 → 装到 Chrome → 确认能跑
```

---

## 相关页面

| 页面 | 什么时候看 |
|---|---|
| [代码导读与项目结构](04-code-tour.md) | 逐文件逐函数的代码导读；不知道某个函数在哪、干什么时查它 |
| [B 站投稿视频下载](06-bilibili-ugc.md) | B 站投稿视频的完整分析（durl / DASH 两条路线实测对比） |
| [B 站番剧 DASH 接口](05-bilibili-bangumi.md) | B 站番剧播放地址接口详解 |
| [DASH 下载异常排查](09-troubleshooting.md) | 「体积偏小 + 满屏条码」的完整排查记录 |
| [音视频基础](02-media-fundamentals.md) | 概念入门：视频文件到底是什么、扩展凭什么能下到视频 |
| [开发与调试指南](10-dev-guide.md) | 开发者的完整参考：架构、消息协议、踩坑清单 |
