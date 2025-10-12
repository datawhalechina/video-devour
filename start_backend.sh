#!/bin/bash

echo "===================================="
echo "  VideoDevour 后端服务器启动"
echo "===================================="
echo ""

# 检查 uv 环境
if ! command -v uv &> /dev/null; then
    echo "[错误] 未检测到 uv，请先安装 uv"
    echo "[提示] 安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "uv 版本: $(uv --version)"
echo ""

# 激活 uv 环境并安装依赖
echo "[检查] 正在同步 uv 环境和依赖..."
uv sync

if [ $? -ne 0 ]; then
    echo "[错误] uv 环境同步失败"
    exit 1
fi

echo ""
echo "[启动] 后端服务器正在启动..."
echo "[访问] http://localhost:8000"
echo "[文档] http://localhost:8000/docs"
echo "[提示] 按 Ctrl+C 停止服务器"
echo ""

cd backend/api
uv run python main.py