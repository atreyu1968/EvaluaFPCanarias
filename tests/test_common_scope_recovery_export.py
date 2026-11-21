"""Pruebas de recuperación y exportación sin datos personales reales."""
import io
import sqlite3
import unittest
import zipfile
from unittest.mock import patch
import common_scopes as cs
import common_scope_notebook as book
import common_scope_recovery as recovery
import common_scope_export as export


class ScopeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT,cycle TEXT,territory TEXT,
            academic_year TEXT,group_name TEXT);
          CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,name TEXT);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
          CREATE TABLE outcomes(id INTEGER PRIMARY KEY);
          INSERT INTO outcomes VALUES(99);
        """)
        for mid in (1,2):
            self.db.execute('INSERT INTO modules VALUES(?,?,?,?,?,?)',
                (mid,'Matemáticas y Ciencias aplicadas','CFGB Servicios Administrativos','Canarias',
                 '2026-2027','2 A'))
            self.db.execute('INSERT INTO students VALUES(?,?,?,?)',(mid,mid,'X1','Alumno de prueba'))
            cs.save(self.db,mid,{'competencies':[{'code':'1','description':'Competencia',
                    'criteria':[{'code':'1.1','description':'Criterio'}]}],'teacher_reviewed':True})
        self.db.execute('INSERT INTO students VALUES(?,?,?,?)',(3,1,'X3','OTRO_ALUMNO_CONFIDENCIAL'))
        self.raw={'student_id':1,'kind':'refuerzo','criterion_codes':['1.1'],
                  'objectives':'Objetivos','actions':'Actuaciones','instruments':'Rúbrica',
                  'due_date':'2026-12-15'}
        self.aid=book.create_activity(self.db,1,{'title':'Actividad','situation':'Situación','instrument':'rubrica',
                    'term':1,'activity_date':'2026-11-20','criterion_codes':['1.1']})
        self.eid=book.record_evidence(self.db,1,{'activity_id':self.aid,'student_id':1,
                    'criterion_code':'1.1','level':'SU','notes':'Evidencia','evidence_ref':''})

    def test_plan_and_revisions_are_preserved(self):
        pid=recovery.create(self.db,1,self.raw)
        raw={'plan_id':pid,'status':'revisado','observations':'Primera revisión',
             'evidence_ids':[self.eid],'teacher_confirmed':True}
        recovery.review(self.db,1,raw)
        recovery.review(self.db,1,{**raw,'status':'finalizado','observations':'Segunda revisión'})
        plan=recovery.load(self.db,1)['plans'][0]
        self.assertEqual(plan['status'],'finalizado')
        self.assertEqual(len(plan['reviews']),2)
        self.assertEqual(plan['reviews'][0]['evidence'][0]['id'],self.eid)
        self.assertEqual(self.db.execute('SELECT id FROM outcomes').fetchone()[0],99)

    def test_wrong_student_and_criterion(self):
        for raw in ({**self.raw,'student_id':2},{**self.raw,'criterion_codes':['RA1.a']},
                    {**self.raw,'due_date':'2026-02-30'}):
            with self.assertRaises(ValueError):
                recovery.create(self.db,1,raw)
        pid=recovery.create(self.db,1,{**self.raw,'student_id':3})
        with self.assertRaises(ValueError):
            recovery.review(self.db,1,{'plan_id':pid,'status':'revisado','observations':'Prueba',
                'evidence_ids':[self.eid],'teacher_confirmed':True})

    def test_pending_requires_verified_origin(self):
        with patch.object(recovery,'origins',return_value=[]):
            with self.assertRaises(ValueError):
                recovery.create(self.db,1,{**self.raw,'kind':'pendiente_primero','origin_confirmed':True})
        origin={'module_id':2,'student_id':2,'decision_id':10,
                'criteria':list(book.criterion_map(cs.load(self.db,2)['draft']).values())}
        with patch.object(recovery,'origins',return_value=[origin]):
            pid=recovery.create(self.db,1,{**self.raw,'kind':'pendiente_primero','origin_confirmed':True,
                    'origin_module_id':2,'origin_student_id':2,'origin_decision_id':10})
        self.assertEqual(recovery.load(self.db,1)['plans'][0]['snapshot']['origin_decision_id'],10)

    def test_individual_excel_excludes_other_students_and_formulas(self):
        recovery.create(self.db,1,{**self.raw,'objectives':'=1+1'})
        blob,mime,name=export.export(self.db,1,student_id=1)
        self.assertTrue(name.endswith('.xlsx'))
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            self.assertIn('xl/workbook.xml',z.namelist())
            strings=z.read('xl/sharedStrings.xml').decode()
            self.assertIn('=1+1',strings)
            self.assertNotIn('OTRO_ALUMNO_CONFIDENCIAL',strings)
            for path in z.namelist():
                if path.startswith('xl/worksheets/sheet') and path.endswith('.xml'):
                    self.assertNotIn('<f>',z.read(path).decode())
        with self.assertRaises(ValueError):
            export.export(self.db,1,student_id=2)
