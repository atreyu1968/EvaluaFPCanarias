"""Regresiones de importación integral, procedencia y revisión no destructiva."""
from __future__ import annotations
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import program_importer
import program_builder
import database as database

SAMPLE='''PROGRAMACIÓN CURSO 2026-2027
MARCO NORMATIVO DE LA PROGRAMACIÓN
Se relacionan las normas del título y del currículo, sujetas a verificación.
CARACTERÍSTICAS DEL CENTRO
El centro cuenta con aulas de gestión administrativa y ordenadores.
CARACTERÍSTICAS DEL ALUMNADO
El grupo presenta experiencias de aprendizaje diferentes.
OBJETIVOS DEL TÍTULO Y DEL MÓDULO
Interpretar los procesos administrativos aplicables a la actividad comercial.
CONTENIDOS
Registro contable de la actividad comercial y tratamiento del IGIC.
DISTRIBUCIÓN DE LAS ACTIVIDADES DE APRENDIZAJE
Tabla 2. Temporalización de las UT
1
Gestión de documentos de compraventa
X
1ª
2
Registro de operaciones contables
X
2ª
Tabla 3. Trazabilidad UT RA CE
METODOLOGÍA
Enseñanza basada en resolución de supuestos y tareas prácticas.
RECURSOS Y MATERIALES
Se utilizarán documentos de empresa y hojas de cálculo.
ACTIVIDADES EXTRAESCOLARES Y COMPLEMENTARIAS
Visitas a empresas, condicionadas a la autorización del centro.
EVALUACIÓN
Evaluación de RA y criterios a partir de evidencias documentadas.
SESIONES DE EVALUACIÓN
Se realizarán sesiones trimestrales.
CALIFICACIÓN
Los criterios se ponderarán conforme a los acuerdos del departamento.
FALTAS DE ASISTENCIA A CLASE
Se aplicará la normativa de asistencia vigente.
ACTIVIDADES DE RECUPERACIÓN
Se planificarán actividades individualizadas de recuperación.
PRUEBAS EXTRAORDINARIAS
El alumnado tendrá las oportunidades previstas en la norma.
ANEXO DE TRABAJO INTERNO
Apartado adicional del documento, que debe conservarse.
'''

class FullImportLocalTests(unittest.TestCase):
    def test_extracts_multiple_categories_and_preserves_unclassified(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'original.md';source.write_text(SAMPLE,encoding='utf-8')
            result=program_importer.analyze_document(source)
        self.assertGreaterEqual(result['statistics']['fields_identified'],12)
        for field in ('normative_references','center_characteristics','student_characteristics',
                      'objectives','contents','learning_activities','methodology','resources',
                      'extracurricular','assessment','grading','recovery','attendance'):
            self.assertIn(field,result['fields'])
        self.assertIn('ANEXO DE TRABAJO INTERNO',[x['title'] for x in result['sections']])
        self.assertFalse(result['approved'])
        self.assertEqual(len(result['proposed_units']),2)
        self.assertIsNone(result['proposed_units'][0]['hours'])
        self.assertEqual(result['proposed_hours']['total_hours'],None)

    def test_feoe_criteria_detected_without_modifying_grades(self):
        source=[{'field':'enterprise','body':'RA 4. Documentación comercial\no CE g) Protección de datos\no CE h) Archivo digital\nRA 5. Tesorería\no CE b) Medios de cobro','page_start':32}]
        found=program_importer.feoe_criteria_candidates(source)
        self.assertEqual([x['code'] for x in found],['RA4.g','RA4.h','RA5.b'])

    def test_hours_are_not_guessed_from_unrelated_numbers(self):
        result=program_importer.extract_hours('Las fechas son 2026-2027 y la evaluación contiene 13 criterios.')
        self.assertIsNone(result['total_hours'])
        self.assertFalse(result['confirmed_official'])
        result=program_importer.extract_hours('módulo con una duración de 202 horas, lo que supone 6 horas semanales.')
        self.assertEqual(result['total_hours'],202)
        self.assertEqual(result['weekly_hours'],6)
        self.assertFalse(result['confirmed_official'])

    def test_imported_sections_roundtrip_and_exports(self):
        database.init()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGS Administración y Finanzas','Prueba de importación completa','A',database.now()))
            mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            data=program_importer.analyze_document(Path(__file__), text=SAMPLE)
            draft=program_builder.load(db,mid)['draft'];draft['source_type']='import'
            draft['methodology']='Metodología corregida por el docente, no sustituir.'
            for key,value in data['fields'].items():
                if key!='methodology':draft[key]=value
            draft['imported_sections']=[{**sec,'programming_id':123} for sec in data['sections']]
            draft['import_info']={'programming_id':123,'filename':'programacion-original.md',
                                  'applied_fields':[k for k in data['fields'] if k!='methodology']}
            program_builder.save(db,mid,draft)
            loaded=program_builder.load(db,mid)['draft']
            self.assertEqual(loaded['methodology'],'Metodología corregida por el docente, no sustituir.')
            self.assertIn('IGIC',loaded['contents'])
            self.assertGreaterEqual(len(loaded['imported_sections']),14)
            md=program_builder.export(db,mid,'md')[0].decode('utf-8')
            self.assertIn('Apartado adicional del documento',md)
            self.assertIn('Sesiones de evaluación',md)
            self.assertIn('Transcripción',md)
            docx=program_builder.export(db,mid,'docx')[0]
            with zipfile.ZipFile(io.BytesIO(docx)) as z:
                self.assertIsNone(z.testzip())
                self.assertIn('Apartado adicional del documento',z.read('word/document.xml').decode('utf-8'))

    def test_docx_heading_styles_and_tables_imported(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'documento.docx'
            doc=Document()
            doc.add_heading('1. Datos identificativos', level=1)
            doc.add_paragraph('Módulo de gestión y administración del centro.')
            doc.add_heading('2. Punto de partida', level=1)
            doc.add_paragraph('Alumnado y contexto de aprendizaje del ciclo.')
            doc.add_heading('3. Justificación', level=1)
            doc.add_paragraph('Necesidad de desarrollar competencias profesionales.')
            doc.add_heading('4. Concreción objetivos', level=1)
            doc.add_paragraph('Aplicar los procedimientos de gestión documental.')
            doc.add_heading('5. Secuencia situaciones aprendizaje', level=1)
            doc.add_paragraph('Secuenciación y resultados esperados.')
            doc.add_heading('6. Evaluación y calificación', level=1)
            doc.add_paragraph('Los criterios se evaluarán por sus evidencias.')
            doc.add_heading('7. Temporalización', level=1)
            doc.add_paragraph('Se distribuye el aprendizaje entre evaluaciones.')
            table=doc.add_table(rows=1,cols=2)
            table.rows[0].cells[0].text='Unidad'
            table.rows[0].cells[1].text='Horas'
            doc.save(file)
            result=program_importer.analyze_document(file)
        self.assertGreaterEqual(result['statistics']['sections_mapped'],7)
        self.assertIn('identification_data',result['fields'])
        self.assertIn('academic_context',result['fields'])
        self.assertIn('learning_activities',result['fields'])
        self.assertIn('assessment',result['fields'])
        self.assertIn('Unidad | Horas',result['fields']['learning_activities'])

    def test_rejects_excessive_untrusted_content(self):
        draft={'source_type':'import','region':'Canarias','imported_sections':[{'title':'ANEXO', 'field':None,
            'body':'A'*60001,'page_start':1,'page_end':1,'programming_id':8}]}
        with self.assertRaisesRegex(ValueError,'60.000|60000|superar'):
            program_builder.normalise(draft)

class FullImportHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.app=app
        cls.server,cls.base=app.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def request(self,url,payload=None):
        headers={'X-App-Token':self.app.TOKEN}
        data=None
        if payload is not None:
            data=json.dumps(payload).encode('utf-8');headers['Content-Type']='application/json'
        req=urllib.request.Request(self.base+url,data=data,headers=headers,
                                   method='POST' if payload is not None else 'GET')
        with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read())

    def test_preview_and_apply_are_safe_and_require_confirmation(self):
        m=self.request('api/modules',{'academic_year':'2026-2027','cycle':'CFGS','name':'Demo importación','group_name':'A'})
        mid=m['id']
        with database.connect() as db:
            file=database.STORAGE/'programaciones'/f'prueba_{mid}.md'
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(SAMPLE,encoding='utf-8')
            db.execute('INSERT INTO programmings(module_id,filename,local_path,sha256,extracted_text,uploaded_at) VALUES(?,?,?,?,?,?)',
                  (mid,'Original.md',str(file),'demo',SAMPLE,database.now()))
            pid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            draft=program_builder.load(db,mid)['draft']
            draft['methodology']='No sustituir el texto docente.'
            program_builder.save(db,mid,draft)
        preview=self.request(f'api/programmings/{pid}/import-preview')
        self.assertGreaterEqual(preview['statistics']['fields_identified'],12)
        self.assertTrue(preview['existing_fields']['methodology'])
        self.assertEqual(preview['module_id'],mid)
        before=self.request(f'api/programming-builder/{mid}')
        self.assertEqual(before['draft']['methodology'],'No sustituir el texto docente.')
        data=self.request('api/programmings/apply-content',{
          'programming_id':pid,'accepted_fields':['resources','assessment','contents'],
          'edited_fields':{'resources':'Recursos editados en vista previa'},
          'keep_source_sections':True,'accept_document_hours':False})
        self.assertTrue(data['ok']);self.assertGreaterEqual(data['sections_preserved'],15)
        after=self.request(f'api/programming-builder/{mid}')
        self.assertEqual(after['draft']['methodology'],'No sustituir el texto docente.')
        self.assertEqual(after['draft']['resources'],'Recursos editados en vista previa')
        self.assertIn('IGIC',after['draft']['contents'])
        self.assertGreaterEqual(len(after['draft']['imported_sections']),15)
        self.assertEqual(after['draft']['schedule']['total_hours'],0)
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.request('api/programmings/apply-content',{
                'programming_id':pid,'accepted_fields':['admin'], 'keep_source_sections':False})
        self.assertEqual(err.exception.code,400)
        file.unlink(missing_ok=True)

if __name__=='__main__':unittest.main()
