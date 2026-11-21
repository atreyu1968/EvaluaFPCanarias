"""Regresión del expediente de ciclo con registros sintéticos."""
import sqlite3
import unittest
from unittest.mock import patch
import canarias_cycle_record as rec

CYCLE='CFGM Gestión Administrativa'


class CycleRecordTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT,cycle TEXT,territory TEXT,
                               academic_year TEXT,group_name TEXT);
          CREATE TABLE students(id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,name TEXT);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
        """)
        for mid,name,group,year in [
            (1,'Comunicación empresarial y atención al cliente','1 A','2026-2027'),
            (2,'Operaciones administrativas de compraventa','1 A','2026-2027'),
            (3,'Empresa y administración','1 B','2026-2027'),
            (4,'Empresa y administración','1 A','2026-2027')]:
            self.db.execute('INSERT INTO modules VALUES(?,?,?,?,?,?)',(mid,name,CYCLE,'Canarias',year,group))
            self.db.execute('INSERT INTO students VALUES(?,?,?,?)',
                (mid,mid,'ID1','Alumno <prueba>' if mid!=4 else 'Otra identidad'))
        def reference(db,mid):
            return {'course':1,'module_code':{1:'0437',2:'0438',3:'0439',4:'0439'}[mid]}
        def summary(db,mid,sid):
            return {'students':[{'final_score':9,'closure':{
                'id':10+mid,'current':mid==1,'score':6,'validated_at':'2026-11-21',
                'evidence_sha256':'test'}}]}
        p=patch.object(rec.refs,'read',side_effect=reference)
        p.start()
        self.addCleanup(p.stop)
        p=patch.object(rec.evaluacion,'summary',side_effect=summary)
        p.start()
        self.addCleanup(p.stop)

    def data(self,report):
        return {'session':'ordinaria','report_sha256':report['sha256'],'teacher_confirmed':True,
                'facts':{'action':'permanence','years_used':1,'cycle_years':2,'record_complete':True},
                'agreement':'<script>Texto de prueba</script>','meeting_ref':'Sesión de prueba'}

    def test_states_and_exclusion(self):
        r=rec.report(self.db,1,1,'ordinaria')
        bycode={x['code']:x for x in r['items']}
        self.assertEqual(bycode['0437']['status'],'cierre_sin_convocatoria')
        self.assertEqual(bycode['0437']['score'],6)
        self.assertIsNone(bycode['0438']['score'])
        self.assertEqual(bycode['0439']['status'],'identidad_pendiente')
        self.assertEqual(bycode['0440']['status'],'ausente')
        self.assertEqual(r['previous_candidates'],[])

    def test_record_hash_and_export(self):
        r=rec.report(self.db,1,1,'ordinaria')
        saved=rec.record(self.db,1,1,self.data(r))
        self.assertEqual(saved['result']['status'],'dentro_limite')
        current=rec.report(self.db,1,1,'ordinaria')
        self.assertTrue(current['records'][0]['current_snapshot'])
        payload,mime,name=rec.export_agreement(self.db,1,1,saved['id'])
        html=payload.decode()
        self.assertIn('NO CONSTITUYE ACTA OFICIAL',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertNotIn('Otra identidad',html)
        self.assertTrue(name.endswith('.html'))

    def test_reject_stale_and_foreign_records(self):
        r=rec.report(self.db,1,1,'ordinaria')
        saved=rec.record(self.db,1,1,self.data(r))
        self.db.execute("UPDATE students SET name='Alumno <prueba>' WHERE id=4")
        self.assertFalse(rec.report(self.db,1,1,'ordinaria')['records'][0]['current_snapshot'])
        with self.assertRaises(ValueError):
            rec.record(self.db,1,1,self.data(r))
        with self.assertRaises(ValueError):
            rec.report(self.db,1,2,'ordinaria')
        with self.assertRaises(ValueError):
            rec.export_agreement(self.db,2,2,saved['id'])

    def test_duplicate_catalog_module(self):
        self.db.execute("UPDATE modules SET group_name='1 A' WHERE id=3")
        r=rec.report(self.db,1,1,'ordinaria')
        state=next(x for x in r['items'] if x['code']=='0439')
        self.assertEqual(state['status'],'duplicado')
        self.assertIsNone(state['score'])
