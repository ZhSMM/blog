#!/usr/bin/env python3
"""把 mdBook 的构建产物整理成一个 CHM (Compiled HTML Help) 编译工程。

CHM 是 Windows 的离线帮助格式，编译器是微软的 HTML Help Workshop（hhc.exe）。
本脚本负责生成编译所需的三个东西：

    <out>/<name>.hhp    编译工程（要打包哪些文件、标题、窗口）
    <out>/<name>.hhc    目录树（对应 SUMMARY.md 的章节层级）
    <out>/<name>.hhk    关键字索引（页面 + 页内各级小节标题）
    <out>/**            页面与静态资源（镜像 mdBook 的目录结构）

用法：

    python3 tools/make_chm.py --book book --summary src/SUMMARY.md \
        --out chm --name notes.chm --title "编程笔记"

几点实现说明：

* **文件名转 ASCII**。mdBook 的输出里存在中文文件名（如 `program/mysql/01-视图.html`），
  而 hhc.exe 在处理 [FILES] 里的非 ASCII 路径时并不可靠。所以这里把每个非 ASCII
  字符替换成 `_<四位十六进制码>`，得到确定性的 ASCII 文件名，并同步改写页面里的
  href/src，保证站内链接仍然指向正确的目标。目录树里显示的是章节标题，不受改名影响。

* **保持目录结构**。mdBook 生成的页面之间的链接是相对路径（`../../program/...`），
  只要 CHM 内部保留同样的相对层级，这些链接就能原样工作。

* **index.html**。mdBook 在没有 `src/index.md` 时会生成一个自动跳转的首页，
  这种页面在 CHM 里没有意义，这里会替换成一个真正的目录首页。

* **关键字索引**。用显式的 .hhk 而不是 HTML Help Workshop 的 `Auto Index=Yes`，
  因为自动索引依赖 Itircl.dll，而这个 DLL 需要注册成 COM 组件才能被 32 位的
  hhc.exe 加载（实测开着和关着 Auto Index，产物只差 1 字节，索引根本没生成）。
  索引做成两级：一级是页面，二级是页内各级小节标题，直接跳到对应锚点，
  这样 Index 标签本身就能当目录用。
"""

from __future__ import annotations

import argparse
import html
import posixpath
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, unquote

# Windows 控制台默认编码不是 UTF-8（比如 GitHub runner 上是 cp1252），
# 直接 print 中文会抛 UnicodeEncodeError，这里统一改成 UTF-8 并对无法编码的字符降级
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# mdBook 自动生成的跳转首页（体积很小，内容是一个 location.replace）
REDIRECT_MARK = "location.replace"

# 不进入 CHM 的文件（仅限 book 根目录）
SKIP_ROOT_FILES = {"print.html", "404.html", ".nojekyll", "CNAME"}

# 不进关键字索引的页面：toc.html 是 mdBook 的侧边栏，404.html 是错误页
INDEX_SKIP_PAGES = {"toc.html", "404.html"}

LINK_RE = re.compile(r'(?P<attr>href|src)\s*=\s*"(?P<val>[^"]*)"', re.IGNORECASE)
# mdBook 的「打印本」链接，打印页没有进 CHM，直接摘掉整个锚点
PRINT_LINK_RE = re.compile(r"<a[^>]*href=\"[^\"]*print\.html\"[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
# 指向 CHM 自身的下载链接，在 CHM 内部是死链，去掉
SELF_LINK_RE = re.compile(r"<a[^>]*href=\"[^\"]*\.chm\"[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)

SUMMARY_ITEM_RE = re.compile(r"^(?P<indent>[ \t]*)[-+*]\s+\[(?P<title>[^\]]*)\]\((?P<path>[^)]*)\)")
SUMMARY_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.*?)\s*$")

# mdBook 生成的正文标题：<h2 id="锚点"><a class="header" href="#锚点">标题</a></h2>
HEADING_RE = re.compile(r"<h(?P<level>[1-4])(?P<attrs>[^>]*)>(?P<inner>.*?)</h(?P=level)>", re.IGNORECASE | re.DOTALL)
ID_ATTR_RE = re.compile(r'\bid\s*=\s*"([^"]*)"', re.IGNORECASE)
HEADER_LINK_RE = re.compile(r'class\s*=\s*"[^"]*\bheader\b', re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- #
# 路径处理
# --------------------------------------------------------------------------- #
def ascii_slug(name: str) -> str:
    """把文件名/目录名里的非 ASCII 字符替换成确定性的 ASCII 形式。

    `01-视图.html` -> `01-_89C6_56FE.html`
    """
    out = []
    for ch in name:
        if ch.isascii() and (ch.isalnum() or ch in "._-"):
            out.append(ch)
        else:
            out.append("_%04X" % ord(ch))
    return "".join(out)


def slug_path(rel: str) -> str:
    """把 book 内的相对路径整体转成 ASCII 路径。"""
    return "/".join(ascii_slug(part) for part in rel.split("/") if part)


def md_to_html(path: str) -> str:
    """SUMMARY.md 里的 `a/b.md` 对应构建产物里的 `a/b.html`。"""
    path = path.strip().lstrip("./")
    return path[:-3] + ".html" if path.endswith(".md") else path


# --------------------------------------------------------------------------- #
# SUMMARY.md 解析
# --------------------------------------------------------------------------- #
def parse_summary(text: str) -> list[dict]:
    """把 SUMMARY.md 解析成章节树。

    节点结构：{"title": str, "path": str | None, "children": [节点]}
    `#` 开头的是分组（mdBook 的 prefix chapter），列表项是章节，缩进决定嵌套。
    第一个 `#` 是 SUMMARY 自身的标题（书名），不作为分组。
    """
    root: list[dict] = []
    stack: list[tuple[int, dict]] = []
    group: dict | None = None
    heading_count = 0

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue

        heading = SUMMARY_HEADING_RE.match(line)
        if heading:
            heading_count += 1
            title = heading.group("title").strip()
            if heading_count == 1:
                # SUMMARY.md 的第一个标题是书名本身，mdBook 也不会把它渲染成章节
                group = None
                stack = []
                continue
            group = {"title": title, "path": None, "children": []}
            root.append(group)
            stack = []
            continue

        item = SUMMARY_ITEM_RE.match(line)
        if not item:
            continue

        indent = len(item.group("indent").replace("\t", "  "))
        node = {
            "title": item.group("title").strip(),
            "path": item.group("path").strip() or None,
            "children": [],
        }

        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else group
        if parent is None:
            parent = {"title": "", "path": None, "children": []}
            root.append(parent)
        parent["children"].append(node)
        stack.append((indent, node))

    return root


# --------------------------------------------------------------------------- #
# 链接改写
# --------------------------------------------------------------------------- #
def rewrite_links(text: str, src_rel: str, path_map: dict[str, str]) -> str:
    """把页面里的站内相对链接改写到 ASCII 化之后的新路径。"""
    base = posixpath.dirname(src_rel)

    def repl(match: re.Match) -> str:
        value = match.group("val")
        if not value or value.startswith(("http://", "https://", "mailto:", "data:", "javascript:", "#", "//")):
            return match.group(0)

        raw, sep, fragment = value.partition("#")
        path_part, qsep, query = raw.partition("?")
        if not path_part:
            return match.group(0)

        decoded = unquote(path_part)
        if decoded.startswith("/"):
            target = decoded.lstrip("/")
        else:
            target = posixpath.normpath(posixpath.join(base, decoded))
        if target not in path_map:
            return match.group(0)

        new_rel = posixpath.relpath(path_map[target], base if base else ".")
        out = quote(new_rel, safe="/._-~()!$&'*+,;=@")
        if qsep:
            out += "?" + query
        if sep:
            out += "#" + fragment
        return '%s="%s"' % (match.group("attr"), out)

    return LINK_RE.sub(repl, text)


# --------------------------------------------------------------------------- #
# 目录首页
# --------------------------------------------------------------------------- #
def render_index(title: str, tree: list[dict]) -> str:
    """生成 CHM 的目录首页。"""

    def render(nodes: list[dict]) -> str:
        if not nodes:
            return ""
        parts = ["<ul>"]
        for node in nodes:
            label = html.escape(node["title"])
            if node["path"]:
                target = md_to_html(node["path"])
                parts.append('<li><a href="%s">%s</a>' % (quote(target, safe="/._-"), label))
            else:
                parts.append("<li><strong>%s</strong>" % label)
            if node["children"]:
                parts.append(render(node["children"]))
            parts.append("</li>")
        parts.append("</ul>")
        return "\n".join(parts)

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif; margin: 2em auto; max-width: 52em; line-height: 1.7; padding: 0 1em; }}
h1 {{ border-bottom: 2px solid #ddd; padding-bottom: .3em; }}
ul {{ line-height: 1.9; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>这是本笔记的离线版（CHM），适合在没有网络或需要快速全文检索时阅读。</p>
{body}
</body>
</html>
""".format(title=html.escape(title), body=render(tree))


# --------------------------------------------------------------------------- #
# .hhc / .hhp 生成
# --------------------------------------------------------------------------- #
def emit_hhc_node(node: dict, depth: int, lines: list[str], path_map: dict[str, str]) -> None:
    indent = "    " * (depth + 1)
    lines.append('%s<LI> <OBJECT type="text/sitemap">' % indent)
    lines.append('%s    <param name="Name" value="%s">' % (indent, html.escape(node["title"], quote=True)))
    if node["path"]:
        target = md_to_html(node["path"])
        if target in path_map:
            lines.append('%s    <param name="Local" value="%s">' % (indent, path_map[target]))
    lines.append("%s    </OBJECT>" % indent)
    if node["children"]:
        lines.append("%s<UL>" % indent)
        for child in node["children"]:
            emit_hhc_node(child, depth + 1, lines, path_map)
        lines.append("%s</UL>" % indent)


def render_hhc(tree: list[dict], path_map: dict[str, str]) -> str:
    lines = [
        '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">',
        "<HTML>",
        "<HEAD>",
        '<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">',
        "<!-- Sitemap 1.0 -->",
        "</HEAD><BODY>",
        '<OBJECT type="text/site properties">',
        '    <param name="ImageType" value="Folder">',
        "</OBJECT>",
        "<UL>",
    ]
    for node in tree:
        emit_hhc_node(node, 0, lines, path_map)
    lines += ["</UL>", "</BODY></HTML>", ""]
    return "\n".join(lines)


def summary_page_order(tree: list[dict]) -> list[tuple[str, str]]:
    """按 SUMMARY 的章节顺序列出 (章节标题, 页面相对路径)。

    路径是 mdBook 产物里的形式（`a/b.md` -> `a/b.html`）。
    """
    out: list[tuple[str, str]] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            if node["path"]:
                out.append((node["title"], md_to_html(node["path"])))
            walk(node["children"])

    walk(tree)
    return out


def index_local(page: str, anchor: str) -> str:
    """索引项的跳转目标：页面路径#锚点。

    锚点里常是中文（mdBook 直接用标题文字当 id），必须百分号编码，
    否则 hhc.exe / hh.exe 解析时会当成非法字符。
    """
    return "%s#%s" % (quote(page, safe="/._-"), quote(anchor, safe=""))


def build_heading_tree(headings: list[tuple[int, str, str]]) -> list[dict]:
    """按标题层级把一篇文章里的小节组织成树。

    headings 里每项是 (级别, 锚点, 文本)。
    """
    root: list[dict] = []
    stack: list[tuple[int, dict]] = []

    for level, anchor, text in headings:
        node = {"label": text, "anchor": anchor, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            stack[-1][1]["children"].append(node)
        else:
            root.append(node)
        stack.append((level, node))

    return root


def extract_headings(text: str) -> list[tuple[int, str, str]]:
    """抽出页面里的正文标题，返回 [(级别, 锚点, 文本)]。

    mdBook 会给正文标题挂一个 `class="header"` 的锚点链接；侧边栏标题
    （`menu-title`）和快捷键弹窗标题（`mdbook-help-title`）没有 id，会被过滤掉。
    """
    out: list[tuple[int, str, str]] = []
    for match in HEADING_RE.finditer(text):
        attrs = match.group("attrs")
        inner = match.group("inner")
        id_match = ID_ATTR_RE.search(attrs)
        if not id_match:
            continue
        if not HEADER_LINK_RE.search(inner):
            continue
        anchor = html.unescape(id_match.group(1)).strip()
        label = html.unescape(TAG_RE.sub("", inner)).strip()
        if not anchor or not label:
            continue
        out.append((int(match.group("level")), anchor, label))
    return out


def extract_page_title(text: str) -> str:
    """从 <title> 里取页面标题，剥掉 mdBook 追加的站点名后缀。"""
    match = TITLE_RE.search(text)
    if not match:
        return ""
    title = html.unescape(TAG_RE.sub("", match.group(1))).strip()
    # mdBook 生成的标题形如「环境搭建 - 编程笔记」
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    return title


def render_hhk(pages: list[tuple[str, str, list[tuple[int, str, str]]]]) -> str:
    """生成 .hhk 关键字索引。

    用显式的 .hhk 而不是 `Auto Index=Yes`，是因为自动索引依赖 Itircl.dll，
    而 hhc.exe 是 32 位进程，在没装 HTML Help Workshop 的机器上加载不到它
    （实测 A/B 对照：Full-text search 开关的产物只差 1 字节，
     全文检索索引其实根本没生成）。

    索引做成两级：一级是页面本身，二级是该页里的各级小节标题，
    直接跳到对应锚点。这样即使 CHM 没有全文检索，Index 标签依然能当目录用。

    pages 里每一项是 (显示标题, 页面相对路径, [(级别, 锚点, 文本), ...])。
    """
    lines = [
        '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">',
        "<HTML>",
        "<HEAD>",
        '<meta name="GENERATOR" content="Microsoft">',
        "</HEAD><BODY>",
        "<UL>",
    ]

    def emit(nodes: list[dict], page: str) -> None:
        for node in nodes:
            lines.append('    <LI><OBJECT type="text/sitemap">')
            lines.append(
                '        <param name="Name" value="%s">' % html.escape(node["label"], quote=True)
            )
            lines.append('        <param name="Local" value="%s">' % index_local(page, node["anchor"]))
            lines.append("        </OBJECT>")
            if node["children"]:
                lines.append("    <UL>")
                emit(node["children"], page)
                lines.append("    </UL>")

    for label, path, headings in pages:
        if not label:
            continue
        lines.append('    <LI><OBJECT type="text/sitemap">')
        lines.append('        <param name="Name" value="%s">' % html.escape(label, quote=True))
        lines.append('        <param name="Local" value="%s">' % quote(path, safe="/._-"))
        lines.append("        </OBJECT>")
        tree = build_heading_tree(headings)
        if tree:
            lines.append("    <UL>")
            emit(tree, path)
            lines.append("    </UL>")

    lines += ["</UL>", "</BODY></HTML>", ""]
    return "\n".join(lines)


def render_hhp(stem: str, title: str, files: list[str], default_topic: str) -> str:
    """生成 .hhp 编译工程。

    [FILES] 里用反斜杠（Windows 路径），hhc.exe 会归一化成内部使用的正斜杠路径。
    """
    lines = [
        "[OPTIONS]",
        "Binary TOC=Yes",
        "Compatibility=1.1 or later",
        "Compiled file=%s.chm" % stem,
        "Contents file=%s.hhc" % stem,
        "Default topic=%s" % default_topic,
        "Display compile progress=No",
        "Full-text search=Yes",
        "Index file=%s.hhk" % stem,
        "Error log file=%s.log" % stem,
        "Language=0x804 Chinese (Simplified)",
        "Title=%s" % title,
        "Default Window=%s" % stem,
        "",
        "[WINDOWS]",
        # 窗口名需与 Default Window 一致；字段含义见 HTML Help Workshop 文档
        '%s="%s","%s.hhc","%s.hhk","%s","%s",,"Start",,,0x63520,,0x70387e,[6,1,807,610],0xb0000,,,,,,0'
        % (stem, title, stem, stem, default_topic, default_topic),
        "",
        "[FILES]",
    ]
    lines += [f.replace("/", "\\") for f in files]
    lines += ["", "[INFOTYPES]", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="生成 CHM 编译工程")
    parser.add_argument("--book", required=True, type=Path, help="mdbook build 的输出目录")
    parser.add_argument("--summary", required=True, type=Path, help="src/SUMMARY.md")
    parser.add_argument("--out", required=True, type=Path, help="CHM 工程输出目录")
    parser.add_argument("--name", default="notes.chm", help="生成的 CHM 文件名")
    parser.add_argument("--title", default="编程笔记", help="CHM 标题")
    args = parser.parse_args(argv)

    book: Path = args.book
    out: Path = args.out
    if not book.is_dir():
        print("找不到 mdbook 输出目录: %s" % book, file=sys.stderr)
        return 1
    if not args.summary.is_file():
        print("找不到 SUMMARY.md: %s" % args.summary, file=sys.stderr)
        return 1

    tree = parse_summary(args.summary.read_text(encoding="utf-8"))

    # 1) 收集源文件
    sources: dict[str, Path] = {}
    for path in sorted(book.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(book).as_posix()
        if "/" not in rel and rel in SKIP_ROOT_FILES:
            continue
        sources[rel] = path

    # 2) 建立 ASCII 路径映射
    path_map: dict[str, str] = {}
    used: set[str] = set()
    for rel in sources:
        target = slug_path(rel)
        if target in used:
            target = target + ".dup"
        used.add(target)
        path_map[rel] = target

    # 3) mdBook 的 index.html 是自动跳转页时，换成真正的目录首页
    index_is_redirect = False
    index_src = book / "index.html"
    if index_src.is_file():
        head = index_src.read_text(encoding="utf-8", errors="ignore")
        index_is_redirect = REDIRECT_MARK in head or len(head) < 4000

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 4) 拷贝资源 + 改写链接
    copied = 0
    page_info: dict[str, tuple[str, list[tuple[int, str, str]]]] = {}
    for rel, src in sources.items():
        target_rel = path_map[rel]
        dest = out / target_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == ".html":
            text = src.read_text(encoding="utf-8", errors="ignore")
            # 索引要用原始标题，所以先抽取再改写链接
            headings = extract_headings(text)
            title = extract_page_title(text)
            text = rewrite_links(text, rel, path_map)
            text = PRINT_LINK_RE.sub("", text)
            text = SELF_LINK_RE.sub("", text)
            dest.write_text(text, encoding="utf-8", newline="\n")
            page_info[rel] = (title, headings)
        else:
            shutil.copy2(src, dest)
        copied += 1

    # 5) 目录首页
    if index_is_redirect:
        (out / "index.html").write_text(render_index(args.title, tree), encoding="utf-8", newline="\n")
        path_map["index.html"] = "index.html"
        copied += 1

    # 6) 目录树 + 关键字索引 + 工程文件
    stem = Path(args.name).stem
    (out / ("%s.hhc" % stem)).write_text(render_hhc(tree, path_map), encoding="utf-8", newline="\n")

    # 索引按 SUMMARY 的章节顺序排列，和目录树保持一致
    pages: list[tuple[str, str, list[tuple[int, str, str]]]] = []
    for label, html_rel in summary_page_order(tree):
        if html_rel not in path_map:
            continue
        if html_rel in INDEX_SKIP_PAGES:
            continue
        page_title, headings = page_info.get(html_rel, ("", []))
        pages.append((label or page_title, path_map[html_rel], headings))

    (out / ("%s.hhk" % stem)).write_text(render_hhk(pages), encoding="utf-8", newline="\n")

    file_list = sorted(path_map.values())
    default_topic = "index.html" if "index.html" in path_map else (file_list[0] if file_list else "index.html")
    (out / ("%s.hhp" % stem)).write_text(
        render_hhp(stem, args.title, file_list, default_topic), encoding="utf-8", newline="\n"
    )

    toc_entries = sum(1 for line in (out / ("%s.hhc" % stem)).read_text(encoding="utf-8").splitlines() if "<LI>" in line)
    idx_entries = sum(1 for line in (out / ("%s.hhk" % stem)).read_text(encoding="utf-8").splitlines() if "<LI>" in line)
    print(
        "[chm] 文件 %d 个，目录条目 %d 条，索引条目 %d 条，默认首页 %s"
        % (copied, toc_entries, idx_entries, default_topic)
    )
    print("[chm] 工程 %s，输出目录 %s" % (out / ("%s.hhp" % stem), out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
