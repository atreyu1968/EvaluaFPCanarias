"""Pruebas 1.2.10: calendario general reutilizable sin contaminación local."""
from __future__ import annotations
import json
import sqlite3
import unittest

import general_calendar_library as library
import national_registry as registry
import program_builder
import schedule_engine
import territorial_profiles as territory


class GeneralCalendarLibraryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute("""CREATE TABLE modules(id INTEGER PRIMARY KEY, academic_year TEXT,
                        cycle TEXT, name TEXT, territory TEXT)""")
        self.db.execute("""CREATE TABLE audit_log(id INTEGER PRIMARY KEY, at TEXT,
                        action TEXT, entity TEXT, entity_id INTEGER, details_json TEXT)""")
        program_builder.migrate(self.db)
        registry.migrate(self.db)
        library.migrate(self.db)
        self.module(1,'Comunidad de Madrid','2026-2027')
        self.calendar(1)

    def tearDown(self):
        self.db.close()

    def module(self, ident, region, year):
        self.db.execute('INSERT INTO modules VALUES(?,?,?,?,?)',
                        (ident,year,'Administración y Finanzas','Módulo de prueba',region))

    def calendar(self, ident, center='IES Referencia', region=None, island='', municipality='Madrid',
                 first='2026-09-14', general_days=None, extra_days=None, year=None):
        row=self.db.execute('SELECT * FROM modules WHERE id=?',(ident,)).fetchone()
        region=region or row['territory']
        year=year or row['academic_year']
        draft=program_builder.load(self.db,ident)['draft']
        draft['center']=center
        cfg=schedule_engine.defaults(year,region,island)
        cfg.update(region=region,island=island,municipality=municipality,
             start_date=first,end_date=f"{int(year[:4])+1}-06-18",
             evaluation_ends=[f"{year[:4]}-12-18",f"{int(year[:4])+1}-03-19",
                              f"{int(year[:4])+1}-06-18"],
             weekly_hours=6,total_hours=198,weekday_hours=[2,1,1,1,1],
             feoe_start=f"{int(year[:4])+1}-03-01",feoe_end=f"{int(year[:4])+1}-04-30",
             vacation_periods=[{'start':f"{year[:4]}-12-23",
                                'end':f"{int(year[:4])+1}-01-08",
                                'label':'Navidad'}],
             regional_non_teaching_days=general_days if general_days is not None else
                       [{'date':f"{year[:4]}-10-12",'reason':'Día nacional'}],
             extra_non_teaching_days=extra_days if extra_days is not None else
                       [f"{int(year[:4])+1}-02-15"],
             calendar_source_url='https://www.comunidad.madrid/educacion/calendario-escolar',
             calendar_source_description='Resolución general del calendario: cotejada por docente',
             calendar_confirmed=True)
        draft['schedule']=cfg
        self.db.execute("""INSERT INTO programming_drafts(module_id,content_json,updated_at)
              VALUES(?,?,?) ON CONFLICT(module_id) DO UPDATE SET content_json=excluded.content_json""",
              (ident,json.dumps(draft,ensure_ascii=False),'2026-11-20'))
        return draft

    def save(self,ident=1,**extra):
        payload={'teacher_confirmed':True,'general_scope_confirmed':True}
        payload.update(extra)
        return library.save_from_module(self.db,ident,payload)

    def test_general_calendar_reuses_across_centres_same_territory_year(self):
        first=self.save()
        self.assertEqual(first['revision'],1)
        self.assertTrue(first['saved'])
        self.module(2,'Comunidad de Madrid','2026-2027')
        self.calendar(2,center='IES Otro',municipality='Alcalá de Henares',
                      extra_days=['2027-03-02'])
        info=library.list_for_module(self.db,2)
        self.assertEqual(info['count'],1)
        rec=info['versions'][0]
        self.assertNotIn('center',rec['schedule'])
        self.assertNotIn('municipality',rec['schedule'])
        self.assertNotIn('island',rec['schedule'])
        self.assertNotIn('extra_non_teaching_days',rec['schedule'])
        for field in ('weekly_hours','weekday_hours','total_hours','feoe_start','feoe_end',
                      'evaluation_ends','calendar_confirmed'):
            self.assertNotIn(field,rec['schedule'])
        self.assertEqual(rec['schedule']['start_date'],'2026-09-14')
        self.assertEqual(rec['academic_year'],'2026-2027')

    def test_idempotency_and_historical_comparison(self):
        start=self.save()
        repeated=self.save()
        self.assertTrue(repeated['unchanged'])
        self.assertEqual(library.list_for_module(self.db,1)['count'],1)
        self.calendar(1,first='2026-09-15')
        later=self.save()
        self.assertEqual(later['revision'],2)
        dif=library.compare(self.db,1,start['id'],later['id'])
        self.assertEqual(dif['changes'][0]['field'],'start_date')
        self.assertEqual(dif['changes'][0]['previous'],'2026-09-14')
        self.assertEqual(dif['changes'][0]['current'],'2026-09-15')
        self.assertEqual(library.list_for_module(self.db,1)['versions'][1]['schedule']['start_date'],
                         '2026-09-14')

    def test_territory_year_isolation_and_no_guessing(self):
        first=self.save()
        self.module(3,'Canarias','2026-2027')
        self.calendar(3,region='Canarias')
        self.module(4,'Comunidad de Madrid','2027-2028')
        self.calendar(4,region='Comunidad de Madrid',year='2027-2028',first='2027-09-14')
        for ident in (3,4):
            info=library.list_for_module(self.db,ident)
            self.assertEqual(info['count'],0)
            with self.assertRaises(ValueError):library.compare(self.db,ident,first['id'],first['id'])
        self.assertEqual(len(territory.TERRITORIES),19)
        for code,label in territory.TERRITORIES:
            self.assertEqual(library._scope_key(code,'2027-2028'),(code,'2027-2028','fp_grado_d'))

    def test_center_local_days_are_not_stored_and_schedule_is_untouched(self):
        original=program_builder.load(self.db,1)['draft']['schedule']
        self.save()
        rec=library.list_for_module(self.db,1)['versions'][0]['schedule']
        self.assertNotIn('extra_non_teaching_days',rec)
        new=program_builder.load(self.db,1)['draft']['schedule']
        self.assertEqual(new['extra_non_teaching_days'],original['extra_non_teaching_days'])
        self.assertEqual(new['feoe_start'],original['feoe_start'])
        self.assertTrue(new['calendar_confirmed'])

    def test_cannot_share_known_insular_holiday_as_general(self):
        self.module(5,'Canarias','2026-2027')
        original=schedule_engine.defaults('2026-2027','Canarias','Tenerife')
        self.calendar(5,region='Canarias',island='Tenerife',
             general_days=original['regional_non_teaching_days'])
        with self.assertRaisesRegex(ValueError,'insulares'):
            self.save(5)
        clean=[x for x in original['regional_non_teaching_days']
               if x['date']!='2027-02-02']
        self.calendar(5,region='Canarias',island='Tenerife',
                      general_days=clean,extra_days=['2027-02-02'])
        record=self.save(5)
        self.assertTrue(record['saved'])
        saved=library.list_for_module(self.db,5)['versions'][0]['schedule']
        self.assertNotIn('2027-02-02',[r['date'] for r in saved['regional_non_teaching_days']])

    def test_rejects_unconfirmed_wrong_scope_dates_and_source(self):
        with self.assertRaisesRegex(ValueError,'Confirme'):
            self.save(teacher_confirmed=False)
        with self.assertRaisesRegex(ValueError,'Confirme'):
            self.save(general_scope_confirmed=False)
        draft=program_builder.load(self.db,1)['draft']
        draft['schedule']['calendar_confirmed']=False
        self.db.execute('UPDATE programming_drafts SET content_json=? WHERE module_id=1',
                        (json.dumps(draft,ensure_ascii=False),))
        with self.assertRaisesRegex(ValueError,'confirmado'):self.save()
        self.calendar(1,first='2027-09-14')
        with self.assertRaises(ValueError):self.save()
        self.db.execute('DELETE FROM programming_drafts WHERE module_id=1')
        self.calendar(1)
        draft=program_builder.load(self.db,1)['draft']
        draft['schedule']['calendar_source_url']='https://localhost/private'
        self.db.execute('UPDATE programming_drafts SET content_json=? WHERE module_id=1',
                        (json.dumps(draft,ensure_ascii=False),))
        with self.assertRaises(ValueError):self.save()
        self.calendar(1,region='Canarias')
        # Al cambiar de comunidad, el cargador de programaciones invalida la
        # confirmación antigua. El rechazo sigue siendo la garantía principal.
        with self.assertRaises(ValueError):
            self.save()

    def test_unknown_module_and_duplicate_guard(self):
        with self.assertRaises(ValueError):
            library.list_for_module(self.db,9999)
        self.save()
        self.save()
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM national_general_fp_calendars').fetchone()[0],1)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action='general_calendar_reviewed_by_teacher'"
        ).fetchone()[0],1)


if __name__ == '__main__':
    unittest.main()
