"""Compatibilidad al cambiar de letra de unidad: rebasa rutas en SQLite."""
import json
from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import database, storage_config

class PortableRebaseTests(unittest.TestCase):
    def test_absolute_references_rebased_when_folder_moves(self):
        with tempfile.TemporaryDirectory() as root:
            old=Path(root)/'USB-ANTES'/'EvaluaFP_Datos'
            new=Path(root)/'USB-DESPUES'/'EvaluaFP_Datos'
            with closing(sqlite3.connect(':memory:')) as db, db:
                db.row_factory=sqlite3.Row
                db.execute('CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT)')
                db.execute('CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT)')
                for table,column in [('programmings','local_path'),('materials','local_path'),('submissions','storage_path'),('source_files','local_path'),('pages','image_path')]:
                    db.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY,{column} TEXT)')
                    db.execute(f'INSERT INTO {table}({column}) VALUES(?)',(str(old/'almacen'/'documento.pdf'),))
                database.set_pref(db,'portable_last_data_root',str(old))
                with patch.object(storage_config,'PORTABLE',True),patch.object(database,'DATA',new):
                    database._rebase_on_portable_start(db)
                for table,column in [('programmings','local_path'),('materials','local_path'),('submissions','storage_path'),('source_files','local_path'),('pages','image_path')]:
                    self.assertEqual(db.execute(f'SELECT {column} FROM {table}').fetchone()[0],str(new/'almacen'/'documento.pdf'))
                self.assertEqual(database.pref(db,'portable_last_data_root'),str(new))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0],1)
    def test_imported_legacy_db_without_portable_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            old=Path(root)/'instalado'/'EvaluaFP'
            new=Path(root)/'USB'/'EvaluaFP_Datos'
            with closing(sqlite3.connect(':memory:')) as db, db:
                db.row_factory=sqlite3.Row
                db.execute('CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT)')
                db.execute('CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,entity TEXT,entity_id INTEGER,details_json TEXT)')
                for table,column in [('programmings','local_path'),('materials','local_path'),('submissions','storage_path'),('source_files','local_path'),('pages','image_path')]:
                    db.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY,{column} TEXT)')
                    db.execute(f'INSERT INTO {table}({column}) VALUES(?)',(str(old/'almacen'/'prueba.pdf'),))
                with patch.object(storage_config,'PORTABLE',True),patch.object(database,'DATA',new):
                    database._rebase_on_portable_start(db)
                self.assertEqual(db.execute('SELECT image_path FROM pages').fetchone()[0],str(new/'almacen'/'prueba.pdf'))


if __name__=='__main__':unittest.main()
