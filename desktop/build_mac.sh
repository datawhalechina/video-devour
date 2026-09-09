#!/bin/bash
# VideoDevour macOS 构建脚本（arm64）
#
# 用法：
#   desktop/build_mac.sh            # 构建 + 组装 .app
#   desktop/build_mac.sh --sign    # 额外做 ad-hoc 签名
#
# 产物：desktop/dist/VideoDevour.app
#
# 前置：
#   - 前端已构建（frontend/dist）或本脚本自动构建
#   - 轻量依赖已安装（requirements-lite.txt）+ pyinstaller + pywebview
#   - desktop/bin/ 下已放置 arm64 静态 ffmpeg / ffprobe

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
APP_NAME="VideoDevour"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

DO_SIGN="${1:-}"

echo "=========================================="
echo "  VideoDevour macOS 构建 (arm64)"
echo "=========================================="

# 1. 前端产物
if [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
  echo "[1/4] 构建前端..."
  (cd "$PROJECT_ROOT/frontend" && npm run build)
else
  echo "[1/4] 前端产物已存在，跳过"
fi

# 2. 检查捆绑二进制
for bin in ffmpeg ffprobe; do
  if [ ! -f "$SCRIPT_DIR/bin/$bin" ]; then
    echo "[警告] 缺少 desktop/bin/$bin，将回退系统 PATH"
  fi
done

# 3. PyInstaller
echo "[2/4] PyInstaller 打包..."
"$PYTHON" -m PyInstaller "$SCRIPT_DIR/videodevour.spec" \
  --noconfirm --distpath "$DIST_DIR" --workpath /tmp/vd-pyinstaller-build

# 4. 组装 .app
echo "[3/4] 组装 .app 包..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

cat > "$APP_BUNDLE/Contents/Info.plist" <<'PLIST'
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
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>VideoDevour</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
PLIST

# 资源全部放 Resources，MacOS 下只放启动脚本
cp -R "$DIST_DIR/$APP_NAME/." "$APP_BUNDLE/Contents/Resources/"

cat > "$APP_BUNDLE/Contents/MacOS/$APP_NAME" <<'LAUNCH'
#!/bin/bash
# .app 入口：启动同一可执行文件的壳角色（无参数）
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../Resources" && pwd)"
exec "$HERE/VideoDevour" "$@"
LAUNCH
chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# 5. 签名（可选）
if [ "$DO_SIGN" = "--sign" ]; then
  echo "[4/4] ad-hoc 签名..."
  # 先签内部所有二进制/动态库，再签外层（顺序不能反）
  find "$APP_BUNDLE/Contents/Resources" \( -name "*.so" -o -name "*.dylib" -o -name "ffmpeg" -o -name "ffprobe" -o -name "VideoDevour" \) \
    -exec codesign --force --sign - {} \; 2>/dev/null || true
  codesign --force --deep --sign - "$APP_BUNDLE"
  echo "  已 ad-hoc 签名（正式分发需开发者证书 + 公证）"
else
  echo "[4/4] 跳过签名（加 --sign 启用 ad-hoc 签名）"
fi

echo ""
echo "构建完成：$APP_BUNDLE"
du -sh "$APP_BUNDLE"
echo ""
echo "运行：open '$APP_BUNDLE'"
echo "内测若被 Gatekeeper 拦截：xattr -cr '$APP_BUNDLE'"
