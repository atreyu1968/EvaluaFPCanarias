"""Comprobacion real del Python del entorno, compatible con Windows PowerShell 5.1.

No usar `python -c` con comillas internas desde PowerShell 5.1.
"""
import platform
import struct
import sys
import traceback


def main():
    print("Ruta ejecutable:", sys.executable, flush=True)
    print("Version:", sys.version.splitlines()[0], flush=True)
    print("Arquitectura:", platform.machine(), struct.calcsize("P") * 8, "bits", flush=True)
    assert sys.implementation.name == "cpython", "El interprete no es CPython"
    assert sys.version_info[:2] == (3, 13), "Se necesita Python 3.13"
    assert struct.calcsize("P") == 8, "Se necesita Python x64"
    import sqlite3
    with sqlite3.connect(":memory:") as conn:
        conn.execute("create table prueba(valor integer)")
        conn.execute("insert into prueba values (1)")
        assert conn.execute("select valor from prueba").fetchone() == (1,)
    print("VALIDACION OK: Python 3.13 x64 y SQLite funcionales", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
