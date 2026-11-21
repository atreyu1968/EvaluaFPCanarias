"""La landing de Canarias debe distinguir código y artefactos beta reales."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CanaryLandingTests(unittest.TestCase):
    def test_downloads_come_from_current_repository(self):
        html=(ROOT/"docs"/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="descargas"',html)
        self.assertIn('evaluafp-canarias',html.lower())
        self.assertIn('actions/runs/44909845819',html)
        self.assertIn('actions/runs/44909680492',html)
        self.assertIn('macOS · Intel y Apple Silicon',html)
        self.assertIn('Artifacts',html)
        self.assertNotIn('Versión 1.0.6',html)
        self.assertIn('sin firma',html)

if __name__=="__main__":
    unittest.main()
