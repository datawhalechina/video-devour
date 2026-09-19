import { useEffect, useMemo, useRef, useState } from "react";
import { App, Input, Dropdown } from "antd";
import { fromGraph, find, parentOf, change, flatten } from "./tree";
import { mindmapApi } from "./api";
import { createAutosave } from "../editor/autosave";
import { download } from "../editor/document";
import TreeCanvas from "./TreeCanvas";
import { WorkspaceSelect } from "../../components/ui/Controls";
import "./mindmap.css";

export default function MindmapEditor({ taskId, graph, run }) {
  const [loaded, setLoaded] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setLoaded(null);
    setError("");
    mindmapApi(taskId, run)
      .load()
      .then((data) => {
        if (active) setLoaded(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [taskId, run]);
  if (!loaded) return <div role="status">{error || "正在打开思维导图…"}</div>;
  return (
    <Editor
      key={`${taskId}-${loaded.output_dir}`}
      initial={loaded}
      taskId={taskId}
      graph={graph}
    />
  );
}
function Editor({ initial, taskId, graph }) {
  const { message, modal } = App.useApp();
  const [tree, setTree] = useState(() => initial.document || fromGraph(graph));
  const [selected, setSelected] = useState(tree.id),
    [view, setView] = useState("map"),
    [editing, setEditing] = useState(null),
    [title, setTitle] = useState(""),
    [detail, setDetail] = useState(false);
  const [status, setStatus] = useState("saved"),
    [error, setError] = useState(""),
    [history, setHistory] = useState({ past: [], future: [] });
  const treeRef = useRef(tree),
    saver = useRef();
  const api = useMemo(
    () => mindmapApi(taskId, initial.output_dir.replace(/^frames_/, "")),
    [taskId, initial.output_dir],
  );
  const key = `vd-mindmap-draft:${taskId}:${initial.output_dir}`;
  const [draft, setDraft] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key));
    } catch {
      return null;
    }
  });
  useEffect(() => {
    let alive = true;
    saver.current = createAutosave({
      save: api.save,
      revision: initial.revision,
      notify: (s, e = "") => {
        if (alive) {
          setStatus(s);
          setError(e);
        }
      },
      persist: (snapshot, revision) => {
        try {
          localStorage.setItem(key, JSON.stringify({ ...snapshot, revision }));
        } catch {
          if (alive) setError("本地草稿空间不足，请保持页面打开直到保存完成。");
        }
      },
      clear: () => localStorage.removeItem(key),
    });
    const leave = (e) => {
      if (saver.current.dirty()) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", leave);
    return () => {
      alive = false;
      saver.current.stop();
      window.removeEventListener("beforeunload", leave);
    };
  }, [api, initial.revision, key]);
  const apply = (next) => {
    if (next === treeRef.current) return;
    const previous = treeRef.current;
    setHistory((h) => ({ past: [...h.past.slice(-49), previous], future: [] }));
    treeRef.current = next;
    setTree(next);
    saver.current.change({ document: next });
  };
  const act = (action) => apply(change(treeRef.current, action));
  const select = (id) => setSelected(id);
  const edit = (id) => {
    setSelected(id);
    setTitle(find(treeRef.current, id)?.title || "");
    setEditing(id);
  };
  const add = (sibling) => {
    const id = crypto.randomUUID();
    act({ type: "add", id: selected, sibling, newId: id });
    edit(id);
  };
  const remove = () => {
    const parent = parentOf(tree, selected);
    if (!parent) return;
    act({ type: "delete", id: selected });
    setSelected(parent.id);
  };
  const undo = () => {
    if (!history.past.length) return;
    const previous = history.past.at(-1);
    setHistory({
      past: history.past.slice(0, -1),
      future: [tree, ...history.future],
    });
    treeRef.current = previous;
    setTree(previous);
    setSelected(previous.id);
    saver.current.change({ document: previous });
  };
  const redo = () => {
    if (!history.future.length) return;
    const next = history.future[0];
    setHistory({
      past: [...history.past, tree],
      future: history.future.slice(1),
    });
    treeRef.current = next;
    setTree(next);
    setSelected(next.id);
    saver.current.change({ document: next });
  };
  const move = (id, target, before) => {
    const next = change(treeRef.current, { type: "move", id, target, before });
    if (next === treeRef.current) {
      message.info("不能移动到自身或子分支内");
      return;
    }
    apply(next);
    setSelected(id);
  };
  const commit = () => {
    if (title.trim() && find(treeRef.current, editing)?.title !== title.trim())
      act({ type: "update", id: editing, patch: { title: title.trim() } });
    setEditing(null);
  };
  const node = find(tree, selected) || tree;
  const toggle = (id) =>
    act({
      type: "update",
      id,
      patch: { collapsed: !find(tree, id).collapsed },
    });
  const nodes = flatten(tree);
  const keydown = (e) => {
    if (
      e.target.closest('input,textarea,select,[contenteditable="true"]') ||
      editing
    )
      return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault();
      e.shiftKey ? redo() : undo();
      return;
    }
    if (e.target.closest("button:not([data-node])")) return;
    if (e.key === "Tab") {
      e.preventDefault();
      add(false);
    } else if (e.key === "Enter") {
      e.preventDefault();
      add(true);
    } else if (e.key === "F2") {
      e.preventDefault();
      edit(selected);
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      remove();
    }
  };
  const editField = (
    <textarea
      key={editing}
      autoFocus
      className="mm-title-input"
      aria-label="主题文字"
      value={title}
      maxLength={500}
      rows={3}
      onChange={(e) => {
        const value = e.target.value;
        setTitle(value);
        if (value.trim())
          act({ type: "update", id: editing, patch: { title: value } });
      }}
      onBlur={commit}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.nativeEvent.isComposing) return;
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          commit();
        }
        if (e.key === "Escape") {
          e.preventDefault();
          setEditing(null);
        }
      }}
    />
  );
  const outline = (n, depth = 0) => (
    <div key={n.id} className="mm-outline-branch" style={{ "--depth": depth }}>
      <div
        className={`mm-outline-row ${selected === n.id ? "is-selected" : ""}`}
      >
        <button
          aria-label={`${n.collapsed ? "展开" : "折叠"}：${n.title}`}
          disabled={!n.children.length}
          onClick={() => toggle(n.id)}
        >
          {n.children.length ? (n.collapsed ? "＋" : "−") : "·"}
        </button>
        {editing === n.id ? (
          editField
        ) : (
          <button
            data-node={n.id}
            onClick={() => select(n.id)}
            onDoubleClick={() => edit(n.id)}
          >
            {n.title}
          </button>
        )}
      </div>
      {!n.collapsed && n.children.map((c) => outline(c, depth + 1))}
    </div>
  );
  return (
    <Dropdown
      trigger={["contextMenu"]}
      dropdownRender={() => (
        <div className="mm-toolbar">
          <div className="mm-view">
            <button
              aria-pressed={view === "map"}
              onClick={() => setView("map")}
            >
              思维导图
            </button>
            <button
              aria-pressed={view === "outline"}
              onClick={() => setView("outline")}
            >
              大纲
            </button>
          </div>
          <button onClick={() => add(false)}>＋子主题</button>
          <button onClick={() => add(true)}>＋同级主题</button>
          <button onClick={() => edit(selected)}>编辑</button>
          <button disabled={selected === tree.id} onClick={remove}>
            删除
          </button>
          <button disabled={!history.past.length} onClick={undo}>
            撤销
          </button>
          <button disabled={!history.future.length} onClick={redo}>
            重做
          </button>
          <button aria-pressed={detail} onClick={() => setDetail((v) => !v)}>
            节点详情
          </button>
          <button
            onClick={() =>
              modal.confirm({
                title: "导入生成内容？",
                content: "将用生成的节点树替换当前导图，替换后仍可撤销。",
                okText: "导入",
                cancelText: "取消",
                onOk: () => {
                  const next = fromGraph(graph);
                  apply(next);
                  setSelected(next.id);
                },
              })
            }
          >
            导入生成内容
          </button>
          <button
            onClick={() =>
              download(
                JSON.stringify(tree, null, 2),
                "思维导图.json",
                "application/json",
              )
            }
          >
            备份
          </button>
        </div>
      )}
    >
      <div className="mm-editor" onKeyDown={keydown}>
        {error && (
          <div role="alert" className="mm-alert">
            {error}
          </div>
        )}
        {draft && (
          <div className="mm-alert">
            发现未同步草稿{" "}
            <button
              onClick={() => {
                apply(draft.document);
                setDraft(null);
              }}
            >
              恢复草稿
            </button>
            <button
              onClick={() => {
                localStorage.removeItem(key);
                setDraft(null);
              }}
            >
              忽略
            </button>
          </div>
        )}
        <div className="mm-workspace">
          {view === "map" ? (
            <TreeCanvas
              tree={tree}
              selected={selected}
              onSelect={select}
              onEdit={edit}
              onMove={move}
              editing={editing}
              editField={editField}
            />
          ) : (
            <div className="mm-outline" tabIndex={0}>
              {outline(tree)}
            </div>
          )}
          {detail && (
            <aside className="mm-details" key={selected}>
              <h3>{node.title}</h3>
              <label>
                备注
                <Input.TextArea
                  key={node.id + ":notes"}
                  defaultValue={node.notes}
                  rows={6}
                  maxLength={20000}
                  onBlur={(e) => {
                    if (e.target.value !== node.notes)
                      act({
                        type: "update",
                        id: node.id,
                        patch: { notes: e.target.value },
                      });
                  }}
                />
              </label>
              {node.id !== tree.id && (
                <>
                  <p>移动到其他分支</p>
                  <WorkspaceSelect
                    aria-label="父主题"
                    value={parentOf(tree, node.id)?.id}
                    onChange={(value) => move(node.id, value, false)}
                    options={nodes
                      .filter((n) => !find(node, n.id))
                      .map((n) => ({ value: n.id, label: n.title }))}
                  />
                </>
              )}
              <p>{node.children.length} 个直接子主题</p>
              <button onClick={() => setDetail(false)}>收起详情</button>
            </aside>
          )}
        </div>
        <footer className="mm-help">
          {" "}
          <span role="status">
            {
              {
                saved: "已自动保存",
                pending: "等待保存",
                saving: "正在保存…",
                error: "保存失败，正在重试",
                conflict: "版本冲突，已暂停保存",
              }[status]
            }
          </span>
          右键打开操作菜单 · 双击节点编辑 · Tab 添加子主题 · Enter 添加同级 ·
          拖到节点中央成为子主题，顶部插入同级 · 删除可撤销
        </footer>
      </div>
    </Dropdown>
  );
}
