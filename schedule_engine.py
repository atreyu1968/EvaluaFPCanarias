"""Planificación FP por comunidad, curso, sesiones reales y fuentes explícitas.

No deduce días del horario del docente: si faltan, usa reparto proporcional
estimado y señala la limitación. Días no lectivos y FEOE son editables.
"""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor, isfinite
import territorial_profiles as territorial
from urllib.parse import urlsplit

BOC_CALENDAR_URL = 'https://www.gobiernodecanarias.org/boc/2026/061/1025.html'
BOC_CALENDAR_CORRECTION_URL = 'https://www.gobiernodecanarias.org/boc/2026/075/1240.html'
CALENDAR_SOURCE_NOTE = 'Canarias 2026-2027: Resolución de 17 de marzo de 2026, corregida el 10 de abril de 2026 (Navidad del 23/12/2026 al 08/01/2027).'
CALENDAR_PDF_URL = 'https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/calendario_escolar_26_27.pdf'
FEOE_HELP = ('El 10-20 % de CE es una preferencia de planificación de este asistente, '
             'no un porcentaje normativo general. Se debe revisar la distribución de RA '
             'del conjunto del ciclo, el plan de formación y el régimen dual aplicable.')


def _date(x, name):
    try:
        if not isinstance(x, str) or len(x) != 10 or x[4] != '-' or x[7] != '-':
            raise ValueError()
        result = date.fromisoformat(x)
        if result.isoformat() != x:
            raise ValueError()
        return result
    except ValueError as exc:
        raise ValueError(f'{name}: indique una fecha válida AAAA-MM-DD.') from exc


def defaults(academic_year='2026-2027', region='Canarias', island=''):
    """Solo precarga fechas con una fuente escolar contrastada para ESA combinación.

    Las evaluaciones de una ficha son propuestas de organización del centro.
    """
    academic_year=territorial.year_code(academic_year)
    region=territorial.require_territory(region)
    profile=territorial.calendar_profile(region, academic_year, island)
    return {
        'weekly_hours': 0, 'total_hours': 0, 'weekday_hours': [0, 0, 0, 0, 0],
        'start_date': profile['start_date'] if profile else '',
        'end_date': profile['end_date'] if profile else '',
        'evaluation_ends': list(profile['evaluation_ends']) if profile else ['', '', ''],
        'island': island if region=='Canarias' else '', 'municipality': '',
        'extra_non_teaching_days': [],
        'vacation_periods': list(profile['vacation_periods']) if profile else [],
        'regional_non_teaching_days': list(profile['regional_non_teaching_days']) if profile else [],
        'calendar_profile_id': profile['id'] if profile else '',
        'calendar_academic_year': academic_year,
        'calendar_source_url': profile['source_urls'][0] if profile else '',
        'calendar_source_description': profile['source_description'] if profile else '',
        'calendar_correction_urls': list(profile['source_urls'][1:2]) if profile else [],
        'feoe_start': '', 'feoe_end': '', 'feoe_center_hours_weekly': None,
        'feoe_criteria_codes': [], 'feoe_target_percent': 15,
        'calendar_confirmed': False, 'hours_confirmed': False,
        'hours_source_url': '', 'hours_source_description': '', 'region': region,
    }


def fresh_calendar(academic_year, region, island=''):
    """Devuelve exclusivamente las fechas del nuevo territorio/curso.

    No transfiere festivos locales, fechas ni confirmaciones del anterior.
    """
    cfg=defaults(academic_year,region,island)
    return {key:cfg[key] for key in (
        'region','island','municipality','start_date','end_date','evaluation_ends',
        'vacation_periods','regional_non_teaching_days','extra_non_teaching_days',
        'calendar_profile_id','calendar_academic_year','calendar_source_url',
        'calendar_source_description','calendar_correction_urls','calendar_confirmed')}


def clean(raw, academic_year='2026-2027'):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError('La temporalización debe contener campos de configuración.')
    raw_region=raw.get('region','Canarias')
    raw_island=raw.get('island','')
    base = defaults(academic_year,raw_region,raw_island)
    # Migración conservadora: los borradores antiguos no acreditan que sus
    # fechas pertenezcan al calendario territorial. Nunca se autoconfirman.
    if 'calendar_academic_year' not in raw and raw:
        base['calendar_confirmed']=False
    unknown = set(raw) - set(base)
    if unknown:
        raise ValueError('Campos de temporalización no reconocidos: ' + ', '.join(sorted(unknown)))
    base.update(raw)
    # Las migraciones antiguas no deben heredar una corrección del calendario
    # genérico de Canarias si su fuente principal era una disposición distinta.
    if raw and 'calendar_correction_urls' not in raw:
        original_source=str(raw.get('calendar_source_url') or '')
        default_source=str(defaults(academic_year,raw_region,raw_island)['calendar_source_url'])
        if original_source != default_source:
            base['calendar_correction_urls']=[]
    for key in ('weekly_hours', 'total_hours', 'feoe_target_percent'):
        try:
            val = float(base[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{key}: introduzca un número válido.') from exc
        if not isfinite(val) or (key == 'weekly_hours' and not 0 <= val <= 40) or (key == 'total_hours' and not 0 <= val <= 2500) or (key == 'feoe_target_percent' and not 10 <= val <= 20):
            raise ValueError(f'{key}: valor fuera del intervalo permitido.')
        base[key] = round(val, 2)
    days = base['weekday_hours']
    if not isinstance(days, list) or len(days) != 5:
        raise ValueError('Indique cinco valores de horario de lunes a viernes.')
    nums = []
    for item in days:
        try:
            n = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError('Horas por día inválidas.') from exc
        if not isfinite(n) or not 0 <= n <= 12:
            raise ValueError('Las horas por día deben estar entre 0 y 12.')
        nums.append(round(n, 2))
    if sum(nums) and abs(sum(nums) - base['weekly_hours']) > 0.015:
        raise ValueError('Las horas por días de la semana deben sumar las horas semanales del módulo.')
    base['weekday_hours'] = nums
    for key in ('start_date', 'end_date', 'feoe_start', 'feoe_end'):
        if not isinstance(base[key], str):
            raise ValueError(f'{key}: fecha incorrecta.')
        if base[key]:
            base[key] = _date(base[key], key).isoformat()
    if bool(base['feoe_start']) != bool(base['feoe_end']):
        raise ValueError('Indique inicio y final de FEOE, o deje ambas fechas vacías.')
    if base['start_date'] and base['end_date'] and base['start_date'] >= base['end_date']:
        raise ValueError('El inicio de las clases debe ser anterior a su finalización.')
    ends = base['evaluation_ends']
    if not isinstance(ends, list) or len(ends) != 3:
        raise ValueError('Se necesitan fechas de cierre de las tres evaluaciones.')
    base['evaluation_ends'] = [_date(x, f'final de evaluación {i+1}').isoformat() if x else '' for i, x in enumerate(ends)]
    valid_ends = [x for x in base['evaluation_ends'] if x]
    if valid_ends != sorted(valid_ends) or len(valid_ends) != len(set(valid_ends)):
        raise ValueError('Las evaluaciones deben finalizar en orden cronológico.')
    if base['start_date'] and any(x < base['start_date'] for x in valid_ends):
        raise ValueError('Una evaluación termina antes del inicio del módulo.')
    if base['end_date'] and any(x > base['end_date'] for x in valid_ends):
        raise ValueError('Una evaluación termina después del fin del módulo.')
    extras = base['extra_non_teaching_days']
    if not isinstance(extras, list) or len(extras) > 50:
        raise ValueError('Introduzca una lista de hasta 50 días no lectivos adicionales.')
    base['extra_non_teaching_days'] = sorted(set(_date(v, 'día no lectivo').isoformat() for v in extras))
    for key, maxlen in (('island', 80), ('municipality', 120)):
        if not isinstance(base[key], str) or len(base[key]) > maxlen:
            raise ValueError(f'{key}: valor inválido.')
        base[key] = base[key].strip()
    base['region'] = territorial.require_territory(base['region'])
    academic_year=territorial.year_code(academic_year)
    stored_year=base.get('calendar_academic_year','')
    if stored_year != academic_year:
        # La temporalización de otro curso NO se hereda al siguiente.
        replacement=fresh_calendar(academic_year,base['region'])
        base.update(replacement)
    profile_id=base.get('calendar_profile_id','')
    profile=territorial.calendar_profile(base['region'],academic_year,base['island'])
    if profile_id and (not profile or profile_id != profile['id']):
        # Una referencia a otra comunidad/año es incompatible.
        replacement=fresh_calendar(academic_year,base['region'])
        base.update(replacement)
    if base['region'] != 'Canarias':
        base['island']=''
    for field,maxlen in (('calendar_profile_id',160),('calendar_academic_year',30),
                         ('calendar_source_url',800),('calendar_source_description',700)):
        if not isinstance(base[field],str) or len(base[field])>maxlen:
            raise ValueError(f'{field}: fuente de calendario incorrecta.')
    def intervals(value):
        if not isinstance(value,list) or len(value)>30:
            raise ValueError('Se admiten hasta 30 periodos no lectivos.')
        result=[]
        for row in value:
            if not isinstance(row,dict):raise ValueError('Periodo no lectivo incorrecto.')
            start=_date(row.get('start'),'inicio de vacaciones')
            end=_date(row.get('end'),'fin de vacaciones')
            if end<start or (end-start).days>100:
                raise ValueError('Un periodo no lectivo debe tener inicio y fin válidos (máximo 101 días).')
            label=row.get('label','Vacaciones/no lectivo')
            if not isinstance(label,str) or len(label)>130:raise ValueError('Motivo de periodo no lectivo inválido.')
            result.append({'start':start.isoformat(),'end':end.isoformat(),'label':label.strip() or 'No lectivo'})
        return result
    def individual_days(value):
        if not isinstance(value,list) or len(value)>120:
            raise ValueError('Se admiten hasta 120 festivos/inhábiles asociados al calendario.')
        days={}
        for row in value:
            if not isinstance(row,dict):raise ValueError('Festivo del calendario incorrecto.')
            key=_date(row.get('date'),'día festivo').isoformat()
            reason=row.get('reason','Día no lectivo')
            if not isinstance(reason,str) or len(reason)>130:raise ValueError('Motivo del festivo inválido.')
            days[key]=reason.strip() or 'Día no lectivo'
        return [{'date':key,'reason':value} for key,value in sorted(days.items())]
    url=base.get('calendar_source_url','')
    if url and (urlsplit(url).scheme not in ('https','http') or not urlsplit(url).netloc):
        raise ValueError('La URL del calendario debe usar https:// o http:// y tener dominio válido.')
    corrections = base.get('calendar_correction_urls', [])
    if not isinstance(corrections, list) or len(corrections)>8:
        raise ValueError('Se admiten hasta ocho enlaces de correcciones del calendario.')
    clean_corrections=[]
    for link in corrections:
        if not isinstance(link,str) or len(link)>800 or not link.strip():
            raise ValueError('La URL de corrección del calendario es inválida.')
        link=link.strip()
        parts=urlsplit(link)
        if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or any(ord(c)<32 for c in link) or chr(92) in link:
            raise ValueError('Las correcciones deben identificarse mediante URLs HTTPS públicas.')
        if parts.hostname.lower() in ('localhost','127.0.0.1','::1') or parts.hostname.lower().endswith('.local'):
            raise ValueError('La fuente de una corrección no puede ser local.')
        if link not in clean_corrections:clean_corrections.append(link)
    base['calendar_correction_urls']=clean_corrections
    base['vacation_periods']=intervals(base['vacation_periods'])
    base['regional_non_teaching_days']=individual_days(base['regional_non_teaching_days'])
    # Los enlaces territoriales se enlazan únicamente a su perfil original.
    if not profile_id and base['region']!='Canarias' and 'calendar_source_url' not in raw:
        base['calendar_source_url']=''
        base['calendar_source_description']=''
    selected = base['feoe_criteria_codes']
    if not isinstance(selected, list) or len(selected) > 500:
        raise ValueError('El listado de CE asignados a la FEOE no es correcto.')
    base['feoe_criteria_codes'] = list(dict.fromkeys(str(x).strip() for x in selected if str(x).strip()))
    v = base['feoe_center_hours_weekly']
    if v in ('', None):
        base['feoe_center_hours_weekly'] = None
    else:
        try:
            val = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError('Introduzca horas semanales válidas en el centro durante la FEOE.') from exc
        if not isfinite(val) or not 0 <= val <= base['weekly_hours']:
            raise ValueError('Las horas de centro durante la FEOE no pueden superar las horas semanales del módulo.')
        base['feoe_center_hours_weekly'] = round(val, 2)
    if type(base['calendar_confirmed']) is not bool:
        raise ValueError('La confirmación del calendario debe ser verdadero o falso.')
    if type(base['hours_confirmed']) is not bool:
        raise ValueError('La confirmación de horas debe ser verdadera o falsa.')
    for key in ('hours_source_url','hours_source_description','region'):
        if not isinstance(base[key], str) or len(base[key])>600:
            raise ValueError('La procedencia del horario no es válida.')
    return base


def blocked_days(cfg):
    """Única fuente para las fechas del Gantt y los cuadros de disponibilidad."""
    blocked=set()
    names={}
    def add(day,reason):
        d=date.fromisoformat(day)
        blocked.add(d);names[d]=reason
    for row in cfg.get('vacation_periods',[]):
        start,end=date.fromisoformat(row['start']),date.fromisoformat(row['end'])
        d=start
        while d<=end:
            add(d.isoformat(),row['label']);d+=timedelta(days=1)
    for row in cfg.get('regional_non_teaching_days',[]):
        add(row['date'],row['reason'])
    # Las fiestas insulares se calculan con la isla seleccionada; nunca se
    # trasvasan al resto de comunidades o a otros años académicos.
    reg=territorial.calendar_profile(cfg['region'],cfg.get('calendar_academic_year','2026-2027'),cfg.get('island',''))
    if reg and cfg.get('calendar_profile_id')==reg['id']:
        for row in reg['regional_non_teaching_days']:
            if row['date'] not in {x['date'] for x in cfg.get('regional_non_teaching_days',[])}:
                add(row['date'],row['reason'])
    for holiday in territorial.known_local_holidays(cfg['region'],cfg['calendar_academic_year'],cfg.get('municipality','')):
        add(holiday['date'],holiday['reason'])
    for day in cfg['extra_non_teaching_days']:
        add(day,'No lectivo añadido por el centro / municipio')
    return blocked,names


def _daily_hours(cfg, d):
    if d.weekday() >= 5:
        return 0.0
    dist = cfg['weekday_hours']
    hours = dist[d.weekday()] if sum(dist) > 0 else cfg['weekly_hours'] / 5
    if cfg['feoe_start'] and cfg['feoe_start'] <= d.isoformat() <= cfg['feoe_end'] and cfg['feoe_center_hours_weekly'] is not None:
        feoe_hours = cfg['feoe_center_hours_weekly']
        if sum(dist) > 0:
            hours *= (feoe_hours / cfg['weekly_hours'])
        else:
            hours = feoe_hours / 5
    return hours


def plan(draft, criteria=(), academic_year='2026-2027'):
    cfg = clean(draft.get('schedule') or {}, academic_year)
    messages = []
    if not cfg['start_date'] or not cfg['end_date'] or not cfg['weekly_hours']:
        reason=('Indique las horas semanales oficiales o confirmadas: no se utilizará un valor genérico.'
                if not cfg['weekly_hours'] else 'Introduzca las fechas de inicio y fin de las clases.')
        return {'configured': False, 'config': cfg, 'warnings': [reason],
                'units': [], 'capacity': 0.0, 'terms': [], 'gantt_weeks': [], 'feoe': {}}
    known_profile=territorial.calendar_profile(cfg['region'],academic_year,cfg['island'])
    if not known_profile:
        messages.append('Esta comunidad autónoma NO dispone de un calendario escolar verificado para este curso en el catálogo local. Introduzca y confirme fechas, vacaciones, festivos y fuente oficial.')
    elif cfg.get('calendar_profile_id') != known_profile['id']:
        messages.append('El calendario introducido es personalizado: revise su fuente y los cambios respecto al modelo oficial de referencia.')
    if not cfg.get('vacation_periods') and not cfg.get('regional_non_teaching_days'):
        messages.append('No se han registrado vacaciones ni festivos; la capacidad calculada sería excesiva.')
    if not cfg.get('calendar_source_url'):
        messages.append('Falta la referencia verificable del calendario escolar de este curso y territorio.')
    if not sum(cfg['weekday_hours']):
        messages.append('Horario estimado: las horas se prorratean entre cinco días. Indique qué días tiene clase para descontar correctamente los festivos.')
    if not cfg['hours_confirmed']:
        messages.append('Las horas del módulo todavía no han sido confirmadas por el docente; la temporalización es provisional.')
    if not cfg['calendar_confirmed']:
        messages.append('Confirme las fechas del centro, los días de libre disposición y las adaptaciones de FP Dual antes de cerrar la programación.')
    if cfg['municipality']:
        if not territorial.known_local_holidays(cfg['region'],academic_year,cfg['municipality']):
            messages.append('Compruebe los festivos locales del municipio: no figuran en este catálogo y debe añadirlos manualmente.')
        messages.append('Compruebe los días no lectivos aprobados por su centro, pues no se deducen del municipio.')
    if cfg['feoe_start'] and cfg['feoe_center_hours_weekly'] is None:
        messages.append('FEOE: no se ha indicado el horario presencial del módulo durante la estancia en empresa. No se han descontado horas de centro por este motivo.')
    start, end = date.fromisoformat(cfg['start_date']), date.fromisoformat(cfg['end_date'])
    blocked, reasons = blocked_days(cfg)
    boundaries = cfg['evaluation_ends']
    days = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in blocked:
            h = _daily_hours(cfg, day)
            term = 1 + sum(day.isoformat() > x for x in boundaries[:2] if x)
            if h > 0:
                days.append({'date': day.isoformat(), 'hours': h, 'term': term, 'remaining': h})
        day += timedelta(days=1)
    terms = []
    for t in (1, 2, 3):
        avail = [d for d in days if d['term'] == t]
        terms.append({'term': t, 'start': avail[0]['date'] if avail else None,
                      'end': avail[-1]['date'] if avail else None,
                      'capacity': round(sum(x['hours'] for x in avail), 2), 'planned': 0.0})
    units = []
    for unit in draft.get('units', []):
        need = Decimal(str(unit['hours']))
        t = int(unit['term'])
        term = terms[t-1]
        term['planned'] = round(term['planned'] + float(need), 2)
        start_date, end_date = None, None
        missing = need
        for slot in days:
            if slot['term'] != t or missing <= Decimal('0.000001'):
                continue
            available = Decimal(str(slot['remaining']))
            if available <= 0:
                continue
            take = min(missing, available)
            slot['remaining'] -= float(take)
            missing -= take
            start_date = start_date or slot['date']
            end_date = slot['date']
        if missing > Decimal('0.005'):
            messages.append(f'La {t}.ª evaluación no tiene horas suficientes para {unit["code"]}: faltan {float(missing):.2f} h.')
        units.append({'code': unit['code'], 'title': unit['title'], 'term': t,
                      'hours': float(need), 'start': start_date, 'end': end_date,
                      'unscheduled_hours': round(max(0, float(missing)), 2),
                      'criteria_codes': unit['criteria_codes']})
    capacity = sum(t['capacity'] for t in terms)
    requested = sum(float(u['hours']) for u in draft.get('units', []))
    target = cfg['total_hours']
    if target and abs(target-requested) > 0.02:
        messages.append(f'Las unidades suman {requested:.2f} h y el módulo tiene {target:.2f} h previstas. Diferencia de {target-requested:+.2f} h.')
    if requested > capacity + 0.01:
        messages.append(f'La planificación requiere {requested:.2f} h, pero el calendario ofrece aproximadamente {capacity:.2f} h.')
    if target and target > capacity + 0.01:
        messages.append(f'La carga oficial indicada ({target:.2f} h) excede las horas disponibles ({capacity:.2f} h).')
    for term in terms:
        if term['planned'] > term['capacity'] + 0.01:
            messages.append(f'Evaluación {term["term"]}: {term["planned"]:.2f} h previstas para {term["capacity"]:.2f} h disponibles.')
    ce_codes = [str(c['code']) if isinstance(c, dict) else str(c) for c in criteria]
    ce_all = {x.casefold(): x for x in ce_codes}
    ce_ra = {str(c['code']).casefold():str(c.get('ra_code','')) for c in criteria if isinstance(c,dict)}
    selected = cfg['feoe_criteria_codes']
    invalid = [x for x in selected if x.casefold() not in ce_all]
    if invalid:
        messages.append('La FEOE contiene CE que no figuran en el currículo confirmado: ' + ', '.join(invalid))
    n = len(ce_all)
    valid_selected = {x.casefold() for x in selected if x.casefold() in ce_all}
    count = len(valid_selected)
    rate = 100*count/n if n else 0.0
    ra_all={x for x in ce_ra.values() if x}
    ra_selected={ce_ra[key] for key in valid_selected if key in ce_ra and ce_ra[key]}
    lo, hi = ceil(0.1*n), floor(0.2*n)
    if n and (lo > hi):
        messages.append(f'Con {n} CE no hay un número entero que equivalga exactamente al 10-20 %: seleccione la cantidad más adecuada y justifíquela.')
    elif n and count == 0:
        messages.append('Aún no se han marcado criterios propuestos para la FEOE.')
    elif n and (count < lo or count > hi):
        messages.append(f'Seleccionados {count}/{n} CE ({rate:.1f} %): fuera de la referencia pedagógica del 10-20 %. Revise la selección; no es una regla legal universal.')
    if selected and (not cfg['feoe_start'] or not cfg['feoe_end']):
        messages.append('Indique las fechas aproximadas de FEOE para representarla en el Gantt.')
    gantt = []
    base = start-timedelta(days=start.weekday())
    until = end+timedelta(days=7)
    while base <= until:
        week_end = base+timedelta(days=6)
        if week_end >= start and base <= end:
            gantt.append({'start': base.isoformat(), 'end': week_end.isoformat(),
                          'label': base.strftime('%d/%m'),
                          'blocked': sum(1 for x in range(7) if base+timedelta(days=x) in blocked),
                          'term': 1+sum(base.isoformat() > x for x in boundaries[:2] if x)})
        base += timedelta(days=7)
    return {
        'configured': True, 'config': cfg, 'warnings': list(dict.fromkeys(messages)),
        'units': units, 'capacity': round(capacity, 2),
        'planned': round(requested, 2), 'terms': terms,
        'gantt_weeks': gantt,
        'non_teaching': [{'date': d.isoformat(), 'reason': label} for d, label in sorted(reasons.items()) if start <= d <= end and d.weekday() < 5],
        'feoe': {'selected': [ce_all[x] for x in valid_selected], 'count': count,
                 'criteria_total': n, 'percent': round(rate, 2),
                 'ra_codes': sorted(ra_selected), 'ra_count': len(ra_selected), 'ra_total': len(ra_all),
                 'recommended_min': lo,
                 'recommended_max': hi, 'explanation': FEOE_HELP,
                 'start': cfg['feoe_start'], 'end': cfg['feoe_end']},
        'sources': ([cfg['calendar_source_url']] if cfg.get('calendar_source_url') else []) + ([known_profile['source_urls'][1]] if known_profile and cfg.get('calendar_profile_id')==known_profile['id'] and len(known_profile['source_urls'])>1 else []) + territorial.known_local_sources(cfg['region'],academic_year,cfg.get('municipality','')),
        'calendar_source_description': cfg.get('calendar_source_description',''),
        'calendar_profile_id': cfg.get('calendar_profile_id',''),
    }
