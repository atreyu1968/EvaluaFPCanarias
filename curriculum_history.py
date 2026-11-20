"""Historial local de documentos curriculares comparables, no de notas.

Ámbito obligatorio: módulo + comunidad/ciudad + curso + código oficial.
Nunca convierte una propuesta de extracción en RA/CE aprobados ni afirma vigencia.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import re
import tempfile
from pathlib import Path

import curriculum_review
import national_registry
import territorial_profiles as territories

MAX_VERSIONS_PER_MODULE = 50


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS curriculum_source_snapshots(
       id INTEGER PRIMARY KEY,
       module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
       territory_code TEXT NOT NULL,
       academic_year TEXT NOT NULL,
       module_code TEXT NOT NULL,
       cycle_name TEXT NOT NULL,
       module_name TEXT NOT NULL,
       source_url TEXT NOT NULL,
       source_title TEXT NOT NULL,
       original_filename TEXT NOT NULL,
       document_sha256 TEXT NOT NULL,
       content_sha256 TEXT NOT NULL,
       report_json TEXT NOT NULL,
       noted_at TEXT NOT NULL,
       reviewed_by_teacher INTEGER NOT NULL DEFAULT 1,
       UNIQUE(module_id,territory_code,academic_year,module_code,document_sha256)
     )''')
    db.execute('''CREATE INDEX IF NOT EXISTS idx_curriculum_history_scope
       ON curriculum_source_snapshots(module_id,territory_code,academic_year,module_code,id DESC)''')


def _scope(db, module_id):
    row=db.execute('''SELECT id,academic_year,cycle,name,territory FROM modules WHERE id=?''',
                   (int(module_id),)).fetchone()
    if row is None:raise ValueError('Módulo no encontrado.')
    from program_builder import load
    draft=load(db,int(module_id))['draft']
    code=str(draft.get('official_module_code') or '').strip()
    if not re.fullmatch(r'\d{4}',code):
        raise ValueError('Para crear un historial debe confirmar el código oficial de cuatro cifras del módulo.')
    territory=territories.territory_code(draft.get('region') or row['territory'])
    if territory is None:raise ValueError('Seleccione una comunidad autónoma o ciudad educativa válida.')
    year=territories.year_code(row['academic_year'])
    return dict(row),draft,(territory,year,code)


def _stripped(report):
    """Contenido semántico: diferencias de paginación no son cambios curriculares."""
    return [{'code':ra['code'],'description':' '.join(ra['description'].split()),
             'criteria':[{'code':ce['code'],'description':' '.join(ce['description'].split())}
                         for ce in ra['criteria']]}
            for ra in report['outcomes']]


def _hash_content(report):
    obj=_stripped(report)
    return sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True, separators=(',',':')).encode('utf8')).hexdigest()


def store_document(db,module_id,filename,blob,code,kind,source_url,source_title,confirmed):
    if confirmed is not True:
        raise ValueError('Confirme que el documento y su fuente se han revisado antes de guardarlos en el historial.')
    if kind!='norma_oficial':
        raise ValueError('El historial normativo admite únicamente disposiciones oficiales, no programaciones de otros centros.')
    module,draft,scope=_scope(db,module_id)
    if code!=scope[2]:
        raise ValueError('El código del documento no coincide con el código oficial guardado para el módulo.')
    source_url=national_registry.valid_url(source_url)
    source_title=national_registry.text_value(source_title,'la denominación de la disposición',700)
    filename=str(filename or '')
    if not filename or len(filename)>255 or '/' in filename or '\\' in filename:
        raise ValueError('Nombre de documento inválido.')
    suffix=Path(filename).suffix.lower()
    if suffix not in ('.pdf','.docx','.txt','.md'):
        raise ValueError('Solo se admiten archivos PDF, DOCX, TXT o MD.')
    if not isinstance(blob,bytes) or not blob or len(blob)>curriculum_review.MAX_FILE:
        raise ValueError('El archivo curricular debe tener un máximo de 15 MB.')
    # Volver a analizar los bytes enviados al guardar: no aceptar un JSON de
    # navegador que pudiera estar editado o corresponder a otro documento.
    with tempfile.TemporaryDirectory(prefix='evaluafp_historial_') as folder:
        path=Path(folder)/('norma'+suffix)
        path.write_bytes(blob)
        report=curriculum_review.preview(path,module['name'],code,document_kind=kind)
    count=db.execute('''SELECT COUNT(*) FROM curriculum_source_snapshots WHERE
        module_id=? AND territory_code=? AND academic_year=? AND module_code=?''',
        (int(module_id),*scope)).fetchone()[0]
    digest=report['source']['sha256']
    existed=db.execute('''SELECT id,content_sha256 FROM curriculum_source_snapshots WHERE
        module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND document_sha256=?''',
        (int(module_id),*scope,digest)).fetchone()
    if existed:
        return {'saved':False,'duplicate':True,'id':existed['id'],
                'notice':'Este mismo documento ya está registrado; no se ha creado otra versión.'}
    if count>=MAX_VERSIONS_PER_MODULE:
        raise ValueError('Ha alcanzado el límite de 50 documentos por módulo y curso.')
    content_digest=_hash_content(report)
    saved_report={'schema':report['schema'],'status':'historial_revisado_docente_no_aplicado',
                  'outcomes':report['outcomes'],'summary':report['summary'],
                  'source':{'filename':filename,'sha256':digest,'format':report['source']['format']}}
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    db.execute('''INSERT INTO curriculum_source_snapshots
        (module_id,territory_code,academic_year,module_code,cycle_name,module_name,
         source_url,source_title,original_filename,document_sha256,content_sha256,
         report_json,noted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (int(module_id),*scope,module['cycle'],module['name'],source_url,source_title,
         filename,digest,content_digest,json.dumps(saved_report,ensure_ascii=False),now))
    record_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
    previous=db.execute('''SELECT * FROM curriculum_source_snapshots WHERE module_id=? AND territory_code=?
        AND academic_year=? AND module_code=? AND id<>? ORDER BY id DESC LIMIT 1''',
        (int(module_id),*scope,record_id)).fetchone()
    change=compare_reports(json.loads(previous['report_json']),saved_report) if previous else None
    if change:
        change.update({'old':{'id':previous['id'],'title':previous['source_title'],'url':previous['source_url']},
                       'new':{'id':record_id,'title':source_title,'url':source_url}})
    # Pistas de auditoría sin enunciados completos ni nombres de docentes.
    import database
    database.log(db,'official_curriculum_snapshot_saved','module',module_id,
        {'snapshot_id':record_id,'region':scope[0],'academic_year':scope[1],
         'module_code':scope[2],'source_sha256':digest,'differences':change['counts'] if change else {}})
    return {'saved':True,'duplicate':False,'id':record_id,
            'content_same_as_previous':bool(previous and previous['content_sha256']==content_digest),
            'change':change,'summary':saved_report['summary'],
            'notice':'Se ha archivado una fuente revisada por el docente, NO se han modificado RA, CE, instrumentos, notas ni ponderaciones.'}


def compare_reports(before,after):
    """Diferencias exactas entre dos referencias de RA/CE, sin mutaciones."""
    old={ra['code']:ra for ra in before['outcomes']}
    new={ra['code']:ra for ra in after['outcomes']}
    differences=[]
    for code in sorted(set(old)|set(new),key=lambda k:int(k[2:])):
        a,b=old.get(code),new.get(code)
        if a is None:
            differences.append({'code':code,'state':'nuevo_ra','old':'','new':b['description']})
            differences.extend({'code':ce['code'],'state':'nuevo_ce','old':'','new':ce['description']}
                               for ce in b['criteria'])
            continue
        if b is None:
            differences.append({'code':code,'state':'eliminado_ra','old':a['description'],'new':''})
            differences.extend({'code':ce['code'],'state':'eliminado_ce','old':ce['description'],'new':''}
                               for ce in a['criteria'])
            continue
        if curriculum_review.fold(a['description'])!=curriculum_review.fold(b['description']):
            differences.append({'code':code,'state':'cambio_ra','old':a['description'],'new':b['description']})
        a_ce={ce['code']:ce for ce in a['criteria']}
        b_ce={ce['code']:ce for ce in b['criteria']}
        for key in sorted(set(a_ce)|set(b_ce)):
            x,y=a_ce.get(key),b_ce.get(key)
            if x is None: differences.append({'code':key,'state':'nuevo_ce','old':'','new':y['description']})
            elif y is None: differences.append({'code':key,'state':'eliminado_ce','old':x['description'],'new':''})
            elif curriculum_review.fold(x['description'])!=curriculum_review.fold(y['description']):
                differences.append({'code':key,'state':'cambio_ce','old':x['description'],'new':y['description']})
    return {'differences':differences,'counts':dict(Counter(d['state'] for d in differences)),
            'requires_manual_review':bool(differences),
            'notice':('Este resultado compara fuentes documentales del mismo ámbito y curso, no determina por sí solo qué versión es vigente. '
                      'No cambia la base curricular ni calificaciones existentes.')}


def list_snapshots(db,module_id):
    module,draft,scope=_scope(db,module_id)
    rows=db.execute('''SELECT id,source_title,source_url,noted_at,original_filename,
        document_sha256,content_sha256,report_json,academic_year,territory_code,module_code
        FROM curriculum_source_snapshots
        WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=?
        ORDER BY id DESC LIMIT 50''',(int(module_id),*scope)).fetchall()
    items=[]
    for row in rows:
        summary=json.loads(row['report_json'])['summary']
        items.append({'id':row['id'],'source_title':row['source_title'],'source_url':row['source_url'],
                      'recorded_at':row['noted_at'],'document':row['original_filename'],
                      'document_sha256':row['document_sha256'], 'content_sha256':row['content_sha256'],
                      'ra':summary['ra'],'ce':summary['ce']})
    return {'territory_code':scope[0],'academic_year':scope[1],
            'module_code':scope[2],'versions':items,'count':len(items),
            'notice':'Solo se muestran referencias del mismo módulo, curso y ámbito educativo; ninguna se declara jurídicamente vigente.'}


def compare_snapshots(db,module_id,older,newer):
    _,__,scope=_scope(db,module_id)
    ids=(int(older),int(newer))
    if ids[0]==ids[1]:raise ValueError('Seleccione dos versiones diferentes.')
    data=[]
    for sid in ids:
        row=db.execute('''SELECT id,report_json,source_title,source_url,document_sha256 FROM curriculum_source_snapshots
           WHERE id=? AND module_id=? AND territory_code=? AND academic_year=? AND module_code=?''',
           (sid,int(module_id),*scope)).fetchone()
        if not row:raise ValueError('La versión solicitada no pertenece a este módulo, ámbito y curso.')
        data.append(row)
    return {'old':{'id':data[0]['id'],'title':data[0]['source_title'],'url':data[0]['source_url']},
            'new':{'id':data[1]['id'],'title':data[1]['source_title'],'url':data[1]['source_url']},
            **compare_reports(*[json.loads(row['report_json']) for row in data])}


def catalog(db,region,academic_year,query=''):
    """Índice local creciente; NO catálogo oficial nacional completo."""
    code=territories.territory_code(region)
    if code is None:raise ValueError('Territorio desconocido.')
    year=territories.year_code(academic_year)
    query=curriculum_review.fold(query)
    if len(query)>120:raise ValueError('Búsqueda demasiado larga.')
    rows=db.execute('''SELECT * FROM curriculum_source_snapshots
       WHERE territory_code=? AND academic_year=? ORDER BY id DESC LIMIT 1000''',(code,year)).fetchall()
    index={}
    for row in rows:
        key=(curriculum_review.fold(row['cycle_name']),row['module_code'])
        if key in index:continue
        label=' '.join((row['cycle_name'],row['module_code'],row['module_name']))
        if query and query not in curriculum_review.fold(label):continue
        index[key]={'cycle':row['cycle_name'],'module_name':row['module_name'],
                    'module_code':row['module_code'],'source_url':row['source_url'],
                    'source_title':row['source_title'],'snapshot_id':row['id']}
    return {'territory':territories.require_territory(region),'academic_year':year,
            'modules':list(index.values())[:100],
            'notice':'Catálogo construido únicamente con referencias aportadas y revisadas por docentes; no es un catálogo oficial completo.'}
