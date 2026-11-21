"""Auditoría del motor: no confundir RA/CE ni publicar evidencias parciales."""
import sqlite3
import unittest
import evaluacion as ev


class EvaluationAuditTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY);
          CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,name TEXT);
          CREATE TABLE outcomes(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,description TEXT,weight REAL);
          CREATE TABLE criteria(id INTEGER PRIMARY KEY,outcome_id INTEGER,code TEXT,description TEXT,weight REAL);
          CREATE TABLE exams(id INTEGER PRIMARY KEY,module_id INTEGER);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
          INSERT INTO modules VALUES(1);
          INSERT INTO students VALUES(1,1,'A001','Alumno de prueba');
          INSERT INTO outcomes VALUES(1,1,'RA1','Primer RA',50);
          INSERT INTO outcomes VALUES(2,1,'RA2','Segundo RA',50);
          INSERT INTO criteria VALUES(1,1,'a','Primer criterio',100);
          INSERT INTO criteria VALUES(2,2,'a','Segundo criterio',100);
        """)
        ev.migrate(self.db)
        self.instrument=ev.add_instrument(self.db,{'module_id':1,'term':1,'title':'Prueba','kind':'practica',
            'targets':[{'criterion_id':1,'weight':50},{'criterion_id':2,'weight':100}]})
        self.second=ev.add_instrument(self.db,{'module_id':1,'term':2,'title':'Prueba 2','kind':'practica',
            'targets':[{'criterion_id':1,'weight':50}]})
        ev.update_settings(self.db,{'module_id':1,'enterprise_mode':'integrated','validated':True,
            'teacher_note':'Programación contrastada','criterion_pass_mark':5,'ra_min_criteria_pct':50})

    def test_ambiguous_criterion_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError,'ambiguo'):
            ev.import_csv(self.db,self.instrument,b'codigo_alumno;criterio;nota\nA001;a;9\n')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM evaluation_scores').fetchone()[0],0)

    def test_qualified_and_unique_codes(self):
        count=ev.import_csv(self.db,self.instrument,b'codigo_alumno;criterio;nota\nA001;RA1/a;9\nA001;RA2/a;7\n')
        self.assertEqual(count,2)
        ev.import_csv(self.db,self.second,b'codigo_alumno;criterio;nota\nA001;a;5\n')
        result=ev.summary(self.db,1,1)['students'][0]
        self.assertEqual(result['final_score'],7)
        self.assertTrue(all(c['passed'] for c in result['criteria']))

    def test_partial_and_unrounded_criterion(self):
        ev.put_score(self.db,{'instrument_id':self.instrument,'criterion_id':1,'student_id':1,'score':9})
        result=ev.summary(self.db,1,1)['students'][0]
        self.assertFalse(result['criteria'][0]['passed'])
        self.assertIsNone(result['final_score'])
        with self.assertRaises(ValueError):
            ev.close_student(self.db,1,1,'Justificación de prueba')
        ev.put_score(self.db,{'instrument_id':self.instrument,'criterion_id':1,'student_id':1,'score':4.999})
        ev.put_score(self.db,{'instrument_id':self.second,'criterion_id':1,'student_id':1,'score':4.999})
        self.assertFalse(ev.summary(self.db,1,1)['students'][0]['criteria'][0]['passed'])

    def test_manual_score_clears_old_provenance(self):
        body={'instrument_id':self.instrument,'criterion_id':1,'student_id':1,'score':7}
        ev.put_score(self.db,body)
        self.db.execute("UPDATE evaluation_scores SET origin='exam',source_ref='123'")
        ev.put_score(self.db,{**body,'score':8})
        row=self.db.execute('SELECT origin,source_ref FROM evaluation_scores').fetchone()
        self.assertEqual(tuple(row),('manual',''))

    def test_empty_csv_and_explicit_validation(self):
        with self.assertRaises(ValueError):
            ev.import_csv(self.db,self.instrument,b'')
        ev.update_settings(self.db,{'module_id':1,'enterprise_mode':'integrated','validated':'false',
            'teacher_note':'No es una confirmación booleana'})
        self.assertFalse(ev.summary(self.db,1,1)['settings']['validated'])


    def test_feoe_review_invalidates_only_affected_closure(self):
        from unittest.mock import patch
        import canarias_feoe
        canarias_feoe.migrate(self.db)
        ev.import_csv(self.db,self.instrument,b'codigo_alumno;criterio;nota\nA001;RA1/a;9\nA001;RA2/a;7\n')
        ev.import_csv(self.db,self.second,b'codigo_alumno;criterio;nota\nA001;a;5\n')
        old=ev.close_student(self.db,1,1,'Cierre antes de FEOE')
        evidence={'id':1,'student_id':1,'current_curriculum':True,
                  'valuation':{'id':1,'status':'superado'},'teacher_review':None}
        with patch.object(canarias_feoe,'module_evidence',return_value=[evidence]):
            st=ev.summary(self.db,1,1)['students'][0]
            self.assertIsNone(st['final_score'])
            self.assertFalse(st['closure']['current'])
            with self.assertRaises(ValueError):
                ev.close_student(self.db,1,1,'Cierre sin revisión')
            evidence['teacher_review']={'id':1,'notes':'Contrastado'}
            new=ev.close_student(self.db,1,1,'Cierre con revisión')
            self.assertNotEqual(new['id'],old['id'])
            self.assertTrue(ev.summary(self.db,1,1)['students'][0]['closure']['current'])
            evidence['valuation']={'id':2,'status':'no_superado'}
            evidence['teacher_review']=None
            self.assertFalse(ev.summary(self.db,1,1)['students'][0]['closure']['current'])
