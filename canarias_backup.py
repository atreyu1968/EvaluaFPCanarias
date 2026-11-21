"""Copias locales verificables, sin sobrescribir datos activos.

La instantánea SQLite es consistente. Los originales se copian y verifican
individualmente; no se garantiza una transacción única entre archivos y SQLite.
Hacer la copia sin cargas ni modificaciones concurrentes.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

DB_MEMBER='datos/evaluafp.sqlite3'
MANIFEST='manifest.json'
SECRET='seguridad/api_cifrada.json'
FORMAT='evaluafp-canarias-backup-v1'
MAX_MEMBERS=100000
MAX_TOTAL=100*1024**3


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def safe_file(path,root):
    return path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())


def check_database(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
            raise ValueError('SQLite no supera la comprobación de integridad.')
        required={'modules','students','outcomes','criteria','preferences'}
        names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required<=names:
            raise ValueError('La base no tiene la estructura de EvaluaFP.')


def make(data_dir,backup_dir,db_file,storage,secret=None):
    data_dir,backup_dir,db_file,storage=map(Path,(data_dir,backup_dir,db_file,storage))
    backup_dir.mkdir(parents=True,exist_ok=True)
    name='copia_evaluafp_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.zip'
    final=backup_dir/name
    with tempfile.TemporaryDirectory(prefix='.efp_backup_',dir=backup_dir) as raw:
        temp=Path(raw)
        dbcopy=temp/'snapshot.sqlite3'
        with closing(sqlite3.connect(db_file,timeout=30)) as source:
            with closing(sqlite3.connect(dbcopy)) as dest:
                source.backup(dest)
        check_database(dbcopy)
        archive=temp/'backup.zip'
        records={}
        def add(z,path,member):
            if member in records:
                raise ValueError('Nombre duplicado en la copia.')
            before=path.stat()
            digest=hashlib.sha256()
            with path.open('rb') as src,z.open(member,'w',force_zip64=True) as dst:
                for block in iter(lambda:src.read(1024*1024),b''):
                    digest.update(block)
                    dst.write(block)
            after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                raise ValueError('Un archivo cambió durante la copia. Repita sin actividad.')
            records[member]={'size':after.st_size,'sha256':digest.hexdigest()}
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            add(z,dbcopy,DB_MEMBER)
            for root,dirs,files in os.walk(storage,followlinks=False):
                dirs.sort()
                for directory in dirs:
                    p=Path(root)/directory
                    if p.is_symlink() or not p.resolve().is_relative_to(storage.resolve()):
                        raise ValueError('El almacén contiene un enlace de directorio no permitido.')
                for filename in sorted(files):
                    p=Path(root)/filename
                    if not safe_file(p,storage):
                        raise ValueError('El almacén contiene un archivo no ordinario o externo.')
                    add(z,p,'almacen/'+p.relative_to(storage).as_posix())
            if secret is not None and Path(secret).exists():
                p=Path(secret)
                if not safe_file(p,data_dir):
                    raise ValueError('La clave cifrada no es un archivo local ordinario.')
                add(z,p,SECRET)
            manifest={'format':FORMAT,'created_at':datetime.now(timezone.utc).isoformat(),
                      'original_data_root':str(data_dir.resolve()),'files':records}
            z.writestr(MANIFEST,json.dumps(manifest,ensure_ascii=False,sort_keys=True))
        verify(archive)
        os.replace(archive,final)
    return final


def allowed(name):
    if not isinstance(name,str) or '\\' in name or '\x00' in name:
        return False
    if name in (DB_MEMBER,SECRET,MANIFEST):
        return True
    parts=name.split('/')
    return (len(parts)>1 and parts[0]=='almacen' and
            all(p not in ('','.','..') and not re.search(r'[:*?"<>|]',p)
                and not p.endswith((' ','.')) and
                p.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
                for p in parts))


def verify(path,extract_to=None):
    """Valida estructura y SHA-256 de todos los miembros, con límites."""
    with zipfile.ZipFile(path,'r') as z:
        infos=z.infolist()
        if len(infos)>MAX_MEMBERS or sum(i.file_size for i in infos)>MAX_TOTAL:
            raise ValueError('Copia demasiado extensa.')
        names=set()
        for i in infos:
            mode=(i.external_attr>>16)&0xffff
            if (not allowed(i.filename) or i.is_dir() or i.filename.casefold() in names
                or stat.S_ISLNK(mode) or (i.flag_bits&1)):
                raise ValueError('La copia contiene una ruta, duplicado, enlace o cifrado ZIP no permitido.')
            names.add(i.filename.casefold())
        if MANIFEST not in z.namelist() or z.getinfo(MANIFEST).file_size>32*1024**2:
            raise ValueError('Falta un manifiesto de integridad compatible.')
        manifest=json.loads(z.read(MANIFEST))
        files=manifest.get('files') if isinstance(manifest,dict) else None
        if manifest.get('format')!=FORMAT or not isinstance(files,dict) or DB_MEMBER not in files:
            raise ValueError('Formato de copia incompatible.')
        if set(files)!=(set(z.namelist())-{MANIFEST}):
            raise ValueError('El manifiesto no coincide con el contenido.')
        for name,meta in files.items():
            if not isinstance(meta,dict) or type(meta.get('size')) is not int or meta['size']!=z.getinfo(name).file_size:
                raise ValueError('Tamaño incorrecto en el manifiesto.')
            digest=hashlib.sha256()
            dest=None
            try:
                if extract_to is not None:
                    p=Path(extract_to).joinpath(*PurePosixPath(name).parts)
                    p.parent.mkdir(parents=True,exist_ok=True)
                    dest=p.open('xb')
                with z.open(name) as source:
                    for block in iter(lambda:source.read(1024*1024),b''):
                        digest.update(block)
                        if dest:
                            dest.write(block)
            finally:
                if dest:
                    dest.close()
            if digest.hexdigest()!=meta.get('sha256'):
                raise ValueError('Huella SHA-256 incorrecta: '+name)
        return manifest


def rebase(dbpath,root):
    """Reubica solo rutas conocidas de almacén, sin acceso a rutas externas."""
    paths=(('programmings','local_path'),('materials','local_path'),
           ('submissions','storage_path'),('source_files','local_path'),('pages','image_path'))
    with closing(sqlite3.connect(dbpath)) as db:
        with db:
            for table,column in paths:
                present={r[1] for r in db.execute(f'PRAGMA table_info({table})')}
                if column not in present:
                    continue
                for rid,raw in db.execute(f'SELECT id,{column} FROM {table}').fetchall():
                    parts=str(raw or '').replace('\\','/').split('/')
                    # Último segmento almacen; las rutas deben pertenecer a la copia.
                    positions=[i for i,p in enumerate(parts) if p.casefold()=='almacen']
                    if not positions:
                        raise ValueError('Referencia de archivo sin almacén identificable.')
                    member='/'.join(parts[positions[-1]:])
                    if not allowed(member):
                        raise ValueError('Ruta de documento incompatible.')
                    dest=root.joinpath(*member.split('/'))
                    if not dest.exists():
                        raise ValueError('Falta un original referenciado por SQLite: '+member)
                    db.execute(f'UPDATE {table} SET {column}=? WHERE id=?',(str(dest),rid))
            db.execute("""INSERT INTO preferences(key,value) VALUES('portable_last_data_root',?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(json.dumps(str(root)),))


def restore(path,destination):
    """Recupera a carpeta nueva o vacía; nunca modifica la instalación activa."""
    destination=Path(destination).resolve()
    if destination.exists():
        raise ValueError('La recuperación requiere una carpeta nueva, no existente.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.mkdir(mode=0o700)
    try:
        verify(path,destination)
        (destination/'almacen').mkdir(exist_ok=True)
        dbpath=destination/DB_MEMBER
        check_database(dbpath)
        rebase(dbpath,destination)
        check_database(dbpath)
        return destination
    except BaseException:
        shutil.rmtree(destination)
        raise


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Verificar o recuperar copia EvaluaFP Canarias a una carpeta nueva.')
    parser.add_argument('archive',type=Path)
    parser.add_argument('--restore-to',type=Path)
    args=parser.parse_args()
    if args.restore_to:
        print('Recuperación verificada:',restore(args.archive,args.restore_to))
    else:
        manifest=verify(args.archive)
        print('Integridad SHA-256 verificada:',len(manifest['files']),'archivos')
