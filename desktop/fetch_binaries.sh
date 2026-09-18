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
#
# 可靠性：GitHub release 直连偶发 504 / 超时（CI 曾因此整轮失败），故带
# 重试 + 断点续传，主源不可用后回退镜像源。全部失败才算失败。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_ROOT="$SCRIPT_DIR/bin"
BASE_URL="https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0"
# 镜像源：同一 release 的 CDN 入口（主源不可用时兜底）
MIRROR_URL="https://cdn.jsdelivr.net/gh/eugeneware/ffmpeg-static@b6.0"

# target 名 -> release 文件后缀
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

# 下载单个文件：重试 + 断点续传
fetch_one() { # $1=url $2=dest $3=label
  local url="$1" dest="$2" label="$3" i
  for i in 1 2 3; do
    echo "    [$i/3] 下载 ${label}"
    # -C - 断点续传：中途网络中断不必从头再来
    if curl -fL --retry 3 --retry-delay 3 --connect-timeout 30 --max-time 900 \
            -C - -o "${dest}" "${url}" 2>/dev/null && [ -s "${dest}" ]; then
      echo "      成功"
      return 0
    fi
    echo "      失败，重试"
    sleep 5
  done
  return 1
}

fetch_target() {
  local target="$1"
  local suffix ext dir
  suffix="$(suffix_for "$target")" || { echo "不支持的目标: $target"; return 1; }
  ext="$(ext_for "$target")"
  dir="$BIN_ROOT/$target"
  mkdir -p "$dir"

  for tool in ffmpeg ffprobe; do
    local dest="$dir/$tool$ext"
    if [ -f "${dest}" ] && [ -s "${dest}" ]; then
      echo "[跳过] ${target}/${tool}（已存在）"
      continue
    fi

    local file="${tool}-${suffix}"
    echo "[下载] ${target}/${tool}"
    # 主源 -> 镜像源
    if ! fetch_one "${BASE_URL}/${file}" "${dest}" "${file}"; then
      echo "    主源不可用，尝试镜像源"
      if ! fetch_one "${MIRROR_URL}/${file}" "${dest}" "${file}"; then
        echo "[错误] ${tool} 下载失败（主源与镜像均不可达）"
        echo "       请手动下载后放到: ${dest}"
        echo "       主源: ${BASE_URL}/${file}"
        exit 1
      fi
    fi
    chmod +x "${dest}" 2>/dev/null || true

    # 基本校验：能执行并输出版本（防半截文件）
    local ver
    ver="$("${dest}" -version 2>&1 | head -1)" || true
    if [ -z "${ver}" ]; then
      echo "[错误] ${dest} 无法执行（下载可能损坏）"
      exit 1
    fi
    echo "    OK ${ver:0:60}"
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
  fetch_target "$t"
done

echo ""
echo "完成，desktop/bin/ 现状："
find "$BIN_ROOT" -type f -not -name ".DS_Store" | sort | while read -r f; do
  printf "  %s\n" "${f#"$BIN_ROOT"/}"
done
