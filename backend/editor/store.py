"""文档主存储与 Markdown 兼容副本；读入不会重写旧报告。"""
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.RLock()
FILES = {'detailed': 'detailed_outline.md', 'final': 'final_report.md', 'detailed_report': 'detailed_report.md'}

class ConflictError(Exception):
    pass


def _paths(folder, kind):
    if kind not in FILES:
        raise ValueError('不支持的报告类型')
    source = Path(folder) / FILES[kind]
    return source, source.with_suffix('.blocks.json')


def _atomic(path, text):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(text, encoding='utf-8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def read_document(folder, kind):
    with _LOCK:
        source, sidecar = _paths(folder, kind)
        markdown = source.read_text(encoding='utf-8')
        raw = sidecar.read_text(encoding='utf-8') if sidecar.exists() else ''
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        # 外部生成或旧接口更新了 Markdown 时，不用旧结构覆盖它。
        valid = data.get('markdown_hash') == _hash(markdown)
        return {'document': data.get('document') if valid else None,
                'markdown': markdown, 'revision': _hash(markdown + '\0' + raw),
                'updated_at': data.get('updated_at') if valid else None,
                'output_dir': Path(folder).name}


def save_document(folder, kind, document, markdown, expected_revision):
    with _LOCK:
        current = read_document(folder, kind)
        if current['revision'] != expected_revision:
            raise ConflictError('报告已在其他窗口或处理流程中更新，请先下载本地草稿，再重新加载。')
        source, sidecar = _paths(folder, kind)
        backup = source.with_suffix('.original.md')
        if not backup.exists():
            _atomic(backup, current['markdown'])
        history = Path(folder) / '.editor-history' / kind
        history.mkdir(parents=True, exist_ok=True)
        _atomic(history / (current['revision'] + '.json'), json.dumps(current, ensure_ascii=False))
        updated = datetime.now(timezone.utc).isoformat()
        data = {'schema_version': 1, 'document': document, 'markdown_hash': _hash(markdown), 'updated_at': updated}
        # 单文件原子替换；意外中断导致副本不匹配时，read_document 会重新导入 Markdown。
        _atomic(source, markdown)
        _atomic(sidecar, json.dumps(data, ensure_ascii=False))
        for old in sorted(history.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[20:]:
            old.unlink()
        return read_document(folder, kind)


def list_versions(folder, kind):
    _paths(folder, kind)
    directory = Path(folder) / '.editor-history' / kind
    return [{'id': p.stem, 'saved_at': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}
            for p in sorted(directory.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)]


def get_version(folder, kind, revision):
    _paths(folder, kind)
    if len(revision) != 64 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('版本标识无效')
    return json.loads((Path(folder) / '.editor-history' / kind / (revision + '.json')).read_text(encoding='utf-8'))
