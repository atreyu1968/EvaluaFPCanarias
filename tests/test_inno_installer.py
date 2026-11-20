"""Regresiones de la construcción del instalador en Windows."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InstallerContractTests(unittest.TestCase):
    def test_no_winget_in_active_installer(self):
        bat=(ROOT/'crear_instalador_windows.bat').read_text(encoding='utf-8')
        ps=(ROOT/'scripts/crear_instalador.ps1').read_text(encoding='utf-8-sig')
        self.assertNotIn('winget install', bat.lower())
        self.assertNotIn('winget install', ps.lower())
        self.assertIn('crear_instalador.ps1', bat)
        self.assertIn('comprobar_exe.ps1', bat)
        self.assertNotIn(' -Command ', bat)
    def test_inno_autenticode_and_official_sources(self):
        ps=(ROOT/'scripts/crear_instalador.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('Get-AuthenticodeSignature',ps)
        self.assertIn('Pyrsys B',ps)
        self.assertIn('github.com/jrsoftware/issrc/releases/',ps)
        self.assertIn('files.jrsoftware.org/is/6/',ps)
    def test_preserve_portable_exe_and_validate_output(self):
        bat=(ROOT/'crear_instalador_windows.bat').read_text(encoding='utf-8')
        ps=(ROOT/'scripts/crear_instalador.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('--selftest',bat)
        self.assertIn('Instalar_EvaluaFP.exe',ps)
        self.assertNotIn('Remove-Item -LiteralPath $Exe',ps)
    def test_iss_references_onefile_build_and_nonadmin_install(self):
        s=(ROOT/'instalador/EvaluaFP.iss').read_text(encoding='utf-8')
        self.assertIn('Source: "..\\dist\\EvaluaFP.exe"',s)
        self.assertIn('PrivilegesRequired=lowest',s)
if __name__=='__main__': unittest.main()
