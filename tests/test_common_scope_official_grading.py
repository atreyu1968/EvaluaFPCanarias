"""Pruebas sintéticas del lector de bloques y de la calificación orientativa."""
import unittest
from decimal import Decimal
import common_scope_official as source
import common_scope_grading as grading
from common_scopes import COMM, SCI


def block(n):
    return f"""Competencia específica {n}:
    Enunciado artificial de competencia.
    Descriptores operativos de las competencias clave. Perfil de salida.
    CCL1, CPSAA1
    Criterios de evaluación:
    {n}.1. Primer criterio artificial
    continuado en otra línea.
    CCL1,
    CPSAA1
    {n}.2. Segundo criterio artificial.
    CPSAA1
    Explicación del bloque competencial:
    Texto explicativo que no pertenece a los criterios.
    """


class OfficialScopeTests(unittest.TestCase):
    def test_blocks(self):
        result=source.parse_blocks('\n'.join(block(i) for i in range(1,12)),11)
        self.assertEqual(len(result),11)
        self.assertEqual(result[0]['criteria'][0]['description'],'Primer criterio artificial continuado en otra línea.')
        self.assertEqual(result[0]['criteria'][0]['descriptors'],'CCL1, CPSAA1')
        self.assertEqual(result[-1]['criteria'][-1]['code'],'11.2')
        self.assertNotIn('Texto explicativo',str(result))

    def test_partial_or_mixed_rejected(self):
        with self.assertRaises(ValueError):
            source.parse_blocks(block(1),2)
        with self.assertRaises(ValueError):
            source.parse_blocks(block(1).replace('1.2.','1.3.'),1)
        with self.assertRaises(ValueError):
            source.parse_blocks(block(1).replace('continuado en otra línea.','continuado CCL1 en otra línea.'),1)

    def test_consent_required(self):
        with self.assertRaises(ValueError):
            source.fetch({'ambito':COMM},False)


class ScopeGradeTests(unittest.TestCase):
    def test_same_mean_distinct_outcome(self):
        matters=[{'matter':'lengua_social','grade':'BI','hours':4},
                 {'matter':'extranjera','grade':'IN','hours':2}]
        normal=grading.calculate(COMM,1,'ordinaria',matters,True)
        extra=grading.calculate(COMM,1,'extraordinaria',matters,True)
        self.assertEqual(Decimal(normal['mean']),5)
        self.assertFalse(normal['passed'])
        self.assertTrue(extra['passed'])
        self.assertIsNone(extra['official_grade'])

    def test_all_positive(self):
        result=grading.calculate(SCI,2,'ordinaria',[
            {'matter':'matematicas_ciencias','grade':'NT','hours':4}],True)
        self.assertTrue(result['passed'])
        self.assertEqual(Decimal(result['mean']),Decimal('7.5'))

    def test_missing_duplicate_and_unconfirmed(self):
        row={'matter':'lengua_social','grade':'BI','hours':4}
        for rows,confirmed in [([row],True),([row,row],True),([row],False)]:
            with self.assertRaises(ValueError):
                grading.calculate(COMM,1,'extraordinaria',rows,confirmed)

    def test_no_rounding_to_pass(self):
        matters=[{'matter':'lengua_social','grade':'BI','hours':3.9999},
                 {'matter':'extranjera','grade':'IN','hours':2}]
        result=grading.calculate(COMM,1,'extraordinaria',matters,True)
        self.assertLess(Decimal(result['mean']),5)
        self.assertFalse(result['passed'])
