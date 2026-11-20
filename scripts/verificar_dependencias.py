"""Comprueba importacion real de dependencias y herramientas de compilacion."""
import argparse
import importlib
import struct
import sys
import traceback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    modules = ("fitz", "PIL", "docx", "keyring", "sqlite3", "xlsxwriter", "xlwt")
    if sys.platform == "win32":
        modules += ("webview", "clr_loader", "pythonnet")
    if args.build:
        modules += ("PyInstaller",)
    for name in modules:
        module = importlib.import_module(name)
        print("OK", name, getattr(module, "__version__", ""), flush=True)
    assert sys.version_info[:2] == (3, 13)
    assert struct.calcsize("P") == 8
    print("VALIDACION OK: bibliotecas y arquitectura", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
