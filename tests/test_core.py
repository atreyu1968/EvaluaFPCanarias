"""Pruebas de integridad local (sin llamadas de red a IA). Ejecutar python -m unittest discover -s tests -v"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# El directorio de datos debe definirse antes de importar database.
_TEMP = tempfile.mkdtemp(prefix='evaluafp_test_')
os.environ['EVALUAFP_DATA_DIR'] = _TEMP
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database as dbm
import logic
from PIL import Image

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):dbm.init()
    @classmethod
    def tearDownClass(cls):shutil.rmtree(_TEMP,ignore_errors=True)
    def unique(self):
        with dbm.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                ('2026-2027','CFGM','Técnica Contable','1A',dbm.now()))
            mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,'RA1','Realiza asientos',30))
            rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(rid,'RA1.a','Registra compras',60))
            cid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'A001','Alumno A'))
            sid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('''INSERT INTO exams(module_id,title,kind,total_points,created_at) VALUES(?,?,?,?,?)''',
                      (mid,'Examen de contabilidad','desarrollo',10,dbm.now()))
            eid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('''INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points,ideal_answer,rubric_json)
                VALUES(?,?,?,?,?,?,?,?)''',(eid,cid,1,'desarrollo','Registra una factura de compra.',10,'Debe 600 y 4727; Haber 400',
                '[{"criterion":"Asiento correcto","weight_pct":100}]'))
            return mid, sid, eid, cid
    def test_weights_preserve_programming_proportions(self):
        cs=[{'id':1,'code':'RA1.a','description':'a','outcome_weight':30,'criterion_weight':60},
            {'id':2,'code':'RA2.b','description':'b','outcome_weight':20,'criterion_weight':20}]
        slots=logic.allocate_slots(cs,6,'mixto',10)
        self.assertEqual(len(slots),6)
        self.assertEqual(round(sum(s['points'] for s in slots),2),10)
        self.assertAlmostEqual(sum(s['points'] for s in slots if s['criterion_id']==1),10*18/22,delta=.03)
    def test_no_fabricated_weights(self):
        cs=[{'id':1,'code':'RA1.a','description':'a','outcome_weight':None,'criterion_weight':50}]
        with self.assertRaisesRegex(ValueError,'ponderaciones'):
            logic.allocate_slots(cs,1,'test',10)
    def test_multiple_ordered_files_and_originals(self):
        mid,student_id,exam_id,_=self.unique()
        with dbm.connect() as d:
            exam=d.execute('SELECT * FROM exams WHERE id=?',(exam_id,)).fetchone()
            student=d.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
            im=Image.new('RGB',(150,200),'white');raw=io.BytesIO();im.save(raw,'PNG')
            imagebytes=raw.getvalue()
            import fitz
            pdf=fitz.open();pdf.new_page();pdf.new_page();payload=pdf.tobytes();pdf.close()
            submission_id,n=logic.ingest(d,exam,student,[('primera.png',imagebytes),('dos_paginas.pdf',payload)])
            self.assertEqual(n,3)
            docs=d.execute('SELECT * FROM source_files WHERE submission_id=? ORDER BY sequence',(submission_id,)).fetchall()
            self.assertEqual([x['original_name'] for x in docs],['primera.png','dos_paginas.pdf'])
            self.assertEqual(Path(docs[0]['local_path']).read_bytes(),imagebytes)
            self.assertEqual([x['page_number'] for x in d.execute('SELECT page_number FROM pages WHERE submission_id=? ORDER BY page_number',(submission_id,))],[1,2,3])
            with self.assertRaisesRegex(ValueError,'Ya existe'):
                logic.ingest(d,exam,student,[('primera.png',imagebytes)])
    def test_cross_page_continuation_and_teacher_validation(self):
        mid,student_id,exam_id,_=self.unique()
        with dbm.connect() as d:
            exam=d.execute('SELECT * FROM exams WHERE id=?',(exam_id,)).fetchone()
            student=d.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
            im=Image.new('RGB',(180,100),'white');bytesio=io.BytesIO();im.save(bytesio,'PNG')
            sid,_=logic.ingest(d,exam,student,[('001.png',bytesio.getvalue()),('002.png',bytesio.getvalue())])
            pages=[{'segments':[{'question_number':1,'text':'Debe 600 por 100 €', 'is_continuation':False,'uncertain':False,'notes':''}]},
                   {'segments':[{'question_number':1,'text':'y 4727 por 7 €; Haber 400 por 107 €', 'is_continuation':True,'uncertain':False,'notes':''}]}]
            def fake_chat(role,prompt,images=None):
                self.assertEqual(role,'vision')
                if len(images)==1:return pages[0],'modelo-vision'
                return pages[1],'modelo-vision'
            with patch.object(logic.ia,'chat',side_effect=fake_chat):
                run,count=logic.transcribe(d,d.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone())
            self.assertEqual(count,2)
            cor=d.execute('SELECT * FROM corrections WHERE run_id=?',(run,)).fetchone()
            self.assertIn('Debe 600',cor['transcription'])
            self.assertIn('Haber 400',cor['transcription'])
            self.assertEqual(json.loads(cor['page_numbers_json']),[1,2])
            with patch.object(logic.ia,'chat',return_value=({'score':8,'rubric':[
                 {'criterion':'Asiento correcto','points':8,'max_points':10,'justification':'Bien','evidence':'Debe 600'}],
                 'feedback':'Correcto','needs_review':False},'modelo-corrector')):
                logic.grade(d,d.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone())
            cor=d.execute('SELECT * FROM corrections WHERE run_id=?',(run,)).fetchone()
            self.assertEqual(cor['ai_score'],8)
            self.assertNotEqual(cor['status'],'validated')

if __name__=='__main__': unittest.main()
