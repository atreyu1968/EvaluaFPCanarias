"""Tablas editables de instrumentos por evaluación y plan de evidencias FEOE.

Nunca modifica ni crea RA/CE ni los porcentajes curriculares. Las propuestas
locales son orientativas; las aportaciones de IA requieren consentimiento.
"""
from __future__ import annotations
from datetime import date
from collections import defaultdict
import json
import re
import ia

MAX_LEN = 3000


def text_field(value, field, limit=MAX_LEN):
    if not isinstance(value,str) or '\x00' in value or len(value)>limit:
        raise ValueError(f'{field}: se necesita texto de un máximo de {limit} caracteres.')
    return value.strip()


def normalize_term_assessments(rows):
    if not isinstance(rows,list) or len(rows)>3:
        raise ValueError('Debe configurar como máximo tres evaluaciones.')
    used=set();out=[]
    for item in rows:
        if not isinstance(item,dict):raise ValueError('Registro de evaluación incorrecto.')
        term=item.get('term')
        if type(term) is not int or term not in (1,2,3) or term in used:
            raise ValueError('Las evaluaciones deben identificarse de 1 a 3 sin duplicados.')
        used.add(term)
        out.append({'term':term,
                    'instruments':text_field(item.get('instruments',''),'instrumentos'),
                    'evidence':text_field(item.get('evidence',''),'evidencias'),
                    'resources':text_field(item.get('resources',''),'recursos'),
                    'recovery':text_field(item.get('recovery',''),'recuperación')})
    return sorted(out,key=lambda x:x['term'])


def normalize_feoe_tasks(rows):
    if not isinstance(rows,list) or len(rows)>500:raise ValueError('Existen demasiadas asignaciones de FEOE.')
    used=set();out=[]
    for item in rows:
        if not isinstance(item,dict):raise ValueError('Registro de criterio de empresa incorrecto.')
        code=text_field(item.get('criteria_code',''),'criterio FEOE',60)
        if not code or code.casefold() in used:raise ValueError('Los criterios FEOE deben ser únicos y no estar vacíos.')
        used.add(code.casefold())
        out.append({'criteria_code':code,
                    'activity':text_field(item.get('activity',''),'actividad en empresa'),
                    'evidence':text_field(item.get('evidence',''),'evidencia en empresa'),
                    'assessment_role':text_field(item.get('assessment_role',''),'responsable de seguimiento',150),
                    'support':text_field(item.get('support',''),'apoyos al aprendizaje',1000)})
    return out


def default_term_assessments(units, criteria):
    by_term=defaultdict(list)
    known={c['code']:c for c in criteria}
    for unit in units:
        by_term[int(unit['term'])].append(unit)
    result=[]
    for term in (1,2,3):
        assignments=by_term[term]
        codes=list(dict.fromkeys(c for u in assignments for c in u.get('criteria_codes',[]) if c in known))
        code_label=', '.join(codes[:16]) + ('…' if len(codes)>16 else '')
        title='; '.join(u['code'] for u in assignments) or 'Sin unidades asignadas'
        result.append({'term':term,
            'instruments':('Tareas de aplicación profesional con rúbrica; resolución de supuestos; '
                           'prueba práctica y portafolio de evidencias. Seleccionar los instrumentos pertinentes a las unidades.'),
            'evidence':f'Unidades: {title}. CE: {code_label or "pendientes de asignar"}. Registro de calificaciones por criterio y devolución individualizada.',
            'resources':'Supuestos contextualizados, documentos profesionales, aula y herramientas digitales disponibles en el centro (confirmar dotación).',
            'recovery':f'Actividades de refuerzo y nueva evidencia de los CE no superados al cierre de la {term}.ª evaluación, conforme a los acuerdos del departamento.'})
    return result


def default_feoe_tasks(selected, criteria):
    known={c['code'].casefold():c for c in criteria}
    results=[]
    for code in selected:
        found=known.get(code.casefold())
        if not found:continue
        description=found['description'].strip()
        results.append({'criteria_code':found['code'],
            'activity':f'Aplicación, cuando el entorno productivo lo permita, del criterio «{description[:220]}». Concretar la tarea con el centro y la empresa.',
            'evidence':'Registro supervisado de actividades, producto de trabajo anonimizado o informe de desempeño; definir el instrumento antes de la estancia.',
            'assessment_role':'Seguimiento conjunto del docente y del tutor o tutora de empresa; evaluación definitiva responsabilidad del docente.',
            'support':'Tarea graduada con indicaciones y supervisión, manteniendo el criterio oficial.'})
    return results


def review(units,criteria,selected,terms,tasks):
    valid={c['code'].casefold():c['code'] for c in criteria}
    unit_codes={u['code'].casefold() for u in units}
    notes=[]
    for term in (1,2,3):
        row=next((x for x in terms if x['term']==term),None)
        if any(u['term']==term for u in units):
            if not row or not row['instruments'] or not row['evidence']:
                notes.append(f'Evaluación {term}: indique instrumentos y evidencias de los CE de sus unidades.')
    selected_keys={c.casefold() for c in selected}
    task_keys={t['criteria_code'].casefold() for t in tasks}
    extra=task_keys-selected_keys
    if extra:notes.append('Hay tareas FEOE para CE no seleccionados: '+', '.join(sorted(extra)))
    missing=selected_keys-task_keys
    if missing:notes.append('Faltan tareas y evidencias FEOE para: '+', '.join(sorted(missing)))
    for t in tasks:
        if t['criteria_code'].casefold() not in valid:
            notes.append('FEOE: CE desconocido '+t['criteria_code'])
        if not t['activity'] or not t['evidence']:
            notes.append('FEOE: falta actividad o evidencia para '+t['criteria_code'])
    return notes


def ai_enrich(db,module_id,units,criteria,term_rows,feoe_rows,authorize_ai=False):
    """No guarda nada; respuesta completa y controlada para aceptación individual en UI."""
    if authorize_ai is not True:raise ValueError('Se necesita consentimiento expreso para enviar RA, CE y plan a la IA.')
    if not ia.key_available():raise ValueError('Configure y desbloquee su API de inteligencia artificial.')
    from program_assistant import module_context
    module,ras,ces=module_context(db,module_id)
    codes={c['code'] for c in ces}
    if not isinstance(units,list) or len(units)>100:raise ValueError('Unidades no válidas.')
    if not all(isinstance(u,dict) and isinstance(u.get('criteria_codes'),list) and all(c in codes for c in u['criteria_codes']) for u in units):
        raise ValueError('Las unidades deben contener exclusivamente CE confirmados.')
    terms=normalize_term_assessments(term_rows)
    feoe=normalize_feoe_tasks(feoe_rows)
    if any(x['criteria_code'] not in codes for x in feoe):raise ValueError('La selección FEOE incluye CE desconocidos.')
    prompt={'tarea':'Redacta instrumentos y evidencias de evaluación trimestrales y tareas de formación en empresa para una programación didáctica de FP. Devuelve JSON estricto: {"terms":[{"term":1,"instruments":"...","evidence":"...","resources":"...","recovery":"..."}],"feoe":[{"criteria_code":"...","activity":"...","evidence":"...","assessment_role":"..."}]}',
      'restricciones':['Conserva EXACTAMENTE los tres trimestres y solo los CE FEOE proporcionados.',
       'No inventes fechas, horas, porcentajes, leyes, recursos confirmados ni datos personales.',
       'No asumas que una actividad en empresa ha sido autorizada; deben coordinarse con tutoría y empresa.',
       'Relaciona los instrumentos con los CE y unidades de cada periodo.',
       'Para datos desconocidos señala pendiente de confirmar por el docente.'],
      'modulo':module['name'],'ciclo':module['cycle'],
      'unidades':[{'codigo':u['code'],'titulo':u['title'],'evaluacion':u['term'],'criterios':u['criteria_codes']} for u in units],
      'CE':[{'code':c['code'],'description':c['description'][:260]} for c in ces if c['code'] in {x for u in units for x in u['criteria_codes']} or c['code'] in {x['criteria_code'] for x in feoe}],
      'evaluaciones':terms,'feoe':feoe}
    data,model=ia.chat('generation',json.dumps(prompt,ensure_ascii=False),limit=14500)
    if not isinstance(data,dict):raise ValueError('La IA no ha devuelto un plan estructurado.')
    nt=normalize_term_assessments(data.get('terms'));nf=normalize_feoe_tasks(data.get('feoe'))
    if {x['term'] for x in nt}!={1,2,3} or {x['criteria_code'] for x in nf}!={x['criteria_code'] for x in feoe}:
        raise ValueError('La IA ha omitido evaluaciones o modificado criterios FEOE. La propuesta se ha rechazado.')
    return {'terms':nt,'feoe':nf,'source':'IA ('+model+')','requires_acceptance':True}
