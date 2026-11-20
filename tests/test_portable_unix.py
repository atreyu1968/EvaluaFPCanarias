"""El arranque portátil no debe depender del motor WebView2 de Windows."""
import json
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app


class UnixDesktopTests(unittest.TestCase):
    def test_linux_uses_qt_renderer(self):
        fake=types.SimpleNamespace(create_window=MagicMock(),start=MagicMock())
        with patch.dict(sys.modules,{'webview':fake}),patch.object(app.sys,'platform','linux'):
            app.run_desktop_window('http://127.0.0.1:1/')
        self.assertEqual(fake.start.call_args.kwargs['gui'],'qt')

    def test_macos_uses_native_cocoa(self):
        fake=types.SimpleNamespace(create_window=MagicMock(),start=MagicMock())
        with patch.dict(sys.modules,{'webview':fake}),patch.object(app.sys,'platform','darwin'):
            app.run_desktop_window('http://127.0.0.1:1/')
        self.assertNotIn('gui',fake.start.call_args.kwargs)

    def test_portable_config_outside_mac_app(self):
        import storage_config
        with TemporaryDirectory() as t:
            root=Path(t)
            exe=root/'EvaluaFP_Portatil.app'/'Contents'/'MacOS'/'EvaluaFP_Portatil'
            exe.parent.mkdir(parents=True)
            exe.touch()
            with patch.object(storage_config.sys,'platform','darwin'),\
                 patch.object(storage_config.sys,'frozen',True,create=True),\
                 patch.object(storage_config.sys,'executable',str(exe)),\
                 patch.dict('os.environ',{'EVALUAFP_PORTABLE_HOME':''}):
                self.assertEqual(storage_config._application_home().resolve(),root.resolve())

    def test_explicit_portable_home_is_relative_to_usb(self):
        import storage_config
        with TemporaryDirectory() as t:
            with patch.dict('os.environ',{'EVALUAFP_PORTABLE_HOME':t}):
                self.assertEqual(storage_config._application_home().resolve(),Path(t).resolve())

    def test_workflow_includes_three_architectures(self):
        s=(Path(__file__).resolve().parents[1]/'.github/workflows/portables-linux-macos.yml').read_text(encoding='utf-8')
        self.assertIn('ubuntu-22.04',s)
        self.assertIn('macos-15-intel',s)
        self.assertIn('macos-15',s)
        self.assertIn('actions/upload-artifact@v4',s)

if __name__ == '__main__': unittest.main()