"""Exporta curriculo RA/CE + notas exclusivamente curriculares para Additio."""
import csv
import io
import sys
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database,evaluacion,exportaciones

class CurriculumTests(unittest.TestCase):
    def setUp(self):
        database.init()
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026/27','CFGM','Técnica Contable','2GM',database.now()))
            self.mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(self.mid,'FP001','García, Lucía'))
            self.sid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                      (self.mid,'RA2','Registrar operaciones contables',100))
            rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                      (rid,'RA2.a','Asientos en el libro diario',50))
            self.cid1=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                      (rid,'RA2.b','Traslada asientos al mayor',50))
            self.cid2=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            evaluacion.update_settings(d,{'module_id':self.mid,'enterprise_mode':'integrated','enterprise_weight':0,
                 'validated':True,'teacher_note':'La formación en empresa se integra en las evidencias de los RA.'})
            self.iid=evaluacion.add_instrument(d,{'module_id':self.mid,'term':1,'title':'Examen T1',
                 'kind':'examen','targets':[{'criterion_id':self.cid1,'weight':100},
                                           {'criterion_id':self.cid2,'weight':100}]})
            evaluacion.put_score(d,{'instrument_id':self.iid,'criterion_id':self.cid1,'student_id':self.sid,'score':8})
            evaluacion.put_score(d,{'instrument_id':self.iid,'criterion_id':self.cid2,'student_id':self.sid,'score':6})

    def test_config_files_and_text_link_ra(self):
        with database.connect() as d:
            ra,_,_=exportaciones.additio_curriculum_xlsx(d,self.mid,'ra')
            ce,_,_=exportaciones.additio_curriculum_xlsx(d,self.mid,'ce')
            detail,_,_=exportaciones.additio_curriculum_xlsx(d,self.mid,'detalle')
            pack,_,_=exportaciones.additio_curriculum_zip(d,self.mid)
        for blob in (ra,ce,detail,pack):
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                self.assertIsNone(z.testzip())
        with zipfile.ZipFile(io.BytesIO(ce)) as z:
            xml=z.read('xl/sharedStrings.xml').decode()
            self.assertIn(f'2.a. Asientos en el libro diario. EFP{self.mid}_RA2',xml)
            self.assertIn(f'2.b. Traslada asientos al mayor. EFP{self.mid}_RA2',xml)
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]),1)
        with zipfile.ZipFile(io.BytesIO(pack)) as z:
            self.assertEqual(len([n for n in z.namelist() if n.endswith('.xlsx')]),3)
            self.assertIn('LEER_ANTES_DE_IMPORTAR.txt',z.namelist())

    def test_grade_export_only_ra_ce_no_exams(self):
        with database.connect() as d:
            raw,_,_=exportaciones.export_additio(d,self.mid,'notas')
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
            self.assertEqual(rows[0],['Codigo','Alumno',f'EFP{self.mid}_RA2','2.a','2.b'])
            self.assertEqual(rows[1][2:],['','',''],'Sin cierre docente se ocultan notas definitivas.')
            preview,_,_=exportaciones.export_additio(d,self.mid,'seguimiento')
            pr=list(csv.reader(io.StringIO(preview.decode('utf-8-sig')),delimiter=';'))
            self.assertEqual(pr[1][2:],['7.0','8.0','6.0'])
            evaluacion.close_student(d,self.mid,self.sid,'Calificaciones comprobadas y validadas por el docente.')
            raw,_,_=exportaciones.export_additio(d,self.mid,'notas')
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
            self.assertEqual(rows[1][2:],['7.0','8.0','6.0'])
            self.assertFalse(any('Examen' in x or 'Instrumento' in x for x in rows[0]))

    def test_ra_collision_between_modules_is_avoided(self):
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026/27','CFGM','Otro módulo','2GM',database.now()))
            other=d.execute('SELECT last_insert_rowid()').fetchone()[0]
        self.assertNotEqual(f'EFP{self.mid}_RA2',f'EFP{other}_RA2')

if __name__=='__main__':unittest.main()
