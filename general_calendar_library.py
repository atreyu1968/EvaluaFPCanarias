"""Biblioteca LOCAL de calendarios generales FP, por territorio y curso.

Una ficha general es una referencia revisada por el docente, no una
certificación automática de vigencia normativa. Se excluyen expresamente los
días de centro/municipio, la isla, horarios, evaluaciones y FEOE.
Las revisiones son inmutables y no se transfieren entre cursos o territorios.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json

import territorial_profiles as territory

STAGE = 'fp_grado_d'
GENERAL_FIELDS = ('region', 'calendar_academic_year', 'start_date', 'end_date',
                  'vacation_periods', 'regional_non_teaching_days',
                  'calendar_source_url', 'calendar_source_description',
                  'calendar_correction_urls')


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS national_general_fp_calendars (
        id INTEGER PRIMARY KEY,
        territory_code TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        stage TEXT NOT NULL DEFAULT 'fp_grado_d',
        revision_number INTEGER NOT NULL,
        snapshot_json TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        corrections_json TEXT NOT NULL DEFAULT '[]',
        reviewed_at TEXT NOT NULL,
        source_module_id INTEGER NOT NULL,
        UNIQUE(territory_code, academic_year, stage, revision_number)
    )""")
    db.execute("""CREATE INDEX IF NOT EXISTS idx_national_general_fp_calendars_scope
                 ON national_general_fp_calendars
                 (territory_code, academic_year, stage, revision_number DESC)""")


def _context(db, module_id):
    from national_registry import scope
    module, draft, code = scope(db, int(module_id))
    year = territory.year_code(module['academic_year'])
    region = territory.require_territory(draft['region'])
    if territory.territory_code(region) != code or territory.require_territory(module['territory']) != region:
        raise ValueError('El territorio del módulo y del borrador no coinciden. Guarde primero el ámbito adecuado.')
    return module, draft, code, year


def _scope_key(code, year):
    return (code, year, STAGE)


def _year_date(value, year, field):
    from schedule_engine import _date
    day = _date(value, field)
    first = date(int(year[:4]), 9, 1)
    last = date(int(year[:4]) + 1, 8, 31)
    if not first <= day <= last:
        raise ValueError('La ficha general contiene fechas fuera de su curso académico.')
    return day


def _check_general(cfg, code, year):
    """Evita publicar como común una festividad insular conocida.

    Las demás fiestas municipales/insulares deben ser retiradas por el
    docente y quedan fuera del conjunto compartido por declaración expresa.
    """
    if cfg['calendar_academic_year'] != year or territory.territory_code(cfg['region']) != code:
        raise ValueError('El calendario del borrador no corresponde al territorio y curso del módulo.')
    start = _year_date(cfg['start_date'], year, 'inicio de clases')
    end = _year_date(cfg['end_date'], year, 'fin de clases')
    if not start < end:
        raise ValueError('El inicio general de clases debe preceder a su finalización.')
    for interval in cfg['vacation_periods']:
        lo = _year_date(interval['start'], year, 'inicio de vacaciones')
        hi = _year_date(interval['end'], year, 'fin de vacaciones')
        if hi < lo:
            raise ValueError('Las vacaciones generales deben tener fechas ordenadas.')
    for row in cfg['regional_non_teaching_days']:
        _year_date(row['date'], year, 'día no lectivo')
    if code == 'CN':
        base = territory.calendar_profile('Canarias', year, '')
        if base:
            common = {x['date'] for x in base['regional_non_teaching_days']}
            islands = ('Tenerife', 'Gran Canaria', 'La Palma', 'Lanzarote',
                       'Fuerteventura', 'La Gomera', 'El Hierro', 'La Graciosa')
            insular = set()
            for island in islands:
                profile = territory.calendar_profile('Canarias', year, island)
                insular |= {x['date'] for x in profile['regional_non_teaching_days']} - common
            actual = {x['date'] for x in cfg['regional_non_teaching_days']}
            affected = actual & insular
            if affected:
                raise ValueError('No comparta como calendario autonómico estas fiestas insulares: '
                                 + ', '.join(sorted(affected))
                                 + '. Trasládelas a los días adicionales del centro.')
    return {key: cfg[key] for key in GENERAL_FIELDS}


def _record(row):
    result = dict(row)
    return {'id': result['id'], 'revision': result['revision_number'],
            'territory_code': result['territory_code'],
            'academic_year': result['academic_year'], 'stage': result['stage'],
            'schedule': json.loads(result['snapshot_json']),
            'sha256': result['content_sha256'],
            'source_url': result['source_url'], 'source_title': result['source_title'],
            'correction_urls': json.loads(result['corrections_json']),
            'reviewed_at': result['reviewed_at'],
            'status': 'revisado_por_docente_no_certificado_por_evaluafp'}


def list_for_module(db, module_id):
    module, draft, code, year = _context(db, module_id)
    rows = db.execute("""SELECT * FROM national_general_fp_calendars
            WHERE territory_code=? AND academic_year=? AND stage=?
            ORDER BY revision_number DESC LIMIT 50""", _scope_key(code, year)).fetchall()
    from calendar_versions import source_directory
    return {'territory': territory.require_territory(draft['region']),
            'territory_code': code, 'academic_year': year,
            'stage': STAGE, 'count': len(rows),
            'versions': [_record(row) for row in rows],
            'source_directory': source_directory(code, year),
            'notice': ('Biblioteca LOCAL de calendarios generales revisados por docentes. '
                       'No está sincronizada con boletines oficiales ni demuestra vigencia. '
                       'Debe comprobar modificaciones, festivos municipales/insulares, '
                       'PGA del centro y particularidades de FP Dual antes de aplicar.')}


def _changes(old, new):
    labels = {'start_date': 'Inicio de clases', 'end_date': 'Fin de clases',
              'vacation_periods': 'Vacaciones generales',
              'regional_non_teaching_days': 'Festivos generales',
              'calendar_source_url': 'Disposición principal',
              'calendar_source_description': 'Identificación de la disposición',
              'calendar_correction_urls': 'Correcciones'}
    return [{'field': key, 'label': label,
             'previous': old.get(key) if old else None, 'current': new.get(key)}
            for key, label in labels.items() if old and old.get(key) != new.get(key)]


def save_from_module(db, module_id, payload):
    """Solo registra un calendario guardado y confirmado por el docente.

    No usa valores enviados para fechas por separado; lee exclusivamente el
    borrador validado, para impedir publicar una ficha de otro territorio.
    """
    import database
    from national_registry import valid_url, text_value
    import schedule_engine

    if not isinstance(payload, dict) or payload.get('teacher_confirmed') is not True:
        raise ValueError('Confirme que ha revisado el calendario y la disposición oficial.')
    if payload.get('general_scope_confirmed') is not True:
        raise ValueError('Confirme que los días incluidos son generales, sin fiestas locales, insulares o del centro.')
    module, draft, code, year = _context(db, module_id)
    cfg = schedule_engine.clean(draft['schedule'], year)
    if cfg['calendar_confirmed'] is not True:
        raise ValueError('Guarde primero la programación con el calendario contrastado y confirmado.')
    snapshot = _check_general(cfg, code, year)
    source = valid_url(snapshot['calendar_source_url'])
    title = text_value(snapshot['calendar_source_description'],
                       'la disposición oficial, versión y fecha', 700)
    for url in snapshot['calendar_correction_urls']:
        valid_url(url)
    body = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    digest = sha256(body.encode('utf-8')).hexdigest()
    key = _scope_key(code, year)
    last = db.execute("""SELECT * FROM national_general_fp_calendars
        WHERE territory_code=? AND academic_year=? AND stage=?
        ORDER BY revision_number DESC LIMIT 1""", key).fetchone()
    if last and last['content_sha256'] == digest:
        return {'saved': False, 'unchanged': True, 'id': last['id'],
                'revision': last['revision_number'], 'changes': []}
    version = last['revision_number'] + 1 if last else 1
    previous = json.loads(last['snapshot_json']) if last else None
    changes = _changes(previous, snapshot)
    db.execute("""INSERT INTO national_general_fp_calendars (
        territory_code, academic_year, stage, revision_number, snapshot_json,
        content_sha256, source_url, source_title, corrections_json,
        reviewed_at, source_module_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (*key, version, body, digest, source, title,
         json.dumps(snapshot['calendar_correction_urls'], ensure_ascii=False),
         database.now(), int(module_id)))
    ident = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    database.log(db, 'general_calendar_reviewed_by_teacher', 'module', int(module_id),
                 {'territory': code, 'academic_year': year,
                  'revision': version, 'changed_fields': [x['field'] for x in changes]})
    return {'saved': True, 'unchanged': False, 'id': ident,
            'revision': version, 'changes': changes}


def compare(db, module_id, old_id, new_id):
    module, draft, code, year = _context(db, module_id)
    def get(ident):
        row = db.execute("""SELECT * FROM national_general_fp_calendars
            WHERE id=? AND territory_code=? AND academic_year=? AND stage=?""",
            (int(ident), code, year, STAGE)).fetchone()
        if row is None:
            raise ValueError('La versión solicitada pertenece a otro territorio o curso.')
        return row
    old, new = get(old_id), get(new_id)
    return {'old': _record(old), 'new': _record(new),
            'changes': _changes(json.loads(old['snapshot_json']),
                                json.loads(new['snapshot_json'])),
            'notice': ('Compare las fuentes antes de aplicar una nueva versión. '
                       'No implica que una disposición haya sido contrastada automáticamente.')}
