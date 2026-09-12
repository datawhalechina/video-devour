#!/bin/bash
# VideoDevour macOS 构建脚本（支持 arm64 / x86_64）
#
# 用法：
#   desktop/build_mac.sh                        # 按当前主机架构构建
#   desktop/build_mac.sh --arm64                # Apple Silicon
#   desktop/build_mac.sh --x64                  # Intel
#   desktop/build_mac.sh --both --sign          # 双架构都构建 + ad-hoc 签名
#
# 产物：
#   desktop/dist/arm64/VideoDevour.app
#   desktop/dist/x64/VideoDevour.app
#
# 前置：
#   - 前端已构建（frontend/dist）或本脚本自动构建
#   - 对应架构的 Python 环境与轻量依赖：
#       arm64 → .venv-lite（可用 PYTHON_ARM64 覆盖）
#       x64   → .venv-x64 （可用 PYTHON_X64 覆盖）
#   - desktop/bin/<target>/ 下已放置对应架构静态 ffmpeg / ffprobe
#     （运行 desktop/fetch_binaries.sh --all-macos 一次备齐）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_NAME="VideoDevour"
# 版本号单一来源：默认取 pyproject.toml，可用 APP_VERSION 覆盖
APP_VERSION="${APP_VERSION:-$(sed -n 's/^version *= *"\(.*\)"/\1/p' "${PROJECT_ROOT}/pyproject.toml" | head -1)}"
[ -z "${APP_VERSION}" ] && APP_VERSION="0.0.0"

BUILD_ARM64=0
BUILD_X64=0
DO_SIGN=0

for arg in "$@"; do
  case "${arg}" in
    --arm64) BUILD_ARM64=1 ;;
    --x64)   BUILD_X64=1 ;;
    --both)  BUILD_ARM64=1; BUILD_X64=1 ;;
    --sign)  DO_SIGN=1 ;;
    *) echo "未知参数: ${arg}"; exit 1 ;;
  esac
done

# 未指定架构时按主机判断（Rosetta 下 uname -m 会返回 x86_64）
if [ "${BUILD_ARM64}" -eq 0 ] && [ "${BUILD_X64}" -eq 0 ]; then
  if [ "$(uname -m)" = "arm64" ]; then BUILD_ARM64=1; else BUILD_X64=1; fi
fi

# 1. 前端产物（两个架构共用，只构建一次）
if [ ! -f "${PROJECT_ROOT}/frontend/dist/index.html" ]; then
  echo "[前端] 构建中..."
  (cd "${PROJECT_ROOT}/frontend" && npm run build)
else
  echo "[前端] 产物已存在，跳过"
fi

build_one() {
  local arch="$1"        # arm64 | x64
  local target="$2"      # macos-arm64 | macos-x64
  local py_var="$3"      # 环境变量名
  local out_dir="${SCRIPT_DIR}/dist/${arch}"
  local app_bundle="${out_dir}/${APP_NAME}.app"

  local python="${!py_var:-}"
  [ -z "${python}" ] && python="${PROJECT_ROOT}/.venv-$( [ "${arch}" = "x64" ] && echo x64 || echo lite )/bin/python"

  echo ""
  echo "=========================================="
  echo "  构建 macOS ${arch}"
  echo "  Python: ${python}"
  echo "=========================================="

  # PYTHON_<ARCH> 可以是绝对路径，也可以是 PATH 上的命令名（CI 里传 "python"）
  if ! command -v "${python}" >/dev/null 2>&1 && [ ! -x "${python}" ]; then
    echo "[错误] 找不到 ${arch} 的 Python 环境: ${python}"
    echo "       请先创建（参考 desktop/README.md 的构建章节），或设置 PYTHON_$(echo "${arch}" | tr a-z A-Z)"
    exit 1
  fi
  python="$(command -v "${python}" || echo "${python}")"
  # platform.machine() 返回 arm64 / x86_64，而脚本参数用 arm64 / x64
  local actual expect
  actual="$("${python}" -c 'import platform;print(platform.machine())')"
  expect="$([ "${arch}" = "x64" ] && echo x86_64 || echo arm64)"
  if [ "${actual}" != "${expect}" ]; then
    echo "[错误] Python 架构不匹配：期望 ${expect}（${arch}），实际 ${actual}"
    echo "       PyInstaller 输出的架构由解释器决定，必须用对应架构的 Python。"
    exit 1
  fi

  # 检查捆绑二进制（按架构目录）
  for bin in ffmpeg ffprobe; do
    if [ ! -f "${SCRIPT_DIR}/bin/${target}/${bin}" ]; then
      echo "[警告] 缺少 desktop/bin/${target}/${bin}，将回退系统 PATH"
      echo "       可运行：desktop/fetch_binaries.sh ${target}"
    fi
  done

  echo "[1/3] PyInstaller 打包（${arch}）..."
  VD_TARGET="${target}" "${python}" -m PyInstaller "${SCRIPT_DIR}/videodevour.spec" \
    --noconfirm --distpath "${out_dir}" --workpath "/tmp/vd-pyinstaller-build-${arch}"

  echo "[2/3] 组装 .app（${arch}）..."
  rm -rf "${app_bundle}"
  mkdir -p "${app_bundle}/Contents/MacOS" "${app_bundle}/Contents/Resources"

  cat > "${app_bundle}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>VideoDevour</string>
    <key>CFBundleDisplayName</key>
    <string>VideoDevour</string>
    <key>CFBundleIdentifier</key>
    <string>com.videodevour.app</string>
    <key>CFBundleVersion</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${APP_VERSION}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>VideoDevour</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
PLIST

  cp -R "${out_dir}/${APP_NAME}/." "${app_bundle}/Contents/Resources/"

  cat > "${app_bundle}/Contents/MacOS/${APP_NAME}" <<'LAUNCH'
#!/bin/bash
# .app 入口：启动同一可执行文件的壳角色（无参数）
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../Resources" && pwd)"
exec "${HERE}/VideoDevour" "$@"
LAUNCH
  chmod +x "${app_bundle}/Contents/MacOS/${APP_NAME}"

  if [ "${DO_SIGN}" -eq 1 ]; then
    echo "[3/3] ad-hoc 签名（${arch}）..."
    # 先签内部所有二进制/动态库，再签外层（顺序不能反）
    find "${app_bundle}/Contents/Resources" \
      \( -name "*.so" -o -name "*.dylib" -o -name "ffmpeg" -o -name "ffprobe" -o -name "${APP_NAME}" \) \
      -exec codesign --force --sign - {} \; 2>/dev/null || true
    codesign --force --deep --sign - "${app_bundle}"
  else
    echo "[3/3] 跳过签名（加 --sign 启用）"
  fi

  echo "完成：${app_bundle}"
  du -sh "${app_bundle}" | awk '{print "  体积: "$1}'
  file "${app_bundle}/Contents/Resources/${APP_NAME}" | grep -oE "arm64|x86_64" | head -1 | sed 's/^/  可执行架构: /'
}

if [ "${BUILD_ARM64}" -eq 1 ]; then
  build_one "arm64" "macos-arm64" "PYTHON_ARM64"
fi
if [ "${BUILD_X64}" -eq 1 ]; then
  build_one "x64" "macos-x64" "PYTHON_X64"
fi

echo ""
echo "全部完成。运行：open desktop/dist/<arch>/${APP_NAME}.app"
echo "内测若被 Gatekeeper 拦截：xattr -cr '<app 路径>'"
