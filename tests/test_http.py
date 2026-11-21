"""Prueba end-to-end de servidor, imágenes, SQLite, visor e informes sin API externa."""
import hashlib
import io
import json
import os
import tempfile
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image
from unittest.mock import patch

os.environ['EVALUAFP_DATA_DIR']=tempfile.mkdtemp(prefix='evaluafp_http_')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import database

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for directory in (database.DB_DIR,database.STORAGE,database.BACKUPS):directory.mkdir(parents=True,exist_ok=True)
        cls.server,cls.url=app.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def req(self,path,body=None,ctype='application/json'):
        if body is not None and not isinstance(body,bytes):body=json.dumps(body).encode()
        req=urllib.request.Request(self.url+path,body,headers={
            'X-App-Token':app.TOKEN,'Content-Type':ctype},method='POST' if body is not None else 'GET')
        with urllib.request.urlopen(req,timeout=5) as r:
            payload=r.read()
            return json.loads(payload) if r.headers.get('Content-Type','').startswith('application/json') else payload
    def test_feoe_minimum_standalone_document_endpoints(self):
        m=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa',
                  'name':'Módulo demo de tareas en empresa','group_name':'A'})
        mid=m['id']
        r=self.req('api/outcomes',{'module_id':mid,'code':'RA1',
                    'description':'Organiza documentación','weight':100})
        for j in range(10):
            self.req('api/criteria',{'outcome_id':r['id'],'code':'RA1.'+chr(97+j),
                    'description':'Identifica datos y documentos de trabajo para comprobar registros sencillos.',
                    'weight':10})
        proposed=self.req(f'api/programming-builder/{mid}/feoe-minimum')
        self.assertEqual(proposed['count'],2)
        self.assertFalse(proposed['approved'])
        self.assertTrue(self.req(f'api/programming-builder/{mid}/feoe-minimum.pdf').startswith(b'%PDF-'))
        self.assertTrue(self.req(f'api/programming-builder/{mid}/feoe-minimum.docx').startswith(b'PK'))
        accepted=self.req('api/programming-builder/feoe-minimum/accept',{'module_id':mid,
                          'teacher_confirmed':True,'rows':proposed['rows']})
        self.assertEqual(accepted['count'],2)
        updated=self.req(f'api/programming-builder/{mid}/feoe-minimum')
        self.assertEqual(updated['rows'][0]['activity'],proposed['rows'][0]['activity'])

    def test_generated_models_problem_persistence_and_pdf_route(self):
        m=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa','name':'Tesorería y compraventa','group_name':'A'})
        mid=m['id']
        ra=self.req('api/outcomes',{'module_id':mid,'code':'RA5','description':'Operaciones de gestión','weight':100})
        ce=self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA5.a','description':'Resuelve operaciones de compraventa','weight':100})
        counter=[0]
        def mock_generator(role,prompt,images=None):
            counter[0]+=1
            # En la prueba se simula la API con un banco sin duplicados.
            slots=json.loads(prompt.split('PLAN DE PREGUNTAS: ',1)[1].split('\n',1)[0])
            items=[]
            for n,slot in enumerate(slots,1):
                marker=f'CASO{counter[0]}PREGUNTA{n}'
                item={'number':n,'correct_option':'','options':[],
                      'ideal_answer':'Realizar operaciones contables y comprobar los importes con justificación completa.',
                      'rubric':[{'criterion':'Planteamiento','weight_pct':40},{'criterion':'Operación','weight_pct':60}]}
                if slot['kind']=='test':
                    item['options']=['A) Cuenta 600','B) Cuenta 700','C) Cuenta 430','D) Cuenta 400']
                    item['correct_option']='A'
                item['prompt']='En una empresa de Canarias, resuelva el siguiente supuesto práctico. '+(marker+' ')*25
                items.append(item)
            return {'questions':items},'simulado'
        payload={'module_id':mid,'criteria_ids':[ce['id']],'title':'Evaluación práctica',
                 'kind':'mixto','problem_count':1,'question_count':2,'model_count':2,'difficulty':'alto',
                 'total_points':10,'center_name':'IES Ejemplo Canarias','exam_date':'2026-11-25','duration_minutes':90}
        with patch.object(app.logic.ia,'chat',side_effect=mock_generator):
            result=self.req('api/exams/generate',payload)
        self.assertEqual(len(result['exam_ids']),2)
        self.assertEqual(result['bank_size'],6)
        fingerprints=[]
        for eid in result['exam_ids']:
            detail=self.req(f'api/exams/{eid}')
            self.assertEqual(detail['exam']['center_name'],'IES Ejemplo Canarias')
            self.assertEqual(detail['exam']['duration_minutes'],90)
            self.assertEqual(detail['exam']['exam_date'],'2026-11-25')
            self.assertEqual(sum(q['kind']=='problema' for q in detail['questions']),1)
            self.assertEqual(len(detail['questions']),2)
            fingerprints.extend(q['prompt'] for q in detail['questions'])
            self.assertTrue(self.req(f'api/exams/{eid}/pdf').startswith(b'%PDF-'))
        self.assertEqual(len(set(fingerprints)),4)
        student_zip=self.req(f'api/exam-batches/{result["batch_id"]}/pdf.zip')
        teacher_zip=self.req(f'api/exam-batches/{result["batch_id"]}/soluciones.zip')
        import zipfile
        with zipfile.ZipFile(io.BytesIO(student_zip)) as z:
            self.assertFalse(any('soluciones' in name for name in z.namelist()))
        with zipfile.ZipFile(io.BytesIO(teacher_zip)) as z:
            self.assertTrue(any('soluciones' in name for name in z.namelist()))

    def test_additio_ra_ce_download_routes(self):
        """Se descargan currículo y notas desde la UI/HTTP sin depender de API de IA."""
        m=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa',
                      'name':'Prueba Additio FP','group_name':'1B'})
        mid=m['id']
        ra=self.req('api/outcomes',{'module_id':mid,'code':'RA2','description':'Gestiona operaciones','weight':100})
        self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA2.a',
                                'description':'Contabiliza las compras','weight':100})
        import zipfile
        for path in ('additio-ra.xlsx','additio-ce.xlsx','additio-ce-detalle.xlsx',
                     'additio-notas.xlsx','additio-configuracion.zip'):
            raw=self.req(f'api/evaluation/{mid}/export/{path}')
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                self.assertIsNone(z.testzip())
        notes=self.req(f'api/evaluation/{mid}/export/additio-notas.csv').decode('utf-8-sig')
        self.assertIn(f'EFP{mid}_RA2',notes)
        self.assertNotIn('Instrumento',notes)

    def test_manual_exam_ai_maps_two_criteria_with_teacher_approval(self):
        m=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa',
                    'name':'Contabilidad para asignación curricular','group_name':'1A'})
        ra=self.req('api/outcomes',{'module_id':m['id'],'code':'RA2',
                    'description':'Reconoce el método contable','weight':100})
        c1=self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA2.a',
                     'description':'Reconoce la contabilidad por partida doble','weight':50})
        c2=self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA2.b',
                     'description':'Identifica el ciclo contable','weight':50})
        questions=[{'kind':'desarrollo',
            'prompt':'Explique las fases del ciclo contable y represente un asiento mediante partida doble.',
            'points':10,'ideal_answer':'Fases del ciclo y asiento.',
            'rubric':[{'criterion':'Justificación','weight_pct':100}]}]
        output={'assignments':[{'number':1,'status':'proposed','criteria':[
                  {'criterion_id':c1['id'],'weight_pct':60,'confidence':.95,'rationale':'Requiere partida doble'},
                  {'criterion_id':c2['id'],'weight_pct':40,'confidence':.92,'rationale':'Requiere ciclo contable'}]}]}
        with patch.object(app.manual_alignment.ia,'chat',return_value=(output,'modelo-ia-simulado')):
            found=self.req('api/exams/manual/classify',{'module_id':m['id'],'questions':questions})
        self.assertEqual(found['needs_review'],0)
        questions[0]['criteria_allocations']=found['assignments'][0]['criteria']
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req('api/exams/manual',{'module_id':m['id'],'title':'Prueba sin confirmar',
                  'questions':questions,'teacher_confirmed_curriculum':False})
        self.assertEqual(ctx.exception.code,400)
        created=self.req('api/exams/manual',{'module_id':m['id'],'title':'Prueba confirmada',
                  'questions':questions,'teacher_confirmed_curriculum':True})
        detail=self.req(f'api/exams/{created["id"]}')
        allocations=detail['questions'][0]['criteria_allocations']
        self.assertEqual([(x['criterion_id'],x['weight_pct']) for x in allocations],
                         [(c1['id'],60),(c2['id'],40)])

    def test_full_flow_manual_exam_viewer_and_validation(self):
        m=self.req('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa','name':'Técnica Contable','group_name':'1A'})
        mid=m['id']
        ra=self.req('api/outcomes',{'module_id':mid,'code':'RA1','description':'RA de prueba','weight':100})
        ce=self.req('api/criteria',{'outcome_id':ra['id'],'code':'RA1.a','description':'CE de prueba','weight':100})
        student=self.req('api/students',{'module_id':mid,'code':'COD001','name':'Alumno para prueba'})
        exam=self.req('api/exams/manual',{'module_id':mid,'title':'Prueba manual', 'questions':[{
            'criterion_id':ce['id'],'kind':'desarrollo','prompt':'Explica el asiento',
            'points':10,'ideal_answer':'Debe 600 y Haber 400',
            'rubric':[{'criterion':'Asiento','weight_pct':100}]}]})
        self.assertEqual(len(self.req(f'api/exams/{exam["id"]}')['questions']),1)
        student_pdf=self.req(f'api/exams/{exam["id"]}/pdf')
        teacher_pdf=self.req(f'api/exams/{exam["id"]}/soluciones.pdf')
        self.assertTrue(student_pdf.startswith(b'%PDF-'))
        self.assertTrue(teacher_pdf.startswith(b'%PDF-'))
        self.assertIn(b'Pregunta 1',self.req(f'print/exam/{exam["id"]}'))
        b=io.BytesIO();Image.new('RGB',(120,140),'white').save(b,format='PNG')
        files=b.getvalue();boundary='BOUNDARYTESTXYZ'
        chunks=[]
        for k,v in [('exam_id',str(exam['id'])),('student_id',str(student['id']))]:
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="pages"; filename="001.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+files+b'\r\n')
        chunks.append(f'--{boundary}--\r\n'.encode())
        result=self.req('api/submissions/upload',b''.join(chunks),f'multipart/form-data; boundary={boundary}')
        sid=result['id'];self.assertEqual(result['page_count'],1)
        detail=self.req(f'api/submissions/{sid}')
        pageid=detail['pages'][0]['id']; fid=detail['sources'][0]['id']
        self.assertEqual(self.req(f'api/source/{fid}'),files)
        self.assertTrue(self.req(f'api/pages/{pageid}/image').startswith(b'\xff\xd8'))
        self.assertEqual(detail['submission']['status'],'received')
        with patch.object(app.logic.ia,'chat',return_value=({'segments':[{'question_number':1,'text':'Debe 600 y Haber 400',
              'uncertain':False,'is_continuation':False,'notes':''}]},'modelo-vision')):
            tr=self.req('api/submissions/transcribe',{'submission_id':sid,'authorize_external_transfer':True})
        self.assertEqual(tr['segments'],1)
        c=self.req(f'api/submissions/{sid}')['corrections'][0]
        self.assertEqual(c['status'],'transcribed')
        with patch.object(app.logic.ia,'chat',return_value=({'score':9,'rubric':[
            {'criterion':'Asiento','points':9,'max_points':10,'justification':'Explicación correcta',
             'evidence':'Debe 600'}], 'feedback':'Bien', 'needs_review':False},'modelo-corrector')):
            self.req('api/submissions/correct',{'submission_id':sid,'authorize_external_transfer':True})
        c=self.req(f'api/submissions/{sid}')['corrections'][0]
        self.assertIsNone(c['teacher_score'])
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req('api/corrections/validate',{'correction_id':c['id'],'score':8,'comment':''})
        self.assertEqual(ctx.exception.code,400)
        self.req('api/corrections/validate',{'correction_id':c['id'],'score':8,
                                            'comment':'Respuesta parcialmente incompleta según la rúbrica'})
        report=self.req(f'print/report/{sid}').decode()
        self.assertIn('VALIDADO POR EL DOCENTE',report)
        self.assertIn('8 / 10',report)
        audit=self.req(f'api/audit/{sid}')
        self.assertTrue(any(a['action']=='teacher_grade_validated' for a in audit))
        self.assertEqual(self.req(f'api/submissions/{sid}')['submission']['status'],'validated')
        book=self.req('api/gradebook')
        ours=[r for r in book['exams'] if r['submission_id']==sid]
        self.assertEqual(len(ours),1)
        self.assertEqual(ours[0]['out_of_ten'],8)
        self.assertTrue(any(r['criterion_code']=='RA1.a' for r in book['criteria']))
        backup=self.req('api/backup')
        import zipfile
        with zipfile.ZipFile(io.BytesIO(backup)) as archive:
            names=archive.namelist()
            self.assertIn('datos/evaluafp.sqlite3',names)
            self.assertTrue(any(name.endswith('001_001.png') for name in names))

if __name__=='__main__': unittest.main()
