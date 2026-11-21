"""Prueba real de HTTP/SQLite: catálogo -> creación de módulo sin RA/CE ficticios."""
from __future__ import annotations
import json
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

import app
import database

SOURCE='https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19533'
TABLE=('Código título;Ciclo;Grado;Familia;Código módulo;Módulo\n'
       'DEMO-001;Administración y Finanzas;Superior;Administración y Gestión;0650;Proceso integral de la actividad comercial\n'
       'DEMO-001;Administración y Finanzas;Superior;Administración y Gestión;0651;Comunicación y atención al cliente')

class CatalogHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval123_http_')
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
    def query(self,path,payload=None,expect_error=False):
        data=json.dumps(payload).encode('utf8') if payload is not None else None
        req=urllib.request.Request(self.root+path,method='POST' if payload is not None else 'GET',data=data,
          headers={'X-App-Token':app.TOKEN,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=12) as resp:return resp.status,json.load(resp)
        except urllib.error.HTTPError as err:
            if not expect_error:raise
            return err.code,json.load(err)

    def test_end_to_end_and_non_destructive_draft(self):
        code,preview=self.query('api/national/catalog/preview',{'table':TABLE,'region':'Canarias','academic_year':'2026-2027'})
        self.assertEqual((code,preview['count']),(200,2))
        payload={'table':TABLE,'region':'Canarias','academic_year':'2026-2027',
                 'source_url':SOURCE,'source_title':'Norma consultada — ejemplo de validación del centro','teacher_confirmed':True}
        code,imported=self.query('api/national/catalog/import',payload)
        self.assertEqual((code,imported['added']),(200,2))
        code,catalog=self.query('api/national/catalog?region=Comunidad%20de%20Madrid&academic_year=2026-2027&q=0650')
        self.assertEqual((code,catalog['count']),(200,1))
        entry=catalog['entries'][0]
        creation={'academic_year':'2026-2027','territory':'Canarias',
            'cycle':entry['title_name'],'name':entry['module_name'],'group_name':'1A',
            'catalog_entry_id':entry['id']}
        code,new=self.query('api/modules',creation)
        self.assertEqual(code,200)
        self.assertTrue(new['catalog_used'])
        code,builder=self.query('api/programming-builder/'+str(new['id']))
        self.assertEqual(code,200)
        draft=builder['draft']
        self.assertEqual(draft['official_module_code'],'0650')
        self.assertEqual(draft['official_cycle_code'],'DEMO-001')
        self.assertFalse(draft['curriculum_confirmed'])
        self.assertEqual(draft['curriculum_source_url'],SOURCE)
        self.assertEqual(draft['region'],'Canarias')
        self.assertEqual(builder['counts']['ra'],0)
        self.assertEqual(builder['counts']['ce'],0)
        self.assertFalse(draft['schedule']['hours_confirmed'])
        self.assertFalse(draft['schedule']['calendar_confirmed'])
        # Un ámbito distinto de Canarias nunca puede crear un módulo.
        elsewhere=dict(creation,territory='Comunidad de Madrid')
        code,response=self.query('api/modules',elsewhere,expect_error=True)
        self.assertEqual(code,400)
        self.assertIn('solo admite',response['error'])
        bad=dict(creation,academic_year='2027-2028')
        code,response=self.query('api/modules',bad,expect_error=True)
        self.assertEqual(code,400)
        self.assertIn('no pertenece',response['error'])
        bad=dict(creation,name='Módulo inventado')
        code,response=self.query('api/modules',bad,expect_error=True)
        self.assertEqual(code,400)
        self.assertIn('no coincide',response['error'])
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM modules').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM corrections').fetchone()[0],0)

if __name__=='__main__':unittest.main()
