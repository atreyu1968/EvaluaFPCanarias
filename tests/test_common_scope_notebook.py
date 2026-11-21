"""Pruebas de aislamiento y conservación de evidencias del cuaderno."""
import sqlite3
import unittest
import common_scopes as cs
import common_scope_notebook as book


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT,cycle TEXT,territory TEXT);
          CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER REFERENCES modules(id),code TEXT,name TEXT);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
          CREATE TABLE outcomes(id INTEGER PRIMARY KEY);
          INSERT INTO outcomes VALUES(99);
        """)
        for mid in (1,2):
            self.db.execute('INSERT INTO modules VALUES(?,?,?,?)',
                (mid,'Matemáticas y Ciencias aplicadas','CFGB Servicios Administrativos','Canarias'))
            self.db.execute('INSERT INTO students VALUES(?,?,?,?)',(mid,mid,'A','Alumno de prueba'))
            cs.save(self.db,mid,self.draft())
        self.activity={'title':'Actividad de prueba','situation':'Situación de prueba',
            'instrument':'rubrica','term':1,'activity_date':'2026-11-20','criterion_codes':['1.1']}
        self.aid=book.create_activity(self.db,1,self.activity)
        self.entry={'activity_id':self.aid,'student_id':1,'criterion_code':'1.1',
            'level':'SU','notes':'Observación de prueba','evidence_ref':''}

    def draft(self,description='Criterio de prueba',reviewed=True):
        return {'competencies':[{'code':'1','description':'Competencia de prueba',
                'criteria':[{'code':'1.1','description':description}]}],
                'teacher_reviewed':reviewed}

    def test_history_and_latest(self):
        first=book.record_evidence(self.db,1,self.entry)
        second=book.record_evidence(self.db,1,{**self.entry,'level':'BI'})
        result=book.load(self.db,1)
        self.assertEqual(len(result['history']),2)
        self.assertEqual(result['latest_evidence'][0]['id'],second)
        self.assertEqual(result['history'][-1]['id'],first)
        self.assertEqual(result['latest_evidence'][0]['level'],'BI')
        self.assertEqual(self.db.execute('SELECT id FROM outcomes').fetchone()[0],99)
        self.assertEqual(book.load(self.db,2)['history'],[])

    def test_cross_module_and_wrong_criterion(self):
        for module_id,raw in [(2,{**self.entry,'student_id':2}),
                               (1,{**self.entry,'student_id':2}),
                               (1,{**self.entry,'criterion_code':'1.2'})]:
            with self.assertRaises(ValueError):
                book.record_evidence(self.db,module_id,raw)
        self.assertEqual(book.load(self.db,1)['history'],[])

    def test_changed_curriculum_keeps_snapshot(self):
        book.record_evidence(self.db,1,self.entry)
        cs.save(self.db,1,self.draft('Criterio modificado'))
        result=book.load(self.db,1)
        self.assertFalse(result['activities'][0]['criteria_current'])
        self.assertEqual(result['activities'][0]['criteria'][0]['description'],'Criterio de prueba')
        self.assertEqual(len(result['history']),1)
        with self.assertRaises(ValueError):
            book.record_evidence(self.db,1,self.entry)

    def test_unreviewed_and_invalid_activity(self):
        for raw in [{**self.activity,'activity_date':'2026-02-30'},
                    {**self.activity,'criterion_codes':['1.1','1.1']},
                    {**self.activity,'criterion_codes':['RA1.a']}]:
            with self.assertRaises(ValueError):
                book.create_activity(self.db,1,raw)
        cs.save(self.db,1,self.draft(reviewed=False))
        with self.assertRaises(ValueError):
            book.create_activity(self.db,1,self.activity)
        with self.assertRaises(ValueError):
            book.record_evidence(self.db,1,self.entry)
