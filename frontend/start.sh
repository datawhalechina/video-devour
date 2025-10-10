#!/bin/bash

echo "===================================="
echo "  VideoDevour 前端开发服务器启动"
echo "===================================="
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[错误] 未检测到 Node.js，请先安装 Node.js"
    exit 1
fi

echo "Node.js 版本: $(node --version)"
echo "npm 版本: $(npm --version)"
echo ""

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "[提示] 首次运行，正在安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo ""
echo "[启动] 开发服务器正在启动..."
echo "[访问] http://localhost:3000"
echo "[提示] 按 Ctrl+C 停止服务器"
echo ""

npm run dev

