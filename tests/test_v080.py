"""Regresión v0.8: alumnos desconocidos, altas atómicas, iconos y presentación."""
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import database as data

class Version080HTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server,cls.url=app.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def req(self,path,body=None,ctype='application/json'):
        if body is not None and not isinstance(body,bytes):body=json.dumps(body).encode('utf-8')
        req=urllib.request.Request(self.url+path,body,headers={
            'X-App-Token':app.TOKEN,'Content-Type':ctype},method='POST' if body is not None else 'GET')
        with urllib.request.urlopen(req,timeout=10) as r:
            return json.loads(r.read()) if 'json' in r.headers.get('Content-Type','') else r.read()

    def test_bulk_missing_students_and_atomic_resume(self):
        module=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa','name':'Evaluación v080','group_name':'A'})
        ra=self.req('api/outcomes',{'module_id':module['id'],'code':'RA080','description':'RA de prueba','weight':100})
        ce=self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA080.a','description':'CE de prueba','weight':100})
        exam=self.req('api/exams/manual',{'module_id':module['id'],'title':'Examen v080','questions':[{
            'criterion_id':ce['id'],'kind':'desarrollo','prompt':'Explica el contenido', 'points':10,
            'ideal_answer':'Explicación correcta','rubric':[{'criterion':'Contenido','weight_pct':100}]
        }]})
        pic=io.BytesIO();Image.new('RGB',(90,90),'white').save(pic,format='PNG')
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('COD-080-A/001.png',pic.getvalue())
            z.writestr('COD-080-A/002.png',pic.getvalue())
            z.writestr('COD-080-B/001.png',pic.getvalue())
        boundary='BND080'
        blob=(f'--{boundary}\r\nContent-Disposition: form-data; name="exam_id"\r\n\r\n{exam["id"]}\r\n'.encode()+
              f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="lote.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()+archive.getvalue()+b'\r\n'+
              f'--{boundary}--\r\n'.encode())
        try:
            self.req('api/submissions/batch',blob,'multipart/form-data; boundary='+boundary)
            self.fail('Se esperaba preflight de alumnos desconocidos')
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code,409)
            body=json.loads(e.read())
            self.assertEqual(body['code'],'MISSING_STUDENTS')
            self.assertEqual(body['module_id'],module['id'])
            self.assertEqual(body['missing_students'],['COD-080-A','COD-080-B'])
        self.assertEqual(self.req('api/exams/'+str(exam['id']))['submissions'],[])
        # Un lote incorrecto NO debe crear parcialmente alumnos.
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req('api/students/bulk',{'module_id':module['id'],'students':[
                {'code':'COD-080-A','name':'Alumno de prueba A'}, {'code':'COD-080-B','name':''}]})
        self.assertEqual(ctx.exception.code,400)
        self.assertEqual(self.req('api/modules/'+str(module['id']))['students'],[])
        created=self.req('api/students/bulk',{'module_id':module['id'],'students':[
            {'code':'COD-080-A','name':'Alumno de prueba A'}, {'code':'COD-080-B','name':'Alumno de prueba B'}]})
        self.assertEqual(len(created['created']),2)
        self.assertEqual(len(self.req('api/modules/'+str(module['id']))['students']),2)
        result=self.req('api/submissions/batch',blob,'multipart/form-data; boundary='+boundary)
        self.assertEqual(len(result['created']),2)
        self.assertEqual(sorted(r['pages'] for r in result['created']),[1,2])
        rows=self.req('api/exams/'+str(exam['id']))['submissions']
        self.assertEqual(len(rows),2)
        audit=self.req('api/audit/'+str(rows[0]['id']))
        self.assertTrue(isinstance(audit,list))

    def test_icons_splash_and_binary_packaging(self):
        import struct
        p=ROOT/'web'
        ico=(ROOT/'assets'/'EvaluaFP.ico').read_bytes()
        self.assertEqual(ico[:4],b'\x00\x00\x01\x00')
        self.assertTrue(len(ico)>12000)
        self.assertEqual((p/'favicon.ico').read_bytes(),ico)
        js=(p/'app.js').read_text(encoding='utf-8')
        html=(p/'index.html').read_text(encoding='utf-8')
        self.assertIn('FRANCISCO JAVIER GONZALEZ ROLO',html)
        self.assertIn('id="intro-overlay"',html)
        self.assertIn('id="students-dialog"',html)
        self.assertIn('let remaining=10',js)
        self.assertIn('promptNewStudents',js)
        bat=(ROOT/'crear_exe_windows.bat').read_text(encoding='utf-8')
        self.assertIn('--icon "assets\\EvaluaFP.ico"',bat)
        iss=(ROOT/'instalador'/'EvaluaFP.iss').read_text(encoding='utf-8')
        self.assertIn('SetupIconFile=..\\assets\\EvaluaFP.ico',iss)
        self.assertIn('"1.0.2"',iss)
        for route,magic in [('favicon.ico',b'\x00\x00\x01\x00'),('logo.svg',b'<svg')]:
            b=self.req(route)
            self.assertTrue(b.startswith(magic))
        page=self.req('')
        self.assertIn(b'id="intro-overlay"',page)

if __name__=='__main__':unittest.main()
