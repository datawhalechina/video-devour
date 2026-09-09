#!/bin/bash
# 获取桌面包所需的静态 ffmpeg / ffprobe（放入 desktop/bin/）
#
# 用法：
#   desktop/fetch_binaries.sh            # 按当前平台下载
#   desktop/fetch_binaries.sh macos      # 强制 macOS arm64
#   desktop/fetch_binaries.sh windows    # 强制 Windows x64
#
# 来源：eugeneware/ffmpeg-static（静态构建，无 homebrew/系统库动态依赖，
#       可直接随包分发；Homebrew 版本动态链接 18 个库，不可捆绑）。
# 版本：b6.0（ffmpeg 6.0）。升级需重新验证切片/抽帧/音频提取。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
BASE_URL="https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0"

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  case "$(uname -s)" in
    Darwin) TARGET="macos" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET="windows" ;;
    *) echo "未知平台，请显式指定 macos / windows"; exit 1 ;;
  esac
fi

mkdir -p "$BIN_DIR"

case "$TARGET" in
  macos)
    SUFFIX="darwin-arm64"; EXT=""
    ;;
  windows)
    SUFFIX="win32-x64"; EXT=".exe"
    ;;
  *)
    echo "不支持的目标: $TARGET（可选 macos / windows）"; exit 1
    ;;
esac

for tool in ffmpeg ffprobe; do
  dest="$BIN_DIR/$tool$EXT"
  if [ -f "$dest" ]; then
    echo "[跳过] $dest 已存在"
    continue
  fi
  echo "[下载] $tool ($SUFFIX)"
  curl -fL --retry 3 -o "$dest" "$BASE_URL/$tool-$SUFFIX"
  chmod +x "$dest" 2>/dev/null || true
done

echo ""
echo "完成，当前 desktop/bin/："
ls -la "$BIN_DIR"
