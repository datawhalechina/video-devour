#!/usr/bin/env bash
# 安装 YouTube PO Token 支持（bgutil script 模式，node 生成 PO Token）
# 用法：bash scripts/install_yt_pot.sh
# 前置：git、node/npm（前端开发环境通常已具备）
set -e

TARGET="$HOME/bgutil-ytdlp-pot-provider"

if [ ! -f "$TARGET/server/build/generate_once.js" ]; then
  if [ ! -d "$TARGET" ]; then
    echo "[1/3] 克隆 bgutil-ytdlp-pot-provider ..."
    git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$TARGET"
  fi
  echo "[2/3] 安装依赖并编译 ..."
  cd "$TARGET/server"
  npm install --silent
  npx tsc
else
  echo "已安装，跳过编译：$TARGET/server/build/generate_once.js"
fi

echo "[3/3] 完成。"
echo "VideoDevour 会在 YouTube 下载时自动使用该脚本（无需常驻服务）。"
echo "如需手动指定路径，可设置环境变量 BGUTIL_POT_SCRIPT。"
