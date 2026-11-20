"""Regresión: ninguna fuente se transfiere a otro curso, centro o comunidad."""
import json
import sqlite3
import unittest

import national_registry as registry
import program_builder
import schedule_engine
import territorial_profiles as territories


class NationalRegistryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE modules(id INTEGER PRIMARY KEY,academic_year TEXT,cycle TEXT,
            name TEXT,territory TEXT)''')
        self.db.execute('''CREATE TABLE audit_log(id INTEGER PRIMARY KEY,at TEXT,action TEXT,
            entity TEXT,entity_id INTEGER,details_json TEXT)''')
        program_builder.migrate(self.db)
        registry.migrate(self.db)
        self.add_module(1,'Comunidad de Madrid','2026-2027','Administración y Finanzas','Proceso integral de la actividad comercial')

    def tearDown(self):
        self.db.close()

    def add_module(self,mid,region,year,cycle,name):
        self.db.execute('INSERT INTO modules(id,academic_year,cycle,name,territory) VALUES(?,?,?,?,?)',
                        (mid,year,cycle,name,region))

    def save_hours(self,mid=1,**overrides):
        payload={'teacher_confirmed':True,'total_hours':200,'weekly_hours':6,
                 'source_url':'https://www.bocm.es/boletin/CM_Orden_BOCM_2026.pdf',
                 'source_title':'BOCM 2026, anexo de distribución horaria (comprobado por el docente)'}
        payload.update(overrides)
        return registry.save_hours(self.db,mid,payload)

    def test_sources_cover_all_nineteen_territories_without_guessing_calendar(self):
        self.assertEqual(len(registry.PORTALS),19)
        for code,label in territories.TERRITORIES:
            result=registry.source_directory(code,'Ciclo de ejemplo','2026-2027')
            self.assertEqual(result['territory_code'],code)
            self.assertTrue(all(row['url'].startswith('https://') for row in result['links']))
            self.assertGreaterEqual(len(result['links']),3)
        self.assertGreaterEqual(len(registry.source_directory('Madrid','Administración y Finanzas','2026-2027')['links']),4)

    def test_csv_preview_accepts_spanish_hours_and_rejects_bad_columns(self):
        csv='Código;Módulo;Horas totales;Horas semanales\n0650;Proceso integral de la actividad comercial;202;6\n0651;Comunicación y atención al cliente;170;5'
        report=registry.preview_hours_table(csv)
        self.assertEqual(report['count'],2)
        self.assertEqual(report['rows'][0]['total_hours'],202)
        self.assertEqual(report['rows'][1]['weekly_hours'],5)
        tab='Código\tMódulo\tHoras anuales\tHoras por semana\n0650\tProceso integral de la actividad comercial\t202\t6'
        self.assertEqual(registry.preview_hours_table(tab)['count'],1)
        for bad in ('Código;Módulo;Horas\n0650;Procesos;202',
                    'Código;Módulo;Horas totales;Horas semanales\n0650;Procesos;202;0',
                    'Código;Módulo;Horas totales;Horas semanales\n0650;Procesos;202;6\n0650;Duplicado;202;6'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):registry.preview_hours_table(bad)

    def test_bulk_import_all_modules_reused_by_same_course_only(self):
        csv='Código;Módulo;Horas totales;Horas semanales\n0650;Proceso integral de la actividad comercial;202;6\n0651;Comunicación y atención al cliente;170;5'
        source='https://www.bocm.es/boletin/CM_Orden_BOCM_2026.pdf'
        title='Anexo de distribución horaria 2026'
        with self.assertRaises(ValueError):
            registry.import_hours_table(self.db,1,csv,source,title,teacher_confirmed=False)
        result=registry.import_hours_table(self.db,1,csv,source,title,teacher_confirmed=True)
        self.assertEqual(result['count'],2)
        self.assertEqual(result['records_saved'],4)
        self.assertEqual(registry.find_hours(self.db,1)['total_hours'],202)
        self.add_module(2,'Comunidad de Madrid','2026-2027','Administración y Finanzas','Comunicación y atención al cliente')
        self.assertEqual(registry.find_hours(self.db,2)['total_hours'],170)
        self.add_module(3,'Comunidad de Madrid','2027-2028','Administración y Finanzas','Comunicación y atención al cliente')
        self.assertIsNone(registry.find_hours(self.db,3))
        unchanged=registry.import_hours_table(self.db,1,csv.replace('202;6','201;4'),source,title,teacher_confirmed=True)
        self.assertEqual(unchanged['records_saved'],0)
        self.assertEqual(unchanged['records_unchanged'],4)
        self.assertEqual(registry.find_hours(self.db,1)['total_hours'],202)

    def test_bulk_import_rejects_foreign_cycle_before_writing_any_row(self):
        foreign=('Código;Módulo;Horas totales;Horas semanales\n'
                 '9999;Módulo de un ciclo distinto;120;4\n'
                 '9998;Otro módulo ajeno;80;2')
        with self.assertRaisesRegex(ValueError,'no contiene el módulo seleccionado'):
            registry.import_hours_table(
                self.db,1,foreign,'https://www.bocm.es/boletin/ciclo-ajeno.pdf',
                'Disposición hipotética',teacher_confirmed=True)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM national_hour_records').fetchone()[0],0)

    def test_ai_extraction_requires_literal_quote_and_teacher_approval(self):
        from unittest.mock import patch
        excerpt=('BOCM de Madrid 2026. En el ciclo Administración y Finanzas, '
                 'módulo Proceso integral de la actividad comercial, código 0650, '
                 'horas totales 200, horas semanales 6. Reparto del curso. '*2)
        draft=program_builder.load(self.db,1)['draft']
        draft['official_module_code']='0650'
        self.db.execute('INSERT INTO programming_drafts(module_id,content_json,updated_at) VALUES(?,?,?)',
                        (1,json.dumps(draft,ensure_ascii=False),'2026-11-19'))
        quote='módulo Proceso integral de la actividad comercial, código 0650, horas totales 200, horas semanales 6'
        payload={'module_name':'Proceso integral de la actividad comercial',
                 'module_code':'0650','total_hours':200,'weekly_hours':6,'literal_quote':quote}
        with patch('ia.key_available',return_value=True),patch('ia.chat',return_value=(payload,'simulado')):
            with self.assertRaises(ValueError):
                registry.extract_hours_with_ai(self.db,1,excerpt,authorize_ai=False)
            result=registry.extract_hours_with_ai(self.db,1,excerpt,authorize_ai=True)
            self.assertTrue(result['requires_teacher_confirmation'])
            self.assertEqual(result['total_hours'],200)
            self.assertIsNone(registry.find_hours(self.db,1)) # No escribe nada
            for key,bad in [
                ('weekly_hours',7),('literal_quote','Cita inventada con 0650 y 200 h y 6 h'),
                ('module_code','9999'),('total_hours',999)]:
                with self.subTest(key=key):
                    fake=dict(payload);fake[key]=bad
                    with patch('ia.chat',return_value=(fake,'simulado')):
                        with self.assertRaises(ValueError):
                            registry.extract_hours_with_ai(self.db,1,excerpt,authorize_ai=True)

    def test_legacy_hours_are_not_prefilled_in_future_school_year(self):
        self.add_module(11,'Canarias','2027-2028','Gestión Administrativa','Técnica contable')
        draft=program_builder.load(self.db,11)['draft']
        self.assertFalse(draft['schedule']['total_hours'])
        self.assertFalse(draft['schedule']['weekly_hours'])
        from program_assistant import hours_proposal
        self.assertIsNone(hours_proposal({'name':'Técnica contable','cycle':'Gestión Administrativa',
                                           'academic_year':'2027-2028'},'Canarias'))

    def test_hours_are_only_reused_in_same_year_region_cycle_module(self):
        r=self.save_hours()
        self.assertEqual(r['weekly_hours'],6)
        self.assertEqual(r['source'],'biblioteca_local')
        self.add_module(2,'Comunidad de Madrid','2026-2027','Administración y Finanzas','Proceso integral de la actividad comercial')
        self.add_module(3,'Comunidad de Madrid','2027-2028','Administración y Finanzas','Proceso integral de la actividad comercial')
        self.add_module(4,'Canarias','2026-2027','Administración y Finanzas','Proceso integral de la actividad comercial')
        self.add_module(5,'Comunidad de Madrid','2026-2027','Gestión Administrativa','Proceso integral de la actividad comercial')
        self.add_module(6,'Comunidad de Madrid','2026-2027','Administración y Finanzas','Técnica Contable')
        self.assertEqual(registry.find_hours(self.db,2)['weekly_hours'],6)
        for mid in (3,4,5,6):self.assertIsNone(registry.find_hours(self.db,mid))

    def test_hours_are_not_persisted_without_verifiable_provenance(self):
        for fields in ({'teacher_confirmed':False},{'source_url':''},
                       {'source_url':'http://example.com/norma.pdf'},
                       {'weekly_hours':'6.234'}, {'total_hours':0},
                       {'source_title':''}):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):self.save_hours(**fields)
        self.assertIsNone(registry.find_hours(self.db,1))

    def test_confirmation_can_update_own_year_reference(self):
        self.save_hours()
        self.save_hours(total_hours=202,weekly_hours=6)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM national_hour_records').fetchone()[0],1)
        self.assertEqual(registry.find_hours(self.db,1)['total_hours'],202)

    def test_local_hour_source_prefills_unconfirmed_draft(self):
        self.save_hours(weekly_hours=5,total_hours=170)
        draft=program_builder.load(self.db,1)['draft']
        self.assertEqual(draft['schedule']['weekly_hours'],5)
        self.assertEqual(draft['schedule']['total_hours'],170)
        self.assertEqual(draft['schedule']['hours_source_url'],'https://www.bocm.es/boletin/CM_Orden_BOCM_2026.pdf')
        self.assertFalse(draft['schedule']['hours_confirmed'])

    def _save_draft_with_calendar(self,mid=1,center='IES Ejemplo',source='https://www.comunidad.madrid/calendario-fp-2026.pdf'):
        draft=program_builder.load(self.db,mid)['draft']
        draft['center']=center
        cfg=schedule_engine.defaults('2026-2027','Comunidad de Madrid')
        cfg.update({'start_date':'2026-09-14','end_date':'2027-06-18',
                    'evaluation_ends':['2026-12-18','2027-03-19','2027-06-18'],
                    'vacation_periods':[{'start':'2026-12-23','end':'2027-01-07','label':'Navidad'}],
                    'regional_non_teaching_days':[{'date':'2026-10-12','reason':'Fiesta Nacional'}],
                    'calendar_source_url':source,
                    'calendar_source_description':'Resolución calendario escolar FP 2026-2027',
                    'calendar_confirmed':True})
        draft['schedule']=cfg
        self.db.execute('''INSERT OR REPLACE INTO programming_drafts(module_id,content_json,updated_at)
            VALUES(?,?,?)''',(mid,json.dumps(draft,ensure_ascii=False),'2026-11-19'))

    def test_center_calendar_versioning_and_no_weekly_hours_leak(self):
        self._save_draft_with_calendar()
        rec=registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self.assertEqual(rec['schedule']['start_date'],'2026-09-14')
        self.assertNotIn('weekly_hours',rec['schedule'])
        self.assertNotIn('feoe_start',rec['schedule'])
        self.add_module(2,'Comunidad de Madrid','2026-2027','Gestión Administrativa','Técnica contable')
        self.add_module(3,'Canarias','2026-2027','Gestión Administrativa','Técnica contable')
        self.add_module(4,'Comunidad de Madrid','2027-2028','Gestión Administrativa','Técnica contable')
        self.add_module(5,'Comunidad de Madrid','2026-2027','Gestión Administrativa','Técnica contable')
        for mid,center in [(2,'IES Ejemplo'),(3,'IES Ejemplo'),(4,'IES Ejemplo'),(5,'Otro centro')]:
            draft=program_builder.load(self.db,mid)['draft'];draft['center']=center
            self.db.execute('''INSERT INTO programming_drafts(module_id,content_json,updated_at) VALUES(?,?,?)''',
                            (mid,json.dumps(draft,ensure_ascii=False),'2026-11-19'))
        self.assertEqual(registry.find_calendar(self.db,2)['schedule']['start_date'],'2026-09-14')
        for mid in (3,4,5):self.assertIsNone(registry.find_calendar(self.db,mid))

    def test_center_calendar_requires_explicit_school_and_source(self):
        self._save_draft_with_calendar(center='')
        with self.assertRaises(ValueError):registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        self._save_draft_with_calendar(center='IES Ejemplo',source='')
        with self.assertRaises(ValueError):registry.save_calendar(self.db,1,{'teacher_confirmed':True})
        with self.assertRaises(ValueError):registry.save_calendar(self.db,1,{'teacher_confirmed':False})


if __name__=='__main__':unittest.main()
