"""Regresión 1.2.7: historial local de calendarios y correcciones, sin inferencias."""
import json
import sqlite3
import unittest

import calendar_versions as versions
import national_registry as registry
import program_builder
import schedule_engine
import territorial_profiles as territories


class VersionedCalendarTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE modules(id INTEGER PRIMARY KEY, academic_year TEXT,
                         cycle TEXT, name TEXT, territory TEXT)''')
        self.db.execute('''CREATE TABLE audit_log(id INTEGER PRIMARY KEY, at TEXT,
                         action TEXT, entity TEXT, entity_id INTEGER, details_json TEXT)''')
        program_builder.migrate(self.db)
        registry.migrate(self.db)
        self.add_module(1, 'Comunidad de Madrid', '2026-2027')

    def tearDown(self):
        self.db.close()

    def add_module(self, mid, region, year):
        self.db.execute('INSERT INTO modules VALUES(?,?,?,?,?)',
                        (mid,year,'Administración y Finanzas','Módulo de ejemplo',region))

    def draft(self, mid=1, center='IES Ejemplo', municipality='Madrid',
              start='2026-09-14', correction_urls=None):
        original=program_builder.load(self.db,mid)['draft']
        original['center']=center
        region=original['region']
        year=self.db.execute('SELECT academic_year FROM modules WHERE id=?',(mid,)).fetchone()[0]
        cfg=schedule_engine.defaults(year, region)
        cfg.update(start_date=start,end_date=f'{int(year[:4])+1}-06-18',
            evaluation_ends=[f'{year[:4]}-12-18',f'{int(year[:4])+1}-03-19',f'{int(year[:4])+1}-06-18'],
            municipality=municipality,calendar_source_url='https://www.comunidad.madrid/educacion/calendario-escolar',
            calendar_source_description='Orden de calendario escolar 2026-2027, revisada por docente',
            calendar_correction_urls=correction_urls or [],calendar_confirmed=True,
            extra_non_teaching_days=[f'{int(year[:4])+1}-02-15'])
        original['schedule']=cfg
        self.db.execute('''INSERT OR REPLACE INTO programming_drafts(module_id,content_json,updated_at)
            VALUES(?,?,?)''',(mid,json.dumps(original,ensure_ascii=False),'2026-11-20'))
        return original

    def test_all_territories_have_portal_without_fabricated_dates(self):
        self.assertEqual(len(territories.TERRITORIES),19)
        for code,label in territories.TERRITORIES:
            with self.subTest(code=code):
                entry=versions.source_directory(code,'2026-2027')
                self.assertEqual(entry['territory'],label)
                self.assertFalse(entry['calendar_verified'])
                self.assertTrue(all(l['url'].startswith('https://') for l in entry['links']))
                self.assertGreaterEqual(len(entry['links']),1)
        self.assertTrue(any(x['kind']=='correccion'
            for x in versions.source_directory('Canarias','2026-2027')['links']))
        self.assertEqual(len(versions.source_directory('Comunidad de Madrid','2027-2028')['links']),1)

    def test_first_version_identical_save_and_change_comparison(self):
        self.draft()
        first=registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self.assertEqual(first['revision']['revision'],1)
        self.assertTrue(first['revision']['saved'])
        self.assertEqual(versions.list_versions(self.db,1)['count'],1)
        repeat=registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self.assertTrue(repeat['revision']['unchanged'])
        self.assertEqual(versions.list_versions(self.db,1)['count'],1)
        old_id=first['revision']['id']
        self.draft(correction_urls=['https://www.comunidad.madrid/educacion/calendario-escolar#correcciones'])
        draft=program_builder.load(self.db,1)['draft']
        draft['schedule']['start_date']='2026-09-15'
        self.db.execute('UPDATE programming_drafts SET content_json=? WHERE module_id=1',
                        (json.dumps(draft,ensure_ascii=False),))
        second=registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self.assertEqual(second['revision']['revision'],2)
        self.assertEqual(versions.list_versions(self.db,1)['count'],2)
        comparison=versions.compare_versions(self.db,1,old_id,second['revision']['id'])
        changed={x['field'] for x in comparison['changes']}
        self.assertIn('start_date',changed)
        self.assertIn('calendar_correction_urls',changed)
        saved=versions.list_versions(self.db,1)['versions'][0]['schedule']
        self.assertEqual(saved['calendar_correction_urls'],
            ['https://www.comunidad.madrid/educacion/calendario-escolar#correcciones'])
        self.assertNotIn('weekly_hours',saved)
        self.assertNotIn('feoe_start',saved)
        self.assertNotIn('calendar_confirmed',saved)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM audit_log WHERE action="calendar_revision_reviewed_by_teacher"').fetchone()[0],2)

    def test_revisions_isolated_by_year_territory_centre_and_municipality(self):
        self.draft()
        initial=registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        version_id=initial['revision']['id']
        contexts=[(2,'Comunidad de Madrid','2026-2027','IES Ejemplo','Alcalá de Henares'),
                  (3,'Comunidad de Madrid','2026-2027','Otro IES','Madrid'),
                  (4,'Comunidad de Madrid','2027-2028','IES Ejemplo','Madrid'),
                  (5,'Canarias','2026-2027','IES Ejemplo','Madrid')]
        for mid,region,year,center,city in contexts:
            self.add_module(mid,region,year)
            d=program_builder.load(self.db,mid)['draft']
            d['center']=center;d['schedule']['municipality']=city
            self.db.execute('INSERT INTO programming_drafts VALUES(?,?,?)',
                        (mid,json.dumps(d,ensure_ascii=False),'2026-11-20'))
            self.assertEqual(versions.list_versions(self.db,mid)['count'],0)
            with self.assertRaisesRegex(ValueError,'no encontrada'):
                versions.compare_versions(self.db,mid,version_id,version_id)
        self.add_module(6,'Comunidad de Madrid','2026-2027')
        d=program_builder.load(self.db,6)['draft']
        d['center']='IES Ejemplo';d['schedule']['municipality']='Madrid'
        self.db.execute('INSERT INTO programming_drafts VALUES(?,?,?)',
                        (6,json.dumps(d,ensure_ascii=False),'2026-11-20'))
        self.assertEqual(versions.list_versions(self.db,6)['count'],1)

    def test_same_named_centres_in_different_municipalities_keep_own_versions(self):
        self.draft(mid=1, municipality='Madrid',start='2026-09-14')
        registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self.add_module(2,'Comunidad de Madrid','2026-2027')
        self.draft(mid=2, municipality='Alcalá de Henares',start='2026-09-21')
        registry.save_calendar(self.db,2,{'teacher_confirmed':True})
        first=registry.find_calendar(self.db,1)
        second=registry.find_calendar(self.db,2)
        self.assertEqual(first['schedule']['start_date'],'2026-09-14')
        self.assertEqual(second['schedule']['start_date'],'2026-09-21')
        self.assertEqual(versions.list_versions(self.db,1)['count'],1)
        self.assertEqual(versions.list_versions(self.db,2)['count'],1)

    def test_legacy_custom_canary_calendar_does_not_inherit_boc_correction(self):
        cfg=schedule_engine.defaults('2026-2027','Canarias')
        del cfg['calendar_correction_urls']
        cfg['calendar_source_url']='https://www.example.org/centro/calendario'
        normalised=schedule_engine.clean(cfg,'2026-2027')
        self.assertEqual(normalised['calendar_correction_urls'],[])

    def test_reject_unconfirmed_non_https_and_dates_of_another_course(self):
        self.draft()
        with self.assertRaises(ValueError):registry.save_calendar(self.db,1,{'teacher_confirmed':False})
        data=program_builder.load(self.db,1)['draft']
        data['schedule']['calendar_correction_urls']=['http://localhost/private']
        self.db.execute('UPDATE programming_drafts SET content_json=? WHERE module_id=1',
                        (json.dumps(data,ensure_ascii=False),))
        with self.assertRaisesRegex(ValueError,'HTTPS'):
            registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        data['schedule']['calendar_correction_urls']=[]
        data['schedule']['extra_non_teaching_days']=['2028-01-15']
        self.db.execute('UPDATE programming_drafts SET content_json=? WHERE module_id=1',
                        (json.dumps(data,ensure_ascii=False),))
        with self.assertRaisesRegex(ValueError,'ajenas al curso'):
            registry.save_calendar(self.db,1,{'teacher_confirmed':True})


if __name__=='__main__':unittest.main()