# 报告块编辑器

- `ReportEditorPage`：兼容 `/editor/:taskId?file=detailed|final|detailed_report&run=...`，加载后固定报告版本。
- `BlockEditor`：BlockNote 单文档编辑界面；中文斜杠菜单、选区格式、块拖拽、表格、图片。
- `api`：唯一 HTTP 入口；`autosave`：串行合并写入、版本冲突暂停、失败重试；`document`：导入与下载。
- 后端 `backend/editor`：JSON 文档为编辑主格式，Markdown 为现有阅读/生成流程的兼容副本。

打开旧 Markdown 不改写文件。第一次用户修改时创建 `.original.md`，保存前保留最近 20 个版本。外部流程改变 Markdown 时忽略旧 JSON，重新导入。多窗口写入通过 revision 拒绝过期覆盖。

浏览器草稿仅用于未同步恢复；服务端确认后移除。页面退出会尽力完成写入，失败仍保留草稿。存储锁针对当前单进程服务；多 worker 部署前应改为数据库事务/文件锁。

Markdown 不表达完整的对齐、颜色和下划线属性；这些保留在 JSON。导入支持 Markdown 和本编辑器 JSON 备份，追加到文档末尾。复杂原始 HTML/自定义 Markdown 扩展不保证无损转换，原文备份可回退。

旧 Slate 组件、工具栏、测试页、全局 editorStore 及专用依赖已移除。第一版不接旧 AI 选区改写，不实现多人实时协作。图片上传限定本地服务 PNG/JPEG/GIF/WebP。

验证：`node --test src/features/editor/autosave.test.js`；仓库根目录 `.venv/bin/python -m unittest discover -s tests -p test_editor_store.py`。使用 `scripts/preview_fixtures.py` 的独立 8001 服务测试编辑，不改真实报告。
