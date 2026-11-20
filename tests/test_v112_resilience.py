"""Regression audit: every relevant route has a handler and the async UI fails visibly."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'web/app.js').read_text(encoding='utf-8')
HTML=(ROOT/'web/index.html').read_text(encoding='utf-8')

class NavigationResilienceTests(unittest.TestCase):
    def test_all_main_sections_are_routed(self):
        main_routes=['inicio','preparar','examenes','entregas','correcciones','evaluacion']
        advanced_routes=['programaciones','ajustes']
        for route in main_routes+advanced_routes:
            with self.subTest(route=route):
                self.assertIn('data-page="'+route+'"',HTML)
                self.assertIn("if(name==='"+route+"')await view",JS)
        self.assertIn('if(!supported.includes(name))throw Error',JS)

    def test_all_literal_data_actions_have_handlers(self):
        actions=set(re.findall(r'data-action=["\']([a-z][\w-]+)["\']',JS))
        handlers=set(re.findall(r"action==='([^']+)'",JS))
        self.assertGreater(len(actions),30)
        self.assertFalse(actions-handlers,f'Sin controlador: {actions-handlers}')
        self.assertIn('retry-page',handlers)

    def test_requests_cannot_wait_indefinitely(self):
        self.assertIn('AbortController',JS)
        self.assertIn('clearTimeout(timer)',JS)
        self.assertIn("controller.abort('timeout')",JS)
        self.assertIn('navigationController.abort',JS)
        self.assertIn('revision!==navigationRevision',JS)

    def test_failures_have_visible_retry_path(self):
        self.assertIn('No se ha podido abrir esta pantalla',JS)
        self.assertIn('data-action="retry-page"',JS)
        self.assertIn('Error al actualizar la selección.',JS)
        self.assertIn('Error al realizar la acción.',JS)

    def test_unit_generation_cannot_reuse_existing_code(self):
        self.assertIn('const used=new Set(',JS)
        self.assertIn('while(used.has(',JS)
        self.assertIn('prepare-remove-unit',JS)

    def test_actions_use_matched_element_not_event_child(self):
        self.assertIn("const active=el.dataset.active==='1'",JS)
        self.assertNotIn("const active=event.target.dataset.active==='1'",JS)

if __name__=='__main__':unittest.main()
