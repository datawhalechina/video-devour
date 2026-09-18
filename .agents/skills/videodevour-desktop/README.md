# videodevour-desktop

VideoDevour 桌面客户端的**打包、签名、发版与热更新**经验沉淀。

面向维护者（不是终端用户）。触发场景：

- 要求打包/构建客户端（macOS `.app`、Windows 安装包）
- 要求发版/release
- 客户端出问题：装不上、打开报错、功能在开发模式正常但客户端里失效
- 要做热更新/自动更新

## 文件

| 文件 | 用途 |
|------|------|
| `SKILL.md` | 主入口：硬约束、构建环境、常用操作、排错索引 |
| `references/pitfalls.md` | **20 项打包坑清单**，按现象索引——排错先查这里 |
| `references/release-checklist.md` | 发版 7 步检查清单（可直接执行） |
| `references/update-design.md` | 热更新设计（三层可行性、弹窗、边界） |
| `scripts/verify_bundle.sh` | **发版前校验产物**：签名 seal / symlink / 架构 / 模块收录 |

## 最该记住的三件事

1. **开发模式正常 ≠ 客户端正常**。冻结环境（PyInstaller）有独立的故障模式，占本 skill 收录坑位的一半以上。

2. **macOS 签名与 symlink 是分发的生死线**。签名后改 bundle 内任何文件、或打包流程丢 symlink（~109 个），都会让用户看到"已损坏，无法打开"，且 `xattr -cr` 无效。

3. **发版前必须跑 `verify_bundle.sh`**。它能在 30 秒内抓出上述问题——已用真实的坏包反向验证过。

## 快速开始

```bash
# 校验已有产物
bash .agents/skills/videodevour-desktop/scripts/verify_bundle.sh desktop/dist/arm64/VideoDevour.app --expect-arch arm64

# 完整构建（macOS 双架构 + 签名）
./desktop/fetch_binaries.sh --all-macos
PYTHON_ARM64=$PWD/.venv-lite/bin/python PYTHON_X64=$PWD/.venv-x64/bin/python \
  ./desktop/build_mac.sh --both --sign

# 发版
# → 见 references/release-checklist.md
```

## 相关文档（项目内）

- `desktop/README.md` —— 客户端构建说明（面向开发者）
- `planning/桌面客户端化方案.md` —— 整体方案与阶段规划
- `planning/A3-A4-构建验证报告.md` —— 实测数据与缺陷编号（本 skill 的坑位编号与之对应）
