"""Controles de cobertura del anexo I original de Gestión Administrativa.

Los enunciados de los documentos de prueba son artificiales. El recuento
de cada RA se ha contrastado en https://www.boe.es/diario_boe/txt.php?id=BOE-A-2009-19148.
"""
import unittest
from unittest.mock import patch, MagicMock
import curriculum_official as co


MODULES = [
    ('0437', 'Comunicación empresarial y atención al cliente', (9, 10, 11, 10, 9, 10, 7, 10)),
    ('0438', 'Operaciones administrativas de compraventa', (9, 10, 7, 9, 8)),
    ('0439', 'Empresa y administración', (7, 6, 7, 8, 6, 10, 6)),
    ('0440', 'Tratamiento informático de la información', (10, 8, 7, 8, 7, 9, 6, 7)),
    ('0441', 'Técnica contable', (7, 9, 9, 7, 9)),
    ('0442', 'Operaciones administrativas de recursos humanos', (10, 10, 10, 9, 6, 5)),
    ('0443', 'Tratamiento de la documentación contable', (7, 8, 9, 10)),
    ('0446', 'Empresa en el aula', (6, 8, 6, 7, 6, 6, 10)),
    ('0448', 'Operaciones auxiliares de gestión de tesorería', (9, 10, 7, 9)),
]


def fixture(name, code, counts, suffix=''):
    lines = [f'Módulo Profesional: {name}.{suffix} Código: {code}',
             'Resultados de aprendizaje y criterios de evaluación']
    for i, count in enumerate(counts, 1):
        lines.extend([f'{i}. Resultado artificial número {i}.', 'Criterios de evaluación:'])
        for j in range(count):
            lines.append(f'{chr(97+j)}) Criterio ficticio {i}-{j}.')
    lines.extend(['Duración: 70 horas.', 'Contenidos básicos',
                  'Módulo Profesional: Otro módulo. Código: 9999',
                  'Resultados de aprendizaje y criterios de evaluación',
                  '1. No pertenece al módulo seleccionado.'])
    return '<html><body>' + ''.join(f'<p>{line}</p>' for line in lines) + '</body></html>'


def response(text):
    r = MagicMock()
    r.__enter__.return_value = r
    r.headers.get_content_charset.return_value = 'utf-8'
    r.read.return_value = text.encode('utf-8')
    return r


class CanaryManagementCurriculumTests(unittest.TestCase):
    def test_registry_excludes_old_transversal_modules(self):
        self.assertEqual(sum(source=='BOE-A-2009-19148' for source,code in co.EXPECTED_COVERAGE),9)
        self.assertEqual(sum(len(t[2]) for t in MODULES),54)
        self.assertEqual(sum(sum(t[2]) for t in MODULES),440)
        for name in ('Inglés','Inglés profesional (GM)','FOL','Itinerario personal para la empleabilidad I','Proyecto intermodular'):
            self.assertIsNone(co.source_hint(name))

    def test_every_registered_module_and_actual_heading_variants(self):
        for code, name, counts in MODULES:
            with self.subTest(code=code):
                header = 'Operaciones administrativas de compra-venta' if code == '0438' else name
                suffix = ' Equivalencia en créditos ECTS.' if code == '0446' else ''
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(fixture(header, code, counts, suffix))):
                    result = co.fetch_official(name, consent=True)
                self.assertEqual(result['module_code'], code)
                self.assertEqual([len(ra['criteria']) for ra in result['outcomes']],list(counts))
                self.assertEqual(result['reference_coverage']['expected_ce'],sum(counts))
                self.assertFalse(result['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertNotIn('No pertenece',str(result['outcomes']))
                self.assertEqual(co.source_hint(name)['boe_id'],'BOE-A-2009-19148')
                self.assertTrue(all(ce['weight'] is None for ra in result['outcomes']
                                    for ce in ra['criteria']))

    def test_last_criterion_missing_rejected_for_every_module(self):
        for code, name, counts in MODULES:
            with self.subTest(code=code):
                incomplete = counts[:-1] + (counts[-1]-1,)
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(fixture(name,code,incomplete))):
                    with self.assertRaises(ValueError):
                        co.fetch_official(name, consent=True)

    def test_name_variant_does_not_override_code_check(self):
        counts = MODULES[1][2]
        with patch('curriculum_official.urllib.request.urlopen',
                   return_value=response(fixture('Operaciones administrativas de compra-venta','9999',counts))):
            with self.assertRaisesRegex(ValueError,'código'):
                co.fetch_official('Operaciones administrativas de compraventa',consent=True)
