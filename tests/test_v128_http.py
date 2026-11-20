"""API multipart de calendarios: autenticada, sin guardar propuestas en SQLite."""
from __future__ import annotations
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import database

SOURCE='''Calendario FP Canarias. Curso 2026-2027.
Inicio de clases: 16 de septiembre de 2026.
Fin de clases: 22 de junio de 2027.
'''


class CalendarDocumentHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval128_calendar_doc_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()
        with database.connect() as db:
            db.execute('''INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory)
              VALUES(?,?,?,?,?,?)''',('2026-2027','Administración y Finanzas','Ofimática','1A',database.now(),'Canarias'))
            cls.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.temp.cleanup()

    def request(self,region='Canarias',year='2026-2027',module_id=None,token=True):
        bound='----EvaluaFP-Test-Calendar-v128'
        fields={'module_id':str(module_id or self.mid),'region':region,
                'academic_year':year,'allow_ocr':'false'}
        parts=[]
        for key,value in fields.items():
            parts.append((f'--{bound}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
        parts.append((f'--{bound}\r\nContent-Disposition: form-data; name="document"; filename="calendario.txt"\r\n'
                      'Content-Type: text/plain\r\n\r\n').encode()+SOURCE.encode()+b'\r\n')
        parts.append((f'--{bound}--\r\n').encode())
        headers={'Content-Type':'multipart/form-data; boundary='+bound}
        if token:headers['X-App-Token']=app.TOKEN
        req=urllib.request.Request(self.root+'api/national/calendar-document-preview',
                                   method='POST',data=b''.join(parts),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=8) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:return exc.code,json.load(exc)

    def test_success_is_read_only(self):
        status,result=self.request()
        self.assertEqual(status,200)
        self.assertTrue(result['scope_ok'])
        self.assertTrue(result['no_changes_saved'])
        self.assertEqual(result['candidates']['start_date'][0]['value'],'2026-09-16')
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_center_calendars').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_calendar_revisions').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM programming_drafts').fetchone()[0],0)

    def test_scope_and_auth_are_rejected(self):
        self.assertIn(self.request(token=False)[0],(401,403))
        for r,y,m in [('Comunidad de Madrid','2026-2027',None),('Canarias','2027-2028',None),
                      ('Canarias','2026-2027',999999)]:
            status,body=self.request(region=r,year=y,module_id=m)
            self.assertEqual(status,400)
            self.assertIn('error',body)


if __name__=='__main__':unittest.main()