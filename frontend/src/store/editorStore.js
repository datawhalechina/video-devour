import { create } from "zustand";

/**
 * 编辑器全局状态管理
 * 使用 Zustand 管理编辑器的状态，包括文档内容、选区、UI状态等
 */
const useEditorStore = create((set, get) => ({
  // ========== 文档状态 ==========
  document: null, // Slate编辑器的文档内容
  originalDocument: null, // 原始文档（用于对比）
  isDirty: false, // 是否有未保存的修改

  setDocument: (doc) => set({ document: doc, isDirty: true }),
  setOriginalDocument: (doc) => set({ originalDocument: doc }),
  resetDirty: () => set({ isDirty: false }),

  // ========== 编辑模式 ==========
  mode: "preview", // 'preview' | 'edit'
  setMode: (mode) => set({ mode }),
  toggleMode: () =>
    set((state) => ({
      mode: state.mode === "preview" ? "edit" : "preview",
    })),

  // ========== 选区和焦点 ==========
  selection: null,
  focusedBlockId: null,

  setSelection: (selection) => set({ selection }),
  setFocusedBlock: (blockId) => set({ focusedBlockId: blockId }),

  // ========== UI状态 ==========
  // 斜杠命令菜单
  slashMenuOpen: false,
  slashMenuPosition: null,
  slashMenuSearch: "",

  openSlashMenu: (position, search = "") =>
    set({
      slashMenuOpen: true,
      slashMenuPosition: position,
      slashMenuSearch: search,
    }),
  closeSlashMenu: () =>
    set({
      slashMenuOpen: false,
      slashMenuPosition: null,
      slashMenuSearch: "",
    }),
  updateSlashMenuSearch: (search) => set({ slashMenuSearch: search }),

  // 块操作菜单
  blockMenuOpen: false,
  blockMenuPosition: null,
  blockMenuBlockId: null,

  openBlockMenu: (position, blockId) =>
    set({
      blockMenuOpen: true,
      blockMenuPosition: position,
      blockMenuBlockId: blockId,
    }),
  closeBlockMenu: () =>
    set({
      blockMenuOpen: false,
      blockMenuPosition: null,
      blockMenuBlockId: null,
    }),

  // 选区工具栏
  selectionToolbarOpen: false,
  selectionToolbarPosition: null,

  openSelectionToolbar: (position) =>
    set({
      selectionToolbarOpen: true,
      selectionToolbarPosition: position,
    }),
  closeSelectionToolbar: () =>
    set({
      selectionToolbarOpen: false,
      selectionToolbarPosition: null,
    }),

  // ========== AI功能状态 ==========
  aiRewriteLoading: false,
  aiSuggestions: null, // { blockId, original, suggestion, accepted }

  setAiLoading: (loading) => set({ aiRewriteLoading: loading }),
  setAiSuggestions: (suggestions) => set({ aiSuggestions: suggestions }),
  clearAiSuggestions: () => set({ aiSuggestions: null }),

  acceptAiSuggestion: () => {
    const { aiSuggestions } = get();
    if (aiSuggestions) {
      set({ aiSuggestions: { ...aiSuggestions, accepted: true } });
    }
  },

  rejectAiSuggestion: () => {
    set({ aiSuggestions: null });
  },

  // ========== 拖拽状态 ==========
  isDragging: false,
  draggedBlockId: null,

  setDragging: (isDragging, blockId = null) =>
    set({
      isDragging,
      draggedBlockId: blockId,
    }),

  // ========== 历史记录 ==========
  canUndo: false,
  canRedo: false,

  setHistoryState: (canUndo, canRedo) => set({ canUndo, canRedo }),

  // ========== 工具函数 ==========
  reset: () =>
    set({
      document: null,
      originalDocument: null,
      isDirty: false,
      mode: "preview",
      selection: null,
      focusedBlockId: null,
      slashMenuOpen: false,
      blockMenuOpen: false,
      selectionToolbarOpen: false,
      aiRewriteLoading: false,
      aiSuggestions: null,
      isDragging: false,
      draggedBlockId: null,
    }),
}));

export default useEditorStore;
