#!/bin/bash
# VideoDevour 服务启动（局域网可访问）
#
# 用法：
#   ./start.sh              # 监听 0.0.0.0:8000，同一局域网的其他电脑都能访问
#   PORT=9000 ./start.sh    # 换端口
#   ./start.sh --dev        # 开发模式：热重载（代码改动自动生效）
#
# 访问：
#   本机        http://localhost:8000
#   其他电脑    http://<本机局域网IP>:8000
#              （macOS 查看 IP：ipconfig getifaddr en0）
#
# 说明：后端会一并提供前端页面、API 与关键帧图片，单端口即可，无需另开前端服务。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD=""
if [ "${1:-}" = "--dev" ]; then
  RELOAD=1
  echo "[模式] 开发模式（热重载）：修改后端代码会自动生效"
fi

# 1. 安装依赖（生产默认不重装，用 --sync 强制）
if [ "${1:-}" = "--sync" ] || [ "${2:-}" = "--sync" ]; then
  echo "[检查] 同步依赖..."
  uv sync
fi

# 2. 前端构建产物：缺失则构建（后端直接托管 frontend/dist）
if [ ! -f "$SCRIPT_DIR/frontend/dist/index.html" ]; then
  echo "[构建] 未找到前端产物，正在构建 frontend/dist ..."
  (cd "$SCRIPT_DIR/frontend" && npm install && npm run build)
fi

# 3. 本机局域网 IP（供其他电脑访问）
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"

echo "===================================="
echo "  VideoDevour 服务启动中"
echo "===================================="
echo "  监听      ${HOST}:${PORT}"
echo "  本机      http://localhost:${PORT}"
[ -n "${LAN_IP:-}" ] && echo "  局域网    http://${LAN_IP}:${PORT}"
echo "  API 文档  http://localhost:${PORT}/docs"
echo "  Ctrl+C 停止"
echo ""

# 后端同时托管前端页面 + API，因此单端口对外服务。
# 从项目根目录启动，模块路径 backend.api.main 才可导入（热重载依赖）。
cd "$SCRIPT_DIR"
HOST="$HOST" PORT="$PORT" RELOAD="$RELOAD" exec uv run python backend/api/main.py
