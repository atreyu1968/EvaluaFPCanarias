"""Procedencia documental de módulos elegidos en la edición Canarias A&G.

La ficha del anexo de 2024 es una referencia histórica. Nunca acredita por
sí sola la vigencia, las horas de 2026-2027 ni los RA/CE de un módulo.
"""
from __future__ import annotations

import canarias_ag
import canarias_modules


def migrate(db):
    """Migración aditiva y repetible para datos existentes."""
    db.execute("""CREATE TABLE IF NOT EXISTS canarias_module_references (
        module_id INTEGER PRIMARY KEY REFERENCES modules(id) ON DELETE CASCADE,
        cycle TEXT NOT NULL,
        module_name TEXT NOT NULL,
        module_code TEXT,
        course INTEGER NOT NULL CHECK (course IN (1,2)),
        reference_annual_hours INTEGER NOT NULL,
        reference_weekly_hours INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        source_page INTEGER NOT NULL,
        reference_academic_year TEXT NOT NULL,
        state_title_url TEXT NOT NULL,
        state_title TEXT NOT NULL,
        captured_at TEXT NOT NULL
    )""")


def resolve(cycle, academic_year, name, course, code=''):
    """Exige correspondencia literal con el índice según ciclo y curso."""
    if str(course) not in ('1', '2'):
        raise ValueError('Seleccione el primero o segundo curso de la referencia modular.')
    canonical = canarias_ag.canonical_cycle(cycle)
    listing = canarias_modules.list_modules(canonical, academic_year, course)
    module_name = str(name or '').strip()
    module_code = str(code or '').strip()
    matches = [item for item in listing['modules']
               if item['name'] == module_name and (item['code'] or '') == module_code]
    if len(matches) != 1:
        raise ValueError(
            'La referencia seleccionada no coincide con ciclo, curso, código y módulo. '
            'Vuelva a elegirla del índice o cree el módulo manualmente.'
        )
    record = matches[0]
    title = listing['state_title_regulation']
    return {
        'cycle': canonical,
        'module_name': module_name,
        'module_code': record['code'],
        'course': record['course'],
        'reference_annual_hours': record['reference_annual_hours'],
        'reference_weekly_hours': record['reference_weekly_hours'],
        'source_url': listing['source_url'],
        'source_title': listing['source_title'],
        'source_page': record['source_page'],
        'reference_academic_year': listing['reference_academic_year'],
        'state_title_url': title['url'],
        'state_title': title['title'],
    }


def store(db, module_id, record):
    """Guarda una captura de procedencia sin tocar currículo ni calificaciones."""
    fields = (
        'cycle', 'module_name', 'module_code', 'course',
        'reference_annual_hours', 'reference_weekly_hours',
        'source_url', 'source_title', 'source_page',
        'reference_academic_year', 'state_title_url', 'state_title',
    )
    db.execute(
        'INSERT INTO canarias_module_references '
        '(module_id,' + ','.join(fields) + ',captured_at) VALUES (' +
        ','.join('?' for _ in range(len(fields) + 2)) + ')',
        (module_id, *(record[key] for key in fields), __import__('database').now())
    )


def read(db, module_id):
    # Algunas bases antiguas o pruebas con SQLite mínimo aún no han pasado
    # por la migración completa; no debe impedirse leer su programación.
    table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='canarias_module_references'"
    ).fetchone()
    if table is None:
        return None
    row = db.execute(
        'SELECT * FROM canarias_module_references WHERE module_id=?', (module_id,)
    ).fetchone()
    if row is None:
        return None
    return {
        **dict(row),
        'status': 'reference_requires_current_verification',
        'curriculum_confirmed': False,
        'hours_confirmed': False,
        'ra_ce_imported_from_reference': False,
        'notice': (
            'Procedencia histórica de 2024: compruebe su vigencia y las modificaciones '
            'del curso y centro. Las horas, RA y CE no se han confirmado ni importado.'
        ),
    }
