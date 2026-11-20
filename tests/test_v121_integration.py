"""Pruebas HTTP integradas: revisión curricular sin alterar registros."""
from __future__ import annotations
import io, json, tempfile, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
import database, app

MODULE='Proceso integral de la actividad comercial'
SOURCE=f'''Módulo profesional: {MODULE}\nCódigo: 0650\nRESULTADOS DE APRENDIZAJE Y CRITERIOS DE EVALUACIÓN\nRA1. Determina los elementos patrimoniales de una empresa siguiendo sus operaciones.\nCriterios de evaluación:\na) Se han identificado las fases del ciclo económico en una actividad empresarial.\nb) Se han clasificado elementos patrimoniales en distintas masas contables.\nRA2. Aplica normas de registro contable en operaciones empresariales habituales.\nCriterios de evaluación:\na) Se han definido las cuentas necesarias para los asientos contables.\nb) Se han aplicado las normas de cargo y abono de las cuentas.\nCONTENIDOS\nOtras referencias no curriculares.
'''

class PreviewHttpTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='eval121_http_')
  root=Path(cls.tmp.name)
  cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),patch.object(database,'DATA',root),
               patch.object(database,'STORAGE',root/'almacen'),patch.object(database,'BACKUPS',root/'copias')]
  for p in cls.patches:p.start()
  database.STORAGE.mkdir(parents=True,exist_ok=True)
  database.BACKUPS.mkdir(parents=True,exist_ok=True)
  cls.server,cls.url=app.start()
  with database.connect() as db:
   db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',('2026-2027','Administración y Finanzas',MODULE,'A',database.now(),'Comunidad de Madrid'))
   cls.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]

 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close()
  for p in reversed(cls.patches):p.stop()
  cls.tmp.cleanup()

 @classmethod
 def send(cls,document=SOURCE,mod_code='0650',kind='programacion',file_name='curriculo.txt'):
  boundary='----Eval121-Testing'
  header=f'--{boundary}\r\nContent-Disposition: form-data; name="module_id"\r\n\r\n{cls.mid}\r\n--{boundary}\r\nContent-Disposition: form-data; name="module_code"\r\n\r\n{mod_code}\r\n--{boundary}\r\nContent-Disposition: form-data; name="document_kind"\r\n\r\n{kind}\r\n--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{file_name}"\r\nContent-Type: text/plain\r\n\r\n'.encode()
  body=header+(document if isinstance(document,bytes) else document.encode('utf8'))+f'\r\n--{boundary}--\r\n'.encode()
  request=urllib.request.Request(cls.url+'api/curriculum/review-preview',method='POST',data=body,
    headers={'X-App-Token':app.TOKEN,'Content-Type':'multipart/form-data; boundary='+boundary})
  try:
   with urllib.request.urlopen(request,timeout=8) as response:return response.status,json.load(response)
  except urllib.error.HTTPError as ex:return ex.code,json.load(ex)

 def setUp(self):
  with database.connect() as db:
   db.execute('DELETE FROM criteria WHERE outcome_id IN (SELECT id FROM outcomes WHERE module_id=?)',(self.mid,))
   db.execute('DELETE FROM outcomes WHERE module_id=?',(self.mid,))
   db.execute('DELETE FROM programming_drafts WHERE module_id=?',(self.mid,))

 def test_preview_references_and_no_mutation(self):
  code,response=self.send()
  self.assertEqual(code,200,response)
  self.assertEqual(response['summary'],{'ra':2,'ce':4})
  self.assertEqual(response['outcomes'][0]['locations'],['línea 4'])
  self.assertFalse(response['can_auto_apply'])
  self.assertTrue(response['source']['sha256'])
  self.assertEqual(sum(float(x['module_weight_pct']) for x in response['default_weight_proposal']),100)
  with database.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM outcomes WHERE module_id=?',(self.mid,)).fetchone()[0],0)
   self.assertEqual(db.execute('SELECT count(*) FROM criteria').fetchone()[0],0)

 def test_existing_manual_weight_and_criterion_survive(self):
  with database.connect() as db:
   db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(self.mid,'RA1','Texto antiguo intencionado',40.0))
   ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
   db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(ra,'RA1.a','Criterio antiguo con evidencia',90.0))
  code,result=self.send()
  self.assertEqual(code,200,result)
  self.assertEqual(result['existing_ra_count'],1)
  self.assertTrue(result['comparison']['blocking'])
  with database.connect() as db:
   self.assertEqual(db.execute('SELECT weight FROM outcomes WHERE code="RA1"').fetchone()[0],40.0)
   self.assertEqual(db.execute('SELECT weight FROM criteria WHERE code="RA1.a"').fetchone()[0],90.0)

 def test_code_conflict_blocks_preview(self):
  with database.connect() as db:
   import program_builder
   d=program_builder.load(db,self.mid)['draft']
   d['official_module_code']='0650'
   db.execute('INSERT OR REPLACE INTO programming_drafts(module_id,content_json,updated_at) VALUES(?,?,?)',(self.mid,json.dumps(d),database.now()))
  code,response=self.send(mod_code='0651')
  self.assertEqual(code,400,response)
  self.assertIn('no coincide',response['error'])

if __name__=='__main__':unittest.main()
