"""Regresión de la estabilización de SQLite y de las respuestas HTTP."""
import io
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import app
import common_scopes
import common_scope_notebook
import common_scope_consolidation
import common_scope_recovery
import canarias_cycle_record
import canarias_feoe


class AuditMigrationTests(unittest.TestCase):
    def test_repeated_migrations_preserve_existing_rows(self):
        db=sqlite3.connect(':memory:')
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(db.close)
        db.executescript("""
          CREATE TABLE modules(id INTEGER PRIMARY KEY);
          CREATE TABLE students(id INTEGER PRIMARY KEY);
          CREATE TABLE outcomes(id INTEGER PRIMARY KEY);
          CREATE TABLE criteria(id INTEGER PRIMARY KEY);
          INSERT INTO modules VALUES(1);
          INSERT INTO students VALUES(1);
          INSERT INTO outcomes VALUES(1);
          INSERT INTO criteria VALUES(1);
        """)
        features=(common_scopes,common_scope_notebook,common_scope_consolidation,
                  common_scope_recovery,canarias_cycle_record,canarias_feoe)
        for feature in features:
            feature.migrate(db)
        db.execute("INSERT INTO feoe_companies(name,contact,workplace,created_at) VALUES('Empresa','','Sede','Fecha')")
        db.execute("INSERT INTO common_scope_drafts VALUES(1,'{}','Fecha')")
        for feature in features:
            feature.migrate(db)
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'scope_activities','scope_evidence','scope_matter_grades',
                         'scope_final_decisions','scope_recovery_plans','scope_recovery_reviews',
                         'cycle_decision_records','feoe_stays','feoe_targets','feoe_attendance',
                         'feoe_teacher_reviews','common_scope_drafts'}<=tables)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM feoe_companies').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM common_scope_drafts').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0],1)
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


class AuditHttpTests(unittest.TestCase):
    def read(self,payload):
        return app.read_json(SimpleNamespace(headers={'Content-Length':str(len(payload)),
            'Content-Type':'application/json'},rfile=io.BytesIO(payload)))

    def test_json_object_only(self):
        self.assertEqual(self.read(b'{"ok":true}'),{'ok':True})
        for payload in (b'[]',b'null',b'1',b'"text"'):
            with self.assertRaises(ValueError):
                self.read(payload)

    def test_download_preserves_extension_and_safe_headers(self):
        handler=SimpleNamespace(send_response=Mock(),send_header=Mock(),
                                end_headers=Mock(),wfile=io.BytesIO())
        app.Handler.send_bytes(handler,b'abc','application/pdf','Evaluación_'+'a'*90+'.pdf')
        headers=dict(call.args for call in handler.send_header.call_args_list)
        disposition=headers['Content-Disposition']
        self.assertIn('.pdf"',disposition)
        self.assertTrue(disposition.endswith('.pdf'))
        self.assertNotIn('\n',disposition)
        disposition.encode('ascii')
        self.assertEqual(handler.wfile.getvalue(),b'abc')
        self.assertEqual(headers['Cache-Control'],'private, no-store')
