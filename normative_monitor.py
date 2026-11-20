"""Seguimiento conservador de cambios en metadatos oficiales del BOE.

Observa identificadores elegidos por el docente. No determina vigencia jurídica,
no rastrea boletines autonómicos y no modifica programaciones ni calificaciones.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from urllib.parse import parse_qs, urlsplit

import boe_discovery
import database
import program_builder
import territorial_profiles as territories

_ID = re.compile(r'BOE-A-(?:19|20)\d{2}-\d{1,7}\Z', re.I)
_NOTICE = ('La comparación solo examina los metadatos y las modificaciones comunicadas por la API del BOE. '
           'No determina la vigencia de la norma ni su aplicabilidad al currículo autonómico, modalidad, centro o curso. '
           'Una consulta sin cambios observados NO acredita que no existan modificaciones.')


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS boe_monitor_sources (
      module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
      territory_code TEXT NOT NULL, academic_year TEXT NOT NULL, module_code TEXT NOT NULL,
      boe_id TEXT NOT NULL, source_url TEXT NOT NULL, source_title TEXT NOT NULL,
      signature TEXT NOT NULL, metadata_json TEXT NOT NULL,
      first_checked TEXT NOT NULL, last_checked TEXT NOT NULL,
      changed_at TEXT, reviewed_at TEXT, review_note TEXT NOT NULL DEFAULT '',
      PRIMARY KEY (module_id,territory_code,academic_year,module_code,boe_id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS boe_monitor_events (
      id INTEGER PRIMARY KEY,
      module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
      territory_code TEXT NOT NULL, academic_year TEXT NOT NULL, module_code TEXT NOT NULL,
      boe_id TEXT NOT NULL, old_signature TEXT NOT NULL, new_signature TEXT NOT NULL,
      before_json TEXT NOT NULL, after_json TEXT NOT NULL, observed_at TEXT NOT NULL
    )''')
    db.execute('''CREATE INDEX IF NOT EXISTS idx_boe_monitor_events
      ON boe_monitor_events(module_id, territory_code,academic_year,module_code, id DESC)''')


def _scope(db, module_id, require_code=True):
    try:
        mid = int(module_id)
    except (TypeError, ValueError) as exc:
        raise ValueError('Indique un módulo válido.') from exc
    if mid <= 0:
        raise ValueError('Indique un módulo válido.')
    record = db.execute('SELECT id,academic_year,territory FROM modules WHERE id=?', (mid,)).fetchone()
    if record is None:
        raise ValueError('Módulo no encontrado.')
    draft = program_builder.load(db,mid)['draft']
    territory = territories.territory_code(draft.get('region') or record['territory'])
    if territory is None:
        raise ValueError('Indique una administración educativa válida.')
    code = str(draft.get('official_module_code') or '').strip()
    if require_code and not re.fullmatch(r'\d{4}', code):
        raise ValueError('Guarde primero el código oficial de cuatro cifras del módulo.')
    return (mid,territory,territories.year_code(record['academic_year']),code),draft


def _boe_id(value):
    identifier = str(value or '').strip().upper()
    if not _ID.fullmatch(identifier):
        raise ValueError('Introduzca un identificador BOE-A-AAAA-NNN válido.')
    return identifier


def _from_official_url(url):
    """Solo reconoce identificadores de URLs directas de normas del BOE.

    No admite dominios parecidos, credenciales, puertos, rutas arbitrarias ni
    identificadores ocultos en texto o en el fragmento de la URL.
    """
    if not isinstance(url,str) or len(url)>900:
        return None
    try:
        parsed=urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname not in ('boe.es','www.boe.es')
                or parsed.username or parsed.password or parsed.port not in (None,443)
                or parsed.fragment or parsed.path not in ('/buscar/act.php','/diario_boe/txt.php')):
            return None
        query=parse_qs(parsed.query,keep_blank_values=True)
        if set(query)!={'id'} or len(query['id'])!=1:
            return None
        identifier=query['id'][0].upper()
        return identifier if _ID.fullmatch(identifier) else None
    except ValueError:
        return None


def _stable_metadata(response, identifier):
    if not isinstance(response,dict) or str(response.get('id','')).upper()!=identifier:
        raise ValueError('La API del BOE no ha devuelto la disposición solicitada.')
    if not response.get('has_legal_analysis') or not str(response.get('title') or '').strip():
        raise ValueError('El BOE no ha proporcionado metadatos y análisis suficientes para una comparación fiable. No se modificó el registro previo.')
    amendments={}
    for record in response.get('reported_amendments') or []:
        if not isinstance(record,dict):
            continue
        ref=str(record.get('id') or '').upper()
        if _ID.fullmatch(ref):
            amendments[ref]={'id':ref,'type':str(record.get('type') or '')[:150],
                             'title':str(record.get('title') or '')[:500]}
    return {'id':identifier,'title':str(response.get('title') or '')[:500],
            'publication_date':str(response.get('publication_date') or '')[:40],
            'last_update':str(response.get('last_update') or '')[:40],
            'consolidation_state':str(response.get('consolidation_state') or '')[:100],
            'reported_amendments':sorted(amendments.values(),key=lambda x:x['id'])}


def _sources_from_draft(db, scope, draft):
    entries=[]
    if draft.get('curriculum_source_url'):
        entries.append((draft['curriculum_source_url'],draft.get('curriculum_source_description') or 'Fuente curricular del borrador'))
    snapshots=db.execute('''SELECT source_url,source_title FROM curriculum_source_snapshots
      WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=?
      ORDER BY id DESC LIMIT 50''',scope).fetchall()
    entries.extend((row['source_url'],row['source_title']) for row in snapshots)
    discovered={}
    for url,title in entries:
        identifier=_from_official_url(url)
        if identifier and identifier not in discovered:
            discovered[identifier]={'boe_id':identifier,'source_url':url,
                                    'source_title':str(title)[:500], 'origin':'fuente_docente'}
    return discovered


def list_sources(db, module_id):
    scope,draft=_scope(db,module_id,require_code=False)
    if not re.fullmatch(r'\d{4}',scope[3]):
        return {'sources':[],'count':0,'notice':'Guarde el código oficial del módulo para vigilar disposiciones sin mezclar currículos.'}
    discovered=_sources_from_draft(db,scope,draft)
    watched=db.execute('''SELECT boe_id,source_url,source_title,metadata_json,first_checked,last_checked,
      changed_at,reviewed_at,review_note FROM boe_monitor_sources
      WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=? ORDER BY last_checked DESC''',scope).fetchall()
    for row in watched:
        record=discovered.setdefault(row['boe_id'],{'boe_id':row['boe_id'],'origin':'comprobacion_docente'})
        meta=json.loads(row['metadata_json'])
        record.update(source_url=row['source_url'],source_title=row['source_title'],
                      first_checked=row['first_checked'],last_checked=row['last_checked'],
                      changed_at=row['changed_at'],reviewed_at=row['reviewed_at'],
                      review_pending=bool(row['changed_at'] and not row['reviewed_at']),
                      last_update=meta['last_update'],amendment_count=len(meta['reported_amendments']))
    events=db.execute('''SELECT boe_id,old_signature,new_signature,before_json,after_json,observed_at
      FROM boe_monitor_events WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=?
      ORDER BY id DESC LIMIT 20''',scope).fetchall()
    return {'sources':list(discovered.values()),'count':len(discovered),
            'events':[{'boe_id':row['boe_id'],'observed_at':row['observed_at'],
                       'before':json.loads(row['before_json']), 'after':json.loads(row['after_json'])} for row in events],
            'territory_code':scope[1],'academic_year':scope[2],'module_code':scope[3],
            'notice':_NOTICE}


def check_source(db, module_id, boe_id, teacher_confirmed, *, inspector=None):
    if teacher_confirmed is not True:
        raise ValueError('Confirme que la disposición corresponde al módulo antes de consultar sus cambios.')
    scope,_draft=_scope(db,module_id)
    identifier=_boe_id(boe_id)
    # La petición transmite únicamente el ID de una disposición pública.
    response=(inspector or boe_discovery.inspect_boe_id)(identifier)
    meta=_stable_metadata(response,identifier)
    payload=json.dumps(meta,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    signature=sha256(payload.encode('utf-8')).hexdigest()
    url='https://www.boe.es/buscar/act.php?id='+identifier
    current=db.execute('''SELECT signature,metadata_json,changed_at,reviewed_at FROM boe_monitor_sources
      WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND boe_id=?''',scope+(identifier,)).fetchone()
    now=database.now()
    if current is None:
        db.execute('''INSERT INTO boe_monitor_sources
         (module_id,territory_code,academic_year,module_code,boe_id,source_url,source_title,
          signature,metadata_json,first_checked,last_checked)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',scope+(identifier,url,meta['title'],signature,payload,now,now))
        status='referencia_inicial'
    elif current['signature']!=signature:
        db.execute('''INSERT INTO boe_monitor_events
         (module_id,territory_code,academic_year,module_code,boe_id,old_signature,new_signature,
          before_json,after_json,observed_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
          scope+(identifier,current['signature'],signature,current['metadata_json'],payload,now))
        db.execute('''UPDATE boe_monitor_sources SET signature=?, metadata_json=?, source_title=?,
          last_checked=?,changed_at=?,reviewed_at=NULL,review_note=''
          WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND boe_id=?''',
          (signature,payload,meta['title'],now,now)+scope+(identifier,))
        status='cambio_detectado'
    else:
        db.execute('''UPDATE boe_monitor_sources SET last_checked=?
          WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND boe_id=?''',
          (now,)+scope+(identifier,))
        status='cambio_pendiente_de_revision' if current['changed_at'] and not current['reviewed_at'] else 'sin_cambios_observados'
    return {'boe_id':identifier,'status':status,'last_checked':now,'metadata':meta,
            'review_required':status in ('cambio_detectado','cambio_pendiente_de_revision'),
            'curriculum_modified':False,'notice':_NOTICE}


def acknowledge_change(db, module_id, boe_id, note, teacher_confirmed):
    if teacher_confirmed is not True:
        raise ValueError('La revisión de la alerta exige una confirmación expresa del docente.')
    scope,_=_scope(db,module_id)
    identifier=_boe_id(boe_id)
    if not isinstance(note,str) or not 12<=len(note.strip())<=1000:
        raise ValueError('Escriba una conclusión de revisión de 12 a 1.000 caracteres.')
    current=db.execute('''SELECT changed_at,reviewed_at FROM boe_monitor_sources WHERE
      module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND boe_id=?''',scope+(identifier,)).fetchone()
    if not current or not current['changed_at'] or current['reviewed_at']:
        raise ValueError('No existe una alerta de cambios pendiente para esta disposición y módulo.')
    now=database.now()
    db.execute('''UPDATE boe_monitor_sources SET reviewed_at=?,review_note=?
      WHERE module_id=? AND territory_code=? AND academic_year=? AND module_code=? AND boe_id=?''',
      (now,note.strip())+scope+(identifier,))
    database.log(db,'boe_change_reviewed','module',scope[0],{'boe_id':identifier,'note':note.strip()})
    return {'ok':True,'boe_id':identifier,'reviewed_at':now,
            'notice':'Alerta examinada por el docente. Este acuse NO confirma vigencia ni aplica modificaciones curriculares.'}