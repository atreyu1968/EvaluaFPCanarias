"""Asistente de programación didáctica 1.1 (borradores locales, sin IA obligatoria).

La base curricular RA/CE procede exclusivamente de registros confirmados por el docente.
Una exportación es un BORRADOR y no acredita aprobación institucional.
"""
from __future__ import annotations

import io
import json
import math
import re
from html import escape

import database as database
import schedule_engine
import official_catalog
import territorial_profiles as territory
import program_assistant
import planning_matrix

ALLOWED_FIELDS = (
    'source_type', 'region', 'official_module_code', 'official_cycle_code', 'fp_regime',
    'curriculum_source_url', 'curriculum_source_description', 'center', 'teacher', 'department', 'academic_context',
    'normative_references', 'objectives', 'competencies', 'methodology', 'resources',
    'inclusion', 'assessment', 'instruments', 'recovery', 'enterprise', 'observations',
    'justification', 'center_characteristics', 'student_characteristics', 'environment_context',
    'identification_data', 'qualifications', 'contents', 'learning_activities',
    'interdisciplinarity', 'extracurricular', 'assessment_sessions', 'grading',
    'promotion', 'attendance', 'extraordinary_assessment',
)
TEXT_LIMIT = 12000
VALID_SOURCES = ('import', 'create', 'evaluation')


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS programming_drafts (
      module_id INTEGER PRIMARY KEY REFERENCES modules(id) ON DELETE CASCADE,
      content_json TEXT NOT NULL, updated_at TEXT NOT NULL)''')


def _check_string(value, label, limit=TEXT_LIMIT):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError(f'El campo {label} debe ser texto y no superar {limit} caracteres.')
    return value.strip()


def normalise(raw, academic_year='2026-2027'):
    if not isinstance(raw, dict):
        raise ValueError('La programación debe contener campos de formulario.')
    unknown = set(raw) - set(ALLOWED_FIELDS) - {'units','schedule','activities','imported_sections','import_info','assistant_meta','units_mode','term_assessments','feoe_tasks','curriculum_confirmed'}
    if unknown:
        raise ValueError('La programación contiene campos no reconocidos.')
    fields = {key: _check_string(raw.get(key, ''), key) for key in ALLOWED_FIELDS}
    fields['region']=territory.require_territory(fields['region'])
    if fields['fp_regime'] not in ('','pendiente','general','intensivo'):
        raise ValueError('Seleccione el régimen de FP Dual: general, intensivo o pendiente.')
    from urllib.parse import urlsplit
    curriculum_url=fields['curriculum_source_url']
    if curriculum_url and (urlsplit(curriculum_url).scheme not in ('http','https') or not urlsplit(curriculum_url).netloc):
        raise ValueError('Indique una dirección HTTP(S) válida del currículo oficial.')
    curriculum_confirmed=raw.get('curriculum_confirmed',False)
    if type(curriculum_confirmed) is not bool:
        raise ValueError('La confirmación de currículo debe ser verdadera o falsa.')
    if curriculum_confirmed and not curriculum_url:
        raise ValueError('Antes de confirmar el currículo incluya el enlace a la fuente oficial contrastada.')
    if fields['source_type'] not in VALID_SOURCES:
        raise ValueError('Seleccione una vía de preparación del módulo.')
    units = raw.get('units', [])
    if not isinstance(units, list) or len(units) > 100:
        raise ValueError('Se admiten hasta 100 unidades didácticas.')
    prepared = []
    codes = set()
    for index, item in enumerate(units, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Unidad {index}: formato inválido.')
        code = _check_string(item.get('code', ''), 'código de unidad', 30)
        title = _check_string(item.get('title', ''), 'título de unidad', 220)
        term = str(item.get('term', '')).strip()
        if not code or not title or term not in ('1', '2', '3'):
            raise ValueError(f'Unidad {index}: indique código, título y trimestre (1, 2 o 3).')
        if code.casefold() in codes:
            raise ValueError(f'Código de unidad repetido: {code}.')
        codes.add(code.casefold())
        try:
            hours = float(item.get('hours', 0))
        except (TypeError, ValueError):
            raise ValueError(f'Unidad {code}: horas no válidas.') from None
        if not math.isfinite(hours) or hours <= 0 or hours > 1000:
            raise ValueError(f'Unidad {code}: las horas deben ser mayores que cero y menores o iguales que 1000.')
        ids = item.get('criteria_codes', [])
        if not isinstance(ids, list) or len(ids) > 100:
            raise ValueError(f'Unidad {code}: listado de criterios incorrecto.')
        ce = []
        for ident in ids:
            val = _check_string(ident, 'código de criterio', 60)
            if not val:
                continue
            if val not in ce:
                ce.append(val)
        prepared.append({'code': code, 'title': title, 'term': int(term),
                         'hours': round(hours, 2), 'criteria_codes': ce,
                         'resources': _check_string(item.get('resources',''), 'recursos de unidad', 3000),
                         'instruments': _check_string(item.get('instruments',''), 'instrumentos de unidad', 3000)})
    activity_items = raw.get('activities', [])
    if not isinstance(activity_items, list) or len(activity_items) > 80:
        raise ValueError('Se admiten hasta 80 actividades complementarias o extraescolares.')
    activities = []
    for i, activity in enumerate(activity_items, 1):
        if not isinstance(activity, dict) or activity.get('type') not in ('complementaria','extraescolar'):
            raise ValueError(f'Actividad {i}: tipo incorrecto.')
        title = _check_string(activity.get('title', ''), 'actividad', 200)
        when = _check_string(activity.get('date', ''), 'fecha de actividad', 10)
        if when:
            schedule_engine._date(when, 'fecha de actividad')
        if not title:
            raise ValueError(f'Actividad {i}: falta el título.')
        activities.append({'type': activity['type'], 'title': title, 'date': when,
                           'unit_code': _check_string(activity.get('unit_code',''), 'unidad vinculada', 30),
                           'description': _check_string(activity.get('description',''), 'descripción', 3000),
                           'resources': _check_string(activity.get('resources',''), 'recursos', 1000)})
    imported = raw.get('imported_sections', [])
    if not isinstance(imported, list) or len(imported)>120:
        raise ValueError('Se admiten hasta 120 apartados importados.')
    safe_sections=[]
    for n,sec in enumerate(imported,1):
        if not isinstance(sec,dict):raise ValueError('Apartado importado incorrecto.')
        safe_sections.append({
            'title':_check_string(sec.get('title',''),f'título de apartado {n}',220),
            'field':_check_string(sec.get('field') or '',f'asignación {n}',75),
            'page_start':int(sec.get('page_start') or 1),
            'page_end':int(sec.get('page_end') or 1),
            'body':_check_string(sec.get('body',''),f'texto de apartado {n}',60000),
            'programming_id':int(sec.get('programming_id') or 0)})
    if sum(len(sec['body']) for sec in safe_sections)>300000:
        raise ValueError('Los apartados importados superan 300.000 caracteres.')
    info=raw.get('import_info') or {}
    if not isinstance(info,dict):raise ValueError('Información de procedencia incorrecta.')
    info={'programming_id':int(info.get('programming_id') or 0),
          'filename':_check_string(info.get('filename',''),'nombre original',250),
          'applied_fields':[v for v in info.get('applied_fields',[]) if v in ALLOWED_FIELDS][:len(ALLOWED_FIELDS)],
          'source_type':'documento_importado'}
    meta=raw.get('assistant_meta') or {}
    if not isinstance(meta,dict) or len(meta)>len(ALLOWED_FIELDS):
        raise ValueError('Metadatos de propuestas incorrectos.')
    safe_meta={}
    for key,value in meta.items():
        if key not in ALLOWED_FIELDS or not isinstance(value,dict):
            raise ValueError('Metadatos de propuesta no válidos.')
        safe_meta[key]={'origin':_check_string(value.get('origin',''),'origen de propuesta',140),
                        'teacher_edited':bool(value.get('teacher_edited',False))}
    units_mode=raw.get('units_mode','auto')
    if units_mode not in ('auto','manual'):
        raise ValueError('Modo de organización de unidades desconocido.')
    return {**fields, 'curriculum_confirmed':curriculum_confirmed, 'assistant_meta':safe_meta, 'units_mode':units_mode, 'units': prepared, 'activities': activities,
            'term_assessments':planning_matrix.normalize_term_assessments(raw.get('term_assessments',[])),
            'feoe_tasks':planning_matrix.normalize_feoe_tasks(raw.get('feoe_tasks',[])),
            'imported_sections':safe_sections,'import_info':info,
            'schedule': schedule_engine.clean(raw.get('schedule'), academic_year)}



def _suggest_schedule_hours(draft,db,module_id):
    """Ofrece el dato catalogado con procedencia, sin declarar vigencia aprobada."""
    cfg=draft['schedule']
    cfg['region']=territory.require_territory(draft.get('region','Canarias'))
    if cfg.get('weekly_hours') or cfg.get('total_hours') or cfg.get('hours_confirmed'):
        return
    module=db.execute('SELECT name,cycle,academic_year FROM modules WHERE id=?',(module_id,)).fetchone()
    import national_registry
    verified= national_registry.find_hours_for(db,dict(module),draft,territory.territory_code(draft.get('region','Canarias')))
    # Si el usuario eligió una referencia histórica de 2024, no propagar
    # sus horas al calendario actual ni por coincidencia con el catálogo legado.
    # Una fuente de horas contrastada por el docente (national_registry) conserva
    # preferencia, pero tampoco se considera confirmada automáticamente.
    import canarias_reference
    captured_reference=canarias_reference.read(db,module_id)
    legacy=(official_catalog.find(draft.get('region','Canarias'),module['cycle'],module['name'],draft.get('official_module_code',''))
            if module['academic_year']=='2026-2027' and captured_reference is None else None)
    proposal=verified or legacy
    if proposal:
        cfg['weekly_hours']=proposal['weekly_hours']
        cfg['total_hours']=proposal['total_hours']
        cfg['hours_source_url']=proposal['source_url']
        cfg['hours_source_description']=(proposal.get('source_title') or 'Ficha de referencia Canarias, Anexo VI 2024; confirmar modificaciones vigentes')
        cfg['hours_confirmed']=False


def load(db, module_id):
    if not db.execute('SELECT id FROM modules WHERE id=?', (module_id,)).fetchone():
        raise ValueError('El módulo seleccionado no existe.')
    record = db.execute('SELECT content_json, updated_at FROM programming_drafts WHERE module_id=?',
                        (module_id,)).fetchone()
    module_row=db.execute('SELECT academic_year,territory FROM modules WHERE id=?',(module_id,)).fetchone()
    academic_year=module_row['academic_year']
    if record:
        draft=json.loads(record['content_json'])
        draft.setdefault('region',module_row['territory'] or 'Canarias')
        draft['region']=territory.require_territory(draft['region'])
        raw_schedule=draft.get('schedule') or {}
        raw_schedule['region']=draft['region'] if 'region' not in raw_schedule else raw_schedule['region']
        draft['schedule'] = schedule_engine.clean(raw_schedule, academic_year)
        if draft['schedule']['region'] != draft['region']:
            draft['schedule'].update(schedule_engine.fresh_calendar(academic_year,draft['region']))
            draft['schedule']['hours_confirmed']=False
        draft.setdefault('activities', [])
        draft.setdefault('imported_sections', [])
        draft.setdefault('import_info', {})
        draft.setdefault('assistant_meta', {})
        draft.setdefault('units_mode', 'auto')
        draft.setdefault('curriculum_confirmed',False)
        draft.setdefault('term_assessments', [])
        draft.setdefault('feoe_tasks', [])
        for key in ALLOWED_FIELDS:draft.setdefault(key,'')
        for unit in draft.get('units', []):
            unit.setdefault('instruments', '')
            unit.setdefault('resources', '')
        _suggest_schedule_hours(draft,db,module_id)
        return {'draft': draft, 'updated_at': record['updated_at']}
    region=territory.require_territory(module_row['territory'] or 'Canarias')
    draft={**{key: '' for key in ALLOWED_FIELDS}, 'source_type': 'import',
           'region': region, 'units': [], 'activities': [],
           'imported_sections': [], 'import_info': {}, 'assistant_meta': {}, 'units_mode':'auto',
           'term_assessments': [], 'feoe_tasks': [], 'curriculum_confirmed':False,
           'schedule': schedule_engine.defaults(academic_year,region)}
    _suggest_schedule_hours(draft,db,module_id)
    return {'draft': draft, 'updated_at': None}


def save(db, module_id, body):
    if not db.execute('SELECT id FROM modules WHERE id=?', (module_id,)).fetchone():
        raise ValueError('El módulo seleccionado no existe.')
    academic_year=db.execute('SELECT academic_year FROM modules WHERE id=?',(module_id,)).fetchone()[0]
    clean = normalise(body,academic_year)
    stored_region=db.execute('SELECT territory FROM modules WHERE id=?',(module_id,)).fetchone()[0]
    if territory.require_territory(stored_region) != clean['region']:
        clean['curriculum_confirmed']=False
    # No atribuir a una comunidad las fechas o fuentes del territorio anterior.
    if clean['schedule']['region'] != clean['region']:
        clean['schedule'].update(schedule_engine.fresh_calendar(academic_year,clean['region']))
        clean['schedule']['hours_confirmed']=False
        clean['schedule']['weekly_hours']=0
        clean['schedule']['total_hours']=0
        clean['schedule']['weekday_hours']=[0,0,0,0,0]
        clean['schedule']['hours_source_url']=''
        clean['schedule']['hours_source_description']='Cambio de comunidad: pendiente de comprobar el horario oficial'
    clean['schedule']['region']=clean['region']
    db.execute('UPDATE modules SET territory=? WHERE id=?',(clean['region'],module_id))
    db.execute('''INSERT INTO programming_drafts(module_id,content_json,updated_at)
        VALUES(?,?,?) ON CONFLICT(module_id) DO UPDATE SET
        content_json=excluded.content_json,updated_at=excluded.updated_at''',
        (module_id, json.dumps(clean, ensure_ascii=False), database.now()))
    database.log(db, 'programming_draft_saved', 'module', module_id,
                 {'unit_count': len(clean['units']), 'source_type': clean['source_type']})
    return {'saved': True, 'diagnosis': diagnose(db, module_id)}


def diagnose(db, module_id):
    module = db.execute('SELECT id,name,cycle,academic_year FROM modules WHERE id=?', (module_id,)).fetchone()
    if module is None:
        raise ValueError('Módulo no encontrado.')
    loaded = load(db, module_id)
    draft = loaded['draft']
    outcomes = db.execute('SELECT id,code,description,weight FROM outcomes WHERE module_id=? ORDER BY id',
                          (module_id,)).fetchall()
    criteria = db.execute('''SELECT c.id,c.code,c.description,c.weight,c.outcome_id,o.code AS ra_code
                             FROM criteria c JOIN outcomes o ON o.id=c.outcome_id
                             WHERE o.module_id=? ORDER BY o.id,c.id''', (module_id,)).fetchall()
    import weight_defaults
    ras_return=[]
    for r in outcomes:
        one=dict(r);one['weight_origin']=weight_defaults.origin(db,'ra',r['id']) or 'default';ras_return.append(one)
    ces_return=[]
    for c in criteria:
        one=dict(c);one['weight_origin']=weight_defaults.origin(db,'ce',c['id']) or 'default';ces_return.append(one)
    docs = db.execute('SELECT COUNT(*) FROM programmings WHERE module_id=?', (module_id,)).fetchone()[0]
    errors = []
    warnings = []
    if not outcomes:
        errors.append('No hay RA confirmados. Importe una programación o incorpore el currículo desde una fuente verificada.')
    if not criteria:
        errors.append('No hay criterios de evaluación confirmados.')
    if outcomes:
        missing = [r['code'] for r in outcomes if not any(c['outcome_id'] == r['id'] for c in criteria)]
        if missing:
            errors.append('RA sin criterios de evaluación: ' + ', '.join(missing) + '.')
        if any(not r['description'].strip() for r in outcomes) or any(not c['description'].strip() for c in criteria):
            errors.append('Hay RA o CE sin descripción completa.')
        if any(r['weight'] is None for r in outcomes) or any(c['weight'] is None for c in criteria):
            warnings.append('Hay ponderaciones pendientes de revisión.')
        ra_weights = [r['weight'] for r in outcomes]
        if all(x is not None for x in ra_weights) and abs(sum(ra_weights) - 100) > 0.11:
            warnings.append(f'La suma de ponderaciones de RA es {sum(ra_weights):.2f} %, no 100 %. Revísela.')
        for r in outcomes:
            ce_weights = [c['weight'] for c in criteria if c['outcome_id'] == r['id']]
            if ce_weights and all(x is not None for x in ce_weights) and abs(sum(ce_weights) - 100) > 0.11:
                warnings.append(f'Los CE de {r["code"]} suman {sum(ce_weights):.2f} %, no 100 %.')
    if not docs and draft['source_type'] == 'import':
        warnings.append('Todavía no ha incorporado el documento de programación original.')
    if not draft.get('official_module_code'):
        warnings.append('Compruebe e identifique el código oficial del módulo para evitar coincidencias ambiguas.')
    if not draft.get('curriculum_source_url'):
        warnings.append('Falta el enlace al currículo oficial del título y comunidad del curso seleccionado.')
    elif not draft.get('curriculum_confirmed'):
        warnings.append('La fuente curricular está indicada, pero el docente aún no la ha contrastado y confirmado.')
    if not draft['normative_references'].strip():
        warnings.append('Indique y compruebe las referencias normativas aplicables al módulo y curso.')
    if not draft['assessment'].strip():
        warnings.append('Describa el procedimiento de evaluación y criterios de calificación.')
    if not draft['enterprise'].strip():
        warnings.append('Especifique el tratamiento de la formación en empresa, si procede.')
    if not draft['methodology'].strip() and draft['source_type'] != 'evaluation':
        warnings.append('Falta la metodología didáctica para una programación completa.')
    if not draft['recovery'].strip():
        warnings.append('Falta describir el procedimiento de recuperación.')
    from collections import Counter
    counts_by_ce=Counter(code.casefold() for u in draft['units'] for code in u['criteria_codes'])
    repeated=[code for code,n in counts_by_ce.items() if n>1]
    if repeated:
        warnings.append('Hay CE vinculados a varias unidades: '+', '.join(repeated[:20])+'. Compruebe que no se cuenta dos veces la misma evidencia.')
    available = {c['code'].casefold(): c['code'] for c in criteria}
    covered = set()
    for unit in draft['units']:
        for key in unit['criteria_codes']:
            if key.casefold() not in available:
                warnings.append(f'La unidad {unit["code"]} cita un CE desconocido: {key}.')
            else:
                covered.add(key.casefold())
    if draft['source_type'] != 'evaluation':
        if not draft['units']:
            warnings.append('No se han distribuido las unidades didácticas ni los CE por trimestres.')
        elif criteria:
            missing_codes = [c['code'] for c in criteria if c['code'].casefold() not in covered]
            if missing_codes:
                warnings.append('CE no asociados a unidades: ' + ', '.join(missing_codes[:30]) + '.')
    calendar_plan=schedule_engine.plan(draft,[dict(c) for c in criteria],module['academic_year'])
    import national_registry
    hours_reference=(national_registry.find_hours(db,module_id)
                     or program_assistant.hours_proposal(dict(module),draft['region']))
    warnings.extend(calendar_plan['warnings'])
    warnings.extend(planning_matrix.review(draft['units'],[dict(c) for c in criteria],
        draft['schedule']['feoe_criteria_codes'],draft['term_assessments'],draft['feoe_tasks']))
    if len(draft['activities']):
        units_codes={u['code'].casefold() for u in draft['units']}
        for activity in draft['activities']:
            if activity['unit_code'] and activity['unit_code'].casefold() not in units_codes:
                warnings.append('Actividad sin unidad válida: '+activity['title'])
            if not activity['date']:
                warnings.append('Actividad pendiente de fecha/confirmación: '+activity['title'])
    import canarias_reference
    module_reference=canarias_reference.read(db,module_id)
    if module_reference:
        warnings.append(
            'El índice de 2024 es una referencia histórica y no confirma '
            'los módulos ni la carga horaria vigente para este curso.'
        )
    return {'module_reference': module_reference,
            'calendar_plan': calendar_plan, 'hours_reference': hours_reference,
            'module': dict(module), 'draft': draft, 'updated_at': loaded['updated_at'],
            'outcomes': ras_return, 'criteria': ces_return,
            'counts': {'ra': len(outcomes), 'ce': len(criteria), 'documents': docs,
                       'units': len(draft['units'])},
            'errors': errors, 'warnings': warnings, 'ready_for_assessment': not errors,
            'approved': False}


def _display_2(value):
    """Two decimals in Spanish locale, without modifying stored values."""
    if value is None or value == '':
        return 'Pendiente'
    return format(float(value), '.2f').replace('.', ',')


def _sections(db, module_id):
    result = diagnose(db, module_id)
    m, v = result['module'], result['draft']
    parts = [('Identificación del módulo', [
        ('Curso académico', m['academic_year']), ('Ciclo formativo', m['cycle']),
        ('Módulo profesional', m['name']), ('Comunidad autónoma', v['region']),
        ('Código oficial del módulo',v.get('official_module_code') or 'Pendiente'),
        ('Código del ciclo o título',v.get('official_cycle_code') or 'Pendiente'),
        ('Régimen de formación en empresa',v.get('fp_regime') or 'Pendiente'),
        ('Centro educativo', v['center']), ('Departamento', v['department']),
        ('Docente responsable', v['teacher']), ('Contextualización', v['academic_context'])])]
    for heading, fields in [
        ('Marco normativo y objetivos', [('Fuente específica del currículo (URL)',v.get('curriculum_source_url') or 'Pendiente'),
                                         ('Procedencia curricular',v.get('curriculum_source_description') or 'Pendiente'),
                                         ('Currículo contrastado por el docente','Sí' if v.get('curriculum_confirmed') else 'NO'),
                                         ('Referencias normativas propuestas (pendientes de validación docente)', v['normative_references']),
                                         ('Objetivos', v['objectives']), ('Competencias', v['competencies'])]),
        ('Metodología y recursos', [('Metodología', v['methodology']), ('Recursos', v['resources']),
                                   ('Atención a las diferencias individuales', v['inclusion'])]),
        ('Evaluación del módulo', [('Procedimiento y criterios de evaluación', v['assessment']),
                                  ('Instrumentos y evidencias', v['instruments']),
                                  ('Recuperación', v['recovery']), ('Formación en empresa', v['enterprise'])]),
    ]:
        parts.append((heading, fields))
    ra_rows = db.execute('SELECT id,code,description,weight FROM outcomes WHERE module_id=? ORDER BY id', (module_id,)).fetchall()
    curriculum = []
    for ra in ra_rows:
        curriculum.append((ra['code'], f'{ra["description"]} (ponderación: {_display_2(ra["weight"])} %)'))
        for ce in db.execute('''SELECT c.code,c.description,c.weight FROM criteria c
             WHERE c.outcome_id=? ORDER BY c.id''',(ra['id'],)):
            curriculum.append(('   '+ce['code'], f'{ce["description"]} (peso dentro del RA: {_display_2(ce["weight"])} %)'))
    parts.append(('Justificación y contextualización',[
        ('Justificación y principios',v['justification']),
        ('Características del centro',v['center_characteristics']),
        ('Características del alumnado',v['student_characteristics']),
        ('Entorno socioproductivo',v['environment_context']),
        ('Datos identificativos',v['identification_data']),
        ('Competencias y cualificaciones',v['qualifications'])]))
    parts.append(('Contenidos y coordinación',[
        ('Contenidos didácticos',v['contents']),
        ('Distribución de actividades de aprendizaje',v['learning_activities']),
        ('Interdisciplinariedad',v['interdisciplinarity'])]))
    parts.append(('Resultados de aprendizaje y criterios', curriculum))
    units = [(u['code']+' · '+u['title'], f'Trimestre {u["term"]} · {_display_2(u["hours"])} h · CE: {", ".join(u["criteria_codes"]) or "por asignar"}') for u in v['units']]
    parts.append(('Secuenciación de unidades', units))
    calendar = result['calendar_plan']
    conf = calendar['config']
    entries=[('Horas semanales', _display_2(conf['weekly_hours'])+' h/semana (confirmadas: '+('sí' if conf['hours_confirmed'] else 'NO')+')'),
             ('Fuente de distribución horaria', conf.get('hours_source_description') or 'Introducción manual pendiente de comprobación'),
             ('Enlace a fuente horaria',conf.get('hours_source_url') or 'Pendiente'),
             ('Carga horaria oficial o prevista', _display_2(conf['total_hours'])+' h'),
             ('Periodo lectivo', f'{conf["start_date"]} a {conf["end_date"]}'),
             ('Horas disponibles estimadas', _display_2(calendar.get('capacity',0))+' h'),
             ('Horas planificadas en unidades', _display_2(calendar.get('planned',0))+' h'),
             ('Distribución semanal de lunes a viernes', '; '.join(f'{day}: {_display_2(hours)} h' for day,hours in zip(('Lunes','Martes','Miércoles','Jueves','Viernes'),conf['weekday_hours'])) + '; cero en todos los días implica estimación prorrateada'),
             ('Evaluaciones', ', '.join(conf['evaluation_ends'])),
             ('Días no lectivos adicionales', ', '.join(conf['extra_non_teaching_days']) or 'Pendientes de confirmar'),
             ('Fuentes del calendario aplicado', '\n'.join(calendar.get('sources',[])) or 'Pendiente de proporcionar'),
             ('Procedencia del calendario',calendar.get('calendar_source_description') or 'Sin fuente comprobada'),
             ('Ámbito territorial del calendario',conf.get('region',''))]
    for term in calendar.get('terms',[]):
        entries.append((f'Evaluación {term["term"]}',f'Disponibles {_display_2(term["capacity"])} h; previstas {_display_2(term["planned"])} h'))
    for u in calendar.get('units',[]):
        entries.append((u['code']+' · '+u['title'],f'{u["start"] or "Sin fecha"} a {u["end"] or "Sin fecha"} · {_display_2(u["hours"])} h · Evaluación {u["term"]}'))
    parts.append(('Temporalización y calendario escolar', entries))
    parts.append(('Formación en empresa (FEOE)',[
        ('Fechas aproximadas', str(conf['feoe_start'] or 'Pendiente')+' / '+str(conf['feoe_end'] or 'Pendiente')),
        ('CE propuestos en FEOE', ', '.join(conf['feoe_criteria_codes']) or 'Pendiente de selección'),
        ('Porcentaje de CE propuestos',_display_2(calendar.get('feoe',{}).get('percent',0))+' %'),
        ('RA relacionados',str(calendar.get('feoe',{}).get('ra_count',0))+' de '+str(calendar.get('feoe',{}).get('ra_total',0))+' RA del módulo (no equivale al porcentaje global del ciclo)'),
        ('Alcance de la referencia del 10-20 %',schedule_engine.FEOE_HELP)]))
    parts.append(('Instrumentos y recursos por unidad',[
        (u['code']+' · '+u['title'], 'Instrumentos: '+(u.get('instruments') or 'Pendientes de concretar')+' | Recursos: '+(u.get('resources') or 'Pendientes de concretar'))
        for u in v['units']]))
    parts.append(('Instrumentos, evidencias y recursos por evaluación', [
        (f'{row["term"]}.ª evaluación', 'Instrumentos: '+(row['instruments'] or 'Pendientes de confirmar')+
            '\nEvidencias: '+(row['evidence'] or 'Pendientes de confirmar')+
            '\nRecursos: '+(row['resources'] or 'Pendientes de confirmar')+
            '\nRecuperación: '+(row['recovery'] or 'Pendiente de confirmar'))
        for row in v.get('term_assessments', [])]))
    parts.append(('Matriz FEOE: CE, tareas y evidencias', [
        (item['criteria_code'], 'Actividad en empresa: '+(item['activity'] or 'Pendiente')+
            '\nEvidencia y seguimiento: '+(item['evidence'] or 'Pendiente')+
            '\nResponsables: '+(item['assessment_role'] or 'Pendiente'))
        for item in v.get('feoe_tasks', [])]))
    parts.append(('Actividades complementarias y extraescolares',[
        (a['title'],a['type']+' · '+(a['date'] or 'Fecha por concretar')+' · '+a['description']+' · Recursos: '+a['resources'])
        for a in v['activities']]))
    parts.append(('Otros aspectos organizativos y de evaluación',[
        ('Actividades complementarias y extraescolares documentadas',v['extracurricular']),
        ('Sesiones de evaluación',v['assessment_sessions']),
        ('Procedimientos de calificación',v['grading']),
        ('Promoción',v['promotion']),
        ('Asistencia y puntualidad',v['attendance']),
        ('Evaluación extraordinaria',v['extraordinary_assessment'])]))
    if v.get('imported_sections'):
        parts.append(('Trazabilidad de la importación',[
            ('Documento original', v.get('import_info',{}).get('filename','')),
            ('Carácter del contenido','Transcripción de un documento aportado por el docente: la normativa, las fechas, las ponderaciones y los acuerdos NO están verificados por EvalúaFP.'),
            ('Apartados recuperados',str(len(v['imported_sections'])))]))
        # Preservar también apartados que no se pueden traducir a campos del asistente,
        # y los originales largos, sin omitir contenidos ni inventar una estructura.
        for num,section in enumerate(v['imported_sections'],1):
            parts.append((f'Anexo de procedencia {num}. '+str(section['title'])[:85],[
                (f'Página(s) {section["page_start"]}–{section["page_end"]}',section['body'])]))
    parts.append(('Observaciones docentes', [('Observaciones', v['observations'])]))
    parts.append(('Origen de las propuestas pedagógicas', [
        (k,('Modificado por el docente' if meta.get('teacher_edited') else meta.get('origin','Sin registrar')))
        for k,meta in v.get('assistant_meta',{}).items()]))
    parts.append(('Verificaciones pendientes', [('Alertas', '\n'.join(result['errors']+result['warnings']) or 'Sin alertas del control automático. La aprobación sigue siendo competencia del centro.')]))
    # Orden de apartados inspirado en la programación de referencia aportada:
    # cada bloque conserva un título propio para el índice automático del PDF y Word.
    old={name:fields for name,fields in parts}
    remapped={
        'Justificación teórica y principios de la programación': [('Justificación',v['justification'])],
        'Marco normativo: legislación estatal y autonómica': [('Fuentes para revisión y verificación docente',v['normative_references'])],
        'Contextualización: centro, grupo y entorno': [
            ('Punto de partida',v['academic_context']),
            ('Características del centro',v['center_characteristics']),
            ('Características del alumnado',v['student_characteristics']),
            ('Influencia del entorno socioproductivo',v['environment_context'])],
        'Competencias y cualificaciones profesionales': [('Competencias',v['competencies']),('Cualificaciones',v['qualifications'])],
        'Objetivos generales del título y del módulo': [('Objetivos y contribución del módulo',v['objectives'])],
        'Contenidos didácticos': [('Contenidos y saberes',v['contents'])],
        'Distribución de situaciones de aprendizaje': [('Actividades de aprendizaje',v['learning_activities'])],
        'Principios y estructura metodológica': [('Metodología didáctica',v['methodology'])],
        'Interdisciplinariedad y coordinación': [('Organización intermodular',v['interdisciplinarity'])],
        'Atención a las diferencias individuales': [('Inclusión y DUA',v['inclusion'])],
        'Recursos y materiales': [('Recursos e instalaciones',v['resources'])],
        'Evaluación continua y criterios de calificación': [
            ('Evaluación y seguimiento',v['assessment']),('Instrumentos generales',v['instruments']),
            ('Ponderaciones y calificación',v['grading'])],
        'Sesiones de evaluación': [('Sesiones y seguimiento',v['assessment_sessions'])],
        'Asistencia, evaluación y promoción': [('Asistencia',v['attendance']),('Promoción',v['promotion'])],
        'Procedimientos de recuperación': [('Recuperación',v['recovery']),('Pruebas extraordinarias',v['extraordinary_assessment'])],
    }
    order=[
      'Identificación del módulo','Justificación teórica y principios de la programación',
      'Marco normativo: legislación estatal y autonómica','Contextualización: centro, grupo y entorno',
      'Competencias y cualificaciones profesionales','Objetivos generales del título y del módulo',
      'Resultados de aprendizaje y criterios','Contenidos didácticos',
      'Distribución de situaciones de aprendizaje','Secuenciación de unidades',
      'Principios y estructura metodológica','Interdisciplinariedad y coordinación',
      'Atención a las diferencias individuales','Recursos y materiales',
      'Actividades complementarias y extraescolares','Evaluación continua y criterios de calificación',
      'Instrumentos y recursos por unidad','Instrumentos, evidencias y recursos por evaluación',
      'Matriz FEOE: CE, tareas y evidencias','Sesiones de evaluación',
      'Asistencia, evaluación y promoción','Procedimientos de recuperación',
      'Temporalización y calendario escolar','Formación en empresa (FEOE)',
      'Observaciones docentes','Verificaciones pendientes','Origen de las propuestas pedagógicas',
      'Trazabilidad de la importación'
    ]
    parts=[(name,remapped.get(name,old.get(name,[]))) for name in order if name in remapped or name in old]
    parts.extend((name,fields) for name,fields in old.items() if name.startswith('Anexo de procedencia'))
    return result, parts


def export(db, module_id, fmt):
    if fmt not in ('docx','pdf','md'):
        raise ValueError('Formato de exportación no admitido.')
    result, sections = _sections(db, module_id)
    if fmt in ('docx','pdf'):
        import program_export_v113
        return program_export_v113.export(result, sections, module_id, fmt)
    title = 'BORRADOR DE PROGRAMACIÓN DIDÁCTICA — EvalúaFP'
    note = ('Documento editable de trabajo. No es una programación aprobada ni sustituye los acuerdos '
            'del departamento, la normativa aplicable ni la validación docente.')
    if fmt == 'md':
        lines = ['# '+title, '', '> '+note, '']
        for heading, fields in sections:
            lines.extend(['## '+heading, ''])
            for label, value in fields:
                lines.extend([f'**{label}:** {value or "Pendiente de completar"}', ''])
        return '\n'.join(lines).encode('utf-8'), 'text/markdown; charset=utf-8', f'EvaluaFP_Borrador_{module_id}.md'
    if fmt == 'docx':
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        sec = doc.sections[0]
        sec.header.paragraphs[0].text = 'EvalúaFP · Documento de trabajo'
        doc.add_heading(title, 0)
        p = doc.add_paragraph(note)
        for run in p.runs: run.italic = True
        for heading, fields in sections:
            doc.add_heading(heading, level=1)
            for key, value in fields:
                p = doc.add_paragraph(style='Normal')
                p.add_run(key+': ').bold = True
                p.add_run(str(value) if value else '[Pendiente de completar]')
        sec.footer.paragraphs[0].text = 'BORRADOR · Revisión y aprobación pendientes'
        stream = io.BytesIO(); doc.save(stream)
        return stream.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', f'EvaluaFP_Borrador_{module_id}.docx'
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    stream = io.BytesIO()
    pdf = SimpleDocTemplate(stream, pagesize=A4, leftMargin=2.1*cm, rightMargin=2.1*cm,
                            topMargin=2.2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='EFTitle', parent=styles['Title'], fontSize=17,
                              textColor=colors.HexColor('#123d5a'), alignment=TA_CENTER, spaceAfter=16))
    styles.add(ParagraphStyle(name='EFHeading', parent=styles['Heading2'],
                              textColor=colors.HexColor('#126c93'), spaceBefore=15, spaceAfter=8))
    styles.add(ParagraphStyle(name='EFBody', parent=styles['BodyText'], leading=14, spaceAfter=6))
    story = [Paragraph(escape(title), styles['EFTitle']), Paragraph(escape(note), styles['EFBody']), Spacer(1, 12)]
    for heading, fields in sections:
        story.append(Paragraph(escape(heading), styles['EFHeading']))
        if not fields:
            story.append(Paragraph('Pendiente de completar', styles['EFBody']))
        for key, value in fields:
            text = f'<b>{escape(str(key))}:</b> {escape(str(value or "[Pendiente de completar]")).replace(chr(10), "<br/>")}'
            story.append(Paragraph(text, styles['EFBody']))
    def foot(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#617686'))
        canvas.drawString(2.1*cm, 1.1*cm, 'EvalúaFP · BORRADOR pendiente de revisión')
        canvas.drawRightString(A4[0]-2.1*cm, 1.1*cm, f'Página {doc.page}')
    pdf.build(story, onFirstPage=foot, onLaterPages=foot)
    return stream.getvalue(), 'application/pdf', f'EvaluaFP_Borrador_{module_id}.pdf'
