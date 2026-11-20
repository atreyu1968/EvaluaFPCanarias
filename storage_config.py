"""Rutas portables de EvalúaFP y migración segura de SQLite/documentos.

Los ajustes de ubicación son independientes de SQLite, de modo que pueden
cargarse ANTES de abrir la base de datos. Nunca guarda claves de API.
"""
from __future__ import annotations

import json
from contextlib import closing
import os
import shutil
import sqlite3
import sys
from pathlib import Path

def _application_home():
    """Ubicación del dispositivo, estable aunque el ejecutable esté en un .app."""
    explicit = os.environ.get('EVALUAFP_CANARIAS_PORTABLE_HOME')
    if explicit:
        return Path(explicit).expanduser().resolve()
    if not getattr(sys, 'frozen', False):
        return Path(__file__).resolve().parent
    exe = Path(sys.executable).resolve()
    if sys.platform == 'darwin':
        # En un paquete .app, el ejecutable reside en Contents/MacOS.
        # Los datos deben ir al lado del .app, NUNCA en su interior.
        for parent in exe.parents:
            if parent.suffix.lower() == '.app':
                return parent.parent
    return exe.parent


APP_HOME = _application_home()
PORTABLE_FILE = APP_HOME / 'EvaluaFPCanarias.portable.json'
if sys.platform == 'darwin':
    _default_home = Path.home() / 'Library' / 'Application Support'
else:
    _default_home = Path(os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
LOCAL_HOME = _default_home / 'EvaluaFPCanarias'
INSTALLED_FILE = LOCAL_HOME / 'ubicaciones.json'
PORTABLE = (PORTABLE_FILE.is_file() or '--portable' in sys.argv or
            os.environ.get('EVALUAFP_CANARIAS_PORTABLE') == '1' or
            (getattr(sys,'frozen',False) and 'portatil' in Path(sys.executable).stem.casefold()))


def _read_json(path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'No se puede leer la configuración de carpetas: {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise ValueError('La configuración de carpetas debe ser un objeto JSON.')
    return value


def config_file():
    return PORTABLE_FILE if PORTABLE else INSTALLED_FILE


def resolve_folder(value, portable=None):
    """Acepta rutas relativas a la carpeta EXE o absolutas en el MISMO pendrive."""
    portable = PORTABLE if portable is None else portable
    text = str(value).strip()
    if not text or '\x00' in text:
        raise ValueError('Introduzca una carpeta de almacenamiento válida.')
    path = Path(os.path.expandvars(text)).expanduser()
    # Windows puede presentar el mismo directorio como RUNNER~1 o como
    # runneradmin. Comparar siempre rutas canónicas evita confundir alias 8.3.
    home = Path(APP_HOME).resolve()
    result = (path if path.is_absolute() else (home if portable else LOCAL_HOME) / path).resolve()
    if portable:
        if os.name == 'nt' and result.drive.casefold() != home.drive.casefold():
            raise ValueError('En modo portátil, las carpetas deben estar en la misma unidad que el EXE.')
        if result == home:
            raise ValueError('No guarde los datos directamente en la carpeta del EXE; utilice una subcarpeta.')
    return result


def _configured_folders():
    config = _read_json(config_file())
    forced = os.environ.get('EVALUAFP_CANARIAS_DATA_DIR')
    if forced:  # Utilizado por despliegues gestionados y pruebas existentes.
        datadir = Path(forced).expanduser().resolve()
        backups = datadir / 'copias'
    elif PORTABLE:
        datadir = resolve_folder(config.get('data_dir', 'EvaluaFPCanarias_Datos'))
        backups = resolve_folder(config.get('backup_dir', 'EvaluaFPCanarias_Copias'))
    else:
        datadir = resolve_folder(config['data_dir']) if config.get('data_dir') else LOCAL_HOME
        backups = resolve_folder(config['backup_dir']) if config.get('backup_dir') else datadir / 'copias'
    if datadir == backups or datadir in backups.parents or backups in datadir.parents:
        # Por defecto la instalación NO portátil conserva copias en DATA/copias.
        if not PORTABLE and backups == datadir / 'copias':
            return datadir, backups
        raise ValueError('La carpeta de copias debe estar separada de la carpeta de datos.')
    return datadir, backups


DATA_DIR, BACKUP_DIR = _configured_folders()


def get_info():
    return {'portable':PORTABLE, 'app_dir':str(APP_HOME), 'data_dir':str(DATA_DIR),
            'backup_dir':str(BACKUP_DIR),
            'data_dir_edit':os.path.relpath(DATA_DIR.resolve(),APP_HOME.resolve()) if PORTABLE else str(DATA_DIR),
            'backup_dir_edit':os.path.relpath(BACKUP_DIR.resolve(),APP_HOME.resolve()) if PORTABLE else str(BACKUP_DIR), 'configuration_file':str(config_file()),
            'secret_mode':'contraseña maestra (AES-256-GCM)' if PORTABLE else 'credenciales del sistema'}


def _writable(path):
    path.mkdir(parents=True, exist_ok=True)
    probe = path / '.evaluafp_permiso.tmp'
    with probe.open('wb') as stream:
        stream.write(b'Prueba de escritura EvaluaFP')
    probe.unlink()


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def _nested(first, second):
    return first == second or first in second.parents or second in first.parents


def relocate(data_dir, backup_dir, *, migrate=True):
    """Copia base y originales al destino; conserva fuentes y requiere reinicio.

    Los archivos existentes nunca se sobrescriben. La nueva ruta se activa
    únicamente tras completar con éxito todos los pasos y guardar el JSON.
    """
    if os.environ.get('EVALUAFP_CANARIAS_DATA_DIR'):
        raise ValueError('Las rutas están administradas por EVALUAFP_CANARIAS_DATA_DIR; no se pueden cambiar aquí.')
    old_data = DATA_DIR.resolve()
    old_backup = BACKUP_DIR.resolve()
    new_data = resolve_folder(data_dir)
    new_backup = resolve_folder(backup_dir)
    if _nested(new_data, new_backup):
        raise ValueError('Datos y copias no pueden estar contenidos uno dentro de otro.')
    if new_data == old_data and new_backup == old_backup:
        return {'changed':False, 'restart_required':False}
    if new_data != old_data and _nested(new_data, old_data):
        raise ValueError('No se puede migrar la base a una carpeta dentro de la carpeta de datos anterior.')
    if new_backup != old_backup and _nested(new_backup, old_backup):
        raise ValueError('La nueva carpeta de copias no puede estar dentro de la anterior.')
    if new_data != old_data and new_data.exists() and any(new_data.iterdir()):
        raise ValueError('La nueva carpeta de datos debe estar vacía para evitar sobrescribir información.')
    if new_backup != old_backup and new_backup.exists() and any(new_backup.iterdir()):
        raise ValueError('La nueva carpeta de copias debe estar vacía para evitar sobrescribir archivos.')
    for path in (new_data, new_backup):
        _writable(path)
    if new_data != old_data:
        if not migrate:
            raise ValueError('Cambiar la carpeta de datos requiere migrar SQLite y los originales.')
        # Primero copiamos todas las carpetas excepto las partes volátiles de SQLite.
        for src in old_data.rglob('*'):
            rel = src.relative_to(old_data)
            dest = new_data / rel
            if src.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            elif src.is_file() and src.name not in {'evaluafp.sqlite3','evaluafp.sqlite3-wal','evaluafp.sqlite3-shm'}:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
        new_db_path = new_data / 'datos' / 'evaluafp.sqlite3'
        new_db_path.parent.mkdir(parents=True, exist_ok=True)
        # El backup API de sqlite3 crea una instantánea consistente incluso con WAL.
        # IMPORTANTE EN WINDOWS: sqlite3.Connection.__exit__ confirma la
        # transacción, pero NO cierra la conexión. 'closing' libera ambos
        # archivos antes de salir de relocate y antes de limpiar temporales.
        with closing(sqlite3.connect(old_data/'datos'/'evaluafp.sqlite3', timeout=30)) as srcdb:
            with closing(sqlite3.connect(new_db_path, timeout=30)) as dstdb:
                srcdb.backup(dstdb)
                # Las versiones previas guardaban rutas absolutas; reubicarlas.
                for table, column in [('programmings','local_path'),('materials','local_path'),
                                      ('submissions','storage_path'),('source_files','local_path'),
                                      ('pages','image_path')]:
                    try:
                        rows=dstdb.execute(f'SELECT id,{column} FROM {table}').fetchall()
                    except sqlite3.OperationalError:
                        continue
                    for rid, raw in rows:
                        old_path=Path(raw)
                        try: rel=old_path.resolve().relative_to(old_data)
                        except (ValueError,TypeError):continue
                        dstdb.execute(f'UPDATE {table} SET {column}=? WHERE id=?',(str(new_data/rel),rid))
                dstdb.commit()
                if dstdb.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('La copia de SQLite no ha superado la prueba de integridad.')
    if new_backup != old_backup:
        for old_file in old_backup.rglob('*') if old_backup.exists() else []:
            if old_file.is_file():
                dest = new_backup / old_file.relative_to(old_backup)
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(old_file, dest)
    # Se escribe lo último: ante interrupción continúa funcionando la ruta original.
    values = {'mode':'portable' if PORTABLE else 'installed',
              'data_dir':os.path.relpath(new_data,APP_HOME.resolve()) if PORTABLE else str(new_data),
              'backup_dir':os.path.relpath(new_backup,APP_HOME.resolve()) if PORTABLE else str(new_backup)}
    _atomic_json(config_file(), values)
    return {'changed':True, 'restart_required':True, 'data_dir':str(new_data),
            'backup_dir':str(new_backup), 'note':'Cierre EvaluaFP y vuelva a abrirlo. Los datos antiguos se han conservado.'}