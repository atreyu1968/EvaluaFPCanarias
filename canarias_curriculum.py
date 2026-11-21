"""Consulta acotada de los currículos canarios de la Resolución 25/04/2025.

Se recupera la versión HTML informativa del BOC; la confirmación documental
debe hacerse frente al PDF firmado. No importa automáticamente RA/CE/horas.
"""
from __future__ import annotations
import hashlib
import re
import urllib.request
from datetime import datetime, timezone

import curriculum_official as co

SOURCE_ID = 'BOC-A-2025-091-1728'
SOURCE_URL = 'https://www.gobiernodecanarias.org/boc/2025/091/1728.html'
TITLE = 'Resolución de 25/04/2025 (BOC 91, 08/05/2025)'
GB = 'CFGB Servicios Administrativos'
GM = 'CFGM Gestión Administrativa'
REGISTRY = {
    (GB, 'itinerario personal para la empleabilidad'): ('3159', 'V', 66, (5,5,3,3,4)),
    (GB, 'prevencion y salud laboral'): (None, 'V', 33, (6,6,5,3,7)),
    (GB, 'proyecto intermodular de aprendizaje colaborativo'): ('3160', 'V', 66, (9,5,5,4,4)),
    (GM, 'proyecto intermodular'): ('1713', 'VI', 64, (9,11,9,6,4)),
}


def hint(name, cycle):
    record = REGISTRY.get((co._cycle_key(cycle), co._module_key(name)))
    if not record:
        return None
    code, annex, hours, counts = record
    return {
        'source_id':SOURCE_ID, 'source_url':SOURCE_URL, 'source_title':TITLE,
        'source_annex':annex, 'module_code':code,
        'reference_annual_hours':hours, 'expected_ra':len(counts),
        'expected_ce':sum(counts), 'hours_confirmed':False,
        'curriculum_confirmed':False, 'status':'regional_source_requires_review'
    }


def parse(document, name, cycle):
    record = REGISTRY.get((co._cycle_key(cycle), co._module_key(name)))
    if not record:
        raise ValueError('No existe una referencia curricular canaria automática para este módulo y ciclo.')
    code, annex, hours, counts = record
    txt=co._plain(document).replace('\xa0',' ')
    # Limitar el documento a su anexo y al encabezado literal del módulo.
    section=re.search(r'(?im)^[ \t]*ANEXO[ \t]+'+annex+r'[ \t]*$',txt)
    if not section:
        raise ValueError('No se localiza el anexo canario esperado.')
    candidate=txt[section.end():]
    next_annex=re.search(r'(?im)^[ \t]*ANEXO[ \t]+[IVXLCDM]+[ \t]*$',candidate)
    if next_annex:
        candidate=candidate[:next_annex.start()]
    markers=list(re.finditer(r'(?im)^[ \t]*M[oó]dulo[ \t]+profesional[ \t]*:[ \t]*([^\r\n]+)',candidate))
    matches=[(i,m) for i,m in enumerate(markers) if co._module_key(m.group(1))==co._module_key(name)]
    if len(matches)!=1:
        raise ValueError('No se encuentra un encabezado inequívoco en el anexo canario.')
    i,m=matches[0]
    body=candidate[m.end():markers[i+1].start() if i+1<len(markers) else len(candidate)]
    heading=re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',body,re.I)
    if not heading:
        raise ValueError('No se localizan los resultados de aprendizaje.')
    header=body[:heading.start()]
    cm=re.search(r'(?im)^\s*C[oó]digo\s*:\s*(\d{4})(?!\d)',header)
    hm=re.search(r'(?im)^\s*Duraci[oó]n\s*:\s*(\d+)\s+horas',header)
    if (cm.group(1) if cm else None)!=code or not hm or int(hm.group(1))!=hours:
        raise ValueError('El código o la duración no coincide con la referencia del anexo canario.')
    content=body[heading.end():]
    # El BOC contiene rótulos de currículo, contenidos y pie institucional.
    # No se anexan esas líneas al último criterio.
    content=re.split(r'(?im)^[ \t]*(?:CURR[IÍ]CULO B[AÁ]SICO\b|Contenidos\s*[:.]|©|Gobierno de Canarias\s*$)',content,maxsplit=1)[0]
    outcomes=co.parse_ra_block(content)
    co.check_coverage(outcomes,counts)
    return {'outcomes':outcomes,'module_code':code,'reference_coverage':{
        'expected_ra':len(counts),'expected_ce':sum(counts),
        'criteria_per_ra':list(counts),'complete_for_original_source':True,
        'territorial_curriculum_confirmed':False
    }}


def fetch(name, cycle, consent=False):
    if consent is not True:
        raise ValueError('Debe autorizar la consulta al BOC.')
    meta=hint(name,cycle)
    if not meta:
        raise ValueError('No existe una referencia curricular canaria automática para este módulo y ciclo.')
    req=urllib.request.Request(SOURCE_URL,headers={'User-Agent':'EvaluaFP-ConsultaCurricular/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            raw=r.read(6_000_001)
            if len(raw)>6_000_000:
                raise ValueError('El documento excede el tamaño permitido.')
            html=raw.decode(r.headers.get_content_charset() or 'utf-8','replace')
    except (OSError,TimeoutError) as exc:
        raise ValueError('No se ha podido consultar el BOC. Revise la conexión.') from exc
    data=parse(html,name,cycle)
    data.update({
        'source':'BOC','source_id':SOURCE_ID,'source_url':SOURCE_URL,
        'source_title':TITLE,'source_annex':meta['source_annex'],
        'source_sha256':hashlib.sha256(raw).hexdigest(),
        'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'cycle':co._cycle_key(cycle),
        'warnings':[
            'Versión HTML informativa del BOC: coteje el PDF firmado y las disposiciones posteriores antes de confirmar.',
            'Los RA/CE mantienen su procedencia autonómica. No se confirman las horas ni se asignan ponderaciones.',
            'Incorpore a la programación Agenda Canaria de Desarrollo Sostenible 2030, igualdad de oportunidades y no discriminación.'
        ],
        'coverage':{'ra_cited':meta['expected_ra'],'ra_accepted':meta['expected_ra'],
                    'ce_proposed':meta['expected_ce'],'ce_accepted':meta['expected_ce'],'ce_discarded':0},
    })
    return data
