"""Pruebas de Asistencia a la Dirección con textos sintéticos.
Los recuentos se han contrastado con BOE-A-2011-19531 (anexo I original).
"""
import unittest
from unittest.mock import patch
import curriculum_official as co
from test_canarias_finance_curriculum import fixture, response

MODULES = [
    ('0647', 'Gestión de la documentación jurídica y empresarial', (6, 7, 8, 8, 11)),
    ('0648', 'Recursos humanos y responsabilidad social corporativa', (6, 5, 8, 8, 10)),
    ('0649', 'Ofimática y proceso de la información', (8, 10, 11, 10, 8, 8, 5, 10, 6)),
    ('0650', 'Proceso integral de la actividad comercial', (7, 9, 9, 9, 6, 10, 10)),
    ('0651', 'Comunicación y atención al cliente', (10, 10, 11, 11, 7, 10, 10)),
    ('0180', 'Segunda lengua extranjera', (7, 7, 9, 7, 6)),
    ('0661', 'Protocolo empresarial', (7, 11, 11, 10, 8, 10)),
    ('0662', 'Organización de eventos empresariales', (11, 8, 9, 10, 8)),
    ('0663', 'Gestión avanzada de la información', (7, 8, 9, 7, 9)),
]


class CanaryDirectionCurriculumTests(unittest.TestCase):
    def test_all_modules_use_their_own_title(self):
        self.assertEqual(len(co.AD_SUPPORTED),9)
        self.assertEqual(sum(len(c) for _,_,c in MODULES),54)
        self.assertEqual(sum(sum(c) for _,_,c in MODULES),461)
        for code,name,counts in MODULES:
            with self.subTest(code=code):
                hint=co.source_hint(name,co.AD_CYCLE)
                self.assertEqual(hint['boe_id'],'BOE-A-2011-19531')
                self.assertEqual(hint['expected_ce'],sum(counts))
                doc=fixture(name,code,counts,code=='0651')
                # 0662 usa también la variante con punto en el rótulo de CE.
                doc=doc.replace('Criterios de evaluación:', 'Criterios de evaluación.')
                with patch('curriculum_official.urllib.request.urlopen',return_value=response(doc)) as get:
                    result=co.fetch_official(name,consent=True,cycle=co.AD_CYCLE)
                self.assertIn('BOE-A-2011-19531',get.call_args.args[0].full_url)
                self.assertEqual(result['module_code'],code)
                self.assertEqual(result['reference_coverage']['criteria_per_ra'],list(counts))
                self.assertFalse(result['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertNotIn('Criterios de evaluación',str(result['outcomes']))
                self.assertIn('/1582/con',result['verification_links']['state_title'])
                self.assertTrue(all(ra['weight'] is None and all(c['weight'] is None for c in ra['criteria'])
                                    for ra in result['outcomes']))

    def test_shared_modules_require_cycle_or_explicit_title(self):
        code,name,counts=MODULES[0]
        self.assertIsNone(co.source_hint(name))
        with patch('curriculum_official.urllib.request.urlopen') as request:
            with self.assertRaisesRegex(ValueError,'identificador'):
                co.fetch_official(name,consent=True)
            with self.assertRaisesRegex(ValueError,'otro ciclo'):
                co.fetch_official(name,'BOE-A-2011-19533',True,co.AD_CYCLE)
            request.assert_not_called()
        with patch('curriculum_official.urllib.request.urlopen',return_value=response(fixture(name,code,counts))):
            result=co.fetch_official(name,'BOE-A-2011-19531',True)
            self.assertEqual(result['module_code'],code)

    def test_incomplete_criteria_rejected_per_module(self):
        for code,name,counts in MODULES:
            with self.subTest(code=code):
                bad=counts[:-1]+(counts[-1]-1,)
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(fixture(name,code,bad))):
                    with self.assertRaises(ValueError):
                        co.fetch_official(name,consent=True,cycle=co.AD_CYCLE)

    def test_no_automatic_import_of_transversal_or_wrong_title(self):
        for name in ('Inglés profesional (GM)','Proyecto intermodular de administración y finanzas',
                     'Digitalización aplicada a los sectores productivos (GM)','Contabilidad y fiscalidad'):
            self.assertIsNone(co.source_hint(name,co.AD_CYCLE))
        self.assertIsNone(co.source_hint('Segunda lengua extranjera',co.AF_CYCLE))
        self.assertIsNone(co.source_hint('Protocolo empresarial',co.AF_CYCLE))
