"""Regresión de extracción autonómica mediante documentos sintéticos."""
import unittest
from unittest.mock import patch
import canarias_curriculum as c
from test_canarias_finance_curriculum import response

def section(name,code,hours,counts):
    lines=[f'Módulo Profesional: {name}.']
    if code=='3160':
        lines += [f'Código: {code}.',f'Duración: {hours} horas.']
    else:
        lines += [f'Duración: {hours} horas.']
        if code:
            lines.append(f'Código: {code}.')
    lines.append('Resultados de aprendizaje y criterios de evaluación.')
    for i,n in enumerate(counts,1):
        lines.extend([f'{i}. Resultado artificial {i}.','Criterios de evaluación:'])
        lines.extend(f'{chr(97+j)}) Criterio artificial {i}-{j}.' for j in range(n))
    return ''.join(f'<p>{l}</p>' for l in lines)

def fixture():
    return ('<!DOCTYPE html><html><body><h2>ANEXO V</h2>'
        + section('Itinerario personal para la empleabilidad','3159',66,(5,5,3,3,4))
        + '<h2>CURRÍCULO BÁSICO</h2>'
        + section('Prevención y salud laboral',None,33,(6,6,5,3,7))
        + '<p>Contenidos.</p><p>1. No es un RA.</p>'
        + section('Proyecto intermodular de aprendizaje colaborativo','3160',66,(9,5,5,4,4))
        + '<h2>ANEXO VI</h2>'
        + section('Proyecto intermodular','1713',64,(9,11,9,6,4))
        + '<p>© Gobierno de Canarias</p></body></html>')

class CanaryRegionalCurriculumTests(unittest.TestCase):
    def test_all_four_curricula(self):
        self.assertEqual(len(c.REGISTRY),4)
        for (cycle,name),(code,annex,hours,counts) in c.REGISTRY.items():
            with self.subTest(name=name):
                result=c.parse(fixture(),name,cycle)
                self.assertEqual(result['module_code'],code)
                self.assertEqual(result['reference_coverage']['expected_ce'],sum(counts))
                self.assertFalse(result['reference_coverage']['territorial_curriculum_confirmed'])
                self.assertNotIn('No es un RA',str(result))
                self.assertNotIn('Gobierno de Canarias',str(result['outcomes']))
        final=c.parse(fixture(),'Proyecto intermodular',c.GM)['outcomes'][-1]
        self.assertEqual([x['code'] for x in final['criteria']],['RA5.a','RA5.b','RA5.c','RA5.d'])

    def test_reject_mismatch_and_wrong_cycle(self):
        with self.assertRaises(ValueError):
            c.parse(fixture().replace('Duración: 33 horas.','Duración: 32 horas.'),'Prevención y salud laboral',c.GB)
        self.assertIsNone(c.hint('Proyecto intermodular',c.GB))
        with self.assertRaises(ValueError):
            c.parse(fixture(),'Proyecto intermodular',c.GB)

    def test_fixed_source_and_consent(self):
        with patch('canarias_curriculum.urllib.request.urlopen',return_value=response(fixture())) as get:
            with self.assertRaises(ValueError):
                c.fetch('Proyecto intermodular',c.GM)
            get.assert_not_called()
            result=c.fetch('Proyecto intermodular',c.GM,True)
            self.assertEqual(get.call_args.args[0].full_url,c.SOURCE_URL)
            self.assertEqual(result['source'],'BOC')
            self.assertEqual(len(result['source_sha256']),64)
