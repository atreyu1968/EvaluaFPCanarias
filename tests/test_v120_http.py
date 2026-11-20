"""Prueba HTTP real de las nuevas rutas, aislada con una base temporal."""
from __future__ import annotations
import io
import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import database
import boe_discovery

class HttpNationalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='evalua_v120_http_')
        root=Path(cls.tmp.name)
        cls.stack=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                   patch.object(database,'DATA',root),
                   patch.object(database,'STORAGE',root/'almacen'),
                   patch.object(database,'BACKUPS',root/'copias')]
        for p in cls.stack:p.start()
        for directory in (database.STORAGE,database.BACKUPS):directory.mkdir(parents=True,exist_ok=True)
        cls.server,cls.url=app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.stack):p.stop()
        cls.tmp.cleanup()

    def request_json(self,path,obj):
        req=urllib.request.Request(self.url+path,method='POST',data=json.dumps(obj).encode('utf8'),
            headers={'X-App-Token':app.TOKEN,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=7) as response:
            return json.load(response)

    def test_post_search_and_inspect_boe(self):
        dummy={'data':[{'identificador':'BOE-A-2011-19533','titulo':'Real Decreto del título de Técnico Superior en Administración y Finanzas'}]}
        with patch.object(boe_discovery,'_request_json',return_value=dummy):
            result=self.request_json('api/national/boe-search',{'cycle':'Administración y Finanzas','region':'Galicia','academic_year':'2026-2027'})
        self.assertEqual(result['records'][0]['id'],'BOE-A-2011-19533')
        with patch.object(boe_discovery,'_request_json',side_effect=[
            {'data':dummy['data'][0]}, {'data':{'afectada_por':[]}}]):
            inspected=self.request_json('api/national/boe-inspect',{'boe_id':'BOE-A-2011-19533'})
        self.assertTrue(inspected['approval_required'])
        self.assertIn('Administración y Finanzas',inspected['title'])

    def test_post_docx_table_preview_does_not_save(self):
        from docx import Document
        d=Document();t=d.add_table(rows=2,cols=4)
        for cell,value in zip(t.rows[0].cells,['Código','Módulo','Horas totales','Horas semanales']):cell.text=value
        for cell,value in zip(t.rows[1].cells,['0650','Proceso integral de la actividad comercial','202','6']):cell.text=value
        file=io.BytesIO();d.save(file)
        boundary='----EvaluaFP-Test-V120'
        body=(('--'+boundary+'\r\nContent-Disposition: form-data; name="allow_ocr"\r\n\r\nfalse\r\n--'+boundary+
               '\r\nContent-Disposition: form-data; name="document"; filename="horas.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode('ascii')+
              file.getvalue()+('\r\n--'+boundary+'--\r\n').encode('ascii'))
        req=urllib.request.Request(self.url+'api/national/document-preview',method='POST',data=body,
            headers={'X-App-Token':app.TOKEN,'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(req,timeout=7) as response:
            result=json.load(response)
        self.assertEqual(result['count'],1)
        self.assertTrue(result['requires_teacher_confirmation'])
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_hour_records').fetchone()[0],0)

if __name__=='__main__':unittest.main()
