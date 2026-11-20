"""Pruebas HTTP con SQLite real del historial de calendarios escolares."""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import database
import program_builder
import schedule_engine


class CalendarRevisionsHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='evaluafp_cal127_')
        root=Path(cls.temp.name)
        cls.patches=[patch.object(database,'DB_FILE',root/'datos.sqlite3'),
                     patch.object(database,'DATA',root),
                     patch.object(database,'STORAGE',root/'almacen'),
                     patch.object(database,'BACKUPS',root/'copias')]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',
                        ('2026-2027','Administración y Finanzas','Ejemplo FP','1ºA',database.now(),'Comunidad de Madrid'))
            cls.module_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            draft=program_builder.load(db,cls.module_id)['draft']
            draft['center']='IES Proyecto'
            cfg=schedule_engine.defaults('2026-2027','Comunidad de Madrid')
            cfg.update(start_date='2026-09-14',end_date='2027-06-18',
                       municipality='Madrid',calendar_confirmed=True,
                       calendar_source_url='https://www.comunidad.madrid/educacion/calendario-escolar',
                       calendar_source_description='Calendario Madrid 2026-2027: comprobado por docente')
            draft['schedule']=cfg
            program_builder.save(db,cls.module_id,draft)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.temp.cleanup()

    def request(self,path,payload=None,auth=True):
        headers={'Content-Type':'application/json'}
        if auth:headers['X-App-Token']=app.TOKEN
        req=urllib.request.Request(self.root+path,
             data=json.dumps(payload).encode('utf8') if payload is not None else None,
             headers=headers, method='POST' if payload is not None else 'GET')
        try:
            with urllib.request.urlopen(req,timeout=12) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

    def test_save_and_compare_scoped_versions_with_real_http(self):
        mid=self.module_id
        status,body=self.request(f'api/national/calendar/versions?module_id={mid}')
        self.assertEqual(status,200)
        self.assertEqual(body['count'],0)
        self.assertEqual(body['source_directory']['territory'],'Comunidad de Madrid')
        code,stored=self.request('api/national/save-calendar',{'module_id':mid,'teacher_confirmed':True})
        self.assertEqual(code,200)
        self.assertTrue(stored['record']['revision']['saved'])
        old=stored['record']['revision']['id']
        with database.connect() as db:
            draft=program_builder.load(db,mid)['draft']
            draft['schedule']['start_date']='2026-09-15'
            program_builder.save(db,mid,draft)
        code,new=self.request('api/national/save-calendar',{'module_id':mid,'teacher_confirmed':True})
        self.assertEqual(code,200)
        last=new['record']['revision']['id']
        self.assertEqual(new['record']['revision']['revision'],2)
        code,comparison=self.request(f'api/national/calendar/compare?module_id={mid}&old={old}&new={last}')
        self.assertEqual(code,200)
        self.assertTrue(any(x['field']=='start_date' for x in comparison['changes']))
        code,versions=self.request(f'api/national/calendar/versions?module_id={mid}')
        self.assertEqual(code,200)
        self.assertEqual(versions['count'],2)
        self.assertFalse(versions['versions'][0]['schedule'].get('calendar_confirmed',False))

    def test_auth_and_invalid_id(self):
        self.assertIn(self.request(f'api/national/calendar/versions?module_id={self.module_id}',auth=False)[0],(401,403))
        status,body=self.request(f'api/national/calendar/compare?module_id={self.module_id}&old=999999&new=999999')
        self.assertEqual(status,400)
        self.assertIn('error',body)


if __name__=='__main__':unittest.main()