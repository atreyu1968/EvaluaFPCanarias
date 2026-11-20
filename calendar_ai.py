"""IA opcional para fragmentos de calendario: propuestas sustentadas por citas.

El proveedor recibe solamente el texto que copia y autoriza el docente.
Ni una fecha ni una cita del modelo se aceptan sin su presencia literal
en el fragmento, ni se alteran módulos, programaciones o evaluaciones.
"""
from __future__ import annotations
from datetime import date
from hashlib import sha256
import json
import re

import calendar_document as calendar
import territorial_profiles as territories
import ia

MAX_CHARS=12000
FIELDS={'start_date','end_date','vacation_periods','regional_non_teaching_days'}


def _quoted(value, source, limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        return ''
    quote=' '.join(value.strip().split())
    return quote if territories.fold(quote) in territories.fold(source) else ''


def _dates(quote):
    out=[]
    for match in calendar.DATE_RE.finditer(territories.fold(quote)):
        try:out.append(calendar._parse_date(match.group(1)))
        except ValueError:pass
    return out


def _year_date(raw, year):
    try:
        if not isinstance(raw,str) or not re.fullmatch(r'20\d{2}-\d{2}-\d{2}',raw):
            return None
        parsed=date.fromisoformat(raw)
        return parsed if calendar._within_course(parsed,year) else None
    except ValueError:return None


def _verified_proposal(item, fragment, year):
    if not isinstance(item,dict):return None
    field=item.get('field')
    if field not in FIELDS:return None
    quote=_quoted(item.get('evidence_quote'),fragment,420)
    heading=_quoted(item.get('heading_quote'),fragment,300) if item.get('heading_quote') else ''
    if not quote:return None
    merged=territories.fold(quote+' '+heading)
    if calendar.OTHER_STAGE_RE.search(merged) and not calendar.FP_RE.search(merged):
        return None
    found=_dates(quote)
    if not found:return None
    start=_year_date(item.get('date'),year)
    if not start or start not in found:return None
    if field in ('start_date','end_date'):
        if not calendar.SCHOOL_RE.search(merged) or calendar.EVAL_RE.search(merged):
            return None
        wanted=calendar.START_RE if field=='start_date' else calendar.END_RE
        if not wanted.search(merged):return None
        if len(found)==1 and (not (calendar.START_RE.search(merged) and calendar.END_RE.search(merged))):
            pass
        elif len(found)==2 and heading:
            # La fila con dos fechas solo es interpretable si una cabecera
            # literal ordena expresamente Inicio y Fin.
            label=territories.fold(heading)
            starts=[m.start() for m in calendar.START_RE.finditer(label)]
            ends=[m.start() for m in calendar.END_RE.finditer(label)]
            if len(starts)!=1 or len(ends)!=1:return None
            first_is_start=starts[0]<ends[0]
            expected=found[0] if ((field=='start_date')==first_is_start) else found[1]
            if start!=expected:return None
        else:return None
        value=start.isoformat()
        label='Inicio de clases' if field=='start_date' else 'Fin de clases'
    elif field=='vacation_periods':
        if not calendar.VACATION_RE.search(merged) or len(found)!=2:return None
        finish=_year_date(item.get('date_end'),year)
        if not finish or finish not in found or (found[0],found[1])!=(start,finish):
            return None
        if finish<start or (finish-start).days>100:return None
        value={'start':start.isoformat(),'end':finish.isoformat(),
               'label':calendar._period_label(merged)}
        label='Vacaciones / periodo no lectivo'
    else:
        if not calendar.HOLIDAY_RE.search(merged) or calendar.VACATION_RE.search(merged):
            return None
        if len(found)!=1:return None
        value={'date':start.isoformat(),'reason':quote[:120]}
        label='Festivo / día no lectivo'
    return {'field':field,'value':value,'label':label,
            'excerpt':(heading+' | ' if heading else '')+quote,
            'location':'fragmento facilitado por el docente (cita textual comprobada)',
            'source':'propuesta_ia_sin_verificar_vigencia'}


def interpret(fragment, region, academic_year, authorize_ai=False):
    """Consulta al modelo una sola vez. Descarta cualquier fecha no citada.

    Retorna candidatos compatibles con calendar_document.preview_document,
    sin persistir la respuesta y sin incorporar referencias normativas.
    """
    if authorize_ai is not True:
        raise ValueError('Debe autorizar expresamente el envío de este fragmento a la IA configurada.')
    region=territories.require_territory(region)
    academic_year=territories.year_code(academic_year)
    if not isinstance(fragment,str) or not 35<=len(fragment)<=MAX_CHARS or '\x00' in fragment:
        raise ValueError('Copie un fragmento del calendario de entre 35 y 12.000 caracteres.')
    # El ámbito territorial, el curso y la referencia FP deben estar
    # realmente presentes antes de enviar contenido a un tercero.
    baseline=calendar.preview_document('fragmento.txt',fragment.encode('utf-8'),region,academic_year)
    if not baseline['scope_ok']:
        raise ValueError('El fragmento debe contener literalmente la comunidad, el curso y la referencia a FP antes de consultarlo con IA.')
    prompt={
      'tarea':'Ayuda a localizar fechas explicitas del calendario de FP en un fragmento que puede contener tablas.',
      'territorio':region,'curso_academico':academic_year,'fragmento_textual':fragment,
      'formato_salida':{'proposals':[{'field':'start_date|end_date|vacation_periods|regional_non_teaching_days',
                     'date':'AAAA-MM-DD','date_end':'AAAA-MM-DD solo para vacation_periods',
                     'evidence_quote':'Cita literal donde se vea la fecha completa',
                     'heading_quote':'Cabecera literal adicional solo cuando la tabla lo requiera'}]},
      'reglas':[
        'No inventes fechas ni años; cada fecha debe figurar literalmente en evidence_quote.',
        'Solo FP del curso y territorio indicados, nunca Bachillerato, Primaria o ESO.',
        'Usa heading_quote solo con una cabecera que aparece realmente en el fragmento.',
        'No supongas festivos estatales, municipales ni evaluaciones.',
        'Para intervalos exige dos fechas completas y el mismo orden del original.',
        'Si un dato es ambiguo, omítelo. Máximo 24 propuestas. Responde solo JSON.'
      ]}
    result,model=ia.chat('analysis',json.dumps(prompt,ensure_ascii=False))
    proposals=result.get('proposals') if isinstance(result,dict) else None
    if not isinstance(proposals,list) or len(proposals)>24:
        raise ValueError('La IA no ha devuelto una lista limitada de propuestas contrastables.')
    grouped={};warnings=[]
    for i,raw in enumerate(proposals,1):
        candidate=_verified_proposal(raw,fragment,academic_year)
        if not candidate:
            warnings.append(f'Propuesta {i}: cita, fecha, columna o contexto no coincidentes con el fragmento; descartada.')
            continue
        field=candidate.pop('field')
        grouped.setdefault(field,[]).append(candidate)
    for field in tuple(grouped):
        seen=set();unique=[]
        for item in grouped[field]:
            key=json.dumps(item['value'],sort_keys=True,ensure_ascii=False)
            if key not in seen:unique.append(item);seen.add(key)
        if field in ('start_date','end_date') and len(unique)>1:
            grouped[field]=[]
            warnings.append(f'{field}: la IA ha propuesto fechas incompatibles; se descartan.')
        elif field=='vacation_periods':
            by_label={}
            for item in unique:by_label.setdefault(item['value']['label'],[]).append(item)
            grouped[field]=[items[0] for items in by_label.values() if len(items)==1]
            if any(len(items)>1 for items in by_label.values()):
                warnings.append('Vacaciones: periodos incompatibles con la misma denominación; se descartan.')
        else:
            grouped[field]=unique[:80]
    if grouped.get('start_date') and grouped.get('end_date'):
        if grouped['start_date'][0]['value']>=grouped['end_date'][0]['value']:
            grouped['start_date']=[];grouped['end_date']=[]
            warnings.append('El inicio y fin propuestos son incompatibles; ambos se descartan.')
    count=sum(len(values) for values in grouped.values())
    if not count:warnings.append('La IA no ha encontrado ninguna fecha con una cita literal suficiente.')
    return {'filename':'Fragmento revisado con IA','sha256':sha256(fragment.encode('utf-8')).hexdigest(),
            'region':region,'academic_year':academic_year,'scope_ok':True,
            'scope':baseline['scope'],'candidates':grouped,'candidate_count':count,
            'warnings':warnings[:40],'ocr_used':False,'ocr_pages':0,
            'requires_teacher_confirmation':True,'no_changes_saved':True,'source_type':'ia_fragment',
            'ai_model':model,'evidence_check':'fechas_y_citas_textuales_comprobadas',
            'notice':('La IA solo ha propuesto fechas textuales verificadas en el fragmento que usted aportó. '
                      'No se ha cotejado el boletín oficial, su vigencia ni la etapa específica del centro; '
                      'compruébelas antes de cargar el borrador. No se ha guardado ni modificado nada.')}
