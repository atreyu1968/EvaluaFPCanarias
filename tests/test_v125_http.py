"""API de búsqueda estatal de títulos con autenticación, sin alteración de datos."""
import json
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

import app
import database
import official_title_index as index
from tests.test_v125_title_index import GRADE_HTML


class IndexHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval125_index_http_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.temp.cleanup()

    def request(self,region,year='2026-2027',grade='Superior',query='Administración',auth=True):
        body={'region':region,'academic_year':year,'grade':grade,'query':query}
        req=urllib.request.Request(self.root+'api/national/todofp/search-titles',data=json.dumps(body).encode('utf8'),method='POST',
          headers={'Content-Type':'application/json',**({'X-App-Token':app.TOKEN} if auth else {})})
        try:
            with urllib.request.urlopen(req,timeout=9) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:return exc.code,json.load(exc)

    def test_real_http_scope_and_no_writes(self):
        with patch.object(index.todofp,'fetch_todofp',side_effect=lambda url,opener=None:(url,GRADE_HTML)):
            for region in ('Canarias','Comunidad de Madrid','Ceuta','Melilla'):
                status,body=self.request(region)
                self.assertEqual(status,200)
                self.assertEqual(body['count'],1)
                self.assertEqual(body['territory'],region)
                self.assertEqual(body['results'][0]['title_code'],'')
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM modules').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fp_catalog_entries').fetchone()[0],0)

    def test_bad_scope_and_authentication_fail(self):
        self.assertIn(self.request('Canarias',auth=False)[0],(401,403))
        for reg,yr,grade in [('Comunidad falsa','2026-2027','Superior'),('Canarias','2026-2026','Superior'),('Canarias','2026-2027','Falso')]:
            status,body=self.request(reg,year=yr,grade=grade)
            self.assertEqual(status,400)
            self.assertIn('error',body)

if __name__=='__main__':unittest.main()
