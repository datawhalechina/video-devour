# 🎨 飞书级富文本编辑器

## ✨ 功能特性

### 📝 已实现功能

#### 🎯 核心编辑功能

- ✅ **基础块类型**
  - 段落 (Paragraph)
  - 一级/二级/三级标题 (H1/H2/H3)
  - 有序/无序列表 (Ordered/Bullet List)
  - 待办列表 (Todo List with Checkbox)
  - 引用块 (Quote)
  - 提示框 (Callout: Info/Warning/Error/Success/Quote)
  - 分割线 (Divider)
- ✅ **行内样式**

  - 粗体 (Bold) - `Ctrl+B`
  - 斜体 (Italic) - `Ctrl+I`
  - 下划线 (Underline) - `Ctrl+U`
  - 删除线 (Strikethrough) - `Ctrl+Shift+X`
  - 行内代码 (Inline Code) - `Ctrl+``
  - 链接 (Link) - `Ctrl+K`
  - 高亮 (Highlight)

- ✅ **媒体块**
  - 图片插入和管理
  - 视频插入

#### 🛠️ 高级功能

- ✅ **左右分栏编辑器**

  - 左侧：富文本编辑
  - 右侧：实时 Markdown 预览
  - 三种视图模式：编辑、分栏、预览

- ✅ **斜杠命令菜单** `/`

  - 输入 `/` 触发命令菜单
  - 支持中英文搜索
  - 快速插入各种块类型
  - 键盘导航支持 (↑↓ Enter Esc)

- ✅ **选区浮动工具栏**

  - 选中文本自动显示
  - 格式化工具一键可达
  - 支持链接插入
  - AI 重写功能

- ✅ **Markdown 快捷输入**

  - `# ` → 一级标题
  - `## ` → 二级标题
  - `### ` → 三级标题
  - `* ` 或 `- ` → 无序列表
  - `1. ` → 有序列表
  - `[ ] ` → 待办列表
  - `> ` → 引用块
  - `---` → 分割线

- ✅ **快捷键系统**
  - `Ctrl+B` - 粗体
  - `Ctrl+I` - 斜体
  - `Ctrl+U` - 下划线
  - `Ctrl+` ` - 行内代码
  - `Ctrl+K` - 插入链接
  - `Ctrl+Z` - 撤销
  - `Ctrl+Shift+Z` / `Ctrl+Y` - 重做
  - `Backspace` - 块类型转换

#### 🤖 AI 功能

- ✅ **AI 智能重写**

  - 优化：让文本更清晰流畅
  - 扩展：增加更多细节
  - 精简：删减冗余内容
  - 改写：换一种表达方式
  - 专业化：使用专业术语
  - 通俗化：简化表达

- ✅ **AI 建议面板**
  - 可视化对比原文和建议
  - 一键接受/拒绝
  - 重新生成功能

#### 💅 UI/UX 特性

- ✅ 现代化设计
- ✅ 流畅动画过渡
- ✅ 响应式布局
- ✅ 深色工具栏
- ✅ 悬浮提示
- ✅ 块类型图标

---

## 🚀 快速开始

### 1. 基础使用

```jsx
import { SplitViewEditor } from "./components/Editor";

function App() {
  const handleSave = async (markdown) => {
    console.log("保存内容:", markdown);
    // 调用 API 保存
  };

  return (
    <SplitViewEditor
      initialMarkdown="# Hello World\n\n这是初始内容"
      onSave={handleSave}
      onCancel={() => console.log("取消")}
    />
  );
}
```

### 2. 在 ReportViewer 中使用

```jsx
import ReportViewer from "./components/ReportViewer";

function App() {
  const report = {
    videoName: "示例视频",
    detailedOutline: "# 详细大纲\n\n内容...",
    finalReport: "# 精简报告\n\n内容...",
    // ...
  };

  return <ReportViewer report={report} onBack={() => {}} />;
}
```

点击"编辑报告"按钮即可进入编辑模式。

---

## 📖 使用指南

### 编辑技巧

1. **快速插入块**

   - 输入 `/` 打开命令菜单
   - 使用 ↑↓ 键选择，Enter 确认

2. **Markdown 快捷输入**

   - 直接输入 Markdown 语法
   - 空格后自动转换

3. **格式化文本**

   - 选中文本显示浮动工具栏
   - 或使用快捷键

4. **AI 重写**

   - 选中要重写的文本
   - 点击工具栏的 AI 图标 (✨)
   - 选择重写方式
   - 查看建议并接受/拒绝

5. **视图切换**
   - 编辑模式：专注写作
   - 分栏模式：边写边预览
   - 预览模式：查看最终效果

---

## 🏗️ 技术架构

### 核心技术栈

- **Slate.js** - 富文本编辑框架
- **slate-react** - React 集成
- **slate-history** - 撤销/重做支持
- **Zustand** - 状态管理
- **Framer Motion** - 动画库
- **Tailwind CSS** - 样式框架
- **React Markdown** - Markdown 渲染
- **Prism.js** - 代码高亮
- **Lucide React** - 图标库

### 目录结构

```
src/components/Editor/
├── Blocks/              # 块组件
│   ├── ParagraphBlock.jsx
│   ├── HeadingBlock.jsx
│   ├── ListBlock.jsx
│   ├── QuoteBlock.jsx
│   ├── CalloutBlock.jsx
│   ├── ImageBlock.jsx
│   ├── VideoBlock.jsx
│   └── DividerBlock.jsx
├── Toolbars/            # 工具栏
│   ├── BlockToolbar.jsx
│   ├── SelectionToolbar.jsx
│   ├── SlashMenu.jsx
│   └── AIButton.jsx
├── AI/                  # AI 功能
│   └── AIRewritePanel.jsx
├── Plugins/             # 插件
│   └── withMarkdownShortcuts.js
├── DocumentEditor.jsx   # 核心编辑器
├── SplitViewEditor.jsx  # 分栏编辑器
├── EditorElement.jsx    # 元素渲染
├── EditorLeaf.jsx       # 叶子节点渲染
├── editorConfig.js      # 配置文件
├── editorUtils.js       # 工具函数
└── index.js             # 导出文件

src/store/
└── editorStore.js       # 编辑器状态管理

src/api/
└── aiService.js         # AI API 服务
```

---

## 🔧 自定义扩展

### 添加新的块类型

1. 在 `editorConfig.js` 中定义块类型
2. 创建块组件 (如 `NewBlock.jsx`)
3. 在 `EditorElement.jsx` 中注册
4. 添加到斜杠命令菜单

### 添加新的 AI 功能

1. 在 `aiService.js` 中添加 API 方法
2. 在 `AIRewritePanel.jsx` 中添加选项
3. 更新 AI 按钮逻辑

### 自定义快捷键

在 `editorConfig.js` 的 `HOTKEYS` 中添加：

```javascript
export const HOTKEYS = {
  "mod+b": "bold",
  "mod+shift+k": "custom-action", // 新增
  // ...
};
```

---

## 🎯 待完成功能 (Roadmap)

- ⏳ 块拖拽排序
- ⏳ 表格编辑
- ⏳ 数学公式 (KaTeX)
- ⏳ 多格式导出 (PDF、Word、HTML)
- ⏳ 协同编辑
- ⏳ 版本历史
- ⏳ 评论功能
- ⏳ 更多 AI 功能（续写、总结、翻译）

---

## 📝 注意事项

1. **性能优化**

   - 大文档建议使用虚拟滚动
   - 避免在编辑器中放置过多媒体

2. **浏览器兼容性**

   - 推荐使用 Chrome、Edge、Firefox 最新版
   - Safari 可能有部分样式差异

3. **AI 功能**
   - 当前使用模拟数据
   - 实际项目需要替换为真实 API

---

## 🐛 已知问题

- [ ] Safari 中选区工具栏位置可能不准确
- [ ] 移动端体验待优化
- [ ] 大文档 (>10000 字) 可能有性能问题

---

## 📄 License

MIT License

---

## 🙏 致谢

本编辑器灵感来源于：

- Notion
- Feishu (飞书)
- Confluence

使用的开源项目：

- Slate.js
- React
- Tailwind CSS
- Framer Motion

---

**Happy Editing! ✨**
