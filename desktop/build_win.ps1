<#
VideoDevour Windows 构建脚本（x64）

用法（在 Windows 上执行）：
    powershell -ExecutionPolicy Bypass -File desktop\build_win.ps1

产物：
    desktop\dist\VideoDevour\            # onedir 目录
    desktop\dist\VideoDevour-<版本>-setup.exe   # Inno Setup 安装包（若已安装 iscc）

前置：
    - Python 3.12 + 轻量依赖（requirements-lite.txt）+ pyinstaller + pywebview
    - Node.js（构建前端）
    - desktop\bin\ 下放置 ffmpeg.exe / ffprobe.exe（Windows 静态构建）
    - 可选：Inno Setup 6（ISCC.exe 在 PATH）
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DistDir = Join-Path $ScriptDir "dist"
$Python = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $ProjectRoot ".venv\Scripts\python.exe" }

Write-Host "=========================================="
Write-Host "  VideoDevour Windows 构建 (x64)"
Write-Host "=========================================="

# 1. 前端产物
$FrontendIndex = Join-Path $ProjectRoot "frontend\dist\index.html"
if (-not (Test-Path $FrontendIndex)) {
    Write-Host "[1/4] 构建前端..."
    Push-Location (Join-Path $ProjectRoot "frontend")
    npm run build
    Pop-Location
} else {
    Write-Host "[1/4] 前端产物已存在，跳过"
}

# 2. 检查捆绑二进制
foreach ($bin in @("ffmpeg.exe", "ffprobe.exe")) {
    $p = Join-Path $ScriptDir "bin\$bin"
    if (-not (Test-Path $p)) {
        Write-Warning "缺少 desktop\bin\$bin，将回退系统 PATH"
    }
}

# 3. PyInstaller
Write-Host "[2/4] PyInstaller 打包..."
& $Python -m PyInstaller (Join-Path $ScriptDir "videodevour.spec") `
    --noconfirm --distpath $DistDir --workpath "$env:TEMP\vd-pyinstaller-build"

# 4. Inno Setup 安装包
Write-Host "[3/4] 检查 Inno Setup..."
$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($Iscc) {
    Write-Host "[4/4] 生成安装包..."
    & $Iscc.Source (Join-Path $ScriptDir "installer.iss")
    Write-Host "安装包已生成于 desktop\dist\"
} else {
    Write-Host "[4/4] 未检测到 Inno Setup，跳过安装包（目录版可直接运行）"
    Write-Host "      安装 Inno Setup 6 后重试：winget install JRSoftware.InnoSetup"
}

Write-Host ""
Write-Host "构建完成：$DistDir\VideoDevour"
Write-Host ""
Write-Host "注意：对外分发前必须完成代码签名（详见 planning/桌面客户端化方案.md 第 6.3 节）"
