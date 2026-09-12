#!/bin/bash
# 获取桌面包所需的静态 ffmpeg / ffprobe
#
# 用法：
#   desktop/fetch_binaries.sh                  # 按当前主机平台/架构下载
#   desktop/fetch_binaries.sh macos-arm64      # macOS Apple Silicon
#   desktop/fetch_binaries.sh macos-x64        # macOS Intel
#   desktop/fetch_binaries.sh windows-x64      # Windows x64
#   desktop/fetch_binaries.sh --all-macos      # macOS 双架构都下
#
# 存放位置（按架构分目录，双架构可共存）：
#   desktop/bin/<target>/ffmpeg[.exe]
#
# 来源：eugeneware/ffmpeg-static（静态构建，不依赖 homebrew/系统库，可随包分发；
#       Homebrew 版本动态链接 18 个库，不可捆绑）。
# 版本：b6.0（ffmpeg 6.0）。升级需重新验证切片/抽帧/音频提取。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_ROOT="${SCRIPT_DIR}/bin"
BASE_URL="https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0"

# target 名 → ffmpeg-static 的 release 文件后缀
suffix_for() {
  case "$1" in
    macos-arm64)   echo "darwin-arm64" ;;
    macos-x64)     echo "darwin-x64" ;;
    windows-x64)   echo "win32-x64" ;;
    *) return 1 ;;
  esac
}

ext_for() {
  case "$1" in
    windows-*) echo ".exe" ;;
    *)         echo "" ;;
  esac
}

fetch_target() {
  local target="$1"
  local suffix ext dir
  suffix="$(suffix_for "${target}")" || { echo "不支持的目标: ${target}"; return 1; }
  ext="$(ext_for "${target}")"
  dir="${BIN_ROOT}/${target}"
  mkdir -p "${dir}"

  for tool in ffmpeg ffprobe; do
    local dest="${dir}/${tool}${ext}"
    if [ -f "${dest}" ]; then
      echo "[跳过] ${target}/${tool}（已存在）"
      continue
    fi
    echo "[下载] ${target}/${tool}  (${suffix})"
    curl -fL --retry 3 -o "${dest}" "${BASE_URL}/${tool}-${suffix}"
    chmod +x "${dest}" 2>/dev/null || true
  done
}

TARGETS=()
case "${1:-}" in
  --all-macos) TARGETS=(macos-arm64 macos-x64) ;;
  "") 
    case "$(uname -s)-$(uname -m)" in
      Darwin-arm64) TARGETS=(macos-arm64) ;;
      Darwin-x86_64) TARGETS=(macos-x64) ;;
      MINGW*|MSYS*|CYGWIN*) TARGETS=(windows-x64) ;;
      *) echo "未知平台，请显式指定目标"; exit 1 ;;
    esac
    ;;
  *) TARGETS=("$1") ;;
esac

for t in "${TARGETS[@]}"; do
  fetch_target "${t}"
done

echo ""
echo "完成，desktop/bin/ 现状："
find "${BIN_ROOT}" -type f -not -name ".DS_Store" | sort | while read -r f; do
  printf "  %s\n" "${f#"${BIN_ROOT}"/}"
done
