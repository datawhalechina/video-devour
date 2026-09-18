#!/bin/bash
# 校验 macOS 产物是否可安全分发。
#
# 用法：
#   verify_bundle.sh desktop/dist/arm64/VideoDevour.app
#   verify_bundle.sh <path/to/VideoDevour.app> --expect-arch x86_64
#
# 检查项（任一失败即退出码 1）：
#   1. 签名 seal 完整            —— 损坏的包 Gatekeeper 会判"已损坏，无法打开"
#   2. symlink 数量 > 0          —— 为 0 说明经过丢链接的打包流程（如 upload-artifact）
#   3. 架构一致性                —— 主程序/ffmpeg/关键扩展模块架构必须相同
#   4. 关键模块与依赖已收录      —— 冻结环境特有，缺失会在运行期才暴露
#   5. 版本号与 Info.plist 一致
#
# 设计背景见 references/pitfalls.md（E1/E2、C1-C3、D1）

set -uo pipefail

APP="${1:-}"
shift || true

EXPECT_ARCH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --expect-arch) EXPECT_ARCH="${2:-}"; shift 2 ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done

if [ -z "${APP}" ] || [ ! -d "${APP}" ]; then
  echo "用法: $0 <path/to/VideoDevour.app> [--expect-arch arm64|x86_64]"
  exit 2
fi

RES="${APP}/Contents/Resources"
INTERNAL="${RES}/_internal"
EXE="${RES}/VideoDevour"
FAIL=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; FAIL=1; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

arch_of() { file "$1" 2>/dev/null | grep -oE 'arm64|x86_64' | head -1; }

echo "校验: ${APP}"

# ---------- 1. 签名 seal ----------
echo "[1/5] 签名"
if codesign --verify --deep --strict "${APP}" 2>/dev/null; then
  ok "seal 完整"
else
  bad "签名校验失败 —— 该包会被 Gatekeeper 判「已损坏，无法打开」"
  echo "      诊断: codesign --verify --deep --strict '${APP}'"
fi
if codesign -dv "${APP}" 2>&1 | grep -q "adhoc"; then
  warn "ad-hoc 签名（未公证）：用户需 xattr -cr，且不能做整包自动更新"
fi

# ---------- 2. symlink ----------
echo "[2/5] 符号链接"
LINKS=$(find "${APP}" -type l 2>/dev/null | wc -l | tr -d ' ')
if [ "${LINKS}" -gt 0 ]; then
  ok "symlink ${LINKS} 个"
else
  bad "symlink 为 0 —— 打包流程丢弃了符号链接（已知：upload-artifact 不保留）"
  echo "      修法: 用 ditto -c -k --keepParent 打 zip；见 pitfalls.md E1"
fi

# ---------- 3. 架构一致性 ----------
echo "[3/5] 架构"
MAIN_ARCH=$(arch_of "${EXE}")
if [ -z "${MAIN_ARCH}" ]; then
  bad "无法识别主程序架构: ${EXE}"
else
  ok "主程序: ${MAIN_ARCH}"
  if [ -n "${EXPECT_ARCH}" ] && [ "${MAIN_ARCH}" != "${EXPECT_ARCH}" ]; then
    bad "架构与预期不符（期望 ${EXPECT_ARCH}）"
  fi
fi
MISMATCH=0
for f in "${INTERNAL}/bin/ffmpeg" "${INTERNAL}/bin/ffprobe"; do
  [ -f "$f" ] || continue
  A=$(arch_of "$f")
  [ "$A" = "${MAIN_ARCH}" ] || { bad "架构不一致: $f = ${A:-未知}（主程序 ${MAIN_ARCH}）"; MISMATCH=1; }
done
# 关键扩展模块抽查
for so in $(find "${INTERNAL}" -maxdepth 2 -name "_rust.abi3.so" -o -maxdepth 2 -name "cv2*.so" -o -maxdepth 2 -name "_pydantic_core*.so" 2>/dev/null | head -3); do
  A=$(arch_of "$so")
  [ "$A" = "${MAIN_ARCH}" ] || { bad "架构不一致: $(basename "$so") = ${A:-未知}"; MISMATCH=1; }
done
[ "${MISMATCH}" -eq 0 ] && ok "捆绑二进制与扩展模块架构一致"

# ---------- 4. 关键模块与依赖 ----------
# 注意：项目模块与多数纯 Python 包都在 PYZ 归档内（无实体文件），
# 因此不能只用 find 查文件——必须优先检查 PYZ 清单，实体文件仅作补充。
echo "[4/5] 关键模块"
PYZ_TOC=""
for cand in /tmp/vd-pyinstaller-build-*/videodevour/PYZ-00.toc; do
  [ -f "${cand}" ] && PYZ_TOC="${cand}" && break
done

in_pyz() { # $1=模块名
  [ -n "${PYZ_TOC}" ] && grep -q "'$1'" "${PYZ_TOC}" 2>/dev/null
}
check_any() { # $1=描述 $2=PYZ模块名 $3=实体路径glob(可空)
  if in_pyz "$2"; then ok "$1"
  elif [ -n "${3:-}" ] && find "${APP}" -path "$3" 2>/dev/null | head -1 | grep -q .; then ok "$1"
  elif [ -z "${PYZ_TOC}" ] && [ -z "${3:-}" ]; then warn "$1（无 PYZ 清单可查，建议运行期验证）"
  else bad "缺少 $1（PYZ:$2${3:+ / 实体:$3}）"; fi
}
check_any "vlm_handler（关键帧选择）" "backend.algorithm.vlm_handler" ""
check_any "pdf_export（PDF 导出）"      "backend.algorithm.pdf_export" ""
check_any "reportlab（PDF 依赖）"       "reportlab" "*/reportlab/__init__.py*"
check_any "tiktoken_ext（token 计数）"  "tiktoken_ext" "*/tiktoken_ext/*"
check_any "cryptography rust binding"   "cryptography.hazmat.bindings._rust" "*/cryptography/hazmat/bindings/_rust*.so"

if [ -z "${PYZ_TOC}" ]; then
  warn "未找到 PYZ 清单（构建中间产物已清理）——模块检查仅覆盖实体文件部分"
fi

# 检查 PYZ 中 backend 模块总数（防"命名空间包导致收集失效"，见 pitfalls C1）
if [ -n "${PYZ_TOC}" ]; then
  ALG_N=$(grep -oE "'backend\.algorithm\.[a-z_]+'" "${PYZ_TOC}" 2>/dev/null | sort -u | wc -l | tr -d ' ')
  if [ "${ALG_N}" -ge 18 ]; then ok "backend.algorithm 收录 ${ALG_N} 个模块"
  else bad "backend.algorithm 仅收录 ${ALG_N} 个（应 ≥18，检查 spec 的模块枚举）"; fi
fi

# 固化的依赖版本（见 pitfalls D1）
CRYPTO_V=$(find "${APP}" -maxdepth 4 -name "cryptography-*" -type d 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ -n "${CRYPTO_V}" ]; then
  [ "${CRYPTO_V}" = "46.0.4" ] && ok "cryptography == 46.0.4（已固化）" \
    || warn "cryptography ${CRYPTO_V}（x64 上 50.x 会因 OpenSSL 符号缺失导致在线 ASR 失败）"
fi

# ---------- 5. 版本号 ----------
echo "[5/5] 版本"
ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PLIST_V=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "${APP}/Contents/Info.plist" 2>/dev/null)
PYPROJ_V=$(sed -n 's/^version *= *"\(.*\)"/\1/p' "${ROOT_DIR}/pyproject.toml" 2>/dev/null | head -1)
if [ -n "${PLIST_V}" ]; then
  ok "Info.plist 版本: ${PLIST_V}"
  # 本地产物可能落后于 pyproject（开发中间态），仅提示不判失败
  [ -n "${PYPROJ_V}" ] && [ "${PLIST_V}" != "${PYPROJ_V}" ] \
    && warn "与 pyproject.toml (${PYPROJ_V}) 不一致——发版前请重新构建" || true
else
  bad "无法读取 Info.plist 版本号"
fi

echo
if [ "${FAIL}" -eq 0 ]; then
  printf "\033[32m通过：产物可分发\033[0m\n"
  echo "提示：发版前还应在用户目录做一次启动冒烟（勿在 /tmp，XProtect 首次扫描会放大耗时）"
else
  printf "\033[31m存在失败项，不要分发此产物\033[0m\n"
fi
exit "${FAIL}"
