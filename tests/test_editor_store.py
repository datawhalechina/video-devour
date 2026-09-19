import tempfile
import unittest
from pathlib import Path
from backend.editor import store

class EditorStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder/'detailed_outline.md').write_text('# 原始报告\n\n**重要**', encoding='utf-8')
    def tearDown(self): self.temp.cleanup()
    def test_read_does_not_migrate(self):
        data = store.read_document(self.folder, 'detailed')
        self.assertIsNone(data['document'])
        self.assertEqual(len(list(self.folder.iterdir())), 1)
    def test_save_preserves_structure_original_and_history(self):
        old = store.read_document(self.folder, 'detailed')
        blocks = [{'type':'heading','props':{'level':2,'textAlignment':'center'},'content':[{'type':'text','text':'标题','styles':{'underline':True}}]}]
        new = store.save_document(self.folder,'detailed',blocks,'## 标题',old['revision'])
        self.assertEqual(new['document'],blocks)
        self.assertNotEqual(new['revision'],old['revision'])
        self.assertEqual((self.folder/'detailed_outline.original.md').read_text(),old['markdown'])
        versions = store.list_versions(self.folder,'detailed')
        self.assertEqual(store.get_version(self.folder,'detailed',versions[0]['id'])['markdown'],old['markdown'])
        with self.assertRaises(store.ConflictError):
            store.save_document(self.folder,'detailed',blocks,'过期修改',old['revision'])
        self.assertEqual(store.read_document(self.folder,'detailed')['markdown'],'## 标题')
    def test_external_generation_invalidates_structure(self):
        data=store.read_document(self.folder,'detailed')
        store.save_document(self.folder,'detailed',[{'type':'paragraph'}],'旧内容',data['revision'])
        (self.folder/'detailed_outline.md').write_text('外部更新')
        self.assertIsNone(store.read_document(self.folder,'detailed')['document'])
    def test_invalid_version_path(self):
        with self.assertRaises(ValueError): store.get_version(self.folder,'detailed','../x')
    def test_history_restore_retains_original(self):
        old=store.read_document(self.folder,'detailed')
        new=store.save_document(self.folder,'detailed',[{'type':'paragraph'}],'新版',old['revision'])
        restored=store.save_document(self.folder,'detailed',[{'type':'paragraph'}],old['markdown'],new['revision'])
        self.assertEqual(restored['markdown'],old['markdown'])
        self.assertEqual(len(store.list_versions(self.folder,'detailed')),2)

if __name__=='__main__': unittest.main()

class EditorRoutesTest(unittest.TestCase):
    def test_routes_conflict_upload_and_run_isolation(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.editor.routes import create_router
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'frames_test-1_20260916'
            folder.mkdir(); (folder/'final_report.md').write_text('原文')
            app=FastAPI(); app.include_router(create_router(lambda task: folder if task=='test-1' else None,root))
            client=TestClient(app); url='/api/editor/test-1/final'
            old=client.get(url).json()
            payload={'document':[{'type':'paragraph','content':[]}],'markdown':'新内容','expected_revision':old['revision']}
            self.assertEqual(client.put(url,json=payload).status_code,200)
            self.assertEqual(client.put(url,json=payload).status_code,409)
            self.assertEqual(client.get(url+'?run=other_20260916').status_code,400)
            self.assertEqual(client.get('/api/editor/test-1/unknown').status_code,400)
            self.assertEqual(client.post(url+'/images',files={'file':('x.svg',b'<svg/>','image/svg+xml')}).status_code,415)
            response=client.post(url+'/images',files={'file':('x.png',b'\x89PNG\r\n\x1a\nfixture','image/png')})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.json()['url'].startswith('/static/frames_test-1_20260916/editor-images/'))
