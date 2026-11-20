"""Índice de títulos estatales por grado: sin inventar códigos ni territorios."""
import unittest
from pathlib import Path

import official_title_index as index
import todofp_discovery as todofp
import territorial_profiles as territories

FAMILY='https://www.todofp.es/que-estudiar/familias-profesionales/'
GRADE_HTML='''<html><head><title>TodoFP</title></head><body>
<nav><a href="/que-estudiar/grados-d/grado-superior.html">Grado superior</a></nav>
<h1>Ciclos Formativos de Grado Superior</h1>
<table><tr><th>Familia</th><th>Titulación</th></tr>
<tr><td>Administración y Gestión</td><td><a href="/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas.html">Técnico Superior en Administración y Finanzas</a></td></tr>
<tr><td>Administración y Gestión</td><td><a href="/que-estudiar/familias-profesionales/administracion-gestion/asistencia-direccion.html">Técnica Superior en Asistencia a la Dirección</a></td></tr>
<tr><td>Sanidad</td><td><a href="/que-estudiar/familias-profesionales/sanidad/laboratorio-clinico-biomedico.html">Técnico Superior en Laboratorio Clínico y Biomédico</a></td></tr>
<tr><td><a href="https://evil.example/que-estudiar/familias-profesionales/administracion-gestion/admin-falso.html">Técnico Superior en Empresa falsa</a></td></tr>
<tr><td><a href="/que-estudiar/logse/administracion/antiguo.html">Técnico Superior en Título no vigente</a></td></tr>
<tr><td><a href="/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas.html">Técnico Superior en Administración y Finanzas</a></td></tr>
<tr><td><a href="/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas/curriculos-ccaa.html">Técnico Superior en currículos</a></td></tr>
</table></body></html>'''

class MockHTTP:
    def __init__(self,url,text=GRADE_HTML):self.url=url;self.body=text.encode();self.headers={'Content-Type':'text/html'}
    def __enter__(self):return self
    def __exit__(self,*a):return None
    def geturl(self):return self.url
    def read(self,n):return self.body[:n]

def mock_open(req,timeout):return MockHTTP(req.full_url)

class IndexTests(unittest.TestCase):
    def test_real_official_source_urls_are_selected_by_grade(self):
        self.assertEqual(len(index.INDICES),4)
        for grade,source in index.INDICES.items():
            self.assertEqual(todofp.validate_todofp_url(source),source)
            self.assertEqual(index.parse_index('<html></html>',source,grade)['grade'],grade)

    def test_only_official_title_links_returned(self):
        result=index.parse_index(GRADE_HTML,index.INDICES['Superior'],'Superior')
        self.assertEqual(result['total_in_index'],3)
        self.assertEqual(result['count'],3)
        self.assertEqual(len(set(x['url'] for x in result['results'])),3)
        self.assertTrue(all(x['url'].startswith(FAMILY) for x in result['results']))
        self.assertTrue(all(x['title_code']=='' for x in result['results']))
        self.assertTrue(all(x['code_status']=='no_aparece_en_el_indice' for x in result['results']))

    def test_accent_insensitive_search_and_grade_validation(self):
        result=index.search('Superior','administracion Y FINANZAS','Canarias','2026-2027',opener=mock_open)
        self.assertEqual(result['count'],1)
        self.assertIn('Administración y Finanzas',result['results'][0]['name'])
        self.assertTrue(result['approval_required'])
        self.assertEqual(result['territory'],'Canarias')
        self.assertEqual(result['academic_year'],'2026-2027')
        self.assertNotIn('hours',result['results'][0])

    def test_all_19_scopes_are_supported_without_inventing_local_implementation(self):
        for _,region in territories.TERRITORIES:
            with self.subTest(region=region):
                result=index.search('Superior','Laboratorio',region,'2027-2028',opener=mock_open)
                self.assertEqual(result['count'],1)
                self.assertEqual(result['territory'],region)
                self.assertIn('no acredita su implantación',result['notice'])

    def test_title_classes_for_each_grade(self):
        samples={
          'Básico':'Título Profesional Básico en Servicios Administrativos',
          'Medio':'Técnico en Gestión Administrativa',
          'Superior':'Técnico Superior en Administración y Finanzas',
          'Especialización':'Curso de Especialización en Big Data e Inteligencia Artificial',
        }
        for grade,title in samples.items():
            with self.subTest(grade=grade):
                html=f'<h1>Listado</h1><a href="/que-estudiar/familias-profesionales/administracion-gestion/formacion.html">{title}</a>'
                report=index.parse_index(html,index.INDICES[grade],grade)
                self.assertEqual(report['count'],1)
        self.assertFalse(index._is_title('Técnico en Gestión Administrativa','Superior'))

    def test_bad_urls_and_years_rejected_before_http_request(self):
        failures=[('Supremo','A','Canarias','2026-2027'),('Superior','A','Madrid','2025-2025'),
                  ('Superior','A','Región falsa','2026-2027'),('Superior','X'*200,'Canarias','2026-2027')]
        for grade,query,region,year in failures:
            with self.subTest(grade=grade,region=region),self.assertRaises(ValueError):
                index.search(grade,query,region,year,opener=mock_open)
        with self.assertRaisesRegex(ValueError,'fuente no corresponde'):
            index.parse_index(GRADE_HTML,index.INDICES['Medio'],'Superior')

    def test_redirect_or_truncated_page_never_becomes_valid_index(self):
        def redirect(req,timeout):return MockHTTP('https://www.todofp.es/que-estudiar/grados-d/grado-medio.html')
        with self.assertRaisesRegex(ValueError,'redirigido'):
            index.search('Superior','', 'Galicia','2026-2027',opener=redirect)
        thousands=''.join(f'<a href="/que-estudiar/familias-profesionales/familia/titulo-{i}.html">Técnico Superior en Título {i}</a>' for i in range(405))
        with self.assertRaisesRegex(ValueError,'supera el número esperado'):
            index.parse_index(thousands,index.INDICES['Superior'],'Superior')

    def test_ui_and_api_endpoints_connected(self):
        root=Path(__file__).resolve().parents[1]
        js=(root/'web/app.js').read_text(encoding='utf-8')
        app=(root/'app.py').read_text(encoding='utf-8')
        self.assertIn('/api/national/todofp/search-titles',app)
        for action in ('todofp-search-titles','todofp-open-title'):
            self.assertIn("action==='"+action+"'",js)
        self.assertIn('S.todofpTitleSearch=null',js)

if __name__=='__main__':unittest.main()
