"""Pruebas de escritorio sin necesidad de Windows ni de WebView2 en CI."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


class DesktopTests(unittest.TestCase):
    def test_default_starts_native_window_not_browser(self):
        server=MagicMock()
        with patch.object(app, 'start', return_value=(server,'http://127.0.0.1:33333/')), \
             patch.object(app, 'run_desktop_window') as desktop, \
             patch.object(app, 'open_interface') as browser, \
             patch.object(sys, 'argv', ['EvaluaFP.exe']):
            app.main()
        desktop.assert_called_once_with('http://127.0.0.1:33333/')
        browser.assert_not_called()
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()

    def test_native_window_requests_edge_webview2(self):
        fake = types.SimpleNamespace(create_window=MagicMock(),start=MagicMock())
        with patch.dict(sys.modules, {'webview':fake}), patch.object(app.sys, 'platform', 'win32'):
            app.run_desktop_window('http://127.0.0.1:33333/')
        self.assertIn('EvalúaFP', fake.create_window.call_args.args[0])
        self.assertEqual(fake.start.call_count,1)
        self.assertEqual(fake.start.call_args.kwargs['gui'],'edgechromium')

    def test_native_failure_not_silently_redirected_to_browser(self):
        fake = types.SimpleNamespace(create_window=MagicMock(),start=MagicMock(side_effect=Exception('Runtime inexistente')))
        with patch.dict(sys.modules, {'webview':fake}), patch.object(app.sys, 'platform', 'win32'):
            with self.assertRaisesRegex(RuntimeError, 'WebView2 Runtime'):
                app.run_desktop_window('http://127.0.0.1:33333/')

    def test_packaging_includes_native_gui_and_mode_selector(self):
        req=(ROOT/'requirements.txt').read_text(encoding='utf-8')
        bat=(ROOT/'crear_exe_windows.bat').read_text(encoding='utf-8')
        start=(ROOT/'INICIAR_EVALUAFP.bat').read_text(encoding='utf-8')
        browser=(ROOT/'iniciar_navegador_windows.bat').read_text(encoding='utf-8')
        self.assertIn('pywebview==6.2.1', req)
        self.assertIn('--collect-all webview', bat)
        self.assertNotIn('app.py" --browser', start)
        self.assertIn('app.py" --browser', browser)


if __name__=='__main__':
    unittest.main()
