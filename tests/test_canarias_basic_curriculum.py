"""Pruebas de Servicios Administrativos. Los recuentos se cotejaron con
BOE-A-2014-2360, anexo I; los enunciados de prueba son artificiales.
"""
import unittest
from unittest.mock import patch
import curriculum_official as co
from test_canarias_finance_curriculum import response

MODULES = [
    ('3001', 'Tratamiento informático de datos', (7, 10, 7, 10)),
    ('3002', 'Aplicaciones básicas de ofimática', (7, 7, 6, 6)),
    ('3003', 'Técnicas administrativas básicas', (5, 9, 9, 8)),
    ('3004', 'Archivo y comunicación', (9, 10, 8, 8)),
    ('3005', 'Atención al cliente', (9, 8, 8, 6)),
    ('3006', 'Preparación de pedidos y venta de productos', (6, 7, 6, 6)),
]


def block(name, code, counts):
    parts=[f'Módulo Profesional: {name}.',f'Código: {code}',
           'Resultados de aprendizaje y criterios de evaluación.']
    for i,count in enumerate(counts,1):
        parts.extend([f'{i}. Resultado artificial {i}.','Criterios de evaluación:'])
        parts.extend(f'{chr(97+j)}) Criterio artificial {i}-{j}.' for j in range(count))
    parts.extend(['Duración: 40 horas.', 'Contenidos básicos.'])
    return ''.join(f'<p>{p}</p>' for p in parts)


def document(entries, other_annex=''):
    return ('<!DOCTYPE html><html><body><h3>ANEXO I</h3>'
            '<h3>Título Profesional Básico en Servicios Administrativos</h3>'
            + ''.join(block(name,code,counts) for code,name,counts in entries)
            + '<h3>ANEXO II</h3><h3>Otro título</h3>' + other_annex + '</body></html>')


class CanaryBasicCurriculumTests(unittest.TestCase):
    def test_all_professional_modules_are_indexed_and_retrievable(self):
        self.assertEqual(len(co.GB_SUPPORTED),6)
        self.assertEqual(sum(len(c) for _,_,c in MODULES),24)
        self.assertEqual(sum(sum(c) for _,_,c in MODULES),182)
        for code,name,counts in MODULES:
            with self.subTest(code=code):
                hint=co.source_hint(name,co.GB_CYCLE)
                self.assertEqual(hint['boe_id'],'BOE-A-2014-2360')
                with patch('curriculum_official.urllib.request.urlopen',
                           return_value=response(document(MODULES))) as request:
                    data=co.fetch_official(name,consent=True,cycle=co.GB_CYCLE)
                self.assertIn('BOE-A-2014-2360',request.call_args.args[0].full_url)
                self.assertEqual(data['module_code'],code)
                self.assertEqual(data['reference_coverage']['criteria_per_ra'],list(counts))
                self.assertFalse(data['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertIn('/2023/025/001.html',data['verification_links']['canarias_curriculum'])
                self.assertIn('/498',data['verification_links']['state_amendment'])
                self.assertTrue(all(c['weight'] is None for r in data['outcomes'] for c in r['criteria']))

    def test_other_annex_cannot_supply_missing_module(self):
        code,name,counts=MODULES[0]
        doc=document(MODULES[1:],other_annex=block(name,code,counts))
        with patch('curriculum_official.urllib.request.urlopen',return_value=response(doc)):
            with self.assertRaisesRegex(ValueError,'encabezado acreditado'):
                co.fetch_official(name,consent=True,cycle=co.GB_CYCLE)

    def test_other_annex_cannot_replace_incomplete_module(self):
        code,name,counts=MODULES[0]
        incomplete=[(code,name,counts[:-1]+(counts[-1]-1,))]+MODULES[1:]
        doc=document(incomplete,other_annex=block(name,code,counts))
        with patch('curriculum_official.urllib.request.urlopen',return_value=response(doc)):
            with self.assertRaisesRegex(ValueError,'CE consecutivos'):
                co.fetch_official(name,consent=True,cycle=co.GB_CYCLE)

    def test_missing_annex_boundary_rejected(self):
        with self.assertRaisesRegex(ValueError,'límite'):
            co.basic_services_annex('ANEXO I\nTítulo Profesional Básico en Servicios Administrativos\nContenido sin límite.')

    def test_scopes_and_obsolete_modules_are_not_suggested(self):
        for name in ('Formación en centros de trabajo','Comunicación y sociedad I',
                     'Ciencias aplicadas I','Lengua castellana y Ciencias sociales',
                     'Matemáticas y Ciencias aplicadas','Itinerario personal para la empleabilidad'):
            self.assertIsNone(co.source_hint(name,co.GB_CYCLE))
        self.assertIsNone(co.source_hint('Técnica contable',co.GB_CYCLE))
        with patch('curriculum_official.urllib.request.urlopen') as get:
            with self.assertRaisesRegex(ValueError,'otro ciclo'):
                co.fetch_official(MODULES[0][1],'BOE-A-2009-19148',True,co.GB_CYCLE)
            get.assert_not_called()
