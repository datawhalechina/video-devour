import { Editor, Transforms, Range, Point } from "slate";
import { BLOCK_TYPES, MARKDOWN_SHORTCUTS } from "../editorConfig";

/**
 * Markdown 快捷输入插件
 * 在输入时自动检测 Markdown 语法并转换为对应的块
 */
export const withMarkdownShortcuts = (editor) => {
  const { insertText, deleteBackward } = editor;

  editor.insertText = (text) => {
    const { selection } = editor;

    if (text === " " && selection && Range.isCollapsed(selection)) {
      const { anchor } = selection;
      const block = Editor.above(editor, {
        match: (n) => Editor.isBlock(editor, n),
      });

      const path = block ? block[1] : [];
      const start = Editor.start(editor, path);
      const range = { anchor, focus: start };
      const beforeText = Editor.string(editor, range);

      // 检查 Markdown 模式
      for (const { pattern, type } of MARKDOWN_SHORTCUTS) {
        if (pattern.test(beforeText)) {
          // 删除 Markdown 标记
          Transforms.select(editor, range);
          Transforms.delete(editor);

          // 转换块类型
          if (type === BLOCK_TYPES.DIVIDER) {
            Transforms.insertNodes(editor, {
              type: BLOCK_TYPES.DIVIDER,
              children: [{ text: "" }],
            });
            Transforms.insertNodes(editor, {
              type: BLOCK_TYPES.PARAGRAPH,
              children: [{ text: "" }],
            });
          } else {
            Transforms.setNodes(editor, { type });
          }

          return;
        }
      }
    }

    insertText(text);
  };

  editor.deleteBackward = (...args) => {
    const { selection } = editor;

    if (selection && Range.isCollapsed(selection)) {
      const match = Editor.above(editor, {
        match: (n) => Editor.isBlock(editor, n),
      });

      if (match) {
        const [block, path] = match;
        const start = Editor.start(editor, path);

        if (
          !Editor.isEditor(block) &&
          block.type !== BLOCK_TYPES.PARAGRAPH &&
          Point.equals(selection.anchor, start)
        ) {
          Transforms.setNodes(editor, { type: BLOCK_TYPES.PARAGRAPH });
          return;
        }
      }

      deleteBackward(...args);
    }
  };

  return editor;
};

export default withMarkdownShortcuts;
