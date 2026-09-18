# 发版检查清单

> 基于 v0.1.0 → v0.1.6 的实际发版流程。每步都可执行，不要跳步。
> **原则**：宁可多等一次 CI，也不要发出一个用户装不上的包。

---

## 0. 前置确认

```bash
git fetch origin
git log --oneline origin/main -5          # 确认待发内容
gh release list | head -3                 # 确认上一个版本号
grep "^version" pyproject.toml            # 当前版本号
```

- [ ] 待发修复都已合并进 `main`（**不是**只在某个分支上）
- [ ] 上个 release 的产物没有已知致命问题（若有，本版 release notes 要写明"请更换本版"）
- [ ] 本地工作区没有会把内容混进发版的未提交改动 —— `git status`

> ⚠️ **有未推送的本地提交时先确认**：不要替用户决定是否发布未推送的工作。只基于 `origin/main` 发版是安全默认。

## 1. 升版本号

```bash
git checkout -b chore/bump-<x.y.z> origin/main
sed -i '' 's/^version = "<旧>"/version = "<新>"/' pyproject.toml
sed -i '' 's/#define AppVersion "<旧>"/#define AppVersion "<新>"/' desktop/installer.iss
```

- [ ] `pyproject.toml` 与 `installer.iss` **两处都改**（macOS `.app` 版本号从 `pyproject.toml` 自动读取，无需手改）
- [ ] 从 `origin/main` 建分支（避免带入未推送的本地提交）

## 2. 提 PR 并等 CI

```bash
git add pyproject.toml desktop/installer.iss
git commit -m "chore: 版本号升级至 <x.y.z>"
git push -u origin chore/bump-<x.y.z>
gh pr create --base main --head chore/bump-<x.y.z> --title "chore: 版本号升级至 <x.y.z>" --body "..."
gh pr checks <PR号>          # 等三平台全 pass
gh pr merge <PR号> --merge
```

- [ ] 三个 job 全绿：macOS arm64 / macOS x86_64 (Intel) / Windows x64
- [ ] CI 里的「解压回验签名」步骤通过（这是防 E1 类损坏的闸门）

> CI run 编号记录：`gh run list --branch chore/bump-<x.y.z> --limit 1 --json databaseId`

## 3. 取产物

```bash
RID=<CI run id>
gh api "repos/<owner>/<repo>/actions/runs/$RID/artifacts" \
  --jq '.artifacts[] | "\(.name)  \(.size_in_bytes/1048576|floor)MB  id=\(.id)"'
```

四个 artifact：`VideoDevour-macos-arm64`、`VideoDevour-macos-x64`、`VideoDevour-windows-x64`、`VideoDevour-windows-x64-installer`

```bash
# 下载（注意：不要加 -H "Accept: application/octet-stream"，会 415）
curl -sL --retry 3 -H "Authorization: token $(gh auth token)" \
  -o a.zip "https://api.github.com/repos/<owner>/<repo>/actions/artifacts/<id>/zip"
```

⚠️ **macOS artifact 是「内层 zip」**（CI 里先打 zip 再上传），需解开一层：

```bash
unzip a.zip                     # 得到 VideoDevour-macos-arm64.zip
ditto -x -k VideoDevour-macos-arm64.zip   # 再解出 VideoDevour.app
```

Windows 绿色版 artifact 是**目录版**（`VideoDevour.exe` + `_internal/`），需自己打包成 zip。

## 4. 逐项校验（发版前必做）

```bash
# macOS：签名 + symlink（关键！）
codesign --verify --deep --strict VideoDevour.app     # 必须无输出（通过）
find VideoDevour.app -type l | wc -l                  # 必须 >0（arm64 约 109、x64 约 29）
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" VideoDevour.app/Contents/Info.plist
file VideoDevour.app/Contents/Resources/VideoDevour   # 架构应匹配

# 启动冒烟（在用户目录下测，别在 /tmp）
cd ~/Downloads && ./VideoDevour.app/Contents/Resources/VideoDevour --backend-only \
  --port 0 --data-dir ./d --handshake-file ./hs.json &
# 等握手 → curl health 应 200、根路径应返回前端标题

# Windows 安装包
ls VideoDevour-<版本>-setup.exe && file *-setup.exe    # 应为 PE32 executable
```

- [ ] macOS：seal 通过 + symlink 数量正常 + 架构正确 + 版本号正确
- [ ] macOS：能启动、health 200、前端有响应
- [ ] Windows：安装包文件名含正确版本号、是合法 PE

## 5. 打 tag 与发布

```bash
git tag -a v<x.y.z> <main 的 merge commit> -m "VideoDevour v<x.y.z> · <一句话>"
git push origin v<x.y.z>
git ls-remote origin 'refs/tags/v<x.y.z>^{}'    # 确认指向预期 commit

gh release create v<x.y.z> \
  --title "VideoDevour v<x.y.z> · <标题>" \
  --notes-file <notes.md> \
  <4 个产物路径>
```

**Release notes 必含**：

- [ ] 4 个资产的平台说明表（macOS 按芯片选择，选错打不开）
- [ ] 安装步骤（`xattr -cr` / SmartScreen 说明）
- [ ] **验证状态表**：如实标注哪些平台真机验证过、哪些仅启动冒烟、哪些经 Rosetta —— **不要把 macOS 的结论扩大为跨平台承诺**
- [ ] 已知限制（未签名/未公证、不含本地 ASR、非完全离线）
- [ ] SHA256 校验和
- [ ] 若修复了上个版本的致命问题，**开头就写明"请更换本版"**

## 6. 发布后验证

```bash
gh release view v<x.y.z> --json assets --jq '.assets[] | "\(.name)  \(.size/1048576|floor)MB  \(.state)"'
for f in <资产名>; do
  curl -sIL --max-time 60 "https://github.com/<owner>/<repo>/releases/download/v<x.y.z>/$f" \
    -o /dev/null -w "%{http_code}  $f\n"
done
```

- [ ] 4 个资产 state 均为 `uploaded`
- [ ] 4 条公开下载链接均返回 **200**

## 7. 收尾

```bash
# 同步本地交付目录（可选，release/*.zip 已 gitignore）
cp <产物> desktop/release/
# 更新测试说明版本号
sed -i '' 's/VideoDevour-<旧版本>-setup.exe/VideoDevour-<新版本>-setup.exe/g' desktop/release/README-测试说明.md

# 清理分支
git checkout main && git pull --ff-only origin main
git push origin --delete chore/bump-<x.y.z>
git branch -D chore/bump-<x.y.z>
```

- [ ] 本地 `main` 与 `origin/main` 一致
- [ ] 临时分支已删除
- [ ] （若本轮有新经验）补进 `references/pitfalls.md` 与 `planning/A3-A4-构建验证报告.md`

---

## 常见卡点

| 卡点 | 处理 |
|------|------|
| `macos-13` job 永久 queued | runner 已弃用，用 `macos-15-intel` |
| Intel job 迟迟不开始 | 该 runner 排队慢（6-8 分钟），正常等待 |
| `gh run download` 报 `unexpected EOF` | 改用 API 直连 + `curl -C -` 续传 |
| artifact 下载 415 | 去掉 `Accept: application/octet-stream` 头 |
| PR 的 push 没触发 CI | 检查 workflow 的 `branches` 是否含该分支前缀（`fix/**` 曾漏配） |
| macOS artifact 解压后目录散开（只有 `Contents/`） | 说明是旧流程产物（丢 symlink），见 pitfalls E1 |
