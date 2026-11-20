"""Pruebas estaticas del preparador portable (el BAT requiere Windows)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'scripts' / 'preparar_entorno.ps1').read_text(encoding='utf-8-sig')

class BootstrapTests(unittest.TestCase):
    def test_uv_is_pinned_and_checksum_is_checked(self):
        self.assertIn('uv-x86_64-pc-windows-msvc.zip', SCRIPT)
        self.assertIn("$UvVersion = '0.13.7'", SCRIPT)
        self.assertIn('0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021', SCRIPT)
        self.assertIn('Get-FileHash', SCRIPT)
        self.assertIn('$actual -ne $UvSha', SCRIPT)
        self.assertIn('Expand-Archive', SCRIPT)

    def test_uv_manages_python_without_system_installer(self):
        self.assertIn('UV_PYTHON_INSTALL_DIR', SCRIPT)
        self.assertIn('UV_PYTHON_INSTALL_BIN', SCRIPT)
        self.assertIn("@('python','install','3.13')", SCRIPT)
        self.assertIn("@('venv','--python','3.13','--managed-python',$VenvDir)", SCRIPT)
        self.assertNotIn('Start-Process -FilePath $Installer', SCRIPT)
        self.assertNotIn('python-3.14.10-amd64.exe', SCRIPT)

    def test_dependencies_and_error_reporting(self):
        self.assertIn("@('pip','install','--python',$Python,'-r'", SCRIPT)
        self.assertIn("@('pip','check','--python',$Python)", SCRIPT)
        self.assertIn('Start-Transcript', SCRIPT)
        self.assertIn('ScriptStackTrace', SCRIPT)
        self.assertIn('No se ha certificado ningun EXE ni instalador', SCRIPT)

    def test_powershell_51_compatibility_regression(self):
        self.assertIn('verificar_python.py', SCRIPT)
        self.assertIn('verificar_dependencias.py', SCRIPT)
        self.assertNotIn('& $Python -c', SCRIPT)
        self.assertNotIn('& $Exe -c', SCRIPT)
        self.assertTrue((ROOT / 'scripts' / 'verificar_python.py').exists())
        self.assertTrue((ROOT / 'scripts' / 'verificar_dependencias.py').exists())

    def test_compiler_tests_before_build_and_selftests(self):
        bat = (ROOT / 'crear_exe_windows.bat').read_text(encoding='utf-8').lower()
        self.assertLess(bat.index('preparar_entorno.bat'), bat.index('unittest discover'))
        self.assertLess(bat.index('unittest discover'), bat.index('pyinstaller --noconfirm'))
        self.assertLess(bat.index('pyinstaller --noconfirm'), bat.index('--selftest'))
        self.assertIn('if errorlevel 1 goto :error', bat)
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('def selftest()', app)
        self.assertIn("'--selftest' in sys.argv", app)

if __name__ == '__main__':
    unittest.main()
