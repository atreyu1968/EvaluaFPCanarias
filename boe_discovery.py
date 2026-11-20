"""Búsqueda limitada de normativa en la API pública de legislación consolidada del BOE.

No es una base completa de boletines autonómicos, NO determina vigencia jurídica
ni deduce horas o CE. Nunca modifica el currículo sin aprobación del docente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
import json
import re
import urllib.error
import urllib.request
import unicodedata

import territorial_profiles as territory

API = 'https://www.boe.es/datosabiertos/api/legislacion-consolidada'
MAX_BYTES = 2_000_000
MAX_RESULTS = 12
BOE_ID = re.compile(r'BOE-A-(?:19|20)\d{2}-\d{1,7}\Z', re.I)


def _normalise(value):
    s=unicodedata.normalize('NFKD',str(value or '').casefold())
    return ' '.join(''.join(c for c in s if not unicodedata.combining(c)).split())


def _request_json(url, opener=None):
    """Solicitud de solo lectura a ruta fija del BOE, con tamaño/tiempo acotados.

    Se permite inyección de cliente HTTP en tests. No se aceptan URLs de usuario.
    """
    if not url.startswith(API) or (len(url)>1500):
        raise ValueError('Solo se permiten las rutas oficiales del BOE.')
    client = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={
        'Accept':'application/json', 'User-Agent':'EvaluaFP/1.2 Consulta BOE (educación)'})
    try:
        with client(request, timeout=12) as response:
            if response.geturl().split('?')[0].startswith(API) is False:
                raise ValueError('La respuesta del BOE ha redirigido a otra dirección.')
            data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES:
                raise ValueError('La respuesta normativa supera el límite permitido.')
    except (OSError,TimeoutError,urllib.error.URLError) as exc:
        raise ValueError('No se pudo consultar el BOE. Compruebe la conexión y utilice la consulta manual.') from exc
    try:
        payload=json.loads(data.decode('utf-8-sig'))
    except (ValueError,UnicodeError) as exc:
        raise ValueError('El BOE no ha devuelto los datos estructurados esperados. Consulte directamente su web.') from exc
    if isinstance(payload,dict) and isinstance(payload.get('response'),dict):
        status=payload['response']
        if str(status.get('code','200')) not in ('200','0'):
            raise ValueError('El BOE ha comunicado un error en la consulta.')
    return payload


def _first_text(data,*names):
    if not isinstance(data,dict):return ''
    for key in names:
        val=data.get(key)
        if isinstance(val,str) and val.strip():return val.strip()[:500]
        if isinstance(val,dict):
            for sub in ('texto','valor','value','content'):
                if isinstance(val.get(sub),str):return val[sub].strip()[:500]
    return ''


def _walk_records(obj, limit=150):
    """Admite envoltorios data/items/lista de versiones del API, sin inferir campos."""
    seen=[]
    def recurse(value,level):
        if len(seen)>=limit or level>7:return
        if isinstance(value,list):
            for item in value[:limit]:recurse(item,level+1)
        if isinstance(value,dict):
            if _first_text(value,'identificador','id','id_norma') and _first_text(value,'titulo','titulo_norma','nombre'):
                seen.append(value)
            for key in ('data','items','normas','disposiciones','resultados','norma','metadatos'):
                if key in value:recurse(value[key],level+1)
    recurse(obj,0)
    return seen


def parse_search_result(payload, needle=''):
    records=[];duplicates=set()
    terms=[x for x in _normalise(needle).split() if len(x)>3]
    for record in _walk_records(payload):
        ident=_first_text(record,'identificador','id','id_norma').upper()
        title=_first_text(record,'titulo','titulo_norma','nombre')
        if not BOE_ID.fullmatch(ident) or not title:continue
        if ident in duplicates:continue
        duplicates.add(ident)
        published=_first_text(record,'fecha_publicacion','fecha_disposicion')
        updated=_first_text(record,'fecha_actualizacion','fecha_ultima_actualizacion','ultima_actualizacion')
        score=sum(1 for term in terms if term in _normalise(title))
        # Preferencia por reales decretos de títulos, sin excluir el resto.
        if 'titulo de tecnico' in _normalise(title) or 'titulo de tecnica' in _normalise(title):score+=1
        records.append({'id':ident,'title':title,'publication_date':published,
                        'last_update':updated,'url':'https://www.boe.es/buscar/act.php?id='+ident,
                        'match_score':score,'status':'resultado_para_revision'})
    records.sort(key=lambda x:(-x['match_score'],x['id']))
    return records[:MAX_RESULTS]


def search_title(cycle, region, academic_year, *, opener=None):
    """Búsqueda real de legislación CONSOLIDADA; no todas las normas están en API.

    Usa SOLO términos de ciclo, nunca datos personales ni texto de la programación.
    """
    territory.require_territory(region)
    territory.year_code(academic_year)
    if not isinstance(cycle,str) or len(cycle)>180:
        raise ValueError('Denominación de ciclo no válida.')
    # Elimina siglas de nivel sin relevancia para la consulta.
    core=re.sub(r'^(?:(?:CFGM|CFGS|CFGB|Grado Medio|Grado Superior)\s+)+','',cycle.strip(),flags=re.I)
    core=re.sub(r'[^\wÀ-ÿ ]+',' ',core,flags=re.UNICODE).strip()
    if not 4<=len(core)<=150 or len(core.split())>20:
        raise ValueError('Indique el ciclo formativo de forma inequívoca.')
    # Consulta BOE por título; las horas semanales y calendarios se fijan en ámbitos autonómicos.
    expression='titulo:"'+core.replace('"','')+'"'
    query=json.dumps({'query':{'query_string':{'query':expression}}},ensure_ascii=False,separators=(',',':'))
    url=API+'?'+urlencode({'query':query,'limit':MAX_RESULTS,'offset':0})
    result=parse_search_result(_request_json(url,opener),core)
    return {'records':result,'search':core,'territory':territory.require_territory(region),
            'academic_year':territory.year_code(academic_year),'source':API,
            'notice':('Búsqueda de normas consolidadas del BOE; NO cubre todas las publicaciones ni los boletines autonómicos. '
                      'Los resultados son candidatos: verifique título, código, modificaciones y currículo de su comunidad. '
                      'Las horas lectivas y el calendario no se deducen de esta búsqueda.'),
            'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}


def inspect_boe_id(boe_id, *, opener=None):
    ident=str(boe_id or '').strip().upper()
    if not BOE_ID.fullmatch(ident):
        raise ValueError('Introduzca un identificador BOE-A-AAAA-NNN válido.')
    metadata=_request_json(API+'/id/'+ident+'/metadatos',opener)
    analysis=_request_json(API+'/id/'+ident+'/analisis',opener)
    rows=_walk_records(metadata)
    record=next((x for x in rows if _first_text(x,'identificador','id','id_norma').upper()==ident),None)
    if record is None:
        raise ValueError('No se han recibido metadatos identificables de esta norma. Consulte el BOE manualmente.')
    title=_first_text(record,'titulo','titulo_norma','nombre')
    details=analysis.get('data',{}) if isinstance(analysis,dict) else {}
    if isinstance(details,list):details=details[0] if details else {}
    if not isinstance(details,dict):details={}
    modifications=[]
    for entry in (details.get('afectada_por') or [])[:30]:
        if not isinstance(entry,dict):continue
        ref=_first_text(entry,'identificador','id').upper()
        if not BOE_ID.fullmatch(ref):continue
        modifications.append({'id':ref,'type':_first_text(entry,'tipo','relacion'),
                              'title':_first_text(entry,'titulo','nombre'),
                              'url':'https://www.boe.es/buscar/act.php?id='+ref})
    result={'id':ident,'title':title,'publication_date':_first_text(record,'fecha_publicacion'),
            'last_update':_first_text(record,'fecha_actualizacion','fecha_ultima_actualizacion'),
            'url':'https://www.boe.es/buscar/act.php?id='+ident,
            'metadata_url':API+'/id/'+ident+'/metadatos',
            'analysis_url':API+'/id/'+ident+'/analisis',
            'has_legal_analysis':bool(details),
            'reported_amendments':modifications, 'reported_amendment_count':len(modifications),
            'consolidation_state':_first_text(record,'estado_consolidacion'),
            'validity_date':_first_text(record,'fecha_vigencia'),
            'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'approval_required':True,
            'notice':('Los metadatos y el análisis se han obtenido del BOE. El texto consolidado tiene valor informativo; '
                      'no se ha acreditado por sí mismo que este sea el currículo aplicable a su módulo, curso y territorio. '
                      'Revise también las modificaciones posteriores y el boletín autonómico.')}
    return result
