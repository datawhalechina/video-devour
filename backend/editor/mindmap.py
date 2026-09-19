"""User-owned mind map trees, independent of generated HTML artifacts."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .store import _atomic, _hash, _LOCK

class Update(BaseModel):
    document: dict
    expected_revision: str

def validate_tree(tree):
    seen = set()
    def visit(node, depth):
        if depth > 50 or len(seen) >= 2000:
            raise ValueError('导图最多支持 2000 个节点、50 层')
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id'] or node['id'] in seen:
            raise ValueError('节点标识无效或重复')
        seen.add(node['id'])
        if not isinstance(node.get('title'), str) or len(node['title']) > 500:
            raise ValueError('节点标题不能超过 500 字')
        if not isinstance(node.get('notes', ''), str) or len(node.get('notes', '')) > 20000:
            raise ValueError('节点备注过长')
        if not isinstance(node.get('children'), list): raise ValueError('节点子项无效')
        for child in node['children']: visit(child, depth + 1)
    visit(tree, 0)

def create_router(resolve_latest, output_root):
    router = APIRouter(prefix='/api/mindmap')
    def path_for(task_id, run):
        if not task_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in task_id):
            raise HTTPException(400, '任务标识无效')
        if run and ('/' in run or '\\' in run or not run.startswith(task_id + '_')):
            raise HTTPException(400, '版本标识无效')
        folder = Path(output_root) / ('frames_' + run) if run else resolve_latest(task_id)
        if not folder or not folder.is_dir(): raise HTTPException(404, '任务不存在')
        return folder / 'mindmap.document.json'
    def read(path):
        raw = path.read_text(encoding='utf-8') if path.exists() else ''
        return {'document': json.loads(raw) if raw else None, 'revision': _hash(raw), 'output_dir': path.parent.name}
    @router.get('/{task_id}')
    def load(task_id: str, run: str = ''):
        with _LOCK: return read(path_for(task_id, run))
    @router.put('/{task_id}')
    def save(task_id: str, body: Update, run: str = ''):
        try: validate_tree(body.document)
        except (ValueError, RecursionError) as exc: raise HTTPException(400, str(exc)) from exc
        with _LOCK:
            path = path_for(task_id, run)
            previous = read(path)
            if previous['revision'] != body.expected_revision:
                raise HTTPException(409, '导图已在其他窗口更新。请下载备份后刷新页面。')
            if previous['document']:
                history = path.parent / '.mindmap-history'
                history.mkdir(exist_ok=True)
                _atomic(history / (previous['revision'] + '.json'), json.dumps(previous['document'], ensure_ascii=False))
                for old in sorted(history.glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True)[20:]: old.unlink()
            _atomic(path, json.dumps(body.document, ensure_ascii=False))
            return read(path)
    return router
