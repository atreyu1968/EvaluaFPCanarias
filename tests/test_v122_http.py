"""API local 1.2.2: archivo de documentos no destructivo con aislamiento de curso."""
from __future__ import annotations
import json
import tempfile
import urllib.parse
import urllib.request
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import database
import program_builder
from tests.test_v122_curriculum_history import SOURCE, REVISED, SOURCE_URL, MODULE

class HistoryHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='efp122_http_')
        root=Path(cls.tmp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'data.sqlite3'),
                     patch.object(database,'DATA',root),patch.object(database,'STORAGE',root/'storage'),
                     patch.object(database,'BACKUPS',root/'backups')]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(exist_ok=True)
        database.BACKUPS.mkdir(exist_ok=True)
        cls.server,cls.url=app.start()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',
                       ('2026-2027','Administración y Finanzas',MODULE,'A',database.now(),'Comunidad de Madrid'))
            cls.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            draft=program_builder.load(db,cls.mid)['draft']
            draft['official_module_code']='0650'
            db.execute('INSERT INTO programming_drafts(module_id,content_json,updated_at) VALUES(?,?,?)',
                       (cls.mid,json.dumps(draft),database.now()))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.tmp.cleanup()

    @classmethod
    def get(cls,path):
        req=urllib.request.Request(cls.url+path,headers={'X-App-Token':app.TOKEN})
        with urllib.request.urlopen(req,timeout=8) as response:return response.status,json.load(response)

    @classmethod
    def store(cls,content,confirmed=True):
        boundary='----Eval122-Curriculum'
        fields={'module_id':str(cls.mid),'module_code':'0650','document_kind':'norma_oficial',
                'source_url':SOURCE_URL,'source_title':'Fuente oficial para revisión docente',
                'teacher_confirmed':'true' if confirmed else 'false'}
        out=[]
        for key,value in fields.items():
            out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="curriculo.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode())
        out.append(content.encode('utf-8'))
        out.append(f'\r\n--{boundary}--\r\n'.encode())
        req=urllib.request.Request(cls.url+'api/curriculum/history/store',data=b''.join(out),method='POST',
            headers={'X-App-Token':app.TOKEN,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with urllib.request.urlopen(req,timeout=8) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:return exc.code,json.load(exc)

    def test_http_snapshot_and_compare(self):
        with database.connect() as db:db.execute('DELETE FROM curriculum_source_snapshots WHERE module_id=?',(self.mid,))
        status,r=self.store(SOURCE)
        self.assertEqual(status,200,r)
        self.assertTrue(r['saved'])
        old_id=r['id']
        status,duplicate=self.store(SOURCE)
        self.assertEqual(status,200)
        self.assertTrue(duplicate['duplicate'])
        status,revised=self.store(REVISED)
        self.assertEqual(status,200,revised)
        self.assertTrue(revised['change']['requires_manual_review'])
        status,h=self.get(f'api/curriculum/history?module_id={self.mid}')
        self.assertEqual(status,200)
        self.assertEqual(h['count'],2)
        status,diff=self.get(f'api/curriculum/history-compare?module_id={self.mid}&old={old_id}&new={revised["id"]}')
        self.assertEqual(status,200)
        self.assertEqual(diff['differences'][0]['code'],'RA2.b')
        status,catalog=self.get('api/curriculum/catalog?region=Comunidad%20de%20Madrid&academic_year=2026-2027&q=0650')
        self.assertEqual(status,200)
        self.assertEqual(len(catalog['modules']),1)

    def test_unconfirmed_document_rejected(self):
        status,body=self.store(SOURCE,confirmed=False)
        self.assertEqual(status,400,body)
        self.assertIn('Confirme',body['error'])

if __name__=='__main__':unittest.main()
