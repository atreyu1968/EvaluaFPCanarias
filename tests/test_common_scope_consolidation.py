"""Pruebas de consolidación sin datos reales ni servicios externos."""
import sqlite3
import unittest
from unittest.mock import patch
from decimal import Decimal
import common_scope_consolidation as c


class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY,academic_year TEXT,cycle TEXT,
            territory TEXT,group_name TEXT,name TEXT);
          CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,name TEXT);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
        """)
        for mid,subject,group in [(1,'Lengua castellana y Ciencias sociales','1 A'),
                                   (2,'Lengua extranjera de iniciación profesional','1 A'),
                                   (3,'Lengua extranjera de iniciación profesional','1 B')]:
            self.db.execute('INSERT INTO modules VALUES(?,?,?,?,?,?)',
                (mid,'2026-2027','CFGB Servicios Administrativos','Canarias',group,subject))
            self.db.execute('INSERT INTO students VALUES(?,?,?,?)',(mid,mid,'TEST1','Alumno de prueba'))
        self.patch=patch.object(c.refs,'read',return_value={'course':1})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def grade(self,mid,grade,session='ordinaria'):
        return c.record_grade(self.db,mid,{'student_id':mid,'session':session,'grade':grade,
            'hours':'4' if mid==1 else '2','hours_source':'Horario de prueba',
            'rationale':'Evidencia de prueba','teacher_confirmed':True})

    def test_pending_then_ordinary_and_extraordinary(self):
        self.grade(1,'BI')
        self.assertIsNone(c.report(self.db,1,'ordinaria')['rows'][0]['calculation'])
        self.grade(2,'IN')
        row=c.report(self.db,1,'ordinaria')['rows'][0]
        self.assertEqual(Decimal(row['calculation']['mean']),5)
        self.assertFalse(row['calculation']['passed'])
        self.grade(1,'BI','extraordinaria')
        self.grade(2,'IN','extraordinaria')
        self.assertTrue(c.report(self.db,2,'extraordinaria')['rows'][0]['calculation']['passed'])

    def test_mismatched_identity_and_duplicate_module(self):
        self.grade(1,'BI')
        self.grade(2,'SU')
        self.db.execute("UPDATE students SET name='Otra persona' WHERE id=2")
        self.assertIsNone(c.report(self.db,1,'ordinaria')['rows'][0]['calculation'])
        self.db.execute("UPDATE modules SET group_name='1 A' WHERE id=3")
        self.assertIn('extranjera',c.report(self.db,1,'ordinaria')['missing_or_duplicate'])

    def test_decision_is_canonical_and_invalidated_by_new_grade(self):
        ids=[self.grade(1,'BI'),self.grade(2,'SU')]
        raw={'student_id':2,'session':'ordinaria','grade_ids':ids,'grade':'BI',
             'meeting_ref':'Sesión de prueba','rationale':'Acuerdo de prueba','team_confirmed':True}
        c.record_decision(self.db,2,raw)
        decision=c.report(self.db,1,'ordinaria')['rows'][0]['decision']
        self.assertTrue(decision['current'])
        self.grade(2,'NT')
        self.assertFalse(c.report(self.db,1,'ordinaria')['rows'][0]['decision']['current'])
        with self.assertRaises(ValueError):
            c.record_decision(self.db,2,raw)

    def test_reject_incoherent_decision(self):
        ids=[self.grade(1,'BI'),self.grade(2,'IN')]
        with self.assertRaises(ValueError):
            c.record_decision(self.db,1,{'student_id':1,'session':'ordinaria','grade_ids':ids,
                'grade':'SU','meeting_ref':'Sesión','rationale':'Prueba','team_confirmed':True})

    def test_trimestral_no_automatic_final_grade(self):
        self.grade(1,'BI','trimestre1')
        self.grade(2,'SU','trimestre1')
        row=c.report(self.db,1,'trimestre1')['rows'][0]
        self.assertEqual(row['blockers'],[])
        self.assertIsNone(row['calculation'])
