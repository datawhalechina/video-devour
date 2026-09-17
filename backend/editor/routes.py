"""编辑器 HTTP 契约。路径解析由现有任务模块提供。"""
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from . import store

class DocumentUpdate(BaseModel):
    document: list[dict] = Field(min_length=1, max_length=10000)
    markdown: str = Field(max_length=5_000_000)
    expected_revision: str = Field(min_length=64, max_length=64)
    schema_version: int = 1


def create_router(resolve_latest, output_root):
    router = APIRouter(prefix='/api/editor', tags=['editor'])

    def folder_for(task_id, kind, run):
        if kind not in store.FILES:
            raise HTTPException(400, '不支持的报告类型')
        if not task_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in task_id):
            raise HTTPException(400, '任务标识无效')
        if run:
            if '/' in run or '\\' in run or not run.startswith(task_id + '_'):
                raise HTTPException(400, '版本标识无效')
            folder = output_root / ('frames_' + run)
        else:
            folder = resolve_latest(task_id)
        if not folder or not folder.is_dir() or not (folder / store.FILES[kind]).is_file():
            raise HTTPException(404, '报告不存在')
        return folder

    @router.get('/{task_id}/{kind}')
    def read(task_id: str, kind: str, run: str = ''):
        return store.read_document(folder_for(task_id, kind, run), kind)

    @router.put('/{task_id}/{kind}')
    def save(task_id: str, kind: str, body: DocumentUpdate, run: str = ''):
        if body.schema_version != 1:
            raise HTTPException(400, '不支持的文档版本')
        try:
            return store.save_document(folder_for(task_id, kind, run), kind, body.document, body.markdown, body.expected_revision)
        except store.ConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.get('/{task_id}/{kind}/versions')
    def versions(task_id: str, kind: str, run: str = ''):
        return store.list_versions(folder_for(task_id, kind, run), kind)

    @router.get('/{task_id}/{kind}/versions/{revision}')
    def version(task_id: str, kind: str, revision: str, run: str = ''):
        try:
            return store.get_version(folder_for(task_id, kind, run), kind, revision)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, '历史版本不存在') from exc

    @router.post('/{task_id}/{kind}/images')
    async def image(task_id: str, kind: str, run: str = '', file: UploadFile = File(...)):
        folder = folder_for(task_id, kind, run)
        data = await file.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, '图片不能超过 10 MB')
        ext = None
        if data.startswith(b'\x89PNG\r\n\x1a\n'): ext = 'png'
        elif data.startswith(b'\xff\xd8\xff'): ext = 'jpg'
        elif data.startswith((b'GIF87a', b'GIF89a')): ext = 'gif'
        elif data.startswith(b'RIFF') and data[8:12] == b'WEBP': ext = 'webp'
        if not ext:
            raise HTTPException(415, '支持 PNG、JPEG、GIF、WebP 图片')
        media = folder / 'editor-images'
        media.mkdir(exist_ok=True)
        name = uuid.uuid4().hex + '.' + ext
        (media / name).write_bytes(data)
        return {'url': f'/static/{folder.name}/editor-images/{name}'}

    return router
