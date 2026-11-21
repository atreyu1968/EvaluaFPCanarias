"""Regresiones con fuentes sintéticas y recuentos cotejados en el BOE."""
import unittest
from unittest.mock import patch
import curriculum_official as co
from test_canarias_finance_curriculum import response

MODULES = [
    ('3159', 'itinerario personal para la empleabilidad', 'BOE-A-2023-16889', (5, 5, 3, 3, 4), (co.GB_CYCLE,)),
    ('1709', 'itinerario personal para la empleabilidad i', 'BOE-A-2023-16889', (3, 9, 7, 11, 9), (co.GA_CYCLE, co.AF_CYCLE, co.AD_CYCLE)),
    ('1710', 'itinerario personal para la empleabilidad ii', 'BOE-A-2023-16889', (4, 7, 6, 9, 9), (co.GA_CYCLE, co.AF_CYCLE, co.AD_CYCLE)),
    ('1664', 'digitalizacion aplicada a los sectores productivos (gm)', 'BOE-A-2023-16889', (6, 6, 5, 8, 8), (co.GA_CYCLE,)),
    ('1665', 'digitalizacion aplicada a los sectores productivos (gs)', 'BOE-A-2023-16889', (7, 7, 5, 6, 9, 11), (co.AF_CYCLE, co.AD_CYCLE)),
    ('1708', 'sostenibilidad aplicada al sistema productivo', 'BOE-A-2023-16889', (6, 5, 3, 6, 9, 5), (co.GA_CYCLE, co.AF_CYCLE, co.AD_CYCLE)),
    ('0156', 'ingles profesional (gm)', 'BOE-A-2023-16889', (9, 9, 13, 10, 5), (co.GA_CYCLE,)),
    ('0179', 'ingles profesional (gs)', 'BOE-A-2023-16889', (8, 10, 11, 8, 6), (co.AF_CYCLE, co.AD_CYCLE)),
    ('3160', 'proyecto intermodular de aprendizaje colaborativo', 'BOE-A-2024-10683', (9, 5, 5, 4, 4), (co.GB_CYCLE,)),
    ('1713', 'proyecto intermodular', 'BOE-A-2024-10684', (9, 11, 9, 6, 4), (co.GA_CYCLE,)),
    ('0657', 'proyecto de administracion y finanzas', 'BOE-A-2011-19533', (9, 9, 8, 7), (co.AF_CYCLE,)),
    ('0664', 'proyecto de asistencia a la direccion', 'BOE-A-2011-19531', (9, 9, 8, 7), (co.AD_CYCLE,)),
]

def fixture(name, code, counts, duplicated=False):
    lines = [f'Módulo Profesional: {name}.',
             'Equivalencia en créditos ECTS (en ciclos formativos de grado superior): 5.',
             'Duración: 50 horas.', f'Código: {code}.',
             'Resultados de aprendizaje y criterios de evaluación:']
    for i,count in enumerate(counts,1):
        lines.append(f'{i}. Resultado sintético {i}. Criterios de evaluación:')
        for j in range(count):
            letter=chr(97+j)
            if duplicated and i==5:
                letter='aabc'[j]
            lines.append(f'{letter}) Criterio sintético {i}-{j}.')
    lines.extend(['ANEXO XI','Texto ajeno que no debe añadirse al último criterio.'])
    return '<html><body>'+''.join(f'<p>{line}</p>' for line in lines)+'</body></html>'

class CanaryTransversalTests(unittest.TestCase):
    def test_recovery_for_all_levels(self):
        for code,name,source,counts,cycles in MODULES:
            for cycle in cycles:
                with self.subTest(code=code,cycle=cycle):
                    hint=co.source_hint(name,cycle)
                    self.assertEqual(hint['module_code'],code)
                    self.assertEqual(hint['boe_id'],source)
                    with patch('curriculum_official.urllib.request.urlopen',
                               return_value=response(fixture(name,code,counts))):
                        data=co.fetch_official(name,consent=True,cycle=cycle)
                    self.assertEqual(data['reference_coverage']['criteria_per_ra'],list(counts))
                    self.assertFalse(data['reference_coverage']['territorial_curriculum_confirmed'])
                    self.assertNotIn('Texto ajeno',str(data['outcomes']))
                    self.assertNotIn('Criterios de evaluación:',str(data['outcomes']))

    def test_project_original_duplicate_blocked(self):
        with patch('curriculum_official.urllib.request.urlopen',
                   return_value=response(fixture('Proyecto intermodular','1713',(9,11,9,6,4),True))):
            with self.assertRaisesRegex(ValueError,'repite a'):
                co.fetch_official('Proyecto intermodular',consent=True,cycle=co.GA_CYCLE)

    def test_new_project_names(self):
        self.assertEqual(co.source_hint('Proyecto intermodular de Administración y Finanzas',co.AF_CYCLE)['module_code'],'0657')
        self.assertEqual(co.source_hint('Proyecto intermodular de Asistencia a la Dirección',co.AD_CYCLE)['module_code'],'0664')
        self.assertEqual(co.source_hint('Proyecto intermodular de aprendizaje colaborativo (GB)',co.GB_CYCLE)['module_code'],'3160')

    def test_wrong_level_or_old_source_rejected(self):
        with patch('curriculum_official.urllib.request.urlopen') as fetch:
            self.assertIsNone(co.source_hint('Inglés profesional (GM)',co.AF_CYCLE))
            with self.assertRaisesRegex(ValueError,'otro nivel'):
                co.fetch_official('Inglés profesional (GM)','BOE-A-2023-16889',True,co.AF_CYCLE)
            with self.assertRaisesRegex(ValueError,'disposición específica'):
                co.fetch_official('Inglés profesional (GM)','BOE-A-2009-19148',True,co.GA_CYCLE)
            fetch.assert_not_called()
