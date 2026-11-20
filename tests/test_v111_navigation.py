"""Regresión: el menú de preparación no debe quedarse en «Cargando…»."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class GuidedNavigationRegressionTests(unittest.TestCase):
    def test_prepare_route_invokes_its_view(self):
        js=(ROOT/'web/app.js').read_text(encoding='utf-8')
        start=js.index('async function page(name){')
        end=js.index('async function listModules(){',start)
        router=js[start:end]
        self.assertIn("if(name==='preparar')await viewPrepare();",router)
        self.assertIn("if(!supported.includes(name))throw Error",router)
        self.assertIn('async function viewPrepare(){',js)

    def test_guided_module_create_and_upload_are_wired(self):
        js=(ROOT/'web/app.js').read_text(encoding='utf-8')
        self.assertIn("if(id==='prepare-create'){",js)
        self.assertIn("if(id==='guided-upload'){",js)
        self.assertIn("await page('preparar')",js)
        self.assertIn("data-page=\"preparar\"",(ROOT/'web/index.html').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
