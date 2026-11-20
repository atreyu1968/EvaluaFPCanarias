"""Ponderación curricular sin porcentajes expresos: equidad entre CE."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database,app,weight_defaults


class DefaultWeightsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(database,'DB_FILE',Path(self.tmp.name)/'prueba.sqlite3')
        self.patch.start();database.init()
        with database.connect() as d:
            d.execute("INSERT INTO modules(id,academic_year,cycle,name,created_at) VALUES(1,'2026-2027','GM','Técnica Contable','hoy')")

    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def test_three_and_five_criteria_equal_global_weight(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[
              {'code':'RA1','description':'Primero','weight':None,'criteria':[{'code':f'a{i}','description':'CE','weight':None} for i in range(3)]},
              {'code':'RA2','description':'Segundo','weight':None,'criteria':[{'code':f'b{i}','description':'CE','weight':None} for i in range(5)]}])
            ras=list(d.execute('SELECT weight FROM outcomes ORDER BY id'))
            self.assertEqual([x['weight'] for x in ras],[37.5,62.5])
            ces=list(d.execute('SELECT weight FROM criteria ORDER BY id'))
            self.assertEqual([x['weight'] for x in ces],[33.34,33.33,33.33,20,20,20,20,20])
            self.assertTrue(all(weight_defaults.origin(d,'ce',x['id'])=='default' for x in d.execute('SELECT id FROM criteria')))

    def test_new_ce_rebalances_only_defaults(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[{'code':'RA1','description':'R1','criteria':[{'code':'a','description':'A'},{'code':'b','description':'B'}]},
                                      {'code':'RA2','description':'R2','criteria':[{'code':'a','description':'A'}]}])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM outcomes ORDER BY id')],[66.67,33.33])
            app.apply_extraction(d,1,[{'code':'RA2','description':'R2','criteria':[{'code':'b','description':'B'}]}])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM outcomes ORDER BY id')],[50,50])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM criteria ORDER BY id')],[50,50,50,50])

    def test_explicit_programming_and_manual_remain(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[{'code':'RA1','description':'R1','weight':70,'criteria':[{'code':'a','description':'A','weight':60},{'code':'b','description':'B'}]},
                                      {'code':'RA2','description':'R2','criteria':[{'code':'a','description':'A'},{'code':'b','description':'B'}]}])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM outcomes ORDER BY id')],[70,30])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM criteria WHERE outcome_id=1 ORDER BY id')],[60,40])
            cid=d.execute("SELECT id FROM criteria WHERE outcome_id=1 AND code='b'").fetchone()['id']
            d.execute('UPDATE criteria SET weight=? WHERE id=?',(32,cid))
            weight_defaults.mark(d,'ce',cid,'manual')
            app.apply_extraction(d,1,[{'code':'RA1','description':'R1','criteria':[{'code':'c','description':'C'}]}])
            # Mantiene decisiones explícitas aunque la suma quede incoherente (60+32+8).
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM criteria WHERE outcome_id=1 ORDER BY id')],[60,32,8])
            self.assertEqual(weight_defaults.origin(d,'ce',cid),'manual')

    def test_conflict_125_not_hidden(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[{'code':f'RA{i}','description':f'RA{i}','weight':25,'criteria':[{'code':'a','description':'A'}]} for i in range(1,6)])
            self.assertEqual(sum(r['weight'] for r in d.execute('SELECT weight FROM outcomes')),125)
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM criteria')],[100]*5)

    def test_ra_without_ce_pending_when_other_ra_has_criteria(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[{'code':'RA1','description':'R1','criteria':[]},
                                     {'code':'RA2','description':'R2','criteria':[{'code':'a','description':'A'}]}])
            self.assertEqual([r['weight'] for r in d.execute('SELECT weight FROM outcomes ORDER BY id')],[None,100])

    def test_startup_migrates_null_weights_in_existing_module(self):
        with database.connect() as d:
            d.execute("INSERT INTO outcomes(module_id,code,description) VALUES(1,'RA1','Primero')")
            rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description) VALUES(?,?,?)',(rid,'a','Criterio A'))
            d.execute('INSERT INTO criteria(outcome_id,code,description) VALUES(?,?,?)',(rid,'b','Criterio B'))
        database.init()
        with database.connect() as d:
            self.assertEqual(d.execute('SELECT weight FROM outcomes').fetchone()['weight'],100)
            self.assertEqual([x['weight'] for x in d.execute('SELECT weight FROM criteria ORDER BY id')],[50,50])

    def test_no_ce_keeps_ra_pending(self):
        with database.connect() as d:
            app.apply_extraction(d,1,[{'code':'RA1','description':'R1','criteria':[]}])
            self.assertIsNone(d.execute('SELECT weight FROM outcomes').fetchone()['weight'])

if __name__=='__main__':unittest.main()
