"""Historial inmutable de calendarios escolares de FP revisados por el docente.

Las fuentes son enlaces de consulta; no certifica calendarios nacionales ni
traslada fechas entre cursos, territorios, municipios, islas o centros.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json

import territorial_profiles as territories

CALENDAR_FIELDS = (
    'region', 'island', 'municipality', 'start_date', 'end_date',
    'evaluation_ends', 'vacation_periods', 'regional_non_teaching_days',
    'extra_non_teaching_days', 'calendar_profile_id', 'calendar_academic_year',
    'calendar_source_url', 'calendar_source_description',
    'calendar_correction_urls',
)

# Enlaces contrastados como PÁGINAS DE CONSULTA, no como prueba automática
# de las fechas de FP de un centro. Los demás ámbitos usan su portal educativo.
CALENDAR_PAGES = {
    'CN': 'https://www.gobiernodecanarias.org/educacion/web/centros/calendario_escolar/',
    'MD': 'https://www.comunidad.madrid/educacion/calendario-escolar',
    'CE': 'https://www.educacionfpydeportes.gob.es/contenidos/ba/ceuta-melilla/ceuta/portada.html',
}
DATED_SOURCES = {
    ('CN', '2026-2027'): [
        {'url': 'https://www.gobiernodecanarias.org/boc/2026/061/1025.html',
         'title': 'BOC: resolución del calendario escolar 2026-2027', 'kind': 'disposicion'},
        {'url': 'https://www.gobiernodecanarias.org/boc/2026/075/1240.html',
         'title': 'BOC: corrección publicada el 20 de abril de 2026', 'kind': 'correccion'},
    ],
    ('MD', '2026-2027'): [
        {'url': 'https://www.comunidad.madrid/educacion/calendario-escolar',
         'title': 'Madrid: calendario escolar 2026-2027, Orden 2034/2026',
         'kind': 'directorio_con_disposicion'},
    ],
}


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS national_calendar_revisions (
       id INTEGER PRIMARY KEY,
       territory_code TEXT NOT NULL,
       academic_year TEXT NOT NULL,
       center_key TEXT NOT NULL,
       municipality_key TEXT NOT NULL,
       island_key TEXT NOT NULL,
       stage TEXT NOT NULL DEFAULT 'fp_grado_d',
       revision_number INTEGER NOT NULL,
       schedule_json TEXT NOT NULL,
       content_sha256 TEXT NOT NULL,
       source_url TEXT NOT NULL,
       source_title TEXT NOT NULL,
       correction_urls_json TEXT NOT NULL DEFAULT '[]',
       reviewed_at TEXT NOT NULL,
       module_id INTEGER NOT NULL,
       UNIQUE(territory_code, academic_year, center_key, municipality_key,
              island_key, stage, revision_number)
    )''')
    db.execute('''CREATE INDEX IF NOT EXISTS idx_national_calendar_revisions_scope
      ON national_calendar_revisions(territory_code, academic_year, center_key,
      municipality_key, island_key, stage, revision_number DESC)''')


def source_directory(region, academic_year):
    """Enlace oficial de entrada para todos los ámbitos; fechas no inferidas."""
    from national_registry import PORTALS
    name = territories.require_territory(region)
    year = territories.year_code(academic_year)
    code = territories.territory_code(name)
    entry = {'url': CALENDAR_PAGES.get(code, PORTALS[code]),
             'title': 'Portal oficial de la administración educativa de ' + name,
             'kind': 'portal_para_consultar'}
    links = [entry]
    for row in DATED_SOURCES.get((code, year), []):
        if row['url'] not in {link['url'] for link in links}:
            links.append(row.copy())
    return {'territory': name, 'territory_code': code, 'academic_year': year,
            'links': links, 'calendar_verified': False,
            'notice': ('Se ofrecen accesos a portales y algunas disposiciones de consulta. '
                'No se deducen fechas ni festivos: verifique la enseñanza de FP, '
                'modificaciones, fiestas locales y días del centro. La ausencia de '
                'una fuente no significa que no exista calendario oficial.')}


def _context(db, module_id):
    from national_registry import scope, text_value
    module, draft, code = scope(db, int(module_id))
    center = str(draft.get('center') or '').strip()
    cfg = draft['schedule']
    municipality = str(cfg.get('municipality') or '').strip()
    island = str(cfg.get('island') or '').strip() if code == 'CN' else ''
    if not center:
        return module, draft, code, center, (), None
    text_value(center, 'el centro educativo', 220)
    # No se mezclan centros homónimos que estén en municipios/islas distintos.
    key = (code, territories.year_code(module['academic_year']),
           territories.fold(center), territories.fold(municipality),
           territories.fold(island), 'fp_grado_d')
    return module, draft, code, center, key, cfg


def _validate_year(snapshot, year):
    start = int(year[:4])
    lower, upper = date(start, 9, 1), date(start + 1, 8, 31)
    def inside(raw):
        if raw:
            d = date.fromisoformat(raw)
            if not lower <= d <= upper:
                raise ValueError('El calendario incluye fechas ajenas al curso académico seleccionado.')
    inside(snapshot['start_date'])
    inside(snapshot['end_date'])
    if not snapshot['start_date'] or not snapshot['end_date']:
        raise ValueError('Defina inicio y fin de las clases antes de archivar.')
    for val in snapshot['evaluation_ends']:
        inside(val)
    for row in snapshot['vacation_periods']:
        inside(row['start']); inside(row['end'])
    for row in snapshot['regional_non_teaching_days']:
        inside(row['date'])
    for val in snapshot['extra_non_teaching_days']:
        inside(val)


def _snapshot(cfg, year):
    import schedule_engine
    clean = schedule_engine.clean(cfg, year)
    result = {k: clean[k] for k in CALENDAR_FIELDS}
    _validate_year(result, year)
    return result


def _revision_row(row, full=False):
    rec = dict(row)
    payload = {
        'id': rec['id'], 'revision': rec['revision_number'],
        'territory_code': rec['territory_code'], 'academic_year': rec['academic_year'],
        'center_key': rec['center_key'], 'municipality_key': rec['municipality_key'],
        'island_key': rec['island_key'], 'stage': rec['stage'],
        'source_url': rec['source_url'], 'source_title': rec['source_title'],
        'correction_urls': json.loads(rec['correction_urls_json']),
        'reviewed_at': rec['reviewed_at'], 'sha256': rec['content_sha256'],
        'status': 'revisado_por_docente_no_certificado',
    }
    if full:
        payload['schedule'] = json.loads(rec['schedule_json'])
    return payload


def list_versions(db, module_id):
    module, draft, code, center, key, _ = _context(db, module_id)
    rows = []
    if key:
        rows = db.execute('''SELECT * FROM national_calendar_revisions
            WHERE territory_code=? AND academic_year=? AND center_key=?
             AND municipality_key=? AND island_key=? AND stage=?
            ORDER BY revision_number DESC LIMIT 50''', key).fetchall()
    return {'territory': territories.require_territory(draft.get('region') or module['territory']),
            'territory_code': code, 'academic_year': module['academic_year'],
            'center': center, 'municipality': draft['schedule'].get('municipality',''),
            'island': draft['schedule'].get('island',''), 'count': len(rows),
            'versions': [_revision_row(row, full=True) for row in rows],
            'source_directory': source_directory(code, module['academic_year']),
            'notice': ('Historial local de propuestas revisadas por el docente. '
              'Reutilizar una versión deja la confirmación sin marcar, y exige '
              'nueva revisión del centro y del curso. No acredita vigencia legal.')}


def _changes(old, new):
    if old is None:
        return []
    names = {
        'start_date': 'Inicio de las clases', 'end_date': 'Fin de las clases',
        'evaluation_ends': 'Fechas de evaluación',
        'vacation_periods': 'Vacaciones',
        'regional_non_teaching_days': 'Festivos y días no lectivos territoriales',
        'extra_non_teaching_days': 'Días añadidos por el centro o municipio',
        'municipality': 'Municipio', 'island': 'Isla',
        'calendar_source_url': 'Fuente principal',
        'calendar_source_description': 'Título de la disposición',
        'calendar_correction_urls': 'Enlaces de correcciones',
    }
    return [{'field': k, 'label': label, 'previous': old.get(k), 'current': new.get(k)}
            for k, label in names.items() if old.get(k) != new.get(k)]


def record_from_draft(db, module_id, cfg=None):
    """Únicamente tras confirmación docente y junto al guardado de calendario.

    Nunca sobrescribe versiones. Repetir una misma ficha consecutiva es idempotente.
    """
    from national_registry import text_value, valid_url
    import database
    module, draft, code, center, key, current = _context(db, module_id)
    if not key:
        raise ValueError('Indique el centro educativo para conservar el calendario.')
    cfg = cfg or current
    if cfg.get('calendar_confirmed') is not True:
        raise ValueError('Confirme expresamente el calendario tras revisar las fuentes.')
    snapshot = _snapshot(cfg, module['academic_year'])
    if territories.territory_code(snapshot['region']) != code:
        raise ValueError('El ámbito del calendario no coincide con el módulo.')
    if territories.fold(snapshot['municipality']) != key[3] or territories.fold(snapshot['island']) != key[4]:
        raise ValueError('El calendario no corresponde al municipio/isla del centro.')
    url = valid_url(snapshot['calendar_source_url'])
    title = text_value(snapshot['calendar_source_description'], 'la disposición y su fecha', 700)
    corrections = snapshot['calendar_correction_urls']
    for link in corrections: valid_url(link)
    body = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',',':'))
    digest = sha256(body.encode('utf-8')).hexdigest()
    prior = db.execute('''SELECT * FROM national_calendar_revisions
         WHERE territory_code=? AND academic_year=? AND center_key=?
           AND municipality_key=? AND island_key=? AND stage=?
         ORDER BY revision_number DESC LIMIT 1''', key).fetchone()
    if prior and prior['content_sha256'] == digest:
        return {'saved': False, 'unchanged': True, 'revision': prior['revision_number'],
                'id': prior['id'], 'changes': []}
    changes = _changes(json.loads(prior['schedule_json']) if prior else None, snapshot)
    version = prior['revision_number']+1 if prior else 1
    db.execute('''INSERT INTO national_calendar_revisions
       (territory_code,academic_year,center_key,municipality_key,island_key,stage,
        revision_number,schedule_json,content_sha256,source_url,source_title,
        correction_urls_json,reviewed_at,module_id)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
       (*key, version, body, digest, url, title,
        json.dumps(corrections, ensure_ascii=False), database.now(), int(module_id)))
    ident = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    database.log(db, 'calendar_revision_reviewed_by_teacher', 'module', int(module_id),
                 {'territory': code,'academic_year':module['academic_year'],
                  'center':center,'revision':version,'changed_fields':[x['field'] for x in changes]})
    return {'saved': True, 'unchanged': False, 'revision': version,
            'id': ident, 'changes': changes}


def compare_versions(db, module_id, old_id, new_id):
    module, draft, code, center, key, _ = _context(db, module_id)
    if not key: raise ValueError('Guarde primero el nombre del centro.')
    def get(ident):
        row = db.execute('''SELECT * FROM national_calendar_revisions WHERE id=?
            AND territory_code=? AND academic_year=? AND center_key=?
            AND municipality_key=? AND island_key=? AND stage=?''',
            (int(ident), *key)).fetchone()
        if row is None:
            raise ValueError('Versión no encontrada para este centro, territorio, municipio y curso.')
        return row
    old, new = get(old_id), get(new_id)
    return {'old': _revision_row(old), 'new': _revision_row(new),
            'changes': _changes(json.loads(old['schedule_json']), json.loads(new['schedule_json'])),
            'notice': ('Comparación documental, no decisión sobre la aplicación o '
                       'vigencia de una norma. Revise la legislación y la PGA del centro.')}