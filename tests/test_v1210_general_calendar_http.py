"""API 1.2.10: biblioteca general de calendarios por comunidad y curso."""
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


class GeneralCalendarHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='eval_fp_calendar_1210_')
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
            for region,year in [('Comunidad de Madrid','2026-2027'),
                                ('Canarias','2026-2027'),('Comunidad de Madrid','2027-2028')]:
                db.execute("""INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory)
                              VALUES(?,?,?,?,?,?)""",
                           (year,'Administración y Finanzas','Ofimática','1.º A',database.now(),region))
            cls.ids=[r['id'] for r in db.execute('SELECT id FROM modules ORDER BY id').fetchall()]
            draft=program_builder.load(db,cls.ids[0])['draft']
            draft['center']='IES Ejemplo'
            cfg=schedule_engine.defaults('2026-2027','Comunidad de Madrid')
            cfg.update(start_date='2026-09-14',end_date='2027-06-18',
                       regional_non_teaching_days=[{'date':'2026-10-12','reason':'Festividad general'}],
                       vacation_periods=[{'start':'2026-12-22','end':'2027-01-07','label':'Vacaciones'}],
                       calendar_source_url='https://www.comunidad.madrid/educacion/calendario-escolar',
                       calendar_source_description='Orden de calendario general comprobada por docente',
                       calendar_confirmed=True)
            draft['schedule']=cfg
            program_builder.save(db,cls.ids[0],draft)

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
             headers=headers,method='POST' if payload is not None else 'GET')
        try:
            with urllib.request.urlopen(req,timeout=12) as response:
                return response.status,json.load(response)
        except urllib.error.HTTPError as ex:
            return ex.code,json.load(ex)

    def test_read_save_compare_and_isolation(self):
        mid,other,year_other=self.ids
        path=f'api/national/general-calendar?module_id={mid}'
        status,data=self.request(path)
        self.assertEqual(status,200)
        self.assertEqual(data['count'],0)
        self.assertEqual(data['territory'],'Comunidad de Madrid')
        bad=self.request('api/national/general-calendar/save',
           {'module_id':mid,'teacher_confirmed':True,'general_scope_confirmed':False})
        self.assertEqual(bad[0],400)
        status,stored=self.request('api/national/general-calendar/save',
           {'module_id':mid,'teacher_confirmed':True,'general_scope_confirmed':True})
        self.assertEqual(status,200)
        self.assertEqual(stored['record']['revision'],1)
        first=stored['record']['id']
        with database.connect() as db:
            draft=program_builder.load(db,mid)['draft']
            draft['schedule']['start_date']='2026-09-15'
            program_builder.save(db,mid,draft)
        _,updated=self.request('api/national/general-calendar/save',
           {'module_id':mid,'teacher_confirmed':True,'general_scope_confirmed':True})
        second=updated['record']['id']
        self.assertEqual(updated['record']['revision'],2)
        # Contrasta también la consulta directa con la serialización HTTP.
        import general_calendar_library
        with database.connect() as db:
            rows=[dict(x) for x in db.execute(
                'SELECT id,territory_code,academic_year,stage FROM national_general_fp_calendars ORDER BY id').fetchall()]
            actual=[(x['id'],x['territory_code'],x['academic_year'],x['stage']) for x in rows]
            expected=[(first,'MD','2026-2027','fp_grado_d'),
                      (second,'MD','2026-2027','fp_grado_d')]
            self.assertEqual(actual,expected)
            direct=general_calendar_library.compare(db,mid,first,second)
            self.assertEqual(len(direct['changes']),1,rows)
        status,diff=self.request(
            f'api/national/general-calendar/compare?module_id={mid}&old={first}&new={second}')
        self.assertEqual(status,200, {'result':diff,'first':first,'second':second,'rows':rows})
        self.assertIn('start_date',[x['field'] for x in diff['changes']])
        _,newlist=self.request(path)
        self.assertEqual(newlist['count'],2)
        self.assertNotIn('evaluation_ends',newlist['versions'][0]['schedule'])
        for other_id in (other,year_other):
            _,scoped=self.request(f'api/national/general-calendar?module_id={other_id}')
            self.assertEqual(scoped['count'],0)
            status,_=self.request(
                f'api/national/general-calendar/compare?module_id={other_id}&old={first}&new={second}')
            self.assertEqual(status,400)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM national_general_fp_calendars').fetchone()[0],2)

    def test_auth_missing_module_and_invalid_year(self):
        mid=self.ids[0]
        self.assertIn(self.request(f'api/national/general-calendar?module_id={mid}',auth=False)[0],
                      (401,403))
        self.assertIn(self.request('api/national/general-calendar/save',
            {'module_id':mid,'teacher_confirmed':True,'general_scope_confirmed':True},auth=False)[0],
                      (401,403))
        self.assertEqual(self.request('api/national/general-calendar?module_id=999999')[0],400)


if __name__=='__main__':
    unittest.main()
