#!/usr/bin/env python3
"""Empaqueta EvaluaFPCanarias para Linux x64 o macOS (Intel/Apple Silicon).

Ejecutar en el propio SO de destino. No realiza compilación cruzada.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(r'^APP_VERSION\s*=\s*[\"\']([^\"\']+)', (ROOT/'app.py').read_text(encoding='utf-8'), re.MULTILINE).group(1)


def run(*args):
    print('+', ' '.join(map(str,args)), flush=True)
    subprocess.run(list(map(str,args)), cwd=ROOT, check=True)


def build():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Ejecutar pruebas antes de compilar')
    args=parser.parse_args()
    target = 'macos' if sys.platform == 'darwin' else 'linux' if sys.platform.startswith('linux') else None
    if target is None:
        raise SystemExit('Este compilador solo sirve en Linux o macOS.')
    arch = platform.machine().lower()
    if arch in ('x86_64','amd64'):
        arch = 'x64'
    elif arch in ('arm64','aarch64'):
        arch = 'arm64'
    else:
        raise SystemExit(f'Arquitectura no comprobada: {arch}')
    if target == 'linux' and arch != 'x64':
        raise SystemExit('Esta versión Linux está preparada y documentada solo para x64.')
    if args.test:
        run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q')
    package = f'EvaluaFPCanarias_Portatil_{VERSION}_{target}_{arch}'
    name = 'EvaluaFPCanarias_Portatil'
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
            '--name', name, '--distpath', str(ROOT/'dist'/'build_unix'),
            '--workpath', str(ROOT/'build'/'unix'),
            '--specpath', str(ROOT/'build'/'unix'),
            '--add-data', f'{ROOT/"web"}{os.pathsep}web',
            '--add-data', f'{ROOT/"assets"}{os.pathsep}assets',
            '--hidden-import', 'webview',
            '--hidden-import', 'canarias_reference',
            '--hidden-import', 'canarias_modules',
            '--hidden-import', 'common_scope_official', '--hidden-import', 'common_scope_export',
            '--hidden-import', 'canarias_backup', '--hidden-import', 'canarias_feoe',
            '--hidden-import', 'canarias_cycle_record', '--hidden-import', 'canarias_academic_decisions']
    if target == 'macos':
        args += ['--windowed', '--osx-bundle-identifier', 'org.evaluafpcanarias.local',
                 '--hidden-import', 'webview.platforms.cocoa']
    else:
        args += ['--hidden-import', 'webview.platforms.qt',
                 '--hidden-import', 'PyQt6.QtWebEngineWidgets',
                 '--hidden-import', 'PyQt6.QtWebChannel']
    args.append(str(ROOT/'app.py'))
    run(*args)
    staging = ROOT / 'dist' / package
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    if target == 'macos':
        built = ROOT/'dist'/'build_unix'/f'{name}.app'
        if not built.exists():
            raise RuntimeError('PyInstaller no ha generado la aplicación .app.')
        shutil.copytree(built, staging / built.name, symlinks=True)
        binary = staging/built.name/'Contents'/'MacOS'/name
        # El launcher evita variaciones de ubicación causadas por App Translocation.
        launcher = '#!/bin/sh\nset -eu\nBASE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexport EVALUAFP_CANARIAS_PORTABLE_HOME="$BASE"\nexport EVALUAFP_CANARIAS_PORTABLE=1\nexec "$BASE/EvaluaFPCanarias_Portatil.app/Contents/MacOS/EvaluaFPCanarias_Portatil" "$@"\n'
        (staging/'INICIAR_EVALUAFP.command').write_text(launcher,encoding='utf-8')
        (staging/'INICIAR_EVALUAFP.command').chmod(0o755)
    else:
        built=ROOT/'dist'/'build_unix'/name
        if not built.is_dir():
            raise RuntimeError('PyInstaller no ha generado el directorio Linux.')
        shutil.copytree(built, staging/name, symlinks=True)
        binary=staging/name/name
        launcher = '#!/bin/sh\nset -eu\nBASE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexport EVALUAFP_CANARIAS_PORTABLE_HOME="$BASE"\nexport EVALUAFP_CANARIAS_PORTABLE=1\nexec "$BASE/EvaluaFPCanarias_Portatil/EvaluaFPCanarias_Portatil" "$@"\n'
        (staging/'INICIAR_EVALUAFP.sh').write_text(launcher,encoding='utf-8')
        (staging/'INICIAR_EVALUAFP.sh').chmod(0o755)
    if not binary.is_file():
        raise RuntimeError(f'No está el ejecutable empaquetado: {binary}')
    (staging/'EvaluaFPCanarias.portable.json').write_text(json.dumps({
        'mode':'portable','data_dir':'EvaluaFPCanarias_Datos','backup_dir':'EvaluaFPCanarias_Copias'
    },indent=2),encoding='utf-8')
    (staging/'EvaluaFPCanarias_Datos').mkdir()
    (staging/'EvaluaFPCanarias_Copias').mkdir()
    shutil.copy2(ROOT/'docs'/'PORTABLE_LINUX_MAC.md',staging/'LEEME_LINUX_MAC.md')
    manual='MACOS.md' if target=='macos' else 'LINUX.md'
    shutil.copy2(ROOT/'docs'/'manuales'/manual,staging/('MANUAL_'+manual))
    shutil.copy2(ROOT/'docs'/'manuales'/'DIDACTICO_CANARIAS.md',staging/'GUIA_DIDACTICA.md')
    # Esta prueba NO requiere entorno gráfico, pero verifica que el empaquetado
    # puede cargar HTML, SQLite, exportaciones y pywebview.
    with tempfile.TemporaryDirectory(prefix='efp_selftest_') as test_home:
        env=os.environ.copy()
        env.pop('EVALUAFP_CANARIAS_DATA_DIR',None)
        env['EVALUAFP_CANARIAS_PORTABLE_HOME']=test_home
        env['EVALUAFP_CANARIAS_PORTABLE']='1'
        print('+ Selftest',binary)
        subprocess.run([str(binary),'--selftest'],env=env,check=True,timeout=180)
    archive=ROOT/'dist'/f'{package}.{ "zip" if target=="macos" else "tar.gz"}'
    if target=='macos':
        # ditto mantiene enlaces simbólicos, permisos y metadatos de .app.
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', staging, archive)
    else:
        with tarfile.open(archive,'w:gz') as t:
            t.add(staging,arcname=staging.name)
    print('COMPILACION FINALIZADA:',archive)


if __name__ == '__main__':
    build()
