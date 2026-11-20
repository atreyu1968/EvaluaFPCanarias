"""Verifica PDF real, solución oculta al alumnado, migración y generación de problemas."""
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import database
import logic
import exam_pdf
import fitz

class PdfProblemsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):database.init()
    def create_data(self):
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026-2027','CFGM','Técnica Contable','2.º A',database.now()))
            mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,'RA2','Realiza registros',100))
            rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(rid,'RA2.a','Registra operaciones de compraventa',100))
            cid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
        return mid,cid

    def test_slot_assignment_respects_points_and_problems(self):
        criteria=[{'id':8,'code':'RA2.a','description':'Compras','outcome_weight':60,'criterion_weight':60},
                  {'id':9,'code':'RA3.b','description':'Ventas','outcome_weight':40,'criterion_weight':50}]
        slots=logic.allocate_slots(criteria,8,'mixto',10,3)
        self.assertEqual(sum(s['kind']=='problema' for s in slots),3)
        self.assertEqual(round(sum(x['points'] for x in slots),2),10)
        with self.assertRaisesRegex(ValueError,'número de problemas'):
            logic.allocate_slots(criteria,8,'mixto',10,9)
        self.assertTrue(all(s['kind']=='problema' for s in logic.allocate_slots(criteria,3,'problemas',10)))

    def test_pdf_and_zip_export_from_sqlite(self):
        mid,cid=self.create_data()
        with database.connect() as d:
            d.execute('''INSERT INTO exam_batches(module_id,title,difficulty,model_count,questions_per_model,bank_size,created_at)
                         VALUES(?,?,?,?,?,?,?)''',(mid,'Prueba con problemas','alto',2,1,6,database.now()))
            batch_id=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            for variant in 'AB':
                d.execute('''INSERT INTO exams(module_id,title,kind,total_points,created_at,status,batch_id,variant_label,
                            difficulty,center_name,exam_date,duration_minutes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (mid,'Examen de compraventa','problemas',10,database.now(),'ready',batch_id,variant,
                        'alto','IES Ejemplo Tenerife','2026-11-25',90))
                eid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                d.execute('''INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points,
                           ideal_answer,rubric_json) VALUES(?,?,?,?,?,?,?,?)''',
                      (eid,cid,1,'problema',
                       'La empresa compra mercancías por 1.000 euros. IGIC del 7 %.\na) Calcule la cuota de IGIC.\nb) Registre el asiento contable.',10,
                       'Solución secreta: 70 euros. Debe: 600, 4727. Haber: 400.',
                       json.dumps([{'criterion':'Cálculo IGIC','weight_pct':40},
                                   {'criterion':'Asiento equilibrado','weight_pct':60}])))
            one=d.execute('SELECT id FROM exams WHERE batch_id=? ORDER BY variant_label',(batch_id,)).fetchone()[0]
            student=exam_pdf.build_exam_pdf(d,one)
            teacher=exam_pdf.build_exam_pdf(d,one,True)
            self.assertTrue(student.startswith(b'%PDF-'))
            self.assertTrue(teacher.startswith(b'%PDF-'))
            with fitz.open(stream=student,filetype='pdf') as p:
                self.assertGreaterEqual(len(p),2)
                st='\n'.join(x.get_text() for x in p)
                self.assertIn('IES Ejemplo Tenerife',st)
                self.assertIn('Técnica Contable',st)
                self.assertIn('Modelo / dificultad',st)
                self.assertIn('25/11/2026',st)
                self.assertIn('RA2.a',st)
                self.assertIn('Problema práctico 1',st)
                self.assertIn('Registre el asiento contable',st)
                self.assertNotIn('Solución secreta',st)
                self.assertNotIn('Cálculo IGIC',st)
            with fitz.open(stream=teacher,filetype='pdf') as p:
                txt='\n'.join(x.get_text() for x in p)
                self.assertIn('Solución secreta',txt)
                self.assertIn('Cálculo IGIC',txt)
                self.assertIn('60 %',txt)
            zip_bytes=exam_pdf.build_batch_zip(d,batch_id)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
                names=archive.namelist()
                self.assertIn('Modelo_A_alumnado.pdf',names)
                self.assertIn('Modelo_B_alumnado.pdf',names)
                self.assertNotIn('Modelo_B_soluciones_y_rubrica.pdf',names)
                self.assertEqual(len(names),3)
                self.assertTrue(archive.read('Modelo_B_alumnado.pdf').startswith(b'%PDF-'))
            solutions_zip=exam_pdf.build_batch_zip(d,batch_id,teacher_only=True)
            with zipfile.ZipFile(io.BytesIO(solutions_zip)) as teacher_archive:
                self.assertIn('Modelo_B_soluciones_y_rubrica.pdf',teacher_archive.namelist())
                self.assertNotIn('Modelo_B_alumnado.pdf',teacher_archive.namelist())

    def test_pdf_export_works_for_legacy_exam_without_header(self):
        mid,cid=self.create_data()
        with database.connect() as d:
            d.execute('INSERT INTO exams(module_id,title,kind,total_points,created_at) VALUES(?,?,?,?,?)',
                      (mid,'Antiguo examen','desarrollo',10,database.now()))
            eid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('''INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points,ideal_answer)
                 VALUES(?,?,?,?,?,?,?)''',(eid,cid,1,'desarrollo','Describa la actividad.',10,'Solución.'))
            out=exam_pdf.build_exam_pdf(d,eid)
            self.assertTrue(out.startswith(b'%PDF-'))
            with fitz.open(stream=out,filetype='pdf') as pdf:
                txt='\n'.join(p.get_text() for p in pdf)
                self.assertIn('Antiguo examen',txt)
                self.assertNotIn('Solución.',txt)

    def test_generated_problem_banks_are_triple_and_disjoint(self):
        cs=[{'id':1,'code':'RA2.a','description':'Hacer presupuestos','outcome_weight':100,'criterion_weight':100}]
        slots=logic.allocate_slots(cs,2,'mixto',10,1)
        index=[0]
        def fake_ia(role,prompt,images=None):
            index[0]+=1
            marker=index[0]
            line=prompt.split('PLAN DE PREGUNTAS: ',1)[1].split('\n',1)[0]
            templates=json.loads(line)
            questions=[]
            for slot in templates:
                q={'number':slot['number'],'options':[],'correct_option':'',
                   'rubric':[{'criterion':'Procedimiento','weight_pct':40},{'criterion':'Resultado','weight_pct':60}],
                   'ideal_answer':('Solución paso a paso, calcular el importe, anotar los datos y verificar cada operación. ')*2}
                if slot['kind']=='test':
                    q['options']=['A) Sí','B) No','C) Depende','D) Ninguna'];q['correct_option']='A'
                if slot['kind']=='problema':
                    q['prompt']=(f'Problema profesional sobre presupuestos {marker} apartado {slot["number"]}. '\
                                 +('Coste, unidades y total; a) calcular b) justificar. ')*3 + (f'Muestra{marker}_'*20))
                else:
                    q['prompt']=f'Explica razonadamente el proceso {marker}-{slot["number"]} ' +(f'Concepto{marker}_'*22)
                questions.append(q)
            return {'questions':questions},'mock-model'
        with patch.object(logic.ia,'chat',side_effect=fake_ia):
            models,bank,model=logic.build_exam_models('Compras','mixto',10,slots,2,'medio')
        self.assertGreaterEqual(len(bank),3*len(slots))
        self.assertEqual(len(models),2)
        self.assertEqual(sum(q['kind']=='problema' for q in models[0]),1)
        for m in models:
            self.assertEqual(round(sum(q['points'] for q in m),2),10)
        fps=[logic.question_fingerprint(q['prompt']) for model_questions in models for q in model_questions]
        self.assertEqual(len(set(fps)),len(fps))

if __name__=='__main__':unittest.main()
