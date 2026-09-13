# VideoDevour 文档库 MCP 服务 — 测试报告

- **被测对象**：`mcp_server/videodevour_library_mcp.py`（VideoDevour 个人文档库 MCP，stdio）
- **测试工具**：`mcp_server/test_mcp_client.py`（自建标准 MCP stdio 客户端，`mcp==1.17.0` SDK）
- **测试日期**：2026-09-13
- **环境**：macOS 26 (arm64)，Python 3.12.13，项目 `.venv`，`mcp==1.17.0`
- **样本库规模**：`output/` 下 14 个视频、43 个处理版本、116 篇文章（`tasks.json` 59 条任务）
- **结论**：**功能可用，但测试前存在 1 个致命缺陷，已修复；另修复 1 个版本能力缺口。修复后 28/28 项全部通过。**

---

## 1. 执行摘要

以真实 MCP 协议（`initialize` → `list_tools` → `call_tool`，通过 stdio 子进程）连接服务，
对 5 个工具做了正常路径、边界路径、异常路径与副作用校验，共 28 项断言：

| 指标 | 结果 |
| --- | --- |
| 通过 | **28** |
| 失败 | **0** |
| 发现缺陷 | 2（1 致命 / 1 能力缺口），均已修复 |
| 工具数 / 协议 | 5 个工具 / MCP `2025-06-18` |
| 单次检索耗时 | 13–40 ms（含导出 300 ms 级） |

> 首次运行时 **`get_article` 100% 失败**（任何合法文章都报 `Error executing tool get_article: 'created_at'`）。
> 这是本 MCP 最核心的"取全文"能力，缺陷状态下文档库检索链路实际不可用。已定位并修复。

---

## 2. 被测服务概览

服务把本地已生成的视频笔记/报告暴露给任意支持 MCP 的 LLM 客户端（Claude Code / Cursor / Claude Desktop 等），
无端口、走 stdio。工具集：

| 工具 | 参数 | 作用 |
| --- | --- | --- |
| `search_library` | `query, scope, top_k` | BM25 检索全部文章，返回 top-k 摘要（含 `doc_id`/`scope`/分数/片段） |
| `get_article` | `doc_id, scope, run_id` | 取单篇全文 Markdown |
| `list_library` | `scope` | 无关键词浏览全部索引 |
| `export_article` | `doc_id, scope, target_dir, run_id` | 导出单篇 ZIP（md + 引用图片） |
| `export_library` | `target_dir` | 导出整库 ZIP（md + 关键帧 + `manifest.json`） |

`scope`：`all` / `outline`(图文大纲) / `report`(精简报告) / `detailed`(详细报告) /
`quantum`(量子速读) / `wechat`(公众号) / `xiaohongshu`(小红书)。

底层复用 `backend/algorithm/document_library.py`（自动入库、BM25 进程内缓存、按视频聚合版本）。

---

## 3. 缺陷与修复

### 3.1 【致命】`get_article` 全文获取全部失败 — `KeyError: 'created_at'`

- **现象**：任何合法 `doc_id` 调用 `get_article` 均返回
  `Error executing tool get_article: 'created_at'`（工具 `isError=True`），取全文能力完全失效。
- **根因**：`document_library.get_article()` 返回的 `doc` 字典未包含 `created_at`
  字段，而它与 `search_library` / `list_library` 的返回结构本应一致；
  MCP 包装层 `mcp_server/videodevour_library_mcp.py` 在拼接头部时无条件读取
  `result['doc']['created_at']`，触发 `KeyError`，被 FastMCP 兜底为工具级错误。
- **修复**：
  1. `backend/algorithm/document_library.py`：在 `get_article` 的 `doc` 中补齐
     `"created_at": run["created_at"]`，使三个接口的数据契约一致。
  2. `mcp_server/videodevour_library_mcp.py`：头部读取改为
     `(doc.get('created_at') or '')[:10]`，对缺字段容错，避免同类硬崩。
- **验证**：修复后 `get_article` 正常返回 2289 字符全文；既有单测
  `tests/test_library_versions.py`（5 项）仍全部通过。

### 3.2 【能力缺口】MCP 无法按版本取文，多版本视频存在歧义

- **现象**：库中 **8/14 个视频存在多个处理版本**（同一视频重复处理生成 V1/V2…），
  但 MCP 的 `get_article` / `export_article` 不接收 `run_id`，只能取到"最近一次版本"；
  `list_library` 也未输出 `run_id`，多个版本在列表中呈现为**完全相同**的
  `doc_id + scope` 行，用户无法分辨。
- **修复**：
  - `get_article` / `export_article` 新增可选 `run_id` 参数（透传底层已支持的 `run_id`）。
  - `search_library` 输出补充 `version_label` 与 `run_id`，便于串联"检索 → 指定版本取全文"。
  - 三个工具的 `scope` 说明补齐全部 6 种维度（原文档只写了 3 种，衍生文体对调用方不可见）。
  - 服务 `instructions` 同步更新，向 LLM 说明版本语义。
- **验证**：以真实多版本样本 `doc_id=7ab94fab…` 两次不同 `run_id` 取文，分别得到
  1981 / 1429 字符且内容不同，缺省 `run_id` 正确回退到最新版本。

---

## 4. 测试用例明细

### 4.1 协议与能力发现

| # | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | `initialize` 握手 | PASS | server=`videodevour-library` v1.17.0，protocol=`2025-06-18`（207 ms） |
| 2 | `list_tools` 工具发现 | PASS | 发现 5 个工具，名称集合与预期一致 |
| 3–7 | 各工具 schema 完整性 | PASS | 每个工具均含 description 与 inputSchema，参数齐全 |
| 8 | `list_resources` | PASS | 0 个（本服务无资源能力，符合预期） |
| 9 | `list_prompts` | PASS | 0 个（本服务无提示词能力，符合预期） |

### 4.2 正常路径

| # | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| 10 | `search_library` 中文检索 | PASS | "智能体" 命中 3 条，返回 1193 字符 |
| 11 | `search_library` 英文检索 | PASS | "agent workflow" 返回 1950 字符 |
| 12 | `search_library` 无命中 | PASS | 纯 ASCII 生僻串返回"未找到…" |
| 13 | `search→get` 链路闭环 | PASS | 从检索结果解析出 `doc_id`/`scope` 并成功取全文 |
| 14 | `get_article` 全文获取 | PASS | 返回 2289 字符完整 Markdown |
| 15 | `get_article` 多版本 `run_id` 区分 | PASS | 同 doc 两版本内容不同（1981/1429 字符） |
| 16 | `get_article` 衍生文体 | PASS | 未生成时有明确说明，不报错 |
| 17 | `list_library` 全量索引 | PASS | 共 116 篇 |
| 18 | `export_article` 导出 + ZIP 校验 | PASS | 文件真实落盘，ZIP 内含 `.md` |
| 19 | `export_library` 整库导出 + manifest 校验 | PASS | 291 个文件，14 视频 / 43 版本，`manifest.json` 可解析 |

### 4.3 边界与异常路径

| # | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| 20 | `search_library` scope 过滤 | PASS | 10 条结果全部 `scope: report` |
| 21 | `search_library` `top_k` 上限钳制 | PASS | 请求 100，实际返回 20（钳到上限） |
| 22 | `search_library` CJK 字符级召回 | PASS | 说明性用例：常见汉字逐字召回（BM25 设计行为，非缺陷） |
| 23 | `get_article` 非法 `doc_id` | PASS | 返回中文引导"文章不存在…请先用 search_library 确认" |
| 24 | `get_article` 非法 `scope` | PASS | 同上，不抛异常 |
| 25 | `list_library` scope 过滤 | PASS | 40 篇，无非 report 行 |
| 26 | `list_library` 非法 scope | PASS | 返回"文档库为空"，不崩 |
| 27 | `export_article` 非法 `doc_id` | PASS | 返回"文章不存在…"，不崩 |
| 28 | 并发 5 路 `search_library` | PASS | 错误数 0，进程内索引缓存读写正常 |

---

## 5. 是否满足用户需要（评估）

**结论：满足"让 LLM 检索/引用本地视频笔记库"这一核心诉求，且已具备接入条件；但作为产品能力尚不完整。**

### 5.1 已满足

- **检索闭环可用**：`search_library`（BM25，中英文混检）→ `get_article`（全文）→ `export_*`（落地为文件），
  覆盖"找得到 → 看得全 → 导得出"的完整链路，性能 13–40 ms，交互无感。
- **接入门槛低**：stdio 无需端口，服务文档已给出 Claude Code / Cursor 的 `mcpServers` 配置样例；
  依赖与项目锁定版本一致（`mcp==1.17.0`），不会引入额外冲突。
- **健壮性达标**：异常输入均返回中文引导而非崩溃；stdout 干净（协议消息不被日志污染），
  日志走 stderr，符合 stdio MCP 规范。
- **自动入库**：新生成的报告无需手动登记，扫描 `output/` 即收录，符合"越用越全"的预期。

### 5.2 尚不满足 / 风险

1. **能力边界窄**：该 MCP **只读、只覆盖"已生成的笔记库"**，不含项目的招牌能力
   （下载视频、ASR、生成报告）。真正"吃掉视频"的入口是 Agent Skill（`devour.py`），
   两者**互补而非替代**——若用户以为配了 MCP 就能处理新视频，会落空。
2. **文档零覆盖（重要）**：`README.md`、`docs/`、`planning/` 中**完全没有** MCP 服务的说明，
   全项目仅源码注释里有一处配置示例。用户不知道它存在、怎么配、能做什么——这是当前最大的落地障碍。
3. **~~`list_library` 版本歧义~~（已一并修复）**：给 `search`/`get`/`export` 补了 `run_id` 后，
   又把 `run_id`/`version_label` 加入 `list_library` 输出，多版本视频在无关键词浏览时也可分辨。
4. **整库导出体量无反馈**：`export_library` 对 291 文件/43 版本的库一次性打包，
   返回前无进度，大库场景调用方只能干等（当前约 300 ms，尚可接受，但随库增长会变差）。
5. **无鉴权/路径约束**：`target_dir` 可写任意目录、`export_library` 可导出全库，
   在本机自用场景可接受，若未来把服务暴露给不可信客户端需加白名单。

---

## 6. 复现方式

```bash
cd <项目根>
# 人类可读报告
.venv/bin/python mcp_server/test_mcp_client.py
# 机器可读 JSON（在 @@JSON@@ 之后）
.venv/bin/python mcp_server/test_mcp_client.py --json
```

客户端接入（供参考，文档中建议补入 README）：

```json
{
  "mcpServers": {
    "videodevour-library": {
      "command": "<项目目录>/.venv/bin/python",
      "args": ["<项目目录>/mcp_server/videodevour_library_mcp.py"]
    }
  }
}
```

---

## 7. 结论与建议

- **结论**：MCP 服务设计合理、实现简洁，修复 2 个缺陷后功能完整可用，**可以交付给用户使用**。
  测试前的致命缺陷（`get_article` 全挂）说明该服务此前处于"从未被真实客户端跑通过"的状态。
- **建议（按优先级）**：
  1. 在 README 新增「MCP 服务」小节（一句话定位 + 配置样例 + 5 个工具速查），并把
     `test_mcp_client.py` 作为回归入口写进测试说明。
  2. 明确文档中 MCP 与 Agent Skill 的分工：**MCP = 读已有笔记库，Skill = 处理新视频**。
  3. （可选）为 `export_library` 增加进度/体量预估，为 `target_dir` 增加可写目录约束。

## 附：本次改动文件

| 文件 | 改动 |
| --- | --- |
| `backend/algorithm/document_library.py` | `get_article` 的 `doc` 补 `created_at` 字段（+1 行） |
| `mcp_server/videodevour_library_mcp.py` | 修复 `created_at` 硬崩；新增 `run_id` 透传；补全 scope 文档与版本提示 |
| `mcp_server/test_mcp_client.py` | 新增：标准 MCP stdio 客户端回归测试（28 项断言） |
