#!/usr/bin/env bash
# 本地离线 ASR（FunASR Paraformer V2）按需安装 / 排查脚本
#
# 用法：
#   bash scripts/install_offline_asr.sh --check     # 仅检查环境与模型（只读，推荐先跑）
#   bash scripts/install_offline_asr.sh             # 安装依赖 + 下载模型
#   bash scripts/install_offline_asr.sh --deps      # 只装依赖（torch/funasr 等）
#   bash scripts/install_offline_asr.sh --models    # 只下载模型
#
# 说明：
#   离线 ASR 需要 torch/funasr/modelscope（约 2-3GB）+ 本地模型（约 2GB），
#   首次安装耗时且吃磁盘/内存。**默认不安装**——新用户使用在线 ASR 即可。
#   仅在你需要断网/隐私场景下离线识别时再运行本脚本。
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
MODELS_DIR="$PROJECT_ROOT/models/iic"

# 离线引擎需要的模型目录（与 asr_engine_paraformer_v2._ensure_models_available 对应）
REQUIRED_MODELS="speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
speech_fsmn_vad_zh-cn-16k-common-pytorch
punc_ct-transformer_zh-cn-common-vocab272727-pytorch
speech_campplus_sv_zh-cn_16k-common"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }
info() { printf "  · %s\n" "$1"; }

echo "=========================================="
echo "  本地离线 ASR 环境检查"
echo "=========================================="
echo "项目目录: $PROJECT_ROOT"
echo "Python:   $PYTHON"
echo

# ---- 1. 依赖检查 ----
echo "[1/4] Python 依赖"
MISSING_DEPS=()
for mod in torch funasr modelscope; do
  if "$PYTHON" -c "import $mod" 2>/dev/null; then
    ver=$("$PYTHON" -c "import $mod; print(getattr($mod, '__version__', '?'))" 2>/dev/null)
    ok "$mod ($ver)"
  else
    bad "$mod 未安装"
    MISSING_DEPS+=("$mod")
  fi
done
echo

# ---- 2. 加速后端检查 ----
echo "[2/4] 计算后端"
"$PYTHON" - <<'PYEOF_INNER' || true
try:
    import torch
    if torch.cuda.is_available():
        print("  ✓ CUDA 可用:", torch.cuda.get_device_name(0))
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        print("  ✓ Apple MPS 可用（Apple Silicon GPU 加速）")
    else:
        print("  · 仅 CPU（可运行，但较慢）")
except Exception:
    print("  · torch 未安装，无法检测")
PYEOF_INNER
echo

# ---- 3. 模型目录检查 ----
echo "[3/4] 本地模型目录: $MODELS_DIR"
MODEL_MISSING_COUNT=0
while IFS= read -r m; do
  [ -z "$m" ] && continue
  if [ -d "$MODELS_DIR/$m" ] && [ -n "$(ls -A "$MODELS_DIR/$m" 2>/dev/null)" ]; then
    ok "$m"
  else
    bad "$m 缺失"
    MODEL_MISSING_COUNT=$((MODEL_MISSING_COUNT + 1))
  fi
done <<EOF
$REQUIRED_MODELS
EOF
echo

# ---- 4. ffmpeg ----
echo "[4/4] ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then ok "ffmpeg 可用"; else bad "ffmpeg 未安装"; fi
echo

# ---- 汇总 ----
echo "=========================================="
if [ ${#MISSING_DEPS[@]} -eq 0 ] && [ "$MODEL_MISSING_COUNT" -eq 0 ]; then
  echo "结论：离线 ASR 环境就绪 ✅"
  echo "在设置页把「语音识别模式」切到「离线」即可使用。"
  exit 0
fi
echo "结论：离线 ASR 尚未就绪"
[ ${#MISSING_DEPS[@]} -gt 0 ] && echo "  缺少依赖: ${MISSING_DEPS[*]}"
[ "$MODEL_MISSING_COUNT" -gt 0 ] && echo "  缺少模型: $MODEL_MISSING_COUNT 个"
echo
echo "修复方式（任选其一）："
echo "  1) 一键安装: bash scripts/install_offline_asr.sh"
echo "  2) 只装依赖: bash scripts/install_offline_asr.sh --deps"
echo "  3) 只下模型: bash scripts/install_offline_asr.sh --models"
echo "  4) 无需离线: 在设置页保持「在线」ASR（推荐，零下载）"
echo

# ---- 按参数执行安装 ----
MODE="${1:-all}"
if [ "$MODE" = "--check" ]; then
  exit 1
fi

if [ "$MODE" = "--deps" ] || [ "$MODE" = "all" ]; then
  echo ">>> 安装 Python 依赖（torch/funasr/modelscope，约 2-3GB，耐心等待）..."
  "$PYTHON" -m pip install torch funasr "modelscope[audio]" soundfile 2>&1 | tail -5
  echo ">>> 依赖安装完成"
fi

if [ "$MODE" = "--models" ] || [ "$MODE" = "all" ]; then
  echo ">>> 下载本地模型到 $MODELS_DIR（约 2GB，可用 MODELSCOPE_CACHE 指定缓存）..."
  mkdir -p "$MODELS_DIR"
  MODELS_DIR="$MODELS_DIR" "$PYTHON" - <<'PYEOF_INNER' || true
import os, sys
from pathlib import Path
models_dir = Path(os.environ["MODELS_DIR"])
try:
    from modelscope.hub.snapshot_download import snapshot_download
except Exception as e:
    print("  无法导入 modelscope:", e); sys.exit(1)

ids = [
    "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
    "iic/speech_campplus_sv_zh-cn_16k-common",
]
for mid in ids:
    name = mid.split("/", 1)[1]
    target = models_dir / name
    if target.exists() and any(target.iterdir()):
        print(f"  已存在，跳过: {name}")
        continue
    print(f"  下载中: {mid}")
    try:
        # 下载到项目 models/iic/<name>（下游按此路径查找）
        cache = snapshot_download(mid, cache_dir=str(models_dir / ".cache"))
        src = Path(cache)
        if target.exists():
            import shutil; shutil.rmtree(target)
        shutil.copytree(src, target)
        print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ {name} 失败: {str(e)[:150]}")
PYEOF_INNER
  echo ">>> 模型下载完成"
fi

echo
echo "完成后重新运行自检: bash scripts/install_offline_asr.sh --check"
