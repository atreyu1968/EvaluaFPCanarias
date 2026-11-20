"""API HTTP 1.2.9: IA consentida, contexto del módulo y solo lectura."""
from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import calendar_ai
import database

TEXT=('Calendario Canarias 2026-2027, Formación Profesional FP Grado D.\n'
      'Inicio de clases FP: 16/09/2026.\n')


class CalendarAIHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='evaluafp_cal129_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for patcher in cls.patches:patcher.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()
        with database.connect() as db:
            db.execute('''INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory)
                VALUES(?,?,?,?,?,?)''',('2026-2027','Gestión Administrativa','Comunicación empresarial',
                '1A',database.now(),'Canarias'))
            cls.module_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for patcher in reversed(cls.patches):patcher.stop()
        cls.temp.cleanup()

    def request(self,**override):
        body={'module_id':self.module_id,'region':'Canarias',
              'academic_year':'2026-2027','fragment':TEXT,'authorize_ai':True}
        token=override.pop('token',True)
        body.update(override)
        req=urllib.request.Request(self.root+'api/national/calendar-ai-interpret',
            data=json.dumps(body).encode('utf8'),method='POST',
            headers={'Content-Type':'application/json',
                     **({'X-App-Token':app.TOKEN} if token else {})})
        try:
            with urllib.request.urlopen(req,timeout=12) as response:
                return response.status,json.load(response)
        except urllib.error.HTTPError as exc:return exc.code,json.load(exc)

    def test_authorized_valid_proposal_does_not_write_to_sqlite(self):
        reply={'proposals':[{'field':'start_date','date':'2026-09-16',
                             'evidence_quote':'Inicio de clases FP: 16/09/2026.'}]}
        with patch.object(calendar_ai.ia,'chat',return_value=(reply,'test')) as fake:
            status,response=self.request()
        self.assertEqual(status,200)
        self.assertEqual(fake.call_count,1)
        self.assertTrue(response['no_changes_saved'])
        self.assertEqual(response['candidate_count'],1)
        self.assertEqual(response['candidates']['start_date'][0]['value'],'2026-09-16')
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM programming_drafts').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_calendar_revisions').fetchone()[0],0)

    def test_missing_authorization_mismatched_scope_and_auth_are_blocked_before_ai(self):
        with patch.object(calendar_ai.ia,'chat') as fake:
            for change in [{'authorize_ai':False},
                           {'region':'Comunidad de Madrid'},
                           {'academic_year':'2027-2028'},
                           {'module_id':999999},
                           {'fragment':'Solo fechas sin etapa ni curso.'}]:
                status,result=self.request(**change)
                self.assertEqual(status,400)
                self.assertIn('error',result)
            status,result=self.request(token=False)
            self.assertIn(status,(401,403))
            fake.assert_not_called()

    def test_ai_forged_quote_is_rejected_without_saving(self):
        reply={'proposals':[{'field':'start_date','date':'2026-09-17',
                             'evidence_quote':'Inicio de clases FP: 17/09/2026.'}]}
        with patch.object(calendar_ai.ia,'chat',return_value=(reply,'test')):
            status,response=self.request()
        self.assertEqual(status,200)
        self.assertEqual(response['candidate_count'],0)
        self.assertTrue(response['warnings'])
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_calendar_revisions').fetchone()[0],0)


if __name__=='__main__':
    unittest.main()
