# 前端结构与维护规则

## 本次重构边界

沿用 React Router、Ant Design 和现有后端接口。组件保留原入口作为兼容导出，业务实现迁入 `features`，不进行整个仓库目录搬迁。

- `components/AppShell.jsx`：固定外壳与导航；主题切换不重建路由组件。
- `shared/ui/Workspace.jsx`：页面标题、工具栏、局部滚动、固定页脚、按钮、分段选择、空状态。
- `features/history`：加载与轮询、日期分组、列表展示。
- `features/library`：接口、可取消的检索请求、排序、视图、收藏标记。
- `features/settings`：表单状态、供应商预设、五个设置面板；切换类别不会丢弃未保存输入。
- `features/import`：视频链接、平台搜索、预览和生成流程。
- `features/learning`：数据适配、章节抽取、画布、复习卡、单题练习。

数据依赖方向为页面 → 功能模块 → API / 通用组件。主题只保存应用级外观状态；远端任务数据不放进主题 Context。

## 样式的唯一归属

1. `styles/tokens.css`：间距、字号、圆角、材质、主题变量。
2. `styles/shell.css`：外壳、侧栏/顶栏、窄屏导航。
3. `styles/controls.css`：共享布局与控件、弹窗。
4. `styles/pages/*.css`：每个功能页面独有的布局。
5. `styles/legacy.css`：尚未迁移的阅读器、上传、处理进度和编辑器兼容样式。

旧的 workspace/lake/coast/refinements 四层样式已合并清理。新功能禁止往 legacy 文件追加覆盖；需要改旧页面时，迁移其组件和样式后删除对应旧规则。新页面不使用旧 `workspace-page` 容器，不依赖 `max-width` 补丁。尺寸用 rem，流式比例使用 %、vw、dvh；JS 图形坐标和 Ant Design token 数值遵循各自 API。

固定布局约定：外壳限制可用高度，Workspace 的标题、工具栏和页脚不参与内容滚动，中间内容区设置 `min-height:0` 与 overflow。导入页左右两栏分别滚动，窄屏合并为一栏。不要再为各页面添加不同的标题 top/padding。

## 功能边界与兼容

- 原有报告、文章版本、整库导出、平台账号、字幕速记、上传功能保留。
- 新学习入口：`/learn/:taskId/:kind`；kind 为 mindmap / graph / cards / quiz。
- 原有模型生成接口仍可用。没有生成导图时展示真实报告章节结构；生成版本从现有缓存读取 Markdown / JSON，绝不执行生成文档中的脚本。
- 复习卡来自报告章节原文；掌握状态和知识库收藏标记仅保存在当前浏览器。原来的生成版卡片仍可下载。
- 习题读取缓存，用户点击生成才请求模型；整卷提交服务端判题。没有真实时间戳时显示“回看报告”，不编造视频定位。
- 尚无独立取消/重试接口，因此处理记录使用“查看进度 / 重新导入”。不能把删除任务伪装成取消。
- 设置连通性测试沿用原先“先保存当前配置再测试”的接口流程；后续应新增不保存的测试配置接口。
- 原有阅读器、上传、编辑器的业务逻辑未全面拆分，兼容样式仍需要后续逐模块迁移。

## 本地预览

- `/history?preview=states`：处理与失败样例。
- `/learn/preview-design/cards`、`/learn/preview-design/mindmap`、`/learn/preview-design/graph`、`/learn/preview-design/quiz`：学习界面样例。
- 预览只在 localhost / 127.0.0.1 生效，页面明确标注，数据不写入后端、不调用模型。

## 验证

```sh
npm --prefix frontend run build
npm --prefix frontend run lint
node --test frontend/src/features/history/tests/*.test.js frontend/src/features/learning/tests/*.test.js
```

浏览器重点验证：两套主题、宽/窄屏、页脚固定、页内滚动、检索空态、设置类别切换、收藏/复习状态持久化、习题单选/多选/判题、弹窗焦点与关闭。效果图对照使用 1586×992，同时保留用户后来指定的外壳加宽、取消全局搜索、保存按钮上移等差异。
