"""Regresión de recuperación del anexo I original de Administración y Finanzas.

Recuentos cotejados con BOE-A-2011-19533. Enunciados artificiales en las
pruebas; no constituyen una copia ni una validación del currículo vigente.
"""
import unittest
from unittest.mock import patch, MagicMock
import curriculum_official as co


MODULES = [
    ('0647', 'Gestión de la documentación jurídica y empresarial', (6, 7, 8, 8, 11)),
    ('0648', 'Recursos humanos y responsabilidad social corporativa', (6, 5, 8, 8, 10)),
    ('0649', 'Ofimática y proceso de la información', (8, 10, 11, 10, 8, 8, 5, 10, 6)),
    ('0650', 'Proceso integral de la actividad comercial', (7, 9, 9, 9, 6, 10, 10)),
    ('0651', 'Comunicación y atención al cliente', (10, 10, 11, 11, 7, 10, 10)),
    ('0652', 'Gestión de recursos humanos', (9, 6, 8, 10)),
    ('0653', 'Gestión financiera', (7, 7, 9, 8, 7, 8)),
    ('0654', 'Contabilidad y fiscalidad', (8, 10, 10, 11, 7, 9)),
    ('0655', 'Gestión logística y comercial', (10, 8, 8, 9, 8)),
    ('0656', 'Simulación empresarial', (7, 8, 9, 8, 9, 10)),
]


def fixture(name, code, counts, omit_period=False):
    lines = [f'Módulo Profesional: {name}.',
             'Equivalencia en créditos ECTS: 6',
             f'Código: {code}',
             'Resultados de aprendizaje y criterios de evaluación.']
    for i, count in enumerate(counts, 1):
        period = '' if omit_period and i == 4 else '.'
        lines += [f'{i}{period} Resultado artificial de prueba {i}.',
                  'Criterios de evaluación:']
        lines += [f'{chr(97+j)}) Criterio artificial de prueba {i}-{j}.' for j in range(count)]
    lines += ['Duración: 60 horas.', 'Contenidos básicos:',
              'Módulo Profesional: Otro módulo.', 'Equivalencia en créditos ECTS: 5',
              'Código: 9999', 'Resultados de aprendizaje y criterios de evaluación.',
              '1. No pertenece al módulo.', 'a) Criterio ajeno.']
    return '<!DOCTYPE html><html><body>' + ''.join(f'<p>{line}</p>' for line in lines) + '</body></html>'


def response(text):
    r = MagicMock()
    r.__enter__.return_value = r
    r.headers.get_content_charset.return_value = 'utf-8'
    r.read.return_value = text.encode('utf-8')
    return r


class CanaryFinanceCurriculumTests(unittest.TestCase):
    def test_catalogue_and_complete_extraction_for_all_modules(self):
        self.assertEqual(len(co.AF_SUPPORTED),10)
        self.assertEqual(sum(len(c) for _,_,c in MODULES),60)
        self.assertEqual(sum(sum(c) for _,_,c in MODULES),510)
        for code, name, counts in MODULES:
            with self.subTest(code=code):
                hint=co.source_hint(name, co.AF_CYCLE)
                self.assertEqual(hint['boe_id'],'BOE-A-2011-19533')
                self.assertEqual(hint['expected_ce'],sum(counts))
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(fixture(name,code,counts,code=='0651'))) as request:
                    result=co.fetch_official(name,consent=True,cycle=co.AF_CYCLE)
                self.assertIn('BOE-A-2011-19533',request.call_args.args[0].full_url)
                self.assertEqual(result['module_code'],code)
                self.assertEqual([len(r['criteria']) for r in result['outcomes']],list(counts))
                self.assertTrue(result['reference_coverage']['complete_for_original_source'])
                self.assertFalse(result['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertIn('/1584/con',result['verification_links']['state_title'])
                self.assertIn('/500',result['verification_links']['state_amendment'])
                self.assertEqual(len(result['source_sha256']),64)
                self.assertNotIn('Criterio ajeno',str(result['outcomes']))
                self.assertTrue(all(r['weight'] is None and
                                    all(c['weight'] is None for c in r['criteria'])
                                    for r in result['outcomes']))

    def test_truncated_last_ra_rejected_for_each_module(self):
        for code,name,counts in MODULES:
            with self.subTest(code=code):
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(fixture(name,code,counts[:-1]+(counts[-1]-1,)))):
                    with self.assertRaises(ValueError):
                        co.fetch_official(name,consent=True,cycle=co.AF_CYCLE)

    def test_cycle_isolation_and_transversal_modules(self):
        name=MODULES[0][1]
        self.assertEqual(co.source_hint(name,co.AD_CYCLE)['boe_id'],'BOE-A-2011-19531')
        self.assertIsNone(co.source_hint(name,co.GA_CYCLE))
        self.assertIsNone(co.source_hint('Técnica Contable',co.AF_CYCLE))
        for name in ('Inglés profesional (GS)', 'Sostenibilidad aplicada al sistema productivo',
                     'Proyecto intermodular de administración y finanzas'):
            self.assertIsNone(co.source_hint(name,co.AF_CYCLE))
        with patch('curriculum_official.urllib.request.urlopen') as request:
            with self.assertRaisesRegex(ValueError,'otro ciclo'):
                co.fetch_official(MODULES[0][1], 'BOE-A-2011-19531', True, co.AF_CYCLE)
            request.assert_not_called()

    def test_reject_same_name_with_wrong_code(self):
        _,name,counts=MODULES[0]
        with patch('curriculum_official.urllib.request.urlopen',
                   return_value=response(fixture(name,'9999',counts))):
            with self.assertRaisesRegex(ValueError,'código'):
                co.fetch_official(name,consent=True,cycle=co.AF_CYCLE)
