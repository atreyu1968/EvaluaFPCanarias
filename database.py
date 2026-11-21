"""Persistencia SQLite para EvalúaFP. Sin servicios externos."""
from __future__ import annotations
import json
from contextlib import contextmanager
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# Las rutas se resuelven ANTES de abrir SQLite, desde el ejecutable o
# desde la instalación local según el modo seleccionado.
import storage_config
DATA = storage_config.DATA_DIR
BACKUPS = storage_config.BACKUP_DIR
try:
    DATA.mkdir(parents=True, exist_ok=True)
    (DB_DIR := DATA / 'datos').mkdir(parents=True, exist_ok=True)
    (STORAGE := DATA / 'almacen').mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    for directory in (DATA, BACKUPS):
        check = directory / '.comprobar_escritura'
        check.write_text('ok', encoding='utf-8')
        check.unlink()
except OSError as exc:
    raise RuntimeError(f'No se puede escribir en el almacenamiento de EvalúaFP ({DATA} / {BACKUPS}). '
                       'Compruebe la unidad USB, permisos y espacio disponible.') from exc
DB_FILE = DB_DIR / 'evaluafp.sqlite3'


@contextmanager
def connect():
    db = sqlite3.connect(DB_FILE, timeout=30)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=30000')
        with db:
            yield db
    finally:
        db.close()


def init():
    with connect() as d:
        d.execute('PRAGMA journal_mode=' + ('DELETE' if storage_config.PORTABLE else 'WAL'))
        d.executescript('''
        CREATE TABLE IF NOT EXISTS modules(
          id INTEGER PRIMARY KEY, academic_year TEXT NOT NULL, cycle TEXT NOT NULL,
          name TEXT NOT NULL, group_name TEXT DEFAULT '', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS programmings(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          filename TEXT NOT NULL, local_path TEXT NOT NULL, sha256 TEXT NOT NULL,
          extracted_text TEXT NOT NULL, uploaded_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outcomes(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          code TEXT NOT NULL, description TEXT NOT NULL, weight REAL,
          UNIQUE(module_id,code));
        CREATE TABLE IF NOT EXISTS criteria(
          id INTEGER PRIMARY KEY, outcome_id INTEGER NOT NULL REFERENCES outcomes(id),
          code TEXT NOT NULL, description TEXT NOT NULL, weight REAL,
          UNIQUE(outcome_id,code));
        CREATE TABLE IF NOT EXISTS students(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          code TEXT NOT NULL, name TEXT NOT NULL, UNIQUE(module_id,code));
        CREATE TABLE IF NOT EXISTS exams(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          title TEXT NOT NULL, kind TEXT NOT NULL, total_points REAL NOT NULL,
          instructions TEXT DEFAULT '', created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
          ai_model TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS exam_questions(
          id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL REFERENCES exams(id),
          criterion_id INTEGER NOT NULL REFERENCES criteria(id), number INTEGER NOT NULL,
          kind TEXT NOT NULL, prompt TEXT NOT NULL, points REAL NOT NULL,
          options_json TEXT NOT NULL DEFAULT '[]', correct_option TEXT DEFAULT '',
          ideal_answer TEXT DEFAULT '', rubric_json TEXT NOT NULL DEFAULT '[]',
          UNIQUE(exam_id,number));
        CREATE TABLE IF NOT EXISTS submissions(
          id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL REFERENCES exams(id),
          student_id INTEGER NOT NULL REFERENCES students(id), storage_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'received', created_at TEXT NOT NULL,
          current_run_id INTEGER, UNIQUE(exam_id,student_id));
        CREATE TABLE IF NOT EXISTS source_files(
          id INTEGER PRIMARY KEY, submission_id INTEGER NOT NULL REFERENCES submissions(id),
          sequence INTEGER NOT NULL, original_name TEXT NOT NULL, local_path TEXT NOT NULL,
          mime TEXT NOT NULL, sha256 TEXT NOT NULL, page_count INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS pages(
          id INTEGER PRIMARY KEY, submission_id INTEGER NOT NULL REFERENCES submissions(id),
          file_id INTEGER NOT NULL REFERENCES source_files(id), page_number INTEGER NOT NULL,
          source_page INTEGER NOT NULL, image_path TEXT NOT NULL, sha256 TEXT NOT NULL,
          UNIQUE(submission_id,page_number));
        CREATE TABLE IF NOT EXISTS transcription_runs(
          id INTEGER PRIMARY KEY, submission_id INTEGER NOT NULL REFERENCES submissions(id),
          model TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'started');
        CREATE TABLE IF NOT EXISTS page_segments(
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES transcription_runs(id),
          page_id INTEGER NOT NULL REFERENCES pages(id), question_number INTEGER,
          text TEXT NOT NULL, is_continuation INTEGER NOT NULL DEFAULT 0,
          uncertain INTEGER NOT NULL DEFAULT 0, notes TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS corrections(
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES transcription_runs(id),
          submission_id INTEGER NOT NULL REFERENCES submissions(id),
          question_id INTEGER NOT NULL REFERENCES exam_questions(id),
          transcription TEXT NOT NULL, page_numbers_json TEXT NOT NULL,
          ai_score REAL, teacher_score REAL, rubric_result_json TEXT NOT NULL DEFAULT '[]',
          ai_feedback TEXT DEFAULT '', teacher_comment TEXT DEFAULT '',
          needs_review INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'proposed',
          model TEXT DEFAULT '', created_at TEXT NOT NULL, validated_at TEXT,
          UNIQUE(run_id, question_id));
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
          entity TEXT NOT NULL, entity_id INTEGER, details_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS materials(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          programming_id INTEGER NOT NULL REFERENCES programmings(id),
          filename TEXT NOT NULL, local_path TEXT NOT NULL, sha256 TEXT NOT NULL,
          mime TEXT NOT NULL, unit_count INTEGER NOT NULL, chunk_count INTEGER NOT NULL,
          uploaded_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          UNIQUE(programming_id,sha256));
        CREATE TABLE IF NOT EXISTS material_passages(
          id INTEGER PRIMARY KEY, material_id INTEGER NOT NULL REFERENCES materials(id),
          location_kind TEXT NOT NULL, location_number INTEGER NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS exam_materials(
          exam_id INTEGER NOT NULL REFERENCES exams(id), material_id INTEGER NOT NULL REFERENCES materials(id),
          PRIMARY KEY(exam_id,material_id));
        CREATE INDEX IF NOT EXISTS ix_materials_programming ON materials(programming_id,active);
        CREATE INDEX IF NOT EXISTS ix_material_passages ON material_passages(material_id,location_number);
        CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_exams_module ON exams(module_id);
        CREATE INDEX IF NOT EXISTS ix_pages_submission ON pages(submission_id,page_number);
        CREATE INDEX IF NOT EXISTS ix_corrections_submission ON corrections(submission_id);
        CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity,entity_id);
        ''')
        # Migración aditiva: territorio del módulo (el resto de tablas no cambia).
        if 'territory' not in [c[1] for c in d.execute('PRAGMA table_info(modules)')]:
            d.execute("ALTER TABLE modules ADD COLUMN territory TEXT NOT NULL DEFAULT 'Canarias'")
        # Catálogo incremental de títulos/módulos con procedencia y vigencia territorial.
        import fp_catalog
        fp_catalog.migrate(d)
        # Biblioteca local territorial/curso con procedencia docente explícita.
        import national_registry
        national_registry.migrate(d)
        # 1.2.10: crear la biblioteca general antes de exponer sus rutas HTTP.
        import general_calendar_library
        general_calendar_library.migrate(d)
        # Historial opt-in de versiones de fuentes curriculares (no altera notas).
        import curriculum_history
        curriculum_history.migrate(d)
        import normative_monitor
        normative_monitor.migrate(d)
        # 1.1: borradores de programación didáctica, sin alterar documentos ni calificaciones.
        import program_builder
        program_builder.migrate(d)
        # Origen de ponderaciones: automático, programación o decisión docente.
        import weight_defaults
        weight_defaults.migrate(d)
        # Completa automáticamente los valores NULL antiguos, sin tocar pesos explícitos.
        for module in d.execute('SELECT id FROM modules').fetchall():
            weight_defaults.recalculate(d,module['id'])
        # Sistema de evaluación de unidades, instrumentos y evidencias.
        import evaluacion
        evaluacion.migrate(d)
        # Banco de preguntas persistente: los modelos comparten ponderaciones, no preguntas.
        d.executescript('''
        CREATE TABLE IF NOT EXISTS exam_batches(
          id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
          title TEXT NOT NULL, difficulty TEXT NOT NULL CHECK(difficulty IN ('bajo','medio','alto')),
          model_count INTEGER NOT NULL, questions_per_model INTEGER NOT NULL,
          bank_size INTEGER NOT NULL, created_at TEXT NOT NULL, ai_model TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS question_bank_items(
          id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES exam_batches(id),
          criterion_id INTEGER NOT NULL REFERENCES criteria(id),
          kind TEXT NOT NULL, prompt TEXT NOT NULL, fingerprint TEXT NOT NULL,
          options_json TEXT NOT NULL DEFAULT '[]', correct_option TEXT NOT NULL DEFAULT '',
          ideal_answer TEXT NOT NULL DEFAULT '',rubric_json TEXT NOT NULL DEFAULT '[]',
          source_refs_json TEXT NOT NULL DEFAULT '[]',assigned_variant TEXT,
          UNIQUE(batch_id,fingerprint));
        CREATE INDEX IF NOT EXISTS ix_bank_batch ON question_bank_items(batch_id);
        ''')
        columns={r['name'] for r in d.execute('PRAGMA table_info(exams)')}
        for col,typ in [('batch_id','INTEGER REFERENCES exam_batches(id)'),
                        ('variant_label',"TEXT NOT NULL DEFAULT 'A'"),
                        ('difficulty',"TEXT NOT NULL DEFAULT 'medio'"),
                        ('center_name',"TEXT NOT NULL DEFAULT ''"),
                        ('exam_date',"TEXT NOT NULL DEFAULT ''"),
                        ('duration_minutes','INTEGER NOT NULL DEFAULT 60')]:
            if col not in columns:d.execute(f'ALTER TABLE exams ADD COLUMN {col} {typ}')
        columns={r['name'] for r in d.execute('PRAGMA table_info(exam_questions)')}
        if 'bank_item_id' not in columns:
            d.execute('ALTER TABLE exam_questions ADD COLUMN bank_item_id INTEGER REFERENCES question_bank_items(id)')
        # Migración no destructiva: conserva los exámenes y notas de versiones previas.
        columns={r['name'] for r in d.execute('PRAGMA table_info(exam_questions)')}
        if 'source_refs_json' not in columns:
            d.execute("ALTER TABLE exam_questions ADD COLUMN source_refs_json TEXT NOT NULL DEFAULT '[]'")
        columns={r['name'] for r in d.execute('PRAGMA table_info(exams)')}
        if 'source_mode' not in columns:
            d.execute("ALTER TABLE exams ADD COLUMN source_mode TEXT NOT NULL DEFAULT 'criteria'")
        # Vinculación plural pregunta ↔ CE: conservación de criterios previos y pesos por pregunta.
        d.executescript("""
        CREATE TABLE IF NOT EXISTS exam_question_criteria(
          question_id INTEGER NOT NULL REFERENCES exam_questions(id) ON DELETE CASCADE,
          criterion_id INTEGER NOT NULL REFERENCES criteria(id),
          weight_pct REAL NOT NULL CHECK(weight_pct>0 AND weight_pct<=100),
          confidence REAL, rationale TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(question_id,criterion_id));
        CREATE INDEX IF NOT EXISTS ix_exam_question_criteria_criterion
          ON exam_question_criteria(criterion_id);
        CREATE TRIGGER IF NOT EXISTS trg_evaluafp_exam_question_initial_criterion
          AFTER INSERT ON exam_questions
          BEGIN
            INSERT OR IGNORE INTO exam_question_criteria
              (question_id,criterion_id,weight_pct,confidence,rationale)
              VALUES(NEW.id,NEW.criterion_id,100,1,'Asignación única del examen');
          END;
        """)
        d.execute("""INSERT OR IGNORE INTO exam_question_criteria
          (question_id,criterion_id,weight_pct,confidence,rationale)
          SELECT id,criterion_id,100,1,'Asignación original previa a v1.0.5' FROM exam_questions""")
        # La biblioteca general 1.2.10 necesita su tabla antes de atender HTTP.
        # Migración idempotente, válida para instalaciones nuevas y existentes.
        import general_calendar_library
        general_calendar_library.migrate(d)
        _rebase_on_portable_start(d)


def _rebase_on_portable_start(db):
    """Si cambia la letra del pendrive, actualiza referencias absolutas antiguas.

    Se ejecuta en una sola transacción, ANTES de servir originales o páginas.
    """
    if not storage_config.PORTABLE:
        return
    previous = pref(db,'portable_last_data_root')
    if not previous:
        # Una base importada desde una instalación fija anterior carece de
        # portable_last_data_root. Inferir la raíz por la carpeta almacen.
        for table,col in [('source_files','local_path'),('pages','image_path'),
                          ('programmings','local_path'),('materials','local_path')]:
            row=db.execute(f'SELECT {col} FROM {table} LIMIT 1').fetchone()
            if not row or not row[col]:continue
            old=Path(row[col]);parts=old.parts
            pos=next((i for i,item in enumerate(parts) if item.lower()=='almacen'),None)
            if pos is not None and pos>0:
                candidate=Path(*parts[:pos])
                if candidate!=DATA:
                    previous=str(candidate)
                    break
    current = str(DATA)
    if previous and previous != current:
        previous_path = Path(previous)
        for table,column in [('programmings','local_path'),('materials','local_path'),
                             ('submissions','storage_path'),('source_files','local_path'),('pages','image_path')]:
            for row in db.execute(f'SELECT id,{column} FROM {table}').fetchall():
                try:
                    path=Path(row[column]);relative=path.relative_to(previous_path)
                except (TypeError,ValueError):
                    continue
                db.execute(f'UPDATE {table} SET {column}=? WHERE id=?',(str(DATA/relative),row['id']))
        log(db,'portable_path_rebased','system',None,{'old':previous,'new':current})
    set_pref(db,'portable_last_data_root',current)


def log(db, action, entity, entity_id, details):
    db.execute('INSERT INTO audit_log(at,action,entity,entity_id,details_json) VALUES(?,?,?,?,?)',
               (now(), action, entity, entity_id, json.dumps(details, ensure_ascii=False)))


def dicts(rows):
    return [dict(row) for row in rows]


def slug(value):
    value = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ._-]+', '_', str(value))
    return value.strip('._')[:65] or 'documento'


def pref(db, key, default=None):
    row = db.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default


def set_pref(db, key, value):
    db.execute('INSERT INTO preferences(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
               (key, json.dumps(value, ensure_ascii=False)))
