import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.editor.mindmap import create_router,validate_tree

class MindmapTest(unittest.TestCase):
    def test_roundtrip_conflict_and_generated_html_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'frames_task-1_20260916';folder.mkdir()
            html=folder/'mindmap.html';html.write_text('generated')
            app=FastAPI();app.include_router(create_router(lambda _:folder,root));client=TestClient(app)
            old=client.get('/api/mindmap/task-1').json();self.assertIsNone(old['document'])
            tree={'id':'root','title':'知识','notes':'原文','children':[{'id':'a','title':'观点','children':[]}]}
            body={'document':tree,'expected_revision':old['revision']}
            saved=client.put('/api/mindmap/task-1',json=body);self.assertEqual(saved.status_code,200)
            self.assertEqual(client.get('/api/mindmap/task-1').json()['document'],tree)
            self.assertEqual(client.put('/api/mindmap/task-1',json=body).status_code,409)
            self.assertEqual(html.read_text(),'generated')
            self.assertEqual(client.get('/api/mindmap/task-1?run=other_1').status_code,400)
    def test_reject_duplicate_ids(self):
        with self.assertRaises(ValueError):validate_tree({'id':'r','title':'r','children':[{'id':'r','title':'c','children':[]}]})
