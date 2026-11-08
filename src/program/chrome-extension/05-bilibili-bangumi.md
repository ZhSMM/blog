# B 站番剧 DASH 接口

* auto-gen TOC;
{:toc}

这一页回答一个问题：**番剧的完整音视频地址到底从哪来，扩展又是怎么把它拿到的。** 面向零基础：读完你不但能看懂扩展在番剧页上干了什么，还能自己动手把一集番剧下载下来。在整章里的位置，这是 [章节总览](00-summary.md) 里路线 C「某个站点下不动」的第一站——番剧下载相关的问题看本页；同样的 DASH 接口在投稿页上怎么用，见 [B 站投稿视频下载](06-bilibili-ugc.md)；如果你现在遇到的是「体积不对 / 满屏条码 / 403」这类症状，去 [DASH 下载异常排查](09-troubleshooting.md)；想把这一套做法搬到别的站点上，看 [新站点适配手册](08-new-site-playbook.md)。

---

## 先说结论：三句话

1. 番剧网页播放器向 B 站要播放地址，用的是这个接口：
   `https://api.bilibili.com/ogv/player/pre/check/drm`
2. 这个接口返回一份**「轨道清单」**：里面有几条视频轨、几条音频轨，每条都是一个 CDN 地址。扩展要做的事情，就是找到这份清单、把地址取出来、下载、合并成一个 MP4。
3. **但是**：这个接口是「DRM 协商」接口（名字里的 `drm` 不是白写的）。它给未登录/无权限的访客返回的是**占位清单**——指向别人的文件、码率低到离谱、画面是乱的。扩展因此改用另一个普通接口 `x/player/wbi/playurl` 取地址（详见本章「扩展的修法：换普通播放接口」一节）。

---

## 地址到底藏在哪

### 为什么在网页里找不到视频地址

打开 B 站番剧页，用鼠标右键 `<video>` 标签，复制地址，得到的是：

```
blob:https://www.bilibili.com/8b6f4f8c-8853-499a-a987-af7f21d0d352
```

这个 `blob:` 地址**不是**视频文件，它只是浏览器内存里的一块「临时把手」。

真实流程是这样的：

```
网页上的 <video> 标签
        │  src = blob:...   （只是个句柄）
        ▼
MediaSource（浏览器的“流媒体盒子”）
        │  播放器不断往里塞「一小段一小段」的二进制数据
        ▼
真正的视频数据来自 CDN（bilivideo.com 之类的域名）
```

所以：

- **读 DOM** 拿不到地址（只有 blob）；
- **读网络请求**能拿到地址（CDN 请求的 URL 就是地址）。

本扩展两条路都走：网络嗅探 + 页面钩子。

### DASH 是什么：画面和声音是分开的

普通视频文件（MP4）里，画面和声音是**打包在一起**的。但流媒体网站更喜欢用 **DASH**（Dynamic Adaptive Streaming over HTTP）：

- **视频轨**：只有画面，没有声音（`.m4s` 文件）
- **音频轨**：只有声音，没有画面（`.m4s` 文件）

播放器在运行时把两条轨**同步**播放（一条负责画面、一条负责声音）。

**这就是「DASH 条目」要下载两条轨、再合并成一个 MP4 的原因。**

> 番剧的 `.m4s` 文件其实是「分片 MP4」（fMP4）：
> 文件开头有 `ftyp`（文件类型）、`moov`（索引信息），
> 后面是很多段 `moof` + `mdat`（每段一块画面数据）。

容器、编码、轨道这些词的完整定义，见 [音视频基础](02-media-fundamentals.md)。

### 番剧播放器做的四件事

```
① 打开番剧页，前端渲染出播放器
        ▼
② 播放器向 B 站要地址（就是本章的主角：ogv/player/pre/check/drm）
        ▼
③ 接口返回一份轨道清单（几条画质 + 几条音轨）
        ▼
④ 播放器挑一条视频轨 + 一条音频轨，用 Range 请求一段段从 CDN 取数据，
   喂给 MediaSource，<video> 就开始播了
```

扩展要做的事情，和 ②③ 一样：**把那份清单拿到手**。只不过扩展拿它是为了**下载**，而不是播放。

---

## 番剧用的接口：`ogv/player/pre/check/drm`

### 实际请求长什么样（实测抓包）

番剧页面发出的请求（用 DevTools 抓的）：

```http
GET https://api.bilibili.com/ogv/player/pre/check/drm?drm_tech_type=2
Referer: https://www.bilibili.com/bangumi/play/ep3854802
Accept: application/json, text/plain, */*
```

**但是**：光这样调，返回的**不一定是你要的那一集**。实测（2026-11）：只带 `?drm_tech_type=2` 时，接口可能命中 CDN 缓存，返回的是别的集甚至别的剧的地址。

👉 **所以手动调用时一定要把 `ep_id` 带上：**

```http
GET https://api.bilibili.com/ogv/player/pre/check/drm?ep_id=3854802&drm_tech_type=2
Referer: https://www.bilibili.com/bangumi/play/ep3854802
```

### 参数说明

| 参数 | 必填 | 含义 |
|---|---|---|
| `ep_id` | **是** | 番剧集号。番剧页地址 `/bangumi/play/ep3854802` 里的那个数字。 |
| `drm_tech_type` | 否 | 播放器支持哪种加密技术。`2` = Widevine。**不带这个参数接口会直接报 `-400 请求错误`**（实测）。 |

`Referer` 头也必须有，否则 B 站会拒（403）。

### 为什么名字里有 `drm`

`drm` = Digital Rights Management（数字版权管理）。

这个名字是**如实**的：这个接口用来做**加密能力协商**——播放器告诉服务器「我支持 Widevine」，服务器据此决定给什么形式的流。

**注意边界**：本扩展**不会**、也**不应该**破解任何加密。扩展的做法只是——**换一个本身就提供未加密流的普通接口**（见本章「扩展的修法：换普通播放接口」一节）。

---

## 返回的 JSON 逐字段解读

番剧接口的返回（实测，ep3854802，已省略长地址）：

```jsonc
{
  "code": 0,            // 0 = 成功；-400 = 参数不对
  "message": "success",
  "ttl": 1,
  "data": {
    "video_info": {
      "fnval": 12240,              // 想要哪些格式的位掩码（12240 含 DASH）
      "type": 2,
      "quality": 16,               // ★ 当前给访客播放的画质（16 = 360P）
      "format": "flv360",          // 当前格式
      "timelength": 1440063,       // ★ 总时长（毫秒）= 24分00秒
      "video_codecid": 7,          // 7 = H.264
      "support_formats": [         // ★ 这集**有**哪些画质可选
        { "quality": 112, "format": "hdflv2", "description": "高清 1080P+" },
        { "quality": 80,  "format": "flv",    "description": "高清 1080P" },
        { "quality": 64,  "format": "flv720", "description": "高清 720P" },
        { "quality": 32,  "format": "flv480", "description": "清晰 480P" },
        { "quality": 16,  "format": "flv360", "description": "流畅 360P" }
      ],
      "dash": {
        "duration": 1441,           // ★ 时长（秒）
        "min_buffer_time": 1.5,
        "video": [ /* 见下 */ ],
        "audio": [ /* 见下 */ ]
      },
      "drm_type": "widevine",       // ★ 有值 = 这集走的是 DRM 通道
      "drm_tech_type": 2,
      "format_panel": { /* 播放器右侧清晰度面板的数据 */ }
    }
  }
}
```

### 一条轨道长什么样

```jsonc
{
  "id": 112,                        // 画质编号（和 support_formats.quality 对应）
  "base_url": "https://upos-....m4s?e=ig8...",  // ★ 主地址
  "backup_url": [                   // ★ 备用地址（镜像），第一个挂了换第二个
    "https://cn-hbwh-cm-01-02.bilivideo.com/....m4s?e=ig8..."
  ],
  "bandwidth": 121552,              // 码率（bps）—— ★ 这里有个大坑，见本章「加密与占位流」
  "mime_type": "video/mp4",
  "codecs": "avc1.640032",          // 编码：avc1=H.264, hvc1=HEVC, av01=AV1
  "width": 1920,
  "height": 1080,
  "frame_rate": "25",
  "codecid": 7,
  "md5": "...",
  "size": 21883679,                 // 文件字节数
  "widevine_pssh": "AAAAIGZ0..."    // ★ 有值 = 这条流是加密的
}
```

音频轨字段基本一样，只是没有 `width/height`。

### 三个必须记住的字段

| 字段 | 作用 | 为什么重要 |
|---|---|---|
| `quality` | 当前授权画质 | 没权限时你会拿到**占位清单**；这个字段告诉你站点认为你该看哪一档 |
| `bandwidth` | 码率 | 用来判断这条流是不是「占位流」——1080P 只有 121 kbps 显然不对 |
| `widevine_pssh` | DRM 保护信息 | 有值 = 画面数据是密文，下载下来播不了 |

---

## 扩展是怎么用上它的：代码链路

### 五步流程

下面流程图里的 `src/...` 路径，指的都是 **video-sniffer 项目里的文件**，不是本章的页面。

```
① 页面 MAIN world 钩子拦截 fetch / XHR
        │  src/content/page-hook.js
        ▼
② 判断这个 JSON 是不是「媒体清单」，解析出 DASH 轨道
        │  src/common/dash.js（页面钩子里有一份镜像）
        ▼
③ 通过 postMessage 交给隔离世界的桥接脚本
        │  src/content/bridge.js
        ▼
④ 后台登记成一条「DASH 视频+音频」条目
        │  src/background/service-worker.js → src/background/registry.js
        ▼
⑤ 用户点「下载」：选轨 → 取流 → ffmpeg 合并 → 存盘
           src/background/downloader.js → src/offscreen/offscreen.js
```

这条链路的全貌（五个执行上下文之间怎么传消息）见 [扩展架构：五个执行上下文](03-architecture.md)；每个文件负责什么见 [代码导读与项目结构](04-code-tour.md)。

### 每一步的代码位置

| 步骤 | 文件 | 关键函数 |
|---|---|---|
| ① 拦截 fetch/XHR | `src/content/page-hook.js` | `installFetchHook` / `installXhrHook` |
| ② 找 DASH 清单 | `src/common/dash.js` | `findDash` / `looksLikeDash` / `extractDash` |
| ② 页面内镜像 | `src/content/page-hook.js` | `vsFindDash` / `vsExtractDash`（`dash-mirror` 区块） |
| ③ 转发 | `src/content/bridge.js` | `reportItem` / `send` |
| ④ 登记条目 | `src/background/registry.js` | `upsert` / `linkDashTracks` |
| ⑤ 选轨 + 下发 | `src/background/downloader.js` | `convertDash` / `convertDashTrack` |
| ⑤ 取流 + 合并 | `src/offscreen/offscreen.js` | `fetchTrack` / `runFfmpegDash` |

### 为什么要「树形搜索」而不是写死路径

同一个站点、同一个播放器，不同页面的接口结构完全不一样：

| 页面 | 接口 | DASH 在哪 |
|---|---|---|
| 投稿页 | `api.bilibili.com/x/player/wbi/playurl` | `data.dash` |
| 番剧页 | `api.bilibili.com/ogv/player/pre/check/drm` | `data.video_info.dash` |
| PGC | `api.bilibili.com/pgc/player/web/playurl` | `result.video.dash` |

v1.4.0 之前写死了 `data.dash`，结果**番剧页一条 DASH 都识别不出来**。

现在的做法：不猜路径，直接在 JSON 树里找「长得像 DASH 清单」的那个对象。判定条件（`looksLikeDash`）：

1. 自己带一个 `video` 数组，元素是轨道对象；
2. 第一条轨道能取到地址（`baseUrl` / `base_url` / `url` / `src` 都认）；
3. 还带 DASH 的标志字段：`audio` 数组 / `duration` / `min_buffer_time`。

只满足 1 会把页面上各种叫 `video` 的数组也当成清单；加上 3 才可靠。

这套「不猜路径、在 JSON 树里搜」的思路，在别的站点也照搬，见 [新站点适配手册](08-new-site-playbook.md)。

> **内容脚本不能用 import**（它是 classic script），
> 所以 `page-hook.js` 里内联了一份 `dash.js` 的镜像。
> 为了防止两份代码不同步，`test/dash.test.mjs` 有一个「防漂移守卫」：
> 它把镜像从 `page-hook.js` 里抠出来，在 `vm` 里跑同一批用例，逐项比对结果。

### 下载这一步为什么要 Referer

B 站的 CDN 会校验请求来源。**不带 Referer 就 403**：

```
不带 Referer: HTTP 403  content-type: application/octet-stream|text/html  350~548 字节
带 Referer  : HTTP 200  完整文件
```

坑在于：`Referer` 是 fetch 的**禁止头**，`fetch()` 里写 `headers: { Referer }` 会被浏览器忽略。所以扩展用了两条路：

- `declarativeNetRequest` 规则在网络层注入 Referer；
- 需要 Referer 的下载走 **offscreen 文档**里的 fetch 引擎路径。

> 实测结论：**DNR 规则对 `chrome.downloads.download()` 发起的请求完全不生效**
> （三种规则写法实测均为 350 字节 text/html）。所以有 Referer 需求的下载必须走引擎路径。

---

## 加密与占位流

### 怎么判断一条流是不是「废了」

| 判据 | 怎么查 | 意味着什么 |
|---|---|---|
| 清单里有 `widevine_pssh` | 看 JSON | 这条流是加密的 |
| 文件里有 `pssh` / `encv` / `enca` / `senc` 盒子 | 看 MP4 结构 | 画面数据是密文 |
| `bandwidth` 低得离谱 | `bandwidth ÷ (宽 × 高 × 25)` < 0.01 | 这是占位流 |

**bpp（每像素每帧多少比特）这个指标最直观：**

| 流 | 分辨率 | 码率 | bpp | 判断 |
|---|---|---|---|---|
| 正常 1080P | 1920×1080 | 2~6 Mbps | 0.04~0.10 | ✅ 正常 |
| 正常 480P | 852×480 | 608 kbps | 0.0595 | ✅ 正常 |
| **番剧占位流** | 1920×1080 | **121 kbps** | **0.0023** | ❌ 占位 |

### 实测：DRM 接口对「没权限」的访客给的是占位清单

2026-11 实测，匿名访问下面 4 集番剧，`ogv/player/pre/check/drm` 返回的清单**完全一样**：

```
ep=3854802   timelength=1440063   video0 = 32091867755/32091867755-1-100005.m4s
ep=323085    timelength=1440063   video0 = 32091867755/32091867755-1-100005.m4s
ep=469110    timelength=1440063   video0 = 32091867755/32091867755-1-100005.m4s
ep=109726    timelength=1440063   video0 = 32091867755/32091867755-1-100005.m4s
```

注意 `32091867755` 这个 cid —— 它**根本不是这几集番剧的 cid**。也就是说：**接口给的是一份指向别人文件的占位清单。**

下载这份清单里的文件会得到：

| 现象 | 数值 |
|---|---|
| 文件大小 | 20.9 MB（24 分钟只有 20.9 MB） |
| 实际码率 | 121 kbps（1080P 不可能这么低） |
| 抽帧画面 | 纯灰 + 噪点 |
| 解码器 | `error while decoding MB 0 0` / `concealing 8160 DC, AC, MV errors` |

**这就是「下载的大小远小于实际大小 + 播放时为全屏条码」的根源。**

### 扩展的修法：换普通播放接口

B 站还有另一个播放地址接口（**投稿页本来就在用它**）：

```
https://api.bilibili.com/x/player/wbi/playurl?bvid=<bvid>&cid=<cid>&fnval=16&fourk=1
```

对**同一集番剧**，它返回的是**没有加密**的标准流，而且清晰度按当前账号的权限给：

```
=== 番剧 ep3854802，两个接口对比 ===
DRM 接口  : id=112 1920x1080 avc1.640032 bw=121552  pssh=有  文件=32091867755-1-100005.m4s
普通接口  : id=32   852x480  avc1.64001F bw=608492  pssh=无  文件=40394753402-1-30032.m4s
            id=32   852x480  hvc1.1.6.L bw=361205  pssh=无  文件=40394753402-1-30033.m4s
            id=16   640x360  avc1.64001E bw=334420  pssh=无  文件=40394753402-1-30016.m4s
```

所以扩展在番剧页上会：

```
① 从页面地址取出 ep_id（/bangumi/play/ep3854802 → 3854802）
        ▼
② 调 pgc/view/web/ep/page?ep_id=… 拿到这一集的 cid / bvid
        ▼
③ 调 x/player/wbi/playurl?bvid=…&cid=… 拿到未加密的 DASH 清单
        ▼
④ 用这套地址下载、合并
```

对应代码：`src/background/bilibili-alt.js`。

### 三个必须知道的坑

**坑 1：B 站的接口有人机验证（风控）。**

短时间内重复请求，它会返回：

```json
{"code":0,"message":"OK","ttl":1,"data":{"v_voucher":"voucher_a17ce11b-..."}}
```

这个响应里**没有地址**，只有一个验证凭证。实测同一个请求连发几次，大约一半中招、一半正常。

而且这个风控是**按次**的：不是「这个 IP 一直不行」，而是「这一次不行，隔一会儿再发就好了」。

👉 扩展的做法：**退避几百毫秒重试，最多 5 次**（`bilibili-alt.js` 的 `apiGet`），而且**内容脚本那条通道也要重试** —— 原来只重试后台自取那条路，内容脚本被挡一次就直接掉到后台自取（后台自取 100% 会撞上风控），等于整条路都废了。

**坑 2：普通接口给的是「免会员版」，时长可能短一点。**

实测同一集：

| 接口 | 时长 |
|---|---|
| DRM 接口 | 1441 秒（24:00） |
| 普通接口 | 1282 秒（21:22） |

差的那 159 秒是「**大会员抢先看**」的部分——普通账号本来就看不到。登录大会员后，普通接口给的时长也会跟着变。

**坑 3：番剧页上「页面下载的轨道」和「接口给的清单」对不上号。**

这是最容易把人绕晕的一点，实测（ep3854802）：

| 来源 | 地址里的 cid | 文件编号 | 说明 |
|---|---|---|---|
| DRM 接口给的清单 | `32091867755` | `1xxxxx` | 属于另一部番剧的占位清单 |
| 页面真正下载的轨道 | `40394753402` | `1xxxxx` | 这一集的真实轨道（试看流） |
| 普通播放接口给的清单 | `40394753402` | `3xxxx` | 这一集的真实清单（未加密） |

三者的**主机名、签名参数（`upsig` / `trid` / `deadline`）、文件编号全都不一样**。所以「用地址完全相同来关联单轨和清单」这条路在番剧页上**行不通**。

👉 扩展的做法：番剧页上，只要是 `.m4s` 轨道（来自 B 站 CDN），一律按「轨道」处理，用普通播放接口的清单重新合成一个完整视频。判断代码：`src/background/bilibili-alt.js` 的 `isBangumiTrackItem()`。

> **顺带一提**：B 站的 CDN 一定要 Referer。
> 实测同一个地址，带 Referer 返回 200（完整文件），
> 不带返回 403（一个 0 字节的 text/html）。
> 详见 [DASH 下载异常排查](09-troubleshooting.md) 第 4.4 节（CDN 403 与 Referer 的关系）。

### 边界声明

- 扩展**只**使用站点自己提供的、当前登录账号**有权观看**的普通播放地址；
- **不**做任何解密，**不**提取密钥，**不**修改播放器；
- 账号没权限时，服务器给什么就是什么（通常是一段低码率的免费片段）。

---

## 不用扩展，自己手动下一集

### 拿到播放地址 JSON

```powershell
# PowerShell
$ep = 3854802
$headers = @{ Referer = "https://www.bilibili.com/bangumi/play/ep$ep"; 'User-Agent' = 'Mozilla/5.0' }

# 第 1 步：集号 -> cid / bvid
$epInfo = Invoke-RestMethod "https://api.bilibili.com/pgc/view/web/ep/page?ep_id=$ep" -Headers $headers
# 注意：ep/page 的结构是 result.sections[].pages[].episodes[]，用脚本找 ep_id 对得上的那个
$episode = $epInfo.result.sections[0].pages[0].episodes | Where-Object { $_.ep_id -eq $ep }
$cid = $episode.cid; $bvid = $episode.bvid

# 第 2 步：cid / bvid -> 播放地址（未加密）
$play = Invoke-RestMethod "https://api.bilibili.com/x/player/wbi/playurl?bvid=$bvid&cid=$cid&fnval=16&fourk=1" -Headers $headers
$play.data.dash.video | Select-Object id, width, height, codecs, bandwidth, base_url
```

### 挑一条轨道并下载

```powershell
# 优先挑 H.264（兼容性最好），再挑码率高的
$track = $play.data.dash.video | Sort-Object @{Expression={ if ($_.codecs -like 'avc1*') {0} else {1} }}, -bandwidth | Select-Object -First 1
$audio = $play.data.dash.audio | Sort-Object -Property bandwidth -Descending | Select-Object -First 1

Invoke-WebRequest $track.base_url -Headers $headers -OutFile video.m4s
Invoke-WebRequest $audio.base_url  -Headers $headers -OutFile audio.m4s
```

### 合并成 MP4（需要本机装了 ffmpeg）

```powershell
ffmpeg -i video.m4s -i audio.m4s -c copy -movflags +faststart 凡人修仙传第178集.mp4
```

`-c copy` = 不重新编码，只是把两条轨装进一个文件（快，不掉画质）。

### 一条龙（Node.js）

仓库里有现成的工具：

```bash
node tools/probe-alt-api.mjs 3854802     # 看两个接口分别给了什么
node tools/compare-track-files.mjs 3854802 # 对比文件编号
node tools/diagnose-dash-frames.mjs        # 抽帧看画面
node tools/scan-drm.mjs                   # 批量检查几集番剧的加密情况
```

---

## 常见问题

**Q1：接口返回 `{"code":-400,"message":"请求错误"}`？**

缺 `drm_tech_type=2`，或者 Referer 没带、不是 bilibili.com。

**Q2：返回了 JSON，但 `data` 里只有 `v_voucher`？**

撞上了 B 站人机验证。等几秒重试，或者在浏览器里正常操作一下页面再试。

**Q3：返回的清单里所有集的地址都一样？**

那就是占位清单（没权限）。改用普通接口，见本章「扩展的修法：换普通播放接口」。

**Q4：下载下来只有画面没有声音？**

拿到的是 DASH 的**单条视频轨**。用扩展时点「DASH 视频+音频」那条，或者手动下载时把音频轨也下下来再合并。

**Q5：下下来的文件播出来是满屏条码？**

拿到的是加密流或占位流。检查本章「怎么判断一条流是不是「废了」」里的三个判据。

**Q6：文件只有几十 MB，但这一集明明该有几百 MB？**

占位流。见本章「实测：DRM 接口对「没权限」的访客给的是占位清单」。

**Q7：CDN 返回 403？**

Referer 没带上。CDN 认 Referer，见本章「下载这一步为什么要 Referer」。

**Q8：地址一会儿就失效？**

CDN 地址带签名（`?e=ig8...` 和 `deadline=` 参数），会过期。重新取一次清单即可。

---

## 附录：字段速查表

| 字段 | 在哪 | 含义 |
|---|---|---|
| `code` / `message` | 顶层 | 0 = 成功 |
| `data.video_info.quality` | 番剧 | 当前授权画质编号 |
| `data.video_info.format` | 番剧 | 当前格式（flv360 等） |
| `data.video_info.timelength` | 番剧 | 总时长（毫秒） |
| `data.video_info.support_formats[]` | 番剧 | 有哪些画质可选 |
| `data.video_info.drm_type` | 番剧 | 有值 = 走 DRM 通道 |
| `data.video_info.dash.duration` | 番剧 | 时长（秒） |
| `data.video_info.dash.video[]` | 番剧 | 视频轨数组 |
| `data.video_info.dash.audio[]` | 番剧 | 音频轨数组 |
| `dash.video[].id` | 投稿 | 画质编号 |
| `dash.video[].base_url` / `baseUrl` | 投稿 | 主地址 |
| `dash.video[].backup_url` / `backupUrl` | 投稿 | 备用地址（数组） |
| `dash.video[].codecs` | 投稿 | avc1 / hvc1 / av01 |
| `dash.video[].bandwidth` | 投稿 | 码率 bps |
| `dash.video[].size` | 投稿 | 字节数 |
| `dash.video[].widevine_pssh` | 投稿 | 有值 = 加密流 |

## 附录：命令速查

```bash
# 番剧 DRM 接口（注意 ep_id 必须带）
curl -H "Referer: https://www.bilibili.com/bangumi/play/ep3854802" \
  "https://api.bilibili.com/ogv/player/pre/check/drm?ep_id=3854802&drm_tech_type=2"

# 普通播放接口（未加密）
curl -H "Referer: https://www.bilibili.com/bangumi/play/ep3854802" \
  "https://api.bilibili.com/x/player/wbi/playurl?bvid=BV1UxE16oETX&cid=40394753402&fnval=16&fourk=1"

# 查集号对应的 cid / bvid
curl -H "Referer: https://www.bilibili.com/bangumi/play/ep3854802" \
  "https://api.bilibili.com/pgc/view/web/ep/page?ep_id=3854802"
```

## 附录：相关文件

| 文件 | 作用 |
|---|---|
| `src/common/dash.js` | DASH 清单的通用定位与解析（纯函数，可单测） |
| `src/content/page-hook.js` | 页面钩子 + `dash.js` 的内联镜像 |
| `src/content/bridge.js` | 隔离世界 ↔ 页面 ↔ 后台 的中转 |
| `src/background/registry.js` | 条目登记、DASH 轨道关联 |
| `src/background/bilibili-alt.js` | 番剧「备用播放地址」 |
| `src/background/downloader.js` | 选轨、下发任务 |
| `src/offscreen/offscreen.js` | 取流、ffmpeg 合并、存盘 |
| `test/dash.test.mjs` | DASH 解析单测 + 防漂移守卫 |
| `test/dash-tracks.test.mjs` | 选轨/占位流/加密识别单测 |
| `test/bilibili-alt.test.mjs` | 备用地址 / 风控重试 / 清单缓存 / 轨道判定单测 |
| `tools/probe-fetch-json.mjs` | 测「内容脚本代发接口」这条通道 |
| `tools/probe-track-urls.mjs` | 对比嗅探到的轨道和两个接口清单的地址 |
| `tools/bilibili-test.mjs` | 端到端：真浏览器 + 真番剧 + 真下载 + 校验 |
| [DASH 下载异常排查](09-troubleshooting.md) | 「体积偏小 + 满屏条码」的完整排查记录 |

---

*实测环境：Windows / Chrome 156 / Node 25，2026-11。所有接口返回与数值均为实测记录。*
