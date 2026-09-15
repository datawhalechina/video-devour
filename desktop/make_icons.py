#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 desktop/assets/icon-source.png 生成各平台应用图标。

产物（均已入库，正常构建不需要跑本脚本；换图标时才需要）：
    desktop/assets/icon-1024.png          1024 主图（去白底、裁边、方形留白）
    desktop/assets/VideoDevour.icns       macOS 应用图标（build_mac.sh 使用）
    desktop/assets/VideoDevour.ico        Windows 应用图标（spec / installer.iss 使用）
    frontend/public/favicon-32.png        网页标签页图标
    frontend/public/apple-touch-icon.png  添加到主屏幕图标
    frontend/public/icon-512.png          PWA / 分享大图

用法：
    python3 desktop/make_icons.py          # 生成全部
    （.icns 需要 macOS 的 iconutil；其他平台会跳过并提示）

说明：源图是白底插画，脚本用「四角泛洪」只把外部白底转透明，
鲸鱼腹部的白色与牙齿不会被误删。
"""
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

from PIL import Image

DESKTOP = Path(__file__).resolve().parent
ROOT = DESKTOP.parent
SOURCE = DESKTOP / "assets" / "icon-source.png"
MASTER = DESKTOP / "assets" / "icon-1024.png"
ICONSET = DESKTOP / "assets" / "VideoDevour.iconset"
ICNS = DESKTOP / "assets" / "VideoDevour.icns"
ICO = DESKTOP / "assets" / "VideoDevour.ico"
PUBLIC = ROOT / "frontend" / "public"

# macOS 图标惯例：主体约占画布 88%（四周留约 6% 白边），小尺寸下更饱满清晰
CONTENT_RATIO = 0.88
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ICONSET_SIZES = [
    (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
]


def strip_external_white(img: Image.Image, tol: int = 28) -> Image.Image:
    """把背景白转透明：从四角泛洪，只清除与边缘连通的白色区域。"""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def near_white(c):
        r, g, b, a = c
        return a > 0 and r >= 255 - tol and g >= 255 - tol and b >= 255 - tol

    seen = [[False] * w for _ in range(h)]
    queue = deque()
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if near_white(px[sx, sy]) and not seen[sy][sx]:
            seen[sy][sx] = True
            queue.append((sx, sy))
    while queue:
        x, y = queue.popleft()
        px[x, y] = (255, 255, 255, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and near_white(px[nx, ny]):
                seen[ny][nx] = True
                queue.append((nx, ny))
    return img


def build_master() -> Image.Image:
    src = strip_external_white(Image.open(SOURCE))
    content = src.crop(src.getbbox())
    cw, ch = content.size
    side = int(max(cw, ch) / CONTENT_RATIO)
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    canvas.paste(content, ((side - cw) // 2, (side - ch) // 2), content)
    master = canvas.resize((1024, 1024), Image.LANCZOS)
    master.save(MASTER)
    print(f"[1/4] 主图 {cw}x{ch} → {MASTER.name} (1024x1024，主体占 {int(CONTENT_RATIO * 100)}%)")
    return master


def build_ico(master: Image.Image):
    master.save(ICO, format="ICO", sizes=ICO_SIZES)
    print(f"[2/4] Windows 图标 → {ICO.name} ({len(ICO_SIZES)} 个尺寸)")


def build_icns(master: Image.Image):
    if sys.platform != "darwin" or not shutil.which("iconutil"):
        print("[3/4] 跳过 .icns（需要 macOS + iconutil）；构建 macOS 包时请在本机生成")
        return
    shutil.rmtree(ICONSET, ignore_errors=True)
    ICONSET.mkdir(parents=True)
    for size, name in ICONSET_SIZES:
        master.resize((size, size), Image.LANCZOS).save(ICONSET / name)
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], check=True)
    print(f"[3/4] macOS 图标 → {ICNS.name} ({len(ICONSET_SIZES)} 个尺寸)")


def build_web(master: Image.Image):
    for size, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (512, "icon-512.png")):
        master.resize((size, size), Image.LANCZOS).save(PUBLIC / name)
    print("[4/4] 网页图标 → favicon-32.png / apple-touch-icon.png / icon-512.png")


def main():
    if not SOURCE.is_file():
        sys.exit(f"错误：找不到源图 {SOURCE}")
    master = build_master()
    build_ico(master)
    build_icns(master)
    build_web(master)
    print("\n完成。换图标后请重新构建客户端（desktop/build_mac.sh / build_win.ps1）。")


if __name__ == "__main__":
    main()
