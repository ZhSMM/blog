#!/usr/bin/env python3
"""下载并解包微软官方 HTML Help Workshop，拿到 CHM 编译器 hhc.exe。

为什么要自己解包，而不是直接用 `choco install html-help-workshop`：

* 那个 Chocolatey 包的下载地址指向 web.archive.org 的「包装页」而非原始二进制，
  校验和必然对不上，安装会失败；
* HTML Help Workshop 只有 32 位版本，官方安装程序要求提权并写注册表。

而 htmlhelp.exe 本身是个自解压包，内层是一个标准 CAB。用 Python 把 CAB 从
可执行文件里切出来，再交给 Windows 自带的 expand.exe 解开，全程不需要提权、
不写注册表、不污染系统。

用法：

    python tools/extract_htmlhelp.py --dest ./.hhc

成功后 stdout 会打印 hhc.exe 的完整路径。

也可以用 `--archive` 指定一个已经下载好的 htmlhelp.exe，脚本会跳过下载只做校验
和解包（CI 里通常由 PowerShell 负责下载，因为 Python 的 urllib 不走系统代理）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认编码不是 UTF-8（比如 GitHub runner 上是 cp1252），
# 直接 print 中文会抛 UnicodeEncodeError，这里统一改成 UTF-8 并对无法编码的字符降级
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# 微软官方 htmlhelp.exe（HTML Help Workshop 4.74.8702）的归档地址。
# 原始 download.microsoft.com 链接已失效（HTTP 400），用 Wayback 的 if_ 模式取原始二进制。
SOURCE_URL = (
    "https://web.archive.org/web/20200918004813if_/"
    "https://download.microsoft.com/download/0/A/9/"
    "0A939EF6-E31C-430F-A3DF-DFAE7960D564/htmlhelp.exe"
)
EXPECTED_MD5 = "53899be5da83419d772d5b97e653da7c"


def powershell_exe() -> str:
    """定位 Windows PowerShell 的可执行文件。

    用绝对路径而不是靠 PATH 查找，避免 CI 里 PATH 被裁剪导致找不到命令。
    """
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    candidate = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if candidate.is_file():
        return str(candidate)
    return "powershell.exe"


def expand_exe() -> str:
    """定位 Windows 自带的 CAB 解包工具 expand.exe。"""
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    candidate = Path(system_root) / "System32" / "expand.exe"
    if candidate.is_file():
        return str(candidate)
    return "expand.exe"


def download(url: str, dest: Path) -> bytes:
    """下载 htmlhelp.exe。

    用 PowerShell 的 Invoke-WebRequest 而不是 Python 的 urllib：
    urllib 不读 Windows 的系统代理设置，在部分网络环境下会直接超时，
    而 Invoke-WebRequest 会自动走 PAC / 系统代理。
    """
    print("[hhc] 下载 %s" % url, flush=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    cmd = [
        powershell_exe(),
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "$ProgressPreference='SilentlyContinue';"
        "Invoke-WebRequest -Uri $env:HHC_URL -OutFile $env:HHC_DEST "
        "-UseBasicParsing -TimeoutSec 300",
    ]
    env = dict(os.environ)
    env["HHC_URL"] = url
    env["HHC_DEST"] = str(dest)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0 or not dest.is_file():
        sys.stderr.write(result.stdout + result.stderr)
        print("下载失败（Invoke-WebRequest 返回 %d）" % result.returncode, file=sys.stderr)
        raise RuntimeError("htmlhelp.exe 下载失败")
    return dest.read_bytes()


def find_cab(data: bytes) -> tuple[int, int]:
    """在可执行文件里定位内嵌的 CAB（MSCF），返回 (偏移, 长度)。"""
    best: tuple[int, int] | None = None
    i = 0
    while True:
        i = data.find(b"MSCF", i)
        if i < 0:
            break
        if i + 36 <= len(data):
            reserved1, csize, reserved2, coff, reserved3 = struct.unpack_from("<5I", data, i + 4)
            cfiles, = struct.unpack_from("<H", data, i + 28)
            if (
                reserved1 == 0
                and reserved2 == 0
                and reserved3 == 0
                and 36 <= coff < csize <= len(data) - i
                and cfiles > 0
            ):
                if best is None or csize > best[1]:
                    best = (i, csize)
        i += 4
    if best is None:
        raise RuntimeError("没能在 htmlhelp.exe 里找到 CAB")
    return best


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="解包微软 HTML Help Workshop")
    parser.add_argument("--dest", required=True, type=Path, help="解包目标目录")
    parser.add_argument("--url", default=SOURCE_URL, help="htmlhelp.exe 下载地址")
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="已下载好的 htmlhelp.exe；给了就不下载，只做校验和解包",
    )
    args = parser.parse_args(argv)

    dest: Path = args.dest
    dest.mkdir(parents=True, exist_ok=True)
    hhc = dest / "hhc.exe"
    if hhc.is_file():
        print(hhc.resolve())
        return 0

    if args.archive is not None:
        archive = args.archive
        if not archive.is_file():
            print("找不到归档文件: %s" % archive, file=sys.stderr)
            return 1
        print("[hhc] 使用已有归档: %s" % archive)
        data = archive.read_bytes()
    else:
        archive = dest / "htmlhelp.exe"
        data = download(args.url, archive)

    md5 = hashlib.md5(data).hexdigest()
    if md5 != EXPECTED_MD5:
        print("校验和不匹配: 期望 %s，实际 %s" % (EXPECTED_MD5, md5), file=sys.stderr)
        return 1
    print("[hhc] MD5 校验通过 (%d 字节)" % len(data))

    offset, size = find_cab(data)
    cab = dest / "htmlhelp.cab"
    cab.write_bytes(data[offset : offset + size])
    print("[hhc] 切出 CAB: 偏移 %d，长度 %d" % (offset, size))

    # expand.exe 是 Windows 自带的 CAB 解包工具。
    # 先解到全新的子目录，避免 expand 在遇到同名文件时弹「是否覆盖」的交互提示
    # （CI 里没有 TTY，交互提问会直接把任务卡死）。
    unpack_dir = dest / "_unpack"
    if unpack_dir.exists():
        shutil.rmtree(unpack_dir)
    unpack_dir.mkdir(parents=True)
    result = subprocess.run(
        [expand_exe(), "-F:*", str(cab), str(unpack_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        print("expand 解包失败", file=sys.stderr)
        return 1

    # 把解出来的文件搬到 dest 根目录（hhc.exe 需要 hha.dll / itss.dll 与自己同级）
    for item in unpack_dir.iterdir():
        if item.is_file():
            shutil.move(str(item), str(dest / item.name))
    shutil.rmtree(unpack_dir, ignore_errors=True)

    if not hhc.is_file():
        print("解包完成但没找到 hhc.exe", file=sys.stderr)
        return 1
    print("[hhc] 编译器就绪: %s" % hhc.resolve())
    print(hhc.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
