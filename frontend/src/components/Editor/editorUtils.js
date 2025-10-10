import { Editor, Transforms, Element as SlateElement, Node, Text } from "slate";
import { BLOCK_TYPES, MARKS } from "./editorConfig";

/**
 * 编辑器工具函数集合
 */

// ========== 块操作 ==========

/**
 * 检查当前是否处于某种块类型中
 */
export const isBlockActive = (editor, format, blockType = "type") => {
  const { selection } = editor;
  if (!selection) return false;

  const [match] = Array.from(
    Editor.nodes(editor, {
      at: Editor.unhangRange(editor, selection),
      match: (n) =>
        !Editor.isEditor(n) &&
        SlateElement.isElement(n) &&
        n[blockType] === format,
    })
  );

  return !!match;
};

/**
 * 切换块类型
 */
export const toggleBlock = (editor, format) => {
  const isActive = isBlockActive(editor, format);
  const isList = [
    BLOCK_TYPES.BULLET_LIST,
    BLOCK_TYPES.NUMBERED_LIST,
    BLOCK_TYPES.TODO_LIST,
  ].includes(format);

  Transforms.unwrapNodes(editor, {
    match: (n) =>
      !Editor.isEditor(n) &&
      SlateElement.isElement(n) &&
      [
        BLOCK_TYPES.BULLET_LIST,
        BLOCK_TYPES.NUMBERED_LIST,
        BLOCK_TYPES.TODO_LIST,
      ].includes(n.type),
    split: true,
  });

  let newProperties;
  if (isActive) {
    newProperties = { type: BLOCK_TYPES.PARAGRAPH };
  } else if (isList) {
    newProperties = { type: "list-item" };
  } else {
    newProperties = { type: format };
  }

  Transforms.setNodes(editor, newProperties);

  if (!isActive && isList) {
    const block = { type: format, children: [] };
    Transforms.wrapNodes(editor, block);
  }
};

/**
 * 设置块属性
 */
export const setBlockProperty = (editor, properties) => {
  Transforms.setNodes(editor, properties, {
    match: (n) => SlateElement.isElement(n) && Editor.isBlock(editor, n),
  });
};

// ========== 标记（行内样式）操作 ==========

/**
 * 检查是否有某个标记激活
 */
export const isMarkActive = (editor, format) => {
  const marks = Editor.marks(editor);
  return marks ? marks[format] === true : false;
};

/**
 * 切换标记
 */
export const toggleMark = (editor, format) => {
  const isActive = isMarkActive(editor, format);

  if (isActive) {
    Editor.removeMark(editor, format);
  } else {
    Editor.addMark(editor, format, true);
  }
};

/**
 * 添加标记（支持带值的标记，如颜色）
 */
export const addMark = (editor, format, value = true) => {
  Editor.addMark(editor, format, value);
};

/**
 * 移除标记
 */
export const removeMark = (editor, format) => {
  Editor.removeMark(editor, format);
};

// ========== 选区操作 ==========

/**
 * 获取选中的文本
 */
export const getSelectedText = (editor) => {
  const { selection } = editor;
  if (!selection) return "";

  return Editor.string(editor, selection);
};

/**
 * 检查选区是否折叠（光标状态）
 */
export const isSelectionCollapsed = (editor) => {
  const { selection } = editor;
  return selection && selection.anchor.offset === selection.focus.offset;
};

/**
 * 检查选区是否为空
 */
export const isSelectionEmpty = (editor) => {
  const { selection } = editor;
  if (!selection) return true;

  const text = Editor.string(editor, selection);
  return text.length === 0;
};

// ========== 链接操作 ==========

/**
 * 插入链接
 */
export const insertLink = (editor, url, text = null) => {
  if (editor.selection) {
    wrapLink(editor, url, text);
  }
};

/**
 * 包装选区为链接
 */
const wrapLink = (editor, url, text = null) => {
  if (isLinkActive(editor)) {
    unwrapLink(editor);
  }

  const { selection } = editor;
  const isCollapsed =
    selection && selection.anchor.offset === selection.focus.offset;

  const link = {
    type: "link",
    url,
    children: isCollapsed ? [{ text: text || url }] : [],
  };

  if (isCollapsed) {
    Transforms.insertNodes(editor, link);
  } else {
    Transforms.wrapNodes(editor, link, { split: true });
    Transforms.collapse(editor, { edge: "end" });
  }
};

/**
 * 移除链接
 */
export const unwrapLink = (editor) => {
  Transforms.unwrapNodes(editor, {
    match: (n) =>
      !Editor.isEditor(n) && SlateElement.isElement(n) && n.type === "link",
  });
};

/**
 * 检查是否在链接中
 */
export const isLinkActive = (editor) => {
  const [link] = Editor.nodes(editor, {
    match: (n) =>
      !Editor.isEditor(n) && SlateElement.isElement(n) && n.type === "link",
  });
  return !!link;
};

// ========== 图片/视频插入 ==========

/**
 * 插入图片
 */
export const insertImage = (editor, url, alt = "") => {
  const image = {
    type: BLOCK_TYPES.IMAGE,
    url,
    alt,
    children: [{ text: "" }],
  };
  Transforms.insertNodes(editor, image);
  Transforms.insertNodes(editor, {
    type: BLOCK_TYPES.PARAGRAPH,
    children: [{ text: "" }],
  });
};

/**
 * 插入视频
 */
export const insertVideo = (editor, url) => {
  const video = {
    type: BLOCK_TYPES.VIDEO,
    url,
    children: [{ text: "" }],
  };
  Transforms.insertNodes(editor, video);
  Transforms.insertNodes(editor, {
    type: BLOCK_TYPES.PARAGRAPH,
    children: [{ text: "" }],
  });
};

// ========== 节点查找 ==========

/**
 * 获取当前块节点
 */
export const getCurrentBlock = (editor) => {
  const { selection } = editor;
  if (!selection) return null;

  const [match] = Editor.nodes(editor, {
    match: (n) => SlateElement.isElement(n) && Editor.isBlock(editor, n),
  });

  return match ? match[0] : null;
};

/**
 * 获取当前块路径
 */
export const getCurrentBlockPath = (editor) => {
  const { selection } = editor;
  if (!selection) return null;

  const [match] = Editor.nodes(editor, {
    match: (n) => SlateElement.isElement(n) && Editor.isBlock(editor, n),
  });

  return match ? match[1] : null;
};

// ========== 文档转换 ==========

/**
 * Markdown 转 Slate 文档
 */
export const markdownToSlate = (markdown) => {
  // 简化版实现，实际项目中应使用专门的转换库
  const lines = markdown.split("\n");
  const nodes = [];

  lines.forEach((line) => {
    if (line.startsWith("# ")) {
      nodes.push({
        type: BLOCK_TYPES.HEADING_1,
        children: [{ text: line.slice(2) }],
      });
    } else if (line.startsWith("## ")) {
      nodes.push({
        type: BLOCK_TYPES.HEADING_2,
        children: [{ text: line.slice(3) }],
      });
    } else if (line.startsWith("### ")) {
      nodes.push({
        type: BLOCK_TYPES.HEADING_3,
        children: [{ text: line.slice(4) }],
      });
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      nodes.push({
        type: BLOCK_TYPES.BULLET_LIST,
        children: [
          {
            type: "list-item",
            children: [{ text: line.slice(2) }],
          },
        ],
      });
    } else if (line.match(/^\d+\. /)) {
      nodes.push({
        type: BLOCK_TYPES.NUMBERED_LIST,
        children: [
          {
            type: "list-item",
            children: [{ text: line.replace(/^\d+\. /, "") }],
          },
        ],
      });
    } else if (line.startsWith("> ")) {
      nodes.push({
        type: BLOCK_TYPES.QUOTE,
        children: [{ text: line.slice(2) }],
      });
    } else if (line.trim() === "") {
      // 空行不添加
    } else {
      nodes.push({
        type: BLOCK_TYPES.PARAGRAPH,
        children: [{ text: line }],
      });
    }
  });

  return nodes.length > 0
    ? nodes
    : [{ type: BLOCK_TYPES.PARAGRAPH, children: [{ text: "" }] }];
};

/**
 * Slate 文档转 Markdown
 */
export const slateToMarkdown = (nodes) => {
  return nodes.map((n) => serialize(n)).join("\n");
};

const serialize = (node) => {
  if (Text.isText(node)) {
    let text = node.text;
    if (node.bold) text = `**${text}**`;
    if (node.italic) text = `*${text}*`;
    if (node.code) text = `\`${text}\``;
    if (node.underline) text = `<u>${text}</u>`;
    return text;
  }

  const children = node.children.map((n) => serialize(n)).join("");

  switch (node.type) {
    case BLOCK_TYPES.HEADING_1:
      return `# ${children}`;
    case BLOCK_TYPES.HEADING_2:
      return `## ${children}`;
    case BLOCK_TYPES.HEADING_3:
      return `### ${children}`;
    case BLOCK_TYPES.BULLET_LIST:
      return `- ${children}`;
    case BLOCK_TYPES.NUMBERED_LIST:
      return `1. ${children}`;
    case BLOCK_TYPES.QUOTE:
      return `> ${children}`;
    case BLOCK_TYPES.CODE:
      return `\`\`\`\n${children}\n\`\`\``;
    case BLOCK_TYPES.PARAGRAPH:
      return children;
    default:
      return children;
  }
};

// ========== 初始值 ==========

export const createEmptyDocument = () => [
  {
    type: BLOCK_TYPES.PARAGRAPH,
    children: [{ text: "" }],
  },
];

export default {
  isBlockActive,
  toggleBlock,
  setBlockProperty,
  isMarkActive,
  toggleMark,
  addMark,
  removeMark,
  getSelectedText,
  isSelectionCollapsed,
  isSelectionEmpty,
  insertLink,
  unwrapLink,
  isLinkActive,
  insertImage,
  insertVideo,
  getCurrentBlock,
  getCurrentBlockPath,
  markdownToSlate,
  slateToMarkdown,
  createEmptyDocument,
};
