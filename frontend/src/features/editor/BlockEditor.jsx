import { useEffect, useMemo, useRef, useState } from 'react';
import { useCreateBlockNote } from '@blocknote/react';
import { BlockNoteView } from '@blocknote/mantine';
import { BlockNoteSchema, defaultBlockSpecs } from '@blocknote/core';
import { zh } from '@blocknote/core/locales';
import { Button, Dropdown, Drawer, Alert, Modal } from 'antd';
import { Undo2, Redo2, Download, History, Upload } from 'lucide-react';
import '@blocknote/mantine/style.css';
import { editorApi } from './api';
import { createAutosave } from './autosave';
import { download, importMarkdown } from './document';
import './editor.css';

const supportedBlocks = Object.fromEntries(Object.entries(defaultBlockSpecs).filter(([type]) => !['audio', 'video', 'file'].includes(type)));
const schema = BlockNoteSchema.create({ blockSpecs: supportedBlocks });
const labels = { saved: '已自动保存', pending: '等待保存', saving: '正在保存…', error: '保存失败，正在重试', conflict: '版本冲突，已暂停保存' };
export default function BlockEditor({ taskId, kind, initial }) {
  const api = useMemo(() => editorApi(taskId, kind, initial.output_dir.replace(/^frames_/, '')), [taskId, kind, initial.output_dir]);
  const draftKey = `videodevour-block-draft:${taskId}:${kind}:${initial.output_dir}`;
  const [status, setStatus] = useState('saved');
  const [error, setError] = useState('');
  const [history, setHistory] = useState(null);
  const [draft, setDraft] = useState(() => {
    try { return JSON.parse(localStorage.getItem(draftKey)); } catch { return null; }
  });
  const [storageError, setStorageError] = useState(false);
  const fileRef = useRef();
  const editor = useCreateBlockNote({ schema, dictionary: zh, initialContent: initial.document || undefined, uploadFile: api.upload });
  const saverRef = useRef();
  const readyRef = useRef(false);
  useEffect(() => {
    if (!initial.document) editor.transact(transaction => {
      transaction.setMeta('addToHistory', false);
      editor.replaceBlocks(editor.document, importMarkdown(editor, initial.markdown, initial.output_dir));
    });
    let alive = true;
    const saver = createAutosave({
      save: api.save, revision: initial.revision,
      notify: (next, message = '') => { if (alive) { setStatus(next); setError(message); } },
      persist: (snapshot, revision) => {
        try { localStorage.setItem(draftKey, JSON.stringify({ ...snapshot, revision })); }
        catch { if (alive) setStorageError(true); }
      },
      clear: () => { localStorage.removeItem(draftKey); },
    });
    saverRef.current = saver; readyRef.current = true;
    const unload = event => { if (saver.dirty()) { event.preventDefault(); event.returnValue = ''; } };
    const visibility = () => { if (document.visibilityState === 'hidden') void saver.flush(); };
    window.addEventListener('beforeunload', unload);
    document.addEventListener('visibilitychange', visibility);
    return () => { alive = false; readyRef.current = false; saver.stop(); window.removeEventListener('beforeunload', unload); document.removeEventListener('visibilitychange', visibility); };
  }, [editor, api, initial, draftKey]);
  const snapshot = () => ({ document: editor.document, markdown: editor.blocksToMarkdownLossy() });
  const changed = () => { if (readyRef.current) saverRef.current.change(snapshot()); };
  const exportDraft = () => download(JSON.stringify(snapshot(), null, 2), '报告草稿.json', 'application/json');
  const openHistory = async () => {
    try { setHistory(await api.versions()); } catch (e) { setError(e.message); }
  };
  const restore = async id => {
    try {
      const version = await api.version(id);
      Modal.confirm({ title: '恢复这个版本？', content: '当前内容会保留在历史版本中。', okText: '恢复', cancelText: '返回', onOk: () => {
        editor.replaceBlocks(editor.document, version.document || importMarkdown(editor, version.markdown, initial.output_dir));
        changed(); setHistory(null);
      } });
    } catch (e) { setError(e.message); }
  };
  const importFile = async event => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      const text = await file.text();
      const blocks = file.name.endsWith('.json') ? JSON.parse(text).document : importMarkdown(editor, text, initial.output_dir);
      if (!Array.isArray(blocks) || !blocks.length) throw new Error('文档内容为空或格式不正确');
      editor.insertBlocks(blocks, editor.document.at(-1), 'after'); changed();
    } catch (e) { setError(`导入失败：${e.message}`); }
    event.target.value = '';
  };
  return <section className="vd-page block-editor-page">
    <header className="block-editor-bar">
      <div className="block-editor-state"><strong>文档编辑</strong><span role="status" aria-live="polite">{labels[status]}</span></div>
      <div className="block-editor-actions">
        <Button aria-label="撤销" title="撤销" icon={<Undo2 size="1rem" />} onClick={() => editor.undo()} />
        <Button aria-label="重做" title="重做" icon={<Redo2 size="1rem" />} onClick={() => editor.redo()} />
        <Button icon={<Upload size="1rem" />} onClick={() => fileRef.current.click()}>导入文档</Button>
        <Dropdown menu={{ items: [{ key: 'md', label: '导出 Markdown' }, { key: 'json', label: '下载完整文档备份' }], onClick: ({ key }) => key === 'md' ? download(editor.blocksToMarkdownLossy(), '报告.md', 'text/markdown') : exportDraft() }}>
          <Button icon={<Download size="1rem" />}>导出</Button>
        </Dropdown>
        <Button icon={<History size="1rem" />} onClick={openHistory}>历史版本</Button>
      </div>
    </header>
    <input hidden ref={fileRef} type="file" accept=".md,.markdown,.txt,.json" onChange={importFile} />
    {draft && <Alert type="warning" showIcon message="发现尚未同步的本地草稿" description="可恢复到编辑器中继续编辑，或先下载备份。" action={<div className="block-editor-actions"><Button onClick={() => download(JSON.stringify(draft, null, 2), '本地草稿.json')}>下载草稿</Button><Button onClick={() => { editor.replaceBlocks(editor.document, draft.document); changed(); setDraft(null); }}>恢复草稿</Button><Button onClick={() => { localStorage.removeItem(draftKey); setDraft(null); }}>忽略</Button></div>} />}
    {(error || storageError) && <Alert type="warning" showIcon message={error || '浏览器草稿空间不足，请保持页面打开，等待自动保存完成。'} action={status === 'conflict' ? <div className="block-editor-actions"><Button onClick={exportDraft}>下载本地草稿</Button><Button onClick={() => window.location.reload()}>重新加载</Button></div> : undefined} />}
    <div className="block-editor-paper"><BlockNoteView editor={editor} theme="light" onChange={changed} /></div>
    <footer className="block-editor-help">输入 / 插入内容块 · 选中文字设置格式 · 拖动段落左侧手柄调整顺序</footer>
    <Drawer title="历史版本" open={history !== null} onClose={() => setHistory(null)}>
      {history?.length === 0 && <p>第一次修改后，将在这里保留修改前的版本。</p>}
      {history?.map(version => <div className="block-editor-version" key={version.id}><span>{new Date(version.saved_at).toLocaleString('zh-CN')}</span><Button disabled={status !== 'saved'} onClick={() => restore(version.id)}>恢复</Button></div>)}
    </Drawer>
  </section>;
}
