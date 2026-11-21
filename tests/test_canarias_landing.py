"""La landing de Canarias debe distinguir código y artefactos beta reales."""
from pathlib import Path
import unittest
import re

ROOT=Path(__file__).resolve().parents[1]

class CanaryLandingTests(unittest.TestCase):
    def test_downloads_come_from_current_repository(self):
        html=(ROOT/"docs"/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="descargas"',html)
        self.assertIn('atreyu1968/evaluafpcanarias',html.lower())
        # Las identificaciones de ejecución cambian con cada compilación.
        # Comprobar formato, repositorio propio y dos ejecuciones de compilación
        # evita que la actualización de enlaces válidos rompa la suite.
        runs=set(re.findall(
            r'https://github\.com/atreyu1968/EvaluaFPCanarias/actions/runs/(\d+)',
            html, flags=re.IGNORECASE
        ))
        self.assertGreaterEqual(len(runs),2)
        self.assertTrue(all(int(run)>0 for run in runs))
        self.assertIn('macOS · Intel y Apple Silicon',html)
        self.assertIn('Artifacts',html)
        self.assertNotIn('Versión 1.0.6',html)
        self.assertIn('sin firma',html)

if __name__=="__main__":
    unittest.main()
