"""Pruebas con enunciados artificiales y recuentos de la publicación original."""
import unittest
from unittest.mock import patch, MagicMock
import curriculum_official as co


def fixture(name,code,counts):
    lines=[f'Módulo Profesional: {name}. Código: {code}',
           'Resultados de aprendizaje y criterios de evaluación']
    for i,count in enumerate(counts,1):
        lines += [f'{i}. Resultado de prueba {i}.','Criterios de evaluación:']
        lines += [f'{chr(97+j)}) Criterio artificial de prueba {i}-{j}.' for j in range(count)]
    return '\n'.join(lines+['Duración: 60 horas.','Contenidos básicos'])


def response(text):
    mock=MagicMock()
    mock.__enter__.return_value=mock
    mock.headers.get_content_charset.return_value='utf-8'
    mock.read.return_value=text.encode('utf-8')
    return mock


class CanaryAccountingCurriculumTests(unittest.TestCase):
    def test_complete_original_source(self):
        for name,code,counts in [
            ('Técnica Contable','0441',(7,9,9,7,9)),
            ('Tratamiento de la documentación contable','0443',(7,8,9,10)),
        ]:
            with self.subTest(code=code),patch('curriculum_official.urllib.request.urlopen',
                    return_value=response(fixture(name,code,counts))) as fetch:
                result=co.fetch_official(name,consent=True)
                self.assertEqual(result['module_code'],code)
                self.assertEqual(result['reference_coverage']['expected_ce'],sum(counts))
                self.assertTrue(result['reference_coverage']['complete_for_original_source'])
                self.assertFalse(result['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertEqual([len(r['criteria']) for r in result['outcomes']],list(counts))
                self.assertTrue(all(r['weight'] is None and
                    all(c['weight'] is None for c in r['criteria']) for r in result['outcomes']))
                self.assertIn('BOE-A-2009-19148',fetch.call_args.args[0].full_url)

    def test_partial_source_rejected(self):
        name='Tratamiento de la documentación contable'
        with patch('curriculum_official.urllib.request.urlopen',
                   return_value=response(fixture(name,'0443',(7,8,8,10)))):
            with self.assertRaisesRegex(ValueError,'CE consecutivos'):
                co.fetch_official(name,consent=True)

    def test_duplicate_labels_rejected(self):
        name='Técnica Contable'
        text=fixture(name,'0441',(7,9,9,7,9)).replace(
            'b) Criterio artificial de prueba 1-1.','a) Criterio artificial de prueba 1-1.')
        with patch('curriculum_official.urllib.request.urlopen',return_value=response(text)):
            with self.assertRaises(ValueError):
                co.fetch_official(name,consent=True)

    def test_alternative_source_checks_known_module_code(self):
        name='Técnica Contable'
        with patch('curriculum_official.urllib.request.urlopen',
                   return_value=response(fixture(name,'9999',(7,9,9,7,9)))):
            with self.assertRaisesRegex(ValueError,'código'):
                co.fetch_official(name,'BOE-A-2024-1',consent=True)

    def test_blank_identifier_unknown_module(self):
        with self.assertRaises(ValueError):
            co.fetch_official('Optativa',' ',consent=True)
