"""Integración HTTP del monitor BOE: autenticación y ámbito local."""
import json
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

import app
import database
import normative_monitor as monitor


class BOEMonitorHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval126_boe_http_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for item in cls.patches:item.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()
        with database.connect() as db:
            db.execute('''INSERT INTO modules(id,academic_year,cycle,name,territory,created_at)
                          VALUES(1,'2026-2027','Ciclo de ejemplo','Módulo de ejemplo','Canarias','2026-11-20')''')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for item in reversed(cls.patches):item.stop()
        cls.temp.cleanup()

    def request(self,path,body=None,auth=True):
        method='POST' if body is not None else 'GET'
        req=urllib.request.Request(self.root+path,
           data=json.dumps(body).encode('utf8') if body is not None else None,
           method=method,
           headers={'Content-Type':'application/json',**({'X-App-Token':app.TOKEN} if auth else {})})
        try:
            with urllib.request.urlopen(req,timeout=12) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as error:return error.code,json.load(error)

    @staticmethod
    def metadata(last_update='20261001'):
        return {'id':'BOE-A-2011-19533','title':'Norma de referencia','publication_date':'20111215',
                'last_update':last_update,'has_legal_analysis':True,'reported_amendments':[]}

    def test_endpoints_maintain_teacher_review_and_auth(self):
        scope=((1,'CN','2026-2027','0650'),{})
        identifier='BOE-A-2011-19533'
        payload={'module_id':1,'boe_id':identifier,'teacher_confirmed':True}
        with patch.object(monitor,'_scope',return_value=scope),patch.object(monitor.boe_discovery,'inspect_boe_id',return_value=self.metadata()):
            code,_=self.request('api/national/boe-monitor?module_id=1',auth=False)
            self.assertIn(code,(401,403))
            code,response=self.request('api/national/boe-monitor/check',payload)
            self.assertEqual(code,200)
            self.assertEqual(response['status'],'referencia_inicial')
            code,response=self.request('api/national/boe-monitor?module_id=1')
            self.assertEqual(code,200)
            self.assertEqual(response['sources'][0]['boe_id'],identifier)
            code,response=self.request('api/national/boe-monitor/check',{**payload,'teacher_confirmed':False})
            self.assertEqual(code,400)
            code,response=self.request('api/national/boe-monitor/ack',{**payload,'note':'Nota de revisión suficiente'})
            self.assertEqual(code,400)
        with patch.object(monitor,'_scope',return_value=scope),patch.object(monitor.boe_discovery,'inspect_boe_id',return_value=self.metadata('20261120')):
            code,response=self.request('api/national/boe-monitor/check',payload)
            self.assertEqual(code,200)
            self.assertEqual(response['status'],'cambio_detectado')
            code,response=self.request('api/national/boe-monitor/ack',{**payload,'note':'Consulta de modificaciones contrastada.'})
            self.assertEqual(code,200)
            self.assertTrue(response['ok'])
            code,response=self.request('api/national/boe-monitor?module_id=1')
            self.assertEqual(code,200)
            self.assertFalse(response['sources'][0]['review_pending'])
            self.assertEqual(len(response['events']),1)


if __name__=='__main__':unittest.main()