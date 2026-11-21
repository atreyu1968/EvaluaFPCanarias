"""Regresión Windows: no decodificar fuentes UTF-8 con cp1252 al compilar."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WindowsUtf8BuildTests(unittest.TestCase):
    def test_all_test_source_reads_are_explicit_utf8(self):
        # La lectura implícita usaba cp1252 en Windows y fallaba al leer la Í de app.js.
        for file in sorted((ROOT/'tests').rglob('*.py')):
            tree = ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr == 'read_text':
                    self.assertTrue(any(k.arg=='encoding' for k in node.keywords),
                                    f'{file.name}:{node.lineno}: read_text requiere encoding explícito')

    def test_windows_build_forces_utf8(self):
        bat = (ROOT/'crear_exe_windows.bat').read_text(encoding='utf-8-sig')
        self.assertIn('set "PYTHONUTF8=1"', bat)
        self.assertIn('set "PYTHONIOENCODING=utf-8"', bat)
        self.assertIn('goto :tests_error', bat)

    def test_javascript_is_utf8_not_cp1252(self):
        content=(ROOT/'web/app.js').read_bytes()
        self.assertIn('ADMINISTRACIÓN Y GESTIÓN · CANARIAS'.encode('utf-8'), content)
        with self.assertRaises(UnicodeDecodeError):
            content.decode('cp1252')
        self.assertIn('ADMINISTRACIÓN Y GESTIÓN · CANARIAS',content.decode('utf-8'))

if __name__=='__main__':unittest.main()
