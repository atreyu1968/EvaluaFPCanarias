"""El catálogo local nunca se toma por catálogo oficial estatal completo."""
import io
import json
import sqlite3
import unittest

import fp_catalog
import program_builder
import territorial_profiles

SOURCE='https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19533'
SOURCE_TITLE='Disposición de ejemplo revisada por el departamento; vigencia por comprobar'
TABLE=('Código título;Ciclo;Grado;Familia;Código módulo;Módulo\n'
       'DEMO-001;Administración y Finanzas;Superior;Administración y Gestión;0650;Proceso integral de la actividad comercial\n'
       'DEMO-001;Administración y Finanzas;Superior;Administración y Gestión;0651;Comunicación y atención al cliente\n'
       'DEMO-002;Gestión Administrativa;Medio;Administración y Gestión;0441;Técnica Contable')

class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT)')
        self.db.execute('CREATE TABLE modules(id INTEGER PRIMARY KEY,academic_year TEXT,cycle TEXT,name TEXT,territory TEXT)')
        program_builder.migrate(self.db)
        fp_catalog.migrate(self.db)
    def tearDown(self):self.db.close()
    def imp(self,region='Canarias',year='2026-2027',table=TABLE,**kwargs):
        return fp_catalog.import_table(self.db,table,region,year,SOURCE,SOURCE_TITLE,teacher_confirmed=True,**kwargs)
    def test_preview_import_and_search_identification(self):
        p=fp_catalog.preview_table(TABLE)
        self.assertEqual(p['count'],3)
        self.assertEqual(p['titles'],2)
        r=self.imp()
        self.assertEqual((r['added'],r['updated'],r['unchanged']),(3,0,0))
        q=fp_catalog.search(self.db,'Canarias','2026-2027','0650')
        self.assertEqual(q['count'],1)
        self.assertEqual(q['entries'][0]['module_name'],'Proceso integral de la actividad comercial')
        self.assertEqual(q['entries'][0]['title_code'],'DEMO-001')
        self.assertEqual(q['catalog_source'],'biblioteca_local_confirmada_por_docente')
    def test_all_19_areas_and_courses_isolated(self):
        for code,label in territorial_profiles.TERRITORIES:
            self.imp(region=label)
            self.assertEqual(fp_catalog.search(self.db,label,'2026-2027')['count'],3)
            self.assertEqual(fp_catalog.search(self.db,label,'2027-2028')['count'],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM fp_catalog_entries').fetchone()[0],57)
    def test_no_mutation_without_confirmation_or_valid_source(self):
        for kw in [{'teacher_confirmed':False},{'source_url':'http://localhost/falso'},
                   {'source_url':'http://example.com/norma'}]:
            base=dict(raw=TABLE,region='Canarias',year='2026-2027',source_url=SOURCE,source_title=SOURCE_TITLE,teacher_confirmed=True)
            base.update(kw)
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                fp_catalog.import_table(self.db,**base)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM fp_catalog_entries').fetchone()[0],0)
    def test_bad_table_all_or_nothing(self):
        examples=[
            TABLE+'\nDEMO-001;Administración y Finanzas;Superior;Administración y Gestión;0650;Duplicado',
            TABLE+'\nDEMO-001;Gestión Administrativa;Medio;Administración y Gestión;0662;Otro módulo',
            TABLE.replace('Superior','Intermedio'),
            TABLE.replace('0650;','0650/../;'),
            'Ciclo;Módulo;Horas\nCiclo Falso;Módulo Falso;100',
        ]
        for table in examples:
            with self.subTest(table=table[-32:]),self.assertRaises(ValueError):
                self.imp(table=table)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM fp_catalog_entries').fetchone()[0],0)
    def test_revisions_are_explicit_and_previous_source_preserved(self):
        self.imp()
        again=self.imp()
        self.assertEqual(again['unchanged'],3)
        changed=TABLE.replace('Proceso integral de la actividad comercial','Proceso integral del comercio')
        with self.assertRaisesRegex(ValueError,'Existen fichas diferentes'):
            self.imp(table=changed)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM fp_catalog_revisions').fetchone()[0],0)
        result=self.imp(table=changed,replace_existing=True)
        self.assertEqual((result['updated'],result['unchanged']),(1,2))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM fp_catalog_revisions').fetchone()[0],1)
        old=json.loads(self.db.execute('SELECT previous_json FROM fp_catalog_revisions').fetchone()[0])
        self.assertEqual(old['module_name'],'Proceso integral de la actividad comercial')
    def test_get_entry_rejects_other_territory_or_course(self):
        self.imp()
        ident=fp_catalog.search(self.db,'Canarias','2026-2027')['entries'][0]['id']
        for region,year in [('Galicia','2026-2027'),('Canarias','2027-2028')]:
            with self.subTest(region=region,year=year),self.assertRaisesRegex(ValueError,'no pertenece'):
                fp_catalog.get_entry(self.db,ident,region,year)
    def test_long_queries_bad_year_and_migration_idempotent(self):
        fp_catalog.migrate(self.db)
        with self.assertRaises(ValueError):fp_catalog.search(self.db,'Canarias','2026-2027','x'*101)
        with self.assertRaises(ValueError):fp_catalog.search(self.db,'Canarias','2027-2027')
        with self.assertRaises(ValueError):fp_catalog.search(self.db,'Marte','2026-2027')
        with self.assertRaises(ValueError):fp_catalog.search(self.db,'Canarias','2026-2027',limit=101)

if __name__=='__main__':unittest.main()
