"""Pruebas de separación entre ámbitos comunes y RA profesionales."""
import sqlite3
import unittest
import common_scopes as c


class CommonScopeTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT,cycle TEXT,territory TEXT);
          CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT);
          CREATE TABLE outcomes(id INTEGER PRIMARY KEY);
          INSERT INTO outcomes VALUES(99);
        """)
        for ident,name,cycle,territory in [
            (1,'Matemáticas y Ciencias aplicadas','CFGB Servicios Administrativos','Canarias'),
            (2,'Lengua extranjera de iniciación profesional','CFGB Servicios Administrativos','Canarias'),
            (3,'Técnicas administrativas básicas','CFGB Servicios Administrativos','Canarias'),
            (4,'Matemáticas y Ciencias aplicadas','CFGB Servicios Administrativos','Madrid')]:
            self.db.execute('INSERT INTO modules VALUES(?,?,?,?)',(ident,name,cycle,territory))

    def draft(self,code='1',criterion='1.1'):
        return {'competencies':[{'code':code,'description':'Texto de prueba',
                'descriptors':'CCL1','criteria':[{'code':criterion,'description':'Criterio de prueba'}]}],
                'saberes':'Saberes de prueba','teacher_reviewed':True}

    def test_profiles(self):
        self.assertEqual(c.module_profile(self.db,1)['max_competencies'],11)
        self.assertEqual(c.module_profile(self.db,2)['max_competencies'],8)
        self.assertIsNone(c.module_profile(self.db,3))
        self.assertIsNone(c.module_profile(self.db,4))

    def test_save_and_reload_without_touching_ra(self):
        result=c.save(self.db,1,self.draft())
        self.assertEqual(result['draft']['competencies'][0]['criteria'][0]['code'],'1.1')
        self.assertEqual(c.load(self.db,1)['draft']['saberes'],'Saberes de prueba')
        self.assertEqual(c.load(self.db,2)['draft']['competencies'],[])
        self.assertEqual(self.db.execute('SELECT id FROM outcomes').fetchone()[0],99)

    def test_invalid_codes_and_duplicates(self):
        for raw in (self.draft('12','12.1'), self.draft('1','2.1'), self.draft('RA1','RA1.a')):
            with self.assertRaises(ValueError):
                c.save(self.db,1,raw)
        duplicate=self.draft()
        duplicate['competencies'][0]['criteria']*=2
        with self.assertRaises(ValueError):
            c.save(self.db,1,duplicate)

    def test_wrong_matter_and_unreviewed_empty(self):
        with self.assertRaises(ValueError):
            c.save(self.db,3,self.draft())
        with self.assertRaises(ValueError):
            c.save(self.db,1,{'teacher_reviewed':True})
        result=c.save(self.db,1,{})
        self.assertFalse(result['draft']['teacher_reviewed'])
