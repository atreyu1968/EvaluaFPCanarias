"""Regresiones de cobertura estatal y calendarios por curso, sin API externa."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import schedule_engine as schedule
import official_catalog
import territorial_profiles as terr


class TerritoryTests(unittest.TestCase):
    def test_nineteen_territories_and_aliases(self):
        self.assertEqual(len(terr.TERRITORIES),19)
        for code,label in terr.TERRITORIES:
            self.assertEqual(terr.territory_code(label),code)
            self.assertEqual(terr.require_territory(code),label)
        self.assertEqual(terr.require_territory('Baleares'),'Illes Balears')
        self.assertEqual(terr.require_territory('Madrid'),'Comunidad de Madrid')
        self.assertEqual(terr.require_territory('Comunidad Valenciana'),'Comunitat Valenciana')
        with self.assertRaisesRegex(ValueError,'19 ámbitos'):
            terr.require_territory('Canarias / Madrid')

    def test_years_and_territories_do_not_inherit_canarian_calendar(self):
        for code,label in terr.TERRITORIES:
            for year in ('2025-2026','2026-2027','2027-2028'):
                cfg=schedule.defaults(year,label)
                expected=label=='Canarias' and year=='2026-2027'
                self.assertEqual(bool(cfg['start_date']),expected,(label,year))
                self.assertEqual(bool(cfg['calendar_source_url']),expected,(label,year))
                self.assertEqual(cfg['calendar_academic_year'],year)
                self.assertFalse(cfg['calendar_confirmed'])
                self.assertEqual(cfg['region'],label)
                if not expected:
                    self.assertFalse(any('boc/' in s for s in cfg.values() if isinstance(s,str)))

    def test_real_canarian_christmas_correction_and_local_festival(self):
        cfg=schedule.defaults('2026-2027','Canarias','Tenerife')
        cfg.update(weekly_hours=6,total_hours=202,weekday_hours=[2,0,2,0,2],municipality='Guía de Isora')
        report=schedule.plan({'schedule':cfg,'units':[]})
        blocked={x['date'] for x in report['non_teaching']}
        self.assertIn('2027-01-08',blocked)
        self.assertNotIn('2026-12-22',blocked)
        self.assertIn('2026-09-21',blocked)
        self.assertIn('2027-02-02',blocked)
        self.assertEqual(report['terms'][1]['start'],'2027-01-11')
        self.assertTrue(any('boc/2026/075' in x for x in report['sources']))
        self.assertTrue(any('boc/2025/165' in x for x in report['sources']))

    def test_region_change_invalidates_old_calendar_source_and_year_change(self):
        can=schedule.defaults('2026-2027','Canarias','Tenerife')
        can['region']='Comunidad de Madrid'
        changed=schedule.clean(can,'2026-2027')
        self.assertEqual(changed['start_date'],'')
        self.assertEqual(changed['evaluation_ends'],['','',''])
        self.assertEqual(changed['calendar_source_url'],'')
        self.assertFalse(changed['calendar_confirmed'])
        self.assertEqual(changed['island'],'')
        can=schedule.defaults('2026-2027','Canarias')
        newyear=schedule.clean(can,'2027-2028')
        self.assertEqual(newyear['start_date'],'')
        self.assertEqual(newyear['calendar_academic_year'],'2027-2028')
        self.assertEqual(newyear['calendar_source_url'],'')

    def test_manual_calendar_for_madrid_is_respected_without_cross_territory_sources(self):
        cfg=schedule.defaults('2026-2027','Comunidad de Madrid')
        cfg.update(weekly_hours=4,total_hours=120,weekday_hours=[2,0,2,0,0],
                   start_date='2026-09-14',end_date='2027-06-18',
                   evaluation_ends=['2026-12-20','2027-03-20','2027-06-18'],
                   vacation_periods=[{'start':'2026-12-24','end':'2027-01-07','label':'Vacaciones según calendario del centro'}],
                   regional_non_teaching_days=[{'date':'2026-10-12','reason':'Fiesta Nacional'}],
                   calendar_source_url='https://ejemplo.educacion.es/calendario-aprobado',
                   calendar_source_description='Introducido tras consulta docente',calendar_confirmed=True,
                   hours_confirmed=True)
        result=schedule.plan({'schedule':cfg,'units':[]})
        self.assertTrue(result['configured'])
        self.assertEqual(result['config']['region'],'Comunidad de Madrid')
        self.assertIn('2026-10-12',[x['date'] for x in result['non_teaching']])
        self.assertIn('https://ejemplo.educacion.es/calendario-aprobado',result['sources'])
        self.assertFalse(any('gobiernodecanarias' in x for x in result['sources']))
        self.assertFalse(any('2026-09-21' == x['date'] for x in result['non_teaching']))

    def test_normative_sources_not_assigned_to_wrong_course_or_region(self):
        def refs(region,year):
            return official_catalog.normative_proposal(region,'CFGS Administración y Finanzas',
                      'Proceso integral de la actividad comercial',academic_year=year)
        self.assertIn('boc/2026/075',refs('Canarias','2026-2027'))
        self.assertNotIn('boc/2026/075',refs('Canarias','2025-2026'))
        self.assertNotIn('gobiernodecanarias',refs('Comunidad de Madrid','2026-2027'))
        self.assertIn('Comunidad de Madrid para 2026-2027',refs('Comunidad de Madrid','2026-2027'))
        self.assertIsNone(official_catalog.find('Ceuta','CFGS Administración y Finanzas','Proceso integral de la actividad comercial'))

    def test_bad_manual_holidays_and_sources_are_rejected(self):
        cfg=schedule.defaults('2026-2027','Ceuta')
        cfg['vacation_periods']=[{'start':'2027-02-14','end':'2027-02-13','label':'Inválido'}]
        with self.assertRaisesRegex(ValueError,'periodo no lectivo'):schedule.clean(cfg)
        cfg=schedule.defaults('2026-2027','Melilla')
        cfg['regional_non_teaching_days']=[{'date':'2026-99-99','reason':'Inválido'}]
        with self.assertRaisesRegex(ValueError,'fecha válida'):schedule.clean(cfg)


if __name__=='__main__':unittest.main()
