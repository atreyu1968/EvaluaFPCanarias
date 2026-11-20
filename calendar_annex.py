"""Extracción estructural y conservadora de tablas y líneas de anexos FP.

No deduce el curso ni traslada fechas entre etapas. Solo devuelve registros de
texto con cabeceras explícitas y una fila que identifica FP sin ambigüedad.
"""
from __future__ import annotations
import re
import territorial_profiles as territory

STAGE_RX = re.compile(r'\b(?:fp|formacion profesional|ciclos? formativos?|grado d)\b')
OTHER_RX = re.compile(r'\b(?:bachillerato|infantil|primaria|eso|educacion especial)\b')
STAGE_HEADERS = ('etapa','ensenanza','ensenanzas','nivel educativo','estudios','tipo de ensenanza')
DATE_VALUE = re.compile(r'^(?:20\d{2}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2}|\d{1,2}\s+de\s+\w+\s+de\s+20\d{2})$',re.I)
RANGE_VALUE = re.compile(r'\b(?:del|desde|entre)\b.+\b(?:al|hasta|y)\b',re.I)


def _head(value):
    return territory.fold(str(value or '').replace('\n',' ')).strip()


def _kind(header):
    h=_head(header)
    if h in STAGE_HEADERS:return 'stage'
    if 'inicio' in h or 'comienzo' in h:
        if any(k in h for k in ('clases','lectiva','actividad','curso')):return 'start'
    if 'fin ' in h or h.startswith('fin') or 'finalizacion' in h or 'final de' in h:
        if any(k in h for k in ('clases','lectiva','actividad','curso')):return 'end'
    if 'vacaciones' in h or 'navidad' in h or 'semana santa' in h:return 'vacation'
    return None


def table_records(matrix, origin):
    """Filas FP con cabeceras completas; evita calendarios mixtos de otras etapas.

    Los valores tienen que contener el año, y cada campo procede de una
    columna inequívoca. El texto original de cabecera y fila queda como prueba.
    """
    if not isinstance(matrix,list) or len(matrix)>400:return []
    for header_index,raw_header in enumerate(matrix[:6]):
        if not isinstance(raw_header,(list,tuple)):continue
        kinds={}
        for i,cell in enumerate(raw_header):
            kind=_kind(cell)
            if kind:
                if kind in kinds:kinds[kind]=-1
                else:kinds[kind]=i
        if kinds.get('stage',-1)<0 or not any(kinds.get(k,-1)>=0 for k in ('start','end','vacation')):
            continue
        rows=[]
        for pos,raw in enumerate(matrix[header_index+1:],header_index+2):
            if not isinstance(raw,(list,tuple)):continue
            if kinds['stage']>=len(raw):continue
            stage=_head(raw[kinds['stage']])
            if not STAGE_RX.search(stage) or OTHER_RX.search(stage):continue
            evidence='Encabezados: '+' | '.join(str(x or '') for x in raw_header)
            evidence+='; fila: '+' | '.join(str(x or '') for x in raw)
            for kind,label in [('start','Inicio de las clases de FP'),('end','Fin de las clases de FP'),
                               ('vacation','Vacaciones de FP')]:
                index=kinds.get(kind,-1)
                if index<0 or index>=len(raw):continue
                value=' '.join(str(raw[index] or '').split())
                if not value:continue
                if kind=='vacation':
                    if not RANGE_VALUE.search(territory.fold(value)):continue
                    display=f'Vacaciones de FP {value}'
                else:
                    if not DATE_VALUE.fullmatch(territory.fold(value)):continue
                    display=f'{label}: {value}'
                rows.append({'text':display,'location':f'{origin}, fila {pos}',
                             'excerpt':evidence[:450]})
        return rows
    return []


def stitched_records(records, date_re, range_re, start_re, end_re, school_re, vacation_re):
    """Reconstruye contextos divididos por saltos de línea, sin cambiar páginas.

    Solo une un encabezado *explícito* seguido inmediatamente de una fecha
    aislada, o un encabezado de vacaciones seguido de un intervalo completo.
    """
    extra=[]
    for i in range(len(records)-1):
        a,b=records[i],records[i+1]
        origin_a=a['location'].split(', línea ')[0]
        origin_b=b['location'].split(', línea ')[0]
        if origin_a!=origin_b:continue
        text_a=' '.join(a['text'].split())
        text_b=' '.join(b['text'].split())
        if len(text_a)>180 or len(text_b)>220:continue
        fa,fb=territory.fold(text_a),territory.fold(text_b)
        if date_re.search(fa):continue
        if ((school_re.search(fa) and (start_re.search(fa) or end_re.search(fa))
             and date_re.fullmatch(fb)) or
            (vacation_re.search(fa) and range_re.fullmatch(fb))):
            extra.append({'text':text_a+' '+text_b,'location':a['location']+' + línea siguiente',
                          'excerpt':text_a+' '+text_b})
    return records+extra
