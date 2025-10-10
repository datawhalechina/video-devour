# 📋 编辑器功能补充计划

> 基于 Obsidian 设计理念，结合视频分析报告场景的功能规划

---

## 📊 当前状态分析

### ✅ 已完成功能（优势）

#### 1️⃣ **核心编辑能力**

- ✅ Slate.js 富文本框架
- ✅ 完整的块类型（段落、标题、列表、引用、Callout、图片、视频、分割线）
- ✅ 行内格式（粗体、斜体、下划线、删除线、代码、链接、高亮）
- ✅ Markdown 快捷输入（`#`、`-`、`>`、`1.`、`[]`）
- ✅ 键盘快捷键系统（`Ctrl+B/I/U/K`等）
- ✅ 撤销/重做（slate-history）

#### 2️⃣ **高级功能**

- ✅ 斜杠命令菜单（`/` 触发）
- ✅ 选区浮动工具栏
- ✅ AI 智能重写（6 种模式：优化、扩展、精简、改写、专业化、通俗化）
- ✅ 分栏编辑（编辑 | 分栏 | 预览）
- ✅ 实时 Markdown 预览

#### 3️⃣ **UI/UX**

- ✅ 现代化设计（Tailwind CSS）
- ✅ 流畅动画（Framer Motion）
- ✅ 文档列表侧边栏
- ✅ 响应式布局

#### 4️⃣ **数据管理**

- ✅ Zustand 状态管理
- ✅ 多文档支持
- ✅ JSON 导出功能
- ✅ Markdown 双向转换（基础实现）

---

## 🎯 待补充功能分析

### 🔥 **优先级 P0（核心功能，立即实现）**

#### 1. 🏷️ **标签系统（Tags）**

**重要性**: ⭐⭐⭐⭐⭐  
**实现难度**: ⭐⭐  
**适用场景**: 管理大量视频分析报告

**功能描述**:

- 支持 `#标签名` 语法识别
- 标签自动提取和索引
- 标签侧边栏展示
- 按标签筛选文档
- 标签重命名和合并

**实现计划**:

```javascript
// 1. 扩展文档数据结构
{
  id: 1,
  name: "视频分析报告",
  content: [...],
  tags: ["#教育", "#AI", "#总结"],  // 新增
  metadata: {
    createdAt: "2024-10-10",
    updatedAt: "2024-10-10"
  }
}

// 2. 创建标签提取函数
function extractTags(content) {
  const tagRegex = /#[\u4e00-\u9fa5a-zA-Z0-9_]+/g;
  // 从文档内容中提取所有 #标签
}

// 3. 创建标签侧边栏组件
<TagSidebar
  tags={allTags}
  selectedTag={selectedTag}
  onSelectTag={handleSelectTag}
/>
```

**技术要点**:

- 实时解析文档内容提取标签
- 使用 Set 去重
- 支持中英文标签
- 点击标签跳转到相关文档

---

#### 2. 🔍 **全局搜索（Global Search）**

**重要性**: ⭐⭐⭐⭐⭐  
**实现难度**: ⭐⭐⭐  
**适用场景**: 快速查找历史报告中的关键信息

**功能描述**:

- `Ctrl+P` 打开快速切换器
- `Ctrl+Shift+F` 打开全局搜索
- 搜索文档标题和内容
- 高亮搜索结果
- 支持模糊匹配

**实现计划**:

```javascript
// 1. 创建搜索引擎
class DocumentSearchEngine {
  index(documents) {
    // 建立倒排索引
  }

  search(query) {
    // 返回匹配的文档和位置
  }
}

// 2. 快速切换器组件
const QuickSwitcher = () => {
  const [query, setQuery] = useState("");

  // 搜索逻辑
  const results = useMemo(() => {
    return searchEngine.search(query);
  }, [query]);

  return (
    <CommandPalette isOpen={isOpen} onSelect={handleSelect} results={results} />
  );
};

// 3. 添加快捷键
useEffect(() => {
  const handler = (e) => {
    if (e.ctrlKey && e.key === "p") {
      e.preventDefault();
      openQuickSwitcher();
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, []);
```

**技术要点**:

- 使用 Fuse.js 实现模糊搜索
- 搜索结果高亮显示
- 键盘导航支持（↑↓ Enter Esc）
- 搜索历史记录

---

#### 3. 📂 **文件夹层级结构（Folder Hierarchy）**

**重要性**: ⭐⭐⭐⭐  
**实现难度**: ⭐⭐⭐  
**适用场景**: 组织大量报告文档

**功能描述**:

- 支持多层级文件夹
- 拖拽移动文档到文件夹
- 文件夹折叠/展开
- 文件夹重命名
- 文件夹图标

**实现计划**:

```javascript
// 1. 扩展数据结构为树形
const documentTree = [
  {
    id: 'folder-1',
    name: '教育类视频',
    type: 'folder',
    expanded: true,
    children: [
      { id: 1, name: '数学课程分析', type: 'document', content: [...] },
      { id: 2, name: '物理实验总结', type: 'document', content: [...] }
    ]
  },
  {
    id: 'folder-2',
    name: '娱乐类视频',
    type: 'folder',
    expanded: false,
    children: [...]
  }
];

// 2. 递归渲染文件树
const FolderTree = ({ items, level = 0 }) => {
  return items.map(item => (
    item.type === 'folder' ? (
      <Folder key={item.id} item={item} level={level}>
        <FolderTree items={item.children} level={level + 1} />
      </Folder>
    ) : (
      <DocumentItem key={item.id} doc={item} level={level} />
    )
  ));
};

// 3. 拖拽功能
import { DndContext, useDraggable, useDroppable } from '@dnd-kit/core';
```

**技术要点**:

- 使用 `@dnd-kit/core` 实现拖拽
- 递归组件渲染树形结构
- 本地存储文件树状态
- 右键菜单（新建文件夹、重命名、删除）

---

#### 4. 📌 **双向链接（Bidirectional Links）**

**重要性**: ⭐⭐⭐⭐  
**实现难度**: ⭐⭐⭐⭐  
**适用场景**: 建立视频报告之间的关联

**功能描述**:

- `[[文档名]]` 创建链接
- 自动补全文档名
- 点击跳转到目标文档
- 反向链接面板（显示哪些文档链接到当前文档）
- 链接图谱可视化

**实现计划**:

```javascript
// 1. 扩展 Markdown 插件识别 [[链接]]
export const MARKDOWN_SHORTCUTS = [
  // ... 现有规则
  { pattern: /\[\[([^\]]+)\]\]/, type: "wiki-link" },
];

// 2. 创建 WikiLink 组件
const WikiLinkBlock = ({ element, attributes, children }) => {
  const targetDoc = findDocumentByName(element.target);

  return (
    <span
      {...attributes}
      className="inline-flex items-center gap-1 px-2 py-0.5 
                 bg-blue-50 hover:bg-blue-100 text-blue-600 
                 rounded cursor-pointer border border-blue-200"
      onClick={() => navigateToDocument(targetDoc?.id)}
    >
      <Link2 className="w-3 h-3" />
      {children}
      {!targetDoc && <span className="text-red-500">?</span>}
    </span>
  );
};

// 3. 构建反向链接索引
function buildBacklinkIndex(documents) {
  const index = {};

  documents.forEach((doc) => {
    const links = extractWikiLinks(doc.content);
    links.forEach((targetName) => {
      if (!index[targetName]) index[targetName] = [];
      index[targetName].push(doc.id);
    });
  });

  return index;
}

// 4. 反向链接面板
const BacklinkPanel = ({ currentDocName }) => {
  const backlinks = backlinkIndex[currentDocName] || [];

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold mb-2">反向链接</h3>
      {backlinks.map((docId) => (
        <BacklinkItem key={docId} docId={docId} />
      ))}
    </div>
  );
};
```

**技术要点**:

- 使用正则提取 `[[链接]]`
- 自动补全（Autocomplete）
- 实时更新反向链接索引
- 支持别名 `[[文档名|显示名]]`

---

### 🟡 **优先级 P1（增强功能，短期实现）**

#### 5. 💾 **本地持久化存储（Local Storage）**

**重要性**: ⭐⭐⭐⭐  
**实现难度**: ⭐⭐

**功能描述**:

- IndexedDB 存储文档
- 自动保存
- 离线编辑
- 版本历史（最近 10 个版本）

**实现计划**:

```javascript
// 使用 Dexie.js（IndexedDB 封装库）
import Dexie from "dexie";

const db = new Dexie("VideoDevourDB");
db.version(1).stores({
  documents: "id, name, tags, createdAt, updatedAt",
  versions: "++id, docId, timestamp, content",
});

// 自动保存
const useSaveDocument = (document) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      db.documents.put(document);
    }, 2000); // 2秒防抖

    return () => clearTimeout(timer);
  }, [document]);
};
```

---

#### 6. ⌨️ **命令面板（Command Palette）**

**重要性**: ⭐⭐⭐⭐  
**实现难度**: ⭐⭐⭐

**功能描述**:

- `Ctrl+Shift+P` 打开命令面板
- 快速执行所有功能
- 命令搜索
- 最近使用的命令

**实现计划**:

```javascript
const commands = [
  { id: "new-doc", name: "新建文档", icon: FileText, action: createNewDoc },
  { id: "new-folder", name: "新建文件夹", icon: Folder, action: createFolder },
  {
    id: "export-md",
    name: "导出为 Markdown",
    icon: Download,
    action: exportMd,
  },
  { id: "export-pdf", name: "导出为 PDF", icon: File, action: exportPdf },
  {
    id: "toggle-sidebar",
    name: "切换侧边栏",
    icon: Menu,
    action: toggleSidebar,
  },
  { id: "search", name: "搜索文档", icon: Search, action: openSearch },
  // ... 更多命令
];

const CommandPalette = () => {
  const [query, setQuery] = useState("");
  const filteredCommands = commands.filter((cmd) =>
    cmd.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="command-palette">
      <input
        placeholder="输入命令..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {filteredCommands.map((cmd) => (
        <div key={cmd.id} onClick={cmd.action}>
          <cmd.icon /> {cmd.name}
        </div>
      ))}
    </div>
  );
};
```

---

#### 7. 🎨 **主题系统（Theme System）**

**重要性**: ⭐⭐⭐  
**实现难度**: ⭐⭐

**功能描述**:

- 亮色/暗色主题
- 自定义主题色
- 代码高亮主题
- 字体设置

**实现计划**:

```javascript
// 使用 CSS 变量 + Tailwind Dark Mode
const themes = {
  light: {
    "--bg-primary": "#ffffff",
    "--text-primary": "#1f2937",
    "--accent": "#3b82f6",
    // ...
  },
  dark: {
    "--bg-primary": "#1f2937",
    "--text-primary": "#f9fafb",
    "--accent": "#60a5fa",
    // ...
  },
};

// 主题切换
const useTheme = () => {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    Object.entries(themes[theme]).forEach(([key, value]) => {
      document.documentElement.style.setProperty(key, value);
    });
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return { theme, setTheme };
};
```

---

#### 8. 📊 **文档统计（Document Stats）**

**重要性**: ⭐⭐⭐  
**实现难度**: ⭐

**功能描述**:

- 字数统计
- 阅读时间估算
- 块数量统计
- 图片/视频数量
- 创建/修改时间

**实现计划**:

```javascript
const DocumentStats = ({ content }) => {
  const stats = useMemo(() => {
    const text = content.map((n) => Node.string(n)).join(" ");
    const wordCount = text.split(/\s+/).filter(Boolean).length;
    const charCount = text.length;
    const readingTime = Math.ceil(wordCount / 200); // 平均阅读速度
    const blocks = content.length;
    const images = content.filter((n) => n.type === "image").length;

    return { wordCount, charCount, readingTime, blocks, images };
  }, [content]);

  return (
    <div className="text-xs text-gray-500 flex gap-4">
      <span>{stats.wordCount} 字</span>
      <span>{stats.readingTime} 分钟阅读</span>
      <span>{stats.blocks} 个块</span>
    </div>
  );
};
```

---

### 🟢 **优先级 P2（高级功能，长期实现）**

#### 9. 🕸️ **知识图谱（Graph View）**

**重要性**: ⭐⭐⭐  
**实现难度**: ⭐⭐⭐⭐⭐

**功能描述**:

- 可视化文档关系网络
- 基于双向链接和标签
- 交互式图谱（缩放、拖拽）
- 高亮当前文档

**实现计划**:

```javascript
import ForceGraph2D from "react-force-graph-2d";

const GraphView = ({ documents, backlinkIndex }) => {
  const graphData = useMemo(() => {
    const nodes = documents.map((doc) => ({
      id: doc.id,
      name: doc.name,
      tags: doc.tags,
    }));

    const links = [];
    documents.forEach((doc) => {
      const wikiLinks = extractWikiLinks(doc.content);
      wikiLinks.forEach((targetName) => {
        const target = documents.find((d) => d.name === targetName);
        if (target) {
          links.push({ source: doc.id, target: target.id });
        }
      });
    });

    return { nodes, links };
  }, [documents]);

  return (
    <div className="h-screen">
      <ForceGraph2D
        graphData={graphData}
        nodeLabel="name"
        nodeAutoColorBy="tags"
        linkDirectionalParticles={2}
      />
    </div>
  );
};
```

---

#### 10. 📝 **模板系统（Templates）**

**重要性**: ⭐⭐⭐  
**实现难度**: ⭐⭐

**功能描述**:

- 预设报告模板
- 自定义模板
- 模板变量替换
- 快速创建文档

**实现计划**:

```javascript
const templates = [
  {
    id: "video-analysis",
    name: "视频分析报告模板",
    content: [
      {
        type: "heading",
        level: 1,
        children: [{ text: "{{video_name}} - 分析报告" }],
      },
      { type: "heading", level: 2, children: [{ text: "📊 基本信息" }] },
      { type: "paragraph", children: [{ text: "视频时长：{{duration}}" }] },
      { type: "heading", level: 2, children: [{ text: "📝 内容摘要" }] },
      { type: "paragraph", children: [{ text: "{{summary}}" }] },
      // ...
    ],
  },
  // ... 更多模板
];

const createFromTemplate = (templateId, variables) => {
  const template = templates.find((t) => t.id === templateId);
  const content = JSON.parse(JSON.stringify(template.content));

  // 替换变量
  replaceVariables(content, variables);

  return content;
};
```

---

#### 11. 🔌 **插件系统（Plugin System）**

**重要性**: ⭐⭐⭐  
**实现难度**: ⭐⭐⭐⭐⭐

**功能描述**:

- 可扩展的插件架构
- 插件市场
- 插件配置界面
- 热加载插件

**实现计划**:

```javascript
// 插件接口定义
interface Plugin {
  id: string;
  name: string;
  version: string;

  // 生命周期
  onLoad(context: PluginContext): void;
  onUnload(): void;

  // 扩展点
  extendEditor?(editor: Editor): void;
  extendCommands?(commands: Command[]): void;
  extendUI?(components: UIComponents): void;
}

// 插件示例：表格增强
const tablePlugin: Plugin = {
  id: 'table-enhanced',
  name: '表格增强',
  version: '1.0.0',

  onLoad(context) {
    context.registerCommand({
      id: 'insert-table',
      name: '插入表格',
      action: () => insertTable(context.editor, 3, 3)
    });
  },

  extendEditor(editor) {
    // 添加表格操作快捷键
  }
};
```

---

#### 12. 📤 **多格式导出（Export Formats）**

**重要性**: ⭐⭐⭐⭐  
**实现难度**: ⭐⭐⭐⭐

**功能描述**:

- 导出为 PDF
- 导出为 Word (.docx)
- 导出为 HTML
- 导出为图片
- 批量导出

**实现计划**:

```javascript
import jsPDF from "jspdf";
import { Document, Packer, Paragraph } from "docx";
import html2canvas from "html2canvas";

// PDF 导出
const exportToPDF = async (content) => {
  const doc = new jsPDF();
  const markdown = slateToMarkdown(content);
  // 转换为 PDF...
  doc.save("report.pdf");
};

// Word 导出
const exportToDocx = async (content) => {
  const doc = new Document({
    sections: [
      {
        properties: {},
        children: content.map((block) => convertToDocxParagraph(block)),
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, "report.docx");
};

// HTML 导出
const exportToHTML = (content) => {
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <title>Report</title>
        <style>${getExportStyles()}</style>
      </head>
      <body>${renderToHTML(content)}</body>
    </html>
  `;

  const blob = new Blob([html], { type: "text/html" });
  saveAs(blob, "report.html");
};
```

---

#### 13. 👥 **协同编辑（Collaboration）**

**重要性**: ⭐⭐  
**实现难度**: ⭐⭐⭐⭐⭐

**功能描述**:

- 多人实时编辑
- 用户光标显示
- 评论功能
- 版本冲突解决

**实现计划**:

```javascript
// 使用 Yjs + WebRTC 实现协同编辑
import * as Y from "yjs";
import { WebrtcProvider } from "y-webrtc";
import { slateNodesToInsertDelta } from "@slate-yjs/core";

const ydoc = new Y.Doc();
const provider = new WebrtcProvider("document-room", ydoc);

const sharedType = ydoc.get("content", Y.XmlText);

// 同步 Slate 编辑器和 Yjs 文档
```

---

## 📅 实施时间表

### 🚀 **第一阶段（1-2 周）**

- ✅ 标签系统
- ✅ 全局搜索
- ✅ 本地持久化存储
- ✅ 文档统计

### 🚀 **第二阶段（2-3 周）**

- ✅ 文件夹层级结构
- ✅ 双向链接
- ✅ 命令面板
- ✅ 主题系统

### 🚀 **第三阶段（3-4 周）**

- ✅ 模板系统
- ✅ 多格式导出（PDF、Word、HTML）
- ✅ 知识图谱（可选）

### 🚀 **第四阶段（长期）**

- ✅ 插件系统
- ✅ 协同编辑（可选）

---

## 🎯 核心价值主张

打造一个 **"专为视频分析报告设计的 AI 增强知识管理工具"**：

1. **📊 专业性** - 专注视频分析场景，而非通用笔记
2. **🤖 AI 原生** - 深度集成 AI 能力（重写、总结、续写）
3. **🔗 关联性** - 通过标签、链接、图谱建立知识网络
4. **⚡ 高效性** - 快捷键、命令面板、模板加速工作流
5. **🎨 现代性** - 优秀的 UI/UX，流畅的动画体验

---

## 📊 技术栈总结

| 类别           | 技术选型                 | 用途           |
| -------------- | ------------------------ | -------------- |
| **编辑器核心** | Slate.js                 | 富文本编辑框架 |
| **状态管理**   | Zustand                  | 全局状态       |
| **数据存储**   | Dexie.js (IndexedDB)     | 本地持久化     |
| **搜索引擎**   | Fuse.js                  | 模糊搜索       |
| **拖拽功能**   | @dnd-kit/core            | 文件夹拖拽     |
| **图谱可视化** | react-force-graph-2d     | 知识图谱       |
| **导出功能**   | jsPDF, docx, html2canvas | 多格式导出     |
| **动画效果**   | Framer Motion            | UI 动画        |
| **样式框架**   | Tailwind CSS             | 样式系统       |
| **协同编辑**   | Yjs (可选)               | 实时协作       |

---

## 🎨 设计原则

1. **简洁至上** - 不过度设计，保持界面清爽
2. **快捷键优先** - 所有操作都有快捷键
3. **本地优先** - 数据存储在本地，保护隐私
4. **AI 增强** - AI 作为辅助工具，而非替代编辑
5. **可扩展性** - 为未来的插件系统预留接口

---

**下一步行动**: 开始实现 P0 优先级功能（标签系统 → 全局搜索 → 文件夹层级 → 双向链接）
