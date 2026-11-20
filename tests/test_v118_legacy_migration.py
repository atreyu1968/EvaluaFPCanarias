"""Prueba aislada de migración 1.1.7.1 -> 1.1.8 sin tocar el usuario."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[1]


class MigrationTests(unittest.TestCase):
    def test_old_sqlite_module_survives_additive_territory_migration(self):
        script=textwrap.dedent('''
            import sqlite3,sys
            from pathlib import Path
            import database
            destination=Path(sys.argv[1]);database.DB_FILE=destination
            with sqlite3.connect(destination) as db:
                db.execute('''+repr('''CREATE TABLE modules(id INTEGER PRIMARY KEY, academic_year TEXT NOT NULL,
                            cycle TEXT NOT NULL, name TEXT NOT NULL,group_name TEXT DEFAULT '',
                            created_at TEXT NOT NULL)''')+''')
                db.execute("INSERT INTO modules VALUES(1,'2026-2027','CFGM Gestión Administrativa','Módulo legado','A','2026-10-01')")
            database.init()
            database.init()
            with database.connect() as db:
                row=db.execute('SELECT name,territory FROM modules WHERE id=1').fetchone()
                assert row['name']=='Módulo legado'
                assert row['territory']=='Canarias'
                cols=[v['name'] for v in db.execute('PRAGMA table_info(modules)')]
                assert cols.count('territory')==1
            print('MIGRACION LEGADA OK')
        ''')
        with tempfile.TemporaryDirectory(prefix='ef118_legacy_') as temp:
            env=os.environ.copy()
            env.update({'EVALUAFP_DATA_DIR':str(Path(temp)/'app_data')})
            outcome=subprocess.run([sys.executable,'-c',script,str(Path(temp)/'legacy.sqlite3')],
                                   cwd=str(ROOT),env=env,text=True,capture_output=True,timeout=30)
        self.assertEqual(outcome.returncode,0,outcome.stdout+'\n'+outcome.stderr)
        self.assertIn('MIGRACION LEGADA OK',outcome.stdout)
