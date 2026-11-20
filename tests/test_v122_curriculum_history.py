"""Regresiones de historial curricular: ámbitos aislados, discrepancias y notas protegidas."""
from __future__ import annotations
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import curriculum_history as history
import curriculum_review
import program_builder

MODULE='Proceso integral de la actividad comercial'
SOURCE=f'''Módulo profesional: {MODULE}
Código: 0650
RESULTADOS DE APRENDIZAJE Y CRITERIOS DE EVALUACIÓN
RA1. Determina los elementos patrimoniales de una empresa siguiendo sus operaciones.
Criterios de evaluación:
a) Se han identificado las fases del ciclo económico en una actividad empresarial.
b) Se han clasificado elementos patrimoniales en distintas masas contables.
RA2. Aplica normas de registro contable en operaciones empresariales habituales.
Criterios de evaluación:
a) Se han definido las cuentas necesarias para los asientos contables.
b) Se han aplicado las normas de cargo y abono de las cuentas.
CONTENIDOS
Otras referencias no curriculares.
'''
REVISED=SOURCE.replace('Se han aplicado las normas de cargo y abono de las cuentas.',
    'Se han aplicado las normas de cargo y abono de las cuentas contables con un procedimiento verificado.')
SOURCE_URL='https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19533'


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='efp122_')
        root=Path(self.tmp.name)
        self.patches=[patch.object(database,'DB_FILE',root/'database.sqlite3'),
                      patch.object(database,'DATA',root),patch.object(database,'STORAGE',root/'storage'),
                      patch.object(database,'BACKUPS',root/'backups')]
        for p in self.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        database.init()
        with database.connect() as db:
            db.execute('''INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory)
                VALUES(?,?,?,?,?,?)''',('2026-2027','Administración y Finanzas',MODULE,'A',database.now(),'Comunidad de Madrid'))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            self._code(db,self.mid,'0650')

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def _code(self,db,mid,code):
        draft=program_builder.load(db,mid)['draft']
        draft['official_module_code']=code
        db.execute('''INSERT INTO programming_drafts(module_id,content_json,updated_at) VALUES(?,?,?)
            ON CONFLICT(module_id) DO UPDATE SET content_json=excluded.content_json,
             updated_at=excluded.updated_at''',(mid,json.dumps(draft),database.now()))

    def store(self,text=SOURCE,**options):
        with database.connect() as db:
            return history.store_document(db,self.mid,options.get('filename','modulo.txt'),text.encode('utf8'),
                 options.get('code','0650'),options.get('kind','norma_oficial'),
                 options.get('url',SOURCE_URL),options.get('title','Disposición de ensayo'),options.get('confirmed',True))

    def test_store_version_preserves_existing_manual_grades_and_weights(self):
        with database.connect() as db:
            db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                       (self.mid,'RA1','Enunciado original',42.25))
            ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                       (ra,'RA1.a','Criterio original',84.5))
        result=self.store()
        self.assertTrue(result['saved'])
        self.assertEqual(result['summary'],{'ra':2,'ce':4})
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT weight FROM outcomes WHERE module_id=?',(self.mid,)).fetchone()[0],42.25)
            self.assertEqual(db.execute('SELECT weight FROM criteria WHERE outcome_id=?',(ra,)).fetchone()[0],84.5)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM curriculum_source_snapshots').fetchone()[0],1)

    def test_duplicate_file_and_changed_document_detected(self):
        self.store()
        duplicate=self.store()
        self.assertTrue(duplicate['duplicate'])
        revised=self.store(REVISED,title='Disposición posterior')
        self.assertTrue(revised['saved'])
        self.assertEqual(revised['change']['counts'],{'cambio_ce':1})
        with database.connect() as db:
            record=history.list_snapshots(db,self.mid)
            self.assertEqual(record['count'],2)
            report=history.compare_snapshots(db,self.mid,record['versions'][1]['id'],record['versions'][0]['id'])
            self.assertEqual(report['differences'][0]['code'],'RA2.b')
            self.assertTrue(report['requires_manual_review'])

    def test_semantically_identical_source_does_not_create_false_changes(self):
        self.store()
        alt=SOURCE.replace('CONTENIDOS\n','\nCONTENIDOS\n')
        result=self.store(alt,title='Fuente reimpresa')
        self.assertTrue(result['saved'])
        self.assertTrue(result['content_same_as_previous'])
        self.assertEqual(result['change']['differences'],[])

    def test_scope_isolated_by_code_course_territory_and_module(self):
        self.store()
        with database.connect() as db:
            for year,territory in [('2027-2028','Comunidad de Madrid'),('2026-2027','Canarias'),('2026-2027','Comunidad de Madrid')]:
                db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',
                    (year,'Administración y Finanzas',MODULE,'B',database.now(),territory))
                mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                self._code(db,mid,'0650')
                self.assertEqual(history.list_snapshots(db,mid)['count'],0)
                with self.assertRaisesRegex(ValueError,'no pertenece'):
                    history.compare_snapshots(db,mid,1,2)
            self._code(db,self.mid,'0651')
            self.assertEqual(history.list_snapshots(db,self.mid)['count'],0)

    def test_source_validation_before_any_write(self):
        for values in ({'confirmed':False},{'kind':'programacion'}, {'url':'http://example.com/norma'},
                       {'url':'https://localhost/norma'},{'code':'0651'}, {'filename':'../secreto.txt'}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):self.store(**values)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM curriculum_source_snapshots').fetchone()[0],0)

    def test_bad_source_criteria_not_saved(self):
        with self.assertRaises(ValueError):self.store(SOURCE.replace('b) Se han aplicado','d) Se han aplicado'))
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM curriculum_source_snapshots').fetchone()[0],0)

    def test_local_catalog_exact_scope_and_source(self):
        self.store()
        with database.connect() as db:
            result=history.catalog(db,'Comunidad de Madrid','2026-2027',query='0650')
            self.assertEqual(len(result['modules']),1)
            self.assertEqual(result['modules'][0]['module_code'],'0650')
            self.assertEqual(history.catalog(db,'Comunidad de Madrid','2026-2027','sin coincidencias')['modules'],[])
            self.assertEqual(history.catalog(db,'Canarias','2026-2027')['modules'],[])
            self.assertEqual(history.catalog(db,'Comunidad de Madrid','2027-2028')['modules'],[])

    def test_database_migration_idempotent(self):
        with database.connect() as db:
            history.migrate(db)
            history.migrate(db)
            columns=[r['name'] for r in db.execute('PRAGMA table_info(curriculum_source_snapshots)')]
            self.assertIn('document_sha256',columns)
            self.assertIn('academic_year',columns)

if __name__=='__main__':unittest.main()
