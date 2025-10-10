@echo off
echo ====================================
echo   VideoDevour 前端开发服务器启动
echo ====================================
echo.

echo 正在检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

echo 正在检查依赖...
if not exist "node_modules\" (
    echo [提示] 首次运行，正在安装依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo [启动] 开发服务器正在启动...
echo [访问] http://localhost:3000
echo [提示] 按 Ctrl+C 停止服务器
echo.

npm run dev

