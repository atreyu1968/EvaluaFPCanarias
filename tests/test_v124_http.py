"""Endpoint real HTTP con sesión local y búsqueda TodoFP simulado."""
import json
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

import app
import database
import todofp_discovery as td

URL='https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas.html'
PROFILE='''<html><body><h1>Técnico Superior en Administración y Finanzas</h1>
<h2>Plan de formación</h2><ul><li>0650. Proceso integral de la actividad comercial</li></ul>
<h2>Dónde estudiar</h2><p>España</p>
<a href="/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas/curriculos-ccaa.html">Currículos CCAA</a></body></html>'''
CURR='''<html><h1>Currículos CCAA</h1>
<img alt="Canarias"><li><a href="https://www.gobiernodecanarias.org/boc/2024/226/3747.html">Currículo</a></li>
<img alt="Comunidad de Madrid"><li><a href="https://www.bocm.es/boletin/2025/001">Currículo</a></li>
</html>'''


class TodoFPHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval124_http_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.temp.cleanup()

    def request_json(self,payload,expect_error=False,token=True):
        data=json.dumps(payload).encode('utf-8')
        headers={'Content-Type':'application/json'}
        if token:headers['X-App-Token']=app.TOKEN
        req=urllib.request.Request(self.root+'api/national/todofp/explore',method='POST',data=data,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=10) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:
            if not expect_error:raise
            return exc.code,json.load(exc)

    def fake_fetch(self,url,opener=None):
        return url, (CURR if url.endswith('curriculos-ccaa.html') else PROFILE)

    def test_endpoint_regions_and_non_destructive(self):
        with patch.object(td,'fetch_todofp',side_effect=self.fake_fetch):
            for region,expected in [('Canarias','CN'),('Comunidad de Madrid','MD'),('Ceuta',None)]:
                status,data=self.request_json({'url':URL,'region':region,'academic_year':'2026-2027',
                     'cycle_name':'CFGS Administración y Finanzas','module_name':'Proceso integral de la actividad comercial'})
                self.assertEqual(status,200)
                self.assertTrue(data['approval_required'])
                self.assertTrue(data['suitable_for_current_module'])
                self.assertEqual(data['regional_curricula']['count'],int(expected is not None))
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM modules').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fp_catalog_entries').fetchone()[0],0)

    def test_endpoint_rejects_wrong_cycle(self):
        with patch.object(td,'fetch_todofp',side_effect=self.fake_fetch):
            status,data=self.request_json({'url':URL,'region':'Canarias','academic_year':'2026-2027',
                                          'cycle_name':'CFGM Gestión Administrativa'})
        self.assertEqual(status,200)
        self.assertFalse(data['suitable_for_current_module'])

    def test_endpoint_rejects_wrong_host_and_missing_year(self):
        for payload in ({'url':'http://127.0.0.1/que-estudiar/index.html','region':'Canarias','academic_year':'2026-2027'},
                        {'url':URL,'region':'Canarias','academic_year':'2026-2026'}):
            status,result=self.request_json(payload,expect_error=True)
            self.assertEqual(status,400)
            self.assertIn('error',result)

    def test_session_authentication_required(self):
        status,_=self.request_json({'url':URL,'region':'Canarias','academic_year':'2026-2027'},expect_error=True,token=False)
        self.assertIn(status,(401,403))

if __name__=='__main__':unittest.main()
