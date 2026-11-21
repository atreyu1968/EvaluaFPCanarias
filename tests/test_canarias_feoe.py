"""Regresión del seguimiento local FEOE."""
import sqlite3
import unittest
from unittest.mock import patch
import canarias_feoe as f


class FeoeTests(unittest.TestCase):
    def setUp(self):
        d=self.db=sqlite3.connect(':memory:')
        d.row_factory=sqlite3.Row
        self.addCleanup(d.close)
        d.executescript("""
        CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT,cycle TEXT,territory TEXT,academic_year TEXT,group_name TEXT);
        CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,name TEXT);
        CREATE TABLE outcomes(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,description TEXT);
        CREATE TABLE criteria(id INTEGER PRIMARY KEY,outcome_id INTEGER,code TEXT,description TEXT);
        CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
        INSERT INTO modules VALUES(1,'Técnica contable','CFGM Gestión Administrativa','Canarias','2026-2027','1 A');
        INSERT INTO modules VALUES(2,'Empresa y administración','CFGM Gestión Administrativa','Canarias','2026-2027','1 B');
        INSERT INTO students VALUES(1,1,'TEST','Alumno de prueba');
        INSERT INTO students VALUES(2,2,'TEST','Alumno de prueba');
        INSERT INTO outcomes VALUES(1,1,'RA1','RA de prueba');
        INSERT INTO outcomes VALUES(2,2,'RA2','RA ajeno');
        INSERT INTO criteria VALUES(1,1,'a','CE de prueba');
        INSERT INTO criteria VALUES(2,2,'a','CE ajeno');
        """)
        p=patch.object(f.cycle.refs,'read',return_value={'course':1})
        p.start()
        self.addCleanup(p.stop)
        cid=f.company(d,{'name':'Empresa de prueba','workplace':'Centro de trabajo'})
        self.sid=f.stay(d,{'module_id':1,'student_id':1,'company_id':cid,'center_tutor':'Docente',
            'company_tutor':'Tutor','regime':'general','start_date':'2026-11-01','end_date':'2026-11-30',
            'planned_hours':'100','schedule':'Horario contrastado',**{k:'Referencia' for k in
                ('convenio','plan','prl','anexo_v','edad','incorporacion')}})
        self.raw={'stay_id':self.sid,'outcome_id':1,'location':'compartido','criterion_ids':[1],'activities':'Actividad'}

    def confirm(self):
        tid=f.add_target(self.db,self.raw)
        f.confirm_plan(self.db,{'stay_id':self.sid,'reference':'Plan de prueba','teacher_confirmed':True})
        return tid

    def test_reject_foreign_ra_ce_and_unconfirmed_attendance(self):
        for raw in ({**self.raw,'outcome_id':2},{**self.raw,'criterion_ids':[2]}):
            with self.assertRaises(ValueError):
                f.add_target(self.db,raw)
        with self.assertRaises(ValueError):
            f.attendance(self.db,{'stay_id':self.sid,'day':'2026-11-05','hours':'5','status':'asistencia'})

    def test_attendance_latest_not_sum(self):
        self.confirm()
        raw={'stay_id':self.sid,'day':'2026-11-05','hours':'5','status':'asistencia'}
        f.attendance(self.db,raw)
        f.attendance(self.db,{**raw,'hours':'4'})
        report=f.load(self.db,self.sid)
        self.assertEqual(report['actual_hours'],'4')
        self.assertEqual(len(report['attendance_history']),2)
        with self.assertRaises(ValueError):
            f.attendance(self.db,{**raw,'day':'2026-12-01'})

    def test_qualitative_bridge_and_review(self):
        tid=self.confirm()
        v=f.valuation(self.db,{'target_id':tid,'status':'superado','observations':'Observación',
                               'report_ref':'Informe','teacher_confirmed':True})
        f.teacher_review(self.db,{'valuation_id':v,'notes':'Revisión','teacher_confirmed':True})
        e=f.module_evidence(self.db,1)[0]
        self.assertEqual(e['valuation']['status'],'superado')
        self.assertEqual(e['teacher_review']['notes'],'Revisión')
        self.assertTrue(e['current_curriculum'])
        self.assertEqual(f.module_evidence(self.db,2),[])
        self.db.execute("UPDATE outcomes SET description='Cambiado' WHERE id=1")
        self.assertFalse(f.module_evidence(self.db,1)[0]['current_curriculum'])
