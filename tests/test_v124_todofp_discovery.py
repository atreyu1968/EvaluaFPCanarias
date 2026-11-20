"""Exploración oficial TodoFP: fuentes identificadas sin suplantar verificación legal."""
from __future__ import annotations

import io
import json
import sqlite3
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import todofp_discovery as td
import fp_catalog
import territorial_profiles as territorial

CYCLE_URL='https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas.html'
CURR_URL='https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas/curriculos-ccaa.html'

CYCLE_HTML='''<!doctype html><html><head><title>Ficha oficial</title></head><body>
<nav><a href="/login.html">Entrar</a><a href="#">Administración y Finanzas</a></nav>
<main><h1>Técnico Superior en Administración y Finanzas</h1>
<h2>Salidas profesionales</h2><ul><li>Administración de empresas</li></ul>
<h2>Plan de formación</h2><p>Si estudias primero de FP en el curso 2024-2025...</p><ul>
<li>Gestión de la documentación jurídica y empresarial.</li>
<li>0650. Proceso integral de la actividad comercial.</li>
<li>0651. Comunicación y atención al cliente.</li>
<li>Itinerario personal para la empleabilidad I.</li>
<li>Módulo profesional optativo (competencia de cada Comunidad Autónoma).</li>
<li>Incluye una fase de formación en empresa u organismo equiparado como parte integrada del currículo.</li>
</ul><h2>Dónde estudiar</h2><ul><li>IES Ejemplo (no es un módulo)</li></ul>
<a href="https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19533">Real Decreto</a>
<a href="/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas/curriculos-ccaa.html">Currículos CCAA</a>
</main></body></html>'''

CURRICULA_HTML='''<!doctype html><html><body><h1>Currículos de las Comunidades Autónomas</h1>
<nav><ul><li><a href="#andalucia">Andalucía</a></li><li><a href="#canarias">Canarias</a></li></ul></nav>
<img alt="Andalucía"><h3>Andalucía</h3><ul><li><a href="/dam/and.pdf">Currículo</a></li></ul>
<img alt="Aragón"><h3>Aragón</h3><ul><li><a href="https://www.boa.aragon.es/mod.pdf">Modificación</a></li></ul>
<img alt="Canarias"><h3>Canarias</h3><ul>
<li><a href="/dam/jcr%3A1234/canarias.pdf">Currículo</a></li>
<li><a href="https://www.gobiernodecanarias.org/boc/2024/226/3747.html">Modificación</a></li>
<li><a href="#arriba">Subir</a></li>
<li><a href="javascript:alert(1)">Currículo malicioso</a></li></ul>
<img alt="Comunidad de Madrid"><h3>Comunidad de Madrid</h3><ul>
<li><a href="https://www.bocm.es/bocm-2025.pdf">Currículo</a></li>
<li><a href="https://www.bocm.es/actual.pdf">Modificación</a></li></ul>
</body></html>'''


class DummyHTTP:
    def __init__(self,url,text,content_type='text/html'):
        self.url=url;self.body=text.encode('utf8');self.headers={'Content-Type':content_type}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def geturl(self):return self.url
    def read(self,n):return self.body[:n]


def fake_open(req,timeout=12):
    url=req.full_url
    if url==CYCLE_URL:return DummyHTTP(url,CYCLE_HTML)
    if url==CURR_URL:return DummyHTTP(url,CURRICULA_HTML)
    raise urllib.error.URLError('404 fixture')


class TodoFPTests(unittest.TestCase):
    def test_restrict_external_urls_and_ssrf(self):
        for value in ('http://www.todofp.es/que-estudiar/a.html',
                      'https://www.todofp.es.evil.invalid/que-estudiar/a.html',
                      'https://127.0.0.1/que-estudiar/a.html',
                      'https://www.todofp.es@evil.com/que-estudiar/a.html',
                      'https://www.todofp.es/que-estudiar/../../etc.html',
                      'https://www.todofp.es/que-estudiar/%2e%2e/admin.html',
                      'file:///etc/passwd','javascript:alert(1)',
                      'https://www.todofp.es/que-estudiar/a.html?q=token',
                      'https://www.todofp.es/que-estudiar/a.html#next'):
            with self.subTest(url=value),self.assertRaises(ValueError):td.validate_todofp_url(value)
        self.assertEqual(td.validate_todofp_url(CYCLE_URL),CYCLE_URL)

    def test_only_official_html_and_no_redirect_to_other_site(self):
        def redirected(req,timeout):return DummyHTTP('https://evil.example/que-estudiar/falso.html',CYCLE_HTML)
        with self.assertRaisesRegex(ValueError,'Solo se consultan'):
            td.fetch_todofp(CYCLE_URL,opener=redirected)
        def enormous(req,timeout):return DummyHTTP(req.full_url,'z'*(td.MAX_HTML_BYTES+100))
        with self.assertRaisesRegex(ValueError,'supera'):
            td.fetch_todofp(CYCLE_URL,opener=enormous)
        def wrongmime(req,timeout):return DummyHTTP(req.full_url,CYCLE_HTML,'application/pdf')
        with self.assertRaisesRegex(ValueError,'no ha devuelto'):
            td.fetch_todofp(CYCLE_URL,opener=wrongmime)

    def test_cycle_reads_plan_not_unrelated_lists_or_historical_year(self):
        result=td.parse_cycle(CYCLE_HTML,CYCLE_URL)
        self.assertEqual(result['title'],'Técnico Superior en Administración y Finanzas')
        self.assertEqual(result['grade'],'Superior')
        self.assertEqual(result['modules_count'],5)
        self.assertEqual(result['modules'][1]['code'],'0650')
        self.assertFalse(result['modules'][0]['code_confirmed_from_page'])
        self.assertEqual(result['modules'][3]['name'],'Itinerario personal para la empleabilidad I')
        self.assertTrue(result['modules'][4]['optional'])
        self.assertFalse(any('IES Ejemplo' in r['name'] for r in result['modules']))
        self.assertEqual(result['curricula_url'],CURR_URL)
        self.assertTrue(result['state_norm_url'].startswith('https://www.boe.es/'))

    def test_curricula_by_region_are_separate_and_modifications_visible(self):
        for label,count in [('Andalucía',1),('Canarias',2),('Comunidad de Madrid',2),('Ceuta',0),('Melilla',0)]:
            with self.subTest(label=label):
                result=td.parse_regional_curricula(CURRICULA_HTML,CURR_URL,label)
                self.assertEqual(result['count'],count)
                self.assertTrue(all(x['territory_code']==territorial.territory_code(label) for x in result['links']))
        can=td.parse_regional_curricula(CURRICULA_HTML,CURR_URL,'Canarias')
        self.assertEqual([r['type'] for r in can['links']],['curriculo','modificacion'])
        self.assertTrue(all(x['url'].startswith('https://') for x in can['links']))
        self.assertFalse(any('javascript' in r['url'] for r in can['links']))

    def test_explore_returns_state_and_region_without_claiming_validity(self):
        r=td.explore(CYCLE_URL,'Canarias','2026-2027',opener=fake_open,
                     cycle_name='CFGS Administración y Finanzas',module_name='Proceso integral de la actividad comercial')
        self.assertTrue(r['suitable_for_current_module'])
        self.assertTrue(r['approval_required'])
        self.assertEqual(r['regional_curricula']['count'],2)
        self.assertIn('no implica que el ciclo esté implantado',r['notice'])
        self.assertEqual(r['profile']['modules_count'],5)

    def test_mismatch_blocks_links_to_another_module_and_cycle(self):
        a=td.explore(CYCLE_URL,'Canarias','2026-2027',opener=fake_open,
                     cycle_name='CFGM Gestión Administrativa',module_name='Proceso integral de la actividad comercial')
        self.assertFalse(a['matches_selected_cycle'])
        self.assertFalse(a['suitable_for_current_module'])
        b=td.explore(CYCLE_URL,'Canarias','2026-2027',opener=fake_open,
                     cycle_name='CFGS Administración y Finanzas',module_name='Técnica Contable')
        self.assertFalse(b['matches_selected_module'])
        self.assertFalse(b['suitable_for_current_module'])

    def test_curricula_only_does_not_hallucinate_modules(self):
        result=td.explore(CURR_URL,'Galicia','2027-2028',opener=fake_open)
        self.assertIsNone(result['profile'])
        self.assertEqual(result['regional_curricula']['count'],0)
        self.assertTrue(result['approval_required'])

    def test_missing_curricula_page_keeps_cycle_but_warns(self):
        def fail_second(req,timeout):
            if req.full_url==CYCLE_URL:return DummyHTTP(CYCLE_URL,CYCLE_HTML)
            raise OSError('offline')
        result=td.explore(CYCLE_URL,'Canarias','2026-2027',opener=fail_second)
        self.assertEqual(result['profile']['modules_count'],5)
        self.assertEqual(result['regional_curricula']['count'],0)
        self.assertIn('No se ha podido',result['regional_curricula']['notice'])

    def test_all_19_administrations_supported_without_inventing_missing_links(self):
        for code,name in territorial.TERRITORIES:
            with self.subTest(name=name):
                result=td.explore(CYCLE_URL,name,'2026-2027',opener=fake_open)
                self.assertEqual(result['region'],name)
                if name not in ('Andalucía','Canarias','Comunidad de Madrid','Aragón'):
                    self.assertEqual(result['regional_curricula']['count'],0)

    def test_query_does_not_modify_sqlite(self):
        conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE modules(id INTEGER PRIMARY KEY,name TEXT)')
        conn.execute('INSERT INTO modules VALUES(1,?)',('Técnica Contable',))
        before=conn.total_changes
        td.explore(CYCLE_URL,'Comunidad de Madrid','2026-2027',opener=fake_open)
        self.assertEqual(conn.total_changes,before)
        self.assertEqual(conn.execute('SELECT name FROM modules WHERE id=1').fetchone()[0],'Técnica Contable')
        conn.close()

    def test_parsing_page_with_no_modules_is_visible_as_incomplete(self):
        empty='<html><h1>Técnico en Gestión Administrativa</h1><h2>Salidas profesionales</h2><li>Oficinas</li></html>'
        result=td.parse_cycle(empty,CYCLE_URL)
        self.assertEqual(result['grade'],'Medio')
        self.assertEqual(result['modules_count'],0)
        self.assertEqual(result['modules'],[])

    def test_source_importer_and_catalog_remain_separate(self):
        self.assertEqual(td.explore(CYCLE_URL,'Canarias','2026-2027',opener=fake_open)['profile']['modules'][0]['code'],'')
        with self.assertRaises(ValueError):
            fp_catalog.preview_table('Código título;Ciclo;Grado;Familia;Código módulo;Módulo\n'
                 'DEMO-001;Administración y Finanzas;Superior;Administración y Gestión;;Gestión documental')

    def test_ui_and_http_route_present(self):
        root=Path(__file__).resolve().parents[1]
        js=(root/'web/app.js').read_text(encoding='utf8')
        app=(root/'app.py').read_text(encoding='utf8')
        self.assertIn('/api/national/todofp/explore',app)
        self.assertIn('todofp-explore',js)
        self.assertIn('todofp-add-refs',js)
        self.assertIn('todofp-select-module',js)

if __name__=='__main__':unittest.main()
