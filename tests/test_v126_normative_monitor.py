"""Regresión 1.2.6: fuente BOE, aislamiento territorial y acuse docente."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import normative_monitor as monitor


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE modules (id INTEGER PRIMARY KEY,academic_year TEXT,territory TEXT)')
        self.db.execute('INSERT INTO modules VALUES(1,?,?)',('2026-2027','Canarias'))
        self.db.execute('''CREATE TABLE curriculum_source_snapshots
           (module_id INTEGER,territory_code TEXT,academic_year TEXT,module_code TEXT,
            source_url TEXT,source_title TEXT,id INTEGER PRIMARY KEY)''')
        monitor.migrate(self.db)
        self.scope=(1,'CN','2026-2027','0650')
        self.scope_patch=patch.object(monitor,'_scope',return_value=(self.scope,{}))
        self.scope_patch.start()
        self.addCleanup(self.scope_patch.stop)
        self.addCleanup(self.db.close)

    @staticmethod
    def response(updated='20260101',amendments=()):
        return {'id':'BOE-A-2011-19533','title':'Real Decreto de ejemplo',
                'publication_date':'20111215','last_update':updated,
                'consolidation_state':'', 'has_legal_analysis':True,
                'reported_amendments':[{'id':x,'type':'Modifica','title':'Modificación'} for x in amendments]}

    def test_baseline_detects_change_and_requires_review(self):
        ident='BOE-A-2011-19533'
        r=monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response())
        self.assertEqual(r['status'],'referencia_inicial')
        self.assertFalse(r['review_required'])
        self.assertEqual(monitor.list_sources(self.db,1)['count'],1)
        r=monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response())
        self.assertEqual(r['status'],'sin_cambios_observados')
        r=monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response('20261120',['BOE-A-2026-123']))
        self.assertEqual(r['status'],'cambio_detectado')
        self.assertTrue(r['review_required'])
        self.assertFalse(r['curriculum_modified'])
        self.assertEqual(len(monitor.list_sources(self.db,1)['events']),1)
        r=monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response('20261120',['BOE-A-2026-123']))
        self.assertEqual(r['status'],'cambio_pendiente_de_revision')
        with patch.object(monitor.database,'log',return_value=None):
            acknowledged=monitor.acknowledge_change(self.db,1,ident,'Revisado: comprobar efecto en el currículo autonómico.',True)
        self.assertTrue(acknowledged['ok'])
        r=monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response('20261120',['BOE-A-2026-123']))
        self.assertEqual(r['status'],'sin_cambios_observados')
        self.assertFalse(monitor.list_sources(self.db,1)['sources'][0]['review_pending'])

    def test_explicit_confirmation_and_failure_never_overwrite(self):
        ident='BOE-A-2011-19533'
        with self.assertRaisesRegex(ValueError,'Confirme'):
            monitor.check_source(self.db,1,ident,False,inspector=lambda i:self.response())
        monitor.check_source(self.db,1,ident,True,inspector=lambda i:self.response())
        before=self.db.execute('SELECT signature FROM boe_monitor_sources').fetchone()[0]
        with self.assertRaisesRegex(ValueError,'suficientes'):
            monitor.check_source(self.db,1,ident,True,
                inspector=lambda i:{**self.response('20261120'),'has_legal_analysis':False})
        self.assertEqual(self.db.execute('SELECT signature FROM boe_monitor_sources').fetchone()[0],before)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM boe_monitor_events').fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,'pendiente'):
            monitor.acknowledge_change(self.db,1,ident,'Nota suficientemente detallada',True)

    def test_url_validation_rejects_impostors(self):
        valid='https://www.boe.es/buscar/act.php?id=BOE-A-2011-19533'
        self.assertEqual(monitor._from_official_url(valid),'BOE-A-2011-19533')
        for url in ('https://www.boe.es.evil.org/buscar/act.php?id=BOE-A-2011-19533',
                    'http://www.boe.es/buscar/act.php?id=BOE-A-2011-19533',
                    'https://www.boe.es@evil.org/buscar/act.php?id=BOE-A-2011-19533',
                    'https://www.boe.es/buscar/act.php?id=BOE-A-2011-19533&u=2',
                    'https://www.boe.es/eli/es/rd/2020/12/01/1',
                    'https://www.boe.es/buscar/act.php?id=BOE-A-2011-19533#otro'):
            self.assertIsNone(monitor._from_official_url(url),url)
        for identifier in ('BOE-A-2026-1/../../x','BOE-A-2026-1?y=1','BOE-B-2026-1'):
            with self.assertRaises(ValueError):monitor._boe_id(identifier)

    def test_sources_do_not_mix_region_year_or_module_code(self):
        self.db.execute('''INSERT INTO curriculum_source_snapshots
          (module_id,territory_code,academic_year,module_code,source_url,source_title)
          VALUES(1,'CN','2026-2027','0650',?,?)''',
          ('https://www.boe.es/buscar/act.php?id=BOE-A-2011-19533','Norma 1'))
        self.db.execute('''INSERT INTO curriculum_source_snapshots
          (module_id,territory_code,academic_year,module_code,source_url,source_title)
          VALUES(1,'MD','2026-2027','0650',?,?)''',
          ('https://www.boe.es/buscar/act.php?id=BOE-A-2026-11','Norma incorrecta'))
        sources=monitor.list_sources(self.db,1)['sources']
        self.assertEqual([x['boe_id'] for x in sources],['BOE-A-2011-19533'])
        with patch.object(monitor,'_scope',return_value=((1,'MD','2026-2027','0650'),{})):
            self.assertEqual(monitor.list_sources(self.db,1)['sources'][0]['boe_id'],'BOE-A-2026-11')


if __name__=='__main__':unittest.main()