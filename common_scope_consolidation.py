"""Consolidación local de ámbitos: propuestas por materia y decisiones docentes.

La correspondencia exige el mismo curso de referencia, grupo, año, ciclo y
territorio, y coincidencia de código y nombre del alumno. No emite actas.
"""
import json
from decimal import Decimal, InvalidOperation
import common_scopes as cs
import common_scope_grading as grading
import canarias_reference as refs
import database as data

MATTER_KEYS={
    'lengua castellana y ciencias sociales':'lengua_social',
    'lengua extranjera de iniciacion profesional':'extranjera',
    'matematicas y ciencias aplicadas':'matematicas_ciencias',
    'actividad fisica y bienestar emocional':'actividad_fisica',
}
SESSIONS=('trimestre1','trimestre2','trimestre3','ordinaria','extraordinaria')


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS scope_matter_grades(
        id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
        student_id INTEGER NOT NULL REFERENCES students(id), session TEXT NOT NULL,
        grade TEXT NOT NULL, hours TEXT NOT NULL, hours_source TEXT NOT NULL,
        rationale TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE INDEX IF NOT EXISTS ix_scope_matter_grades
        ON scope_matter_grades(module_id,student_id,session,id)""")
    db.execute("""CREATE TABLE IF NOT EXISTS scope_final_decisions(
        id INTEGER PRIMARY KEY, anchor_module_id INTEGER NOT NULL REFERENCES modules(id),
        anchor_student_id INTEGER NOT NULL REFERENCES students(id), session TEXT NOT NULL,
        grade TEXT NOT NULL, rationale TEXT NOT NULL, meeting_ref TEXT NOT NULL,
        snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL)""")


def context(db,mid):
    row=db.execute('SELECT * FROM modules WHERE id=?',(mid,)).fetchone()
    if not row:
        raise ValueError('Materia no encontrada.')
    m=dict(row)
    meta=cs.profile(m['name'],m['cycle'],m['territory'])
    ref=refs.read(db,mid)
    if not meta or not ref or ref['course'] not in (1,2):
        raise ValueError('Seleccione una materia canaria creada desde el índice con curso de referencia.')
    if not str(m.get('group_name') or '').strip():
        raise ValueError('La materia necesita un grupo identificado para consolidar el ámbito.')
    course=ref['course']
    expected=grading.MATTERS[(meta['ambito'],course)]
    if MATTER_KEYS[cs.key(m['name'])] not in expected:
        raise ValueError('La materia no corresponde a este curso del ámbito.')
    migrate(db)
    return m,meta,course,expected


def session_key(value):
    if value not in SESSIONS:
        raise ValueError('Seleccione una evaluación válida.')
    return value


def record_grade(db,mid,raw):
    m,meta,course,expected=context(db,mid)
    if not isinstance(raw,dict) or raw.get('teacher_confirmed') is not True:
        raise ValueError('Confirme la valoración docente y la carga horaria contrastada.')
    sid=raw.get('student_id')
    if type(sid) is not int or not db.execute('SELECT 1 FROM students WHERE id=? AND module_id=?',(sid,mid)).fetchone():
        raise ValueError('Alumno ajeno a la materia.')
    session=session_key(raw.get('session'))
    grade=raw.get('grade')
    if grade not in grading.CONVERSION:
        raise ValueError('Seleccione IN, SU, BI, NT o SB; una nota pendiente no es IN.')
    try:
        hours=Decimal(str(raw.get('hours')))
    except (InvalidOperation,ValueError):
        raise ValueError('Carga horaria no válida.') from None
    if not hours.is_finite() or not 0<hours<=1000 or hours.as_tuple().exponent < -4:
        raise ValueError('Carga horaria no válida.')
    source=cs.clean_text(raw.get('hours_source',''),1000)
    rationale=cs.clean_text(raw.get('rationale',''),4000)
    if not source or not rationale:
        raise ValueError('Indique la fuente horaria y la justificación de la valoración.')
    cur=db.execute("""INSERT INTO scope_matter_grades(module_id,student_id,session,grade,hours,
        hours_source,rationale,created_at) VALUES(?,?,?,?,?,?,?,?)""",
        (mid,sid,session,grade,str(hours),source,rationale,data.now()))
    data.log(db,'scope_matter_grade_recorded','module',mid,{'grade_id':cur.lastrowid,'session':session})
    return cur.lastrowid


def matching_modules(db,m,meta,course,expected):
    matches={k:[] for k in expected}
    for row in db.execute("""SELECT * FROM modules WHERE academic_year=? AND cycle=?
        AND territory=? AND group_name=? ORDER BY id""",
        (m['academic_year'],m['cycle'],m['territory'],m['group_name'])):
        p=cs.profile(row['name'],row['cycle'],row['territory'])
        if not p or p['ambito']!=meta['ambito']:
            continue
        k=MATTER_KEYS[cs.key(row['name'])]
        ref=refs.read(db,row['id'])
        if k in matches and ref and ref['course']==course:
            matches[k].append({'id':row['id'],'name':row['name']})
    return matches


def report(db,mid,session):
    session=session_key(session)
    m,meta,course,expected=context(db,mid)
    matches=matching_modules(db,m,meta,course,expected)
    missing=[k for k in expected if len(matches[k])!=1]
    rows=[]
    for st in db.execute('SELECT id,code,name FROM students WHERE module_id=? ORDER BY name,id',(mid,)):
        values=[]
        blockers=[]
        for k in expected:
            candidates=matches[k]
            if len(candidates)!=1:
                blockers.append(k+': materia ausente o duplicada')
                continue
            module=candidates[0]
            other=db.execute('SELECT id,name FROM students WHERE module_id=? AND code=?',
                             (module['id'],st['code'])).fetchone()
            if not other or cs.key(other['name'])!=cs.key(st['name']):
                blockers.append(k+': identidad sin correspondencia exacta')
                continue
            grade=db.execute("""SELECT * FROM scope_matter_grades WHERE module_id=? AND student_id=?
                              AND session=? ORDER BY id DESC LIMIT 1""",(module['id'],other['id'],session)).fetchone()
            if not grade:
                blockers.append(k+': valoración pendiente')
                continue
            values.append({'matter':k,'module_name':module['name'],**dict(grade)})
        calculation=None
        if not blockers and session in ('ordinaria','extraordinaria'):
            calculation=grading.calculate(meta['ambito'],course,session,values,True)
        # La decisión se registra en el módulo ancla canónico (primera materia).
        # Si está ausente o duplicado no puede registrarse una decisión.
        decision=None
        if not missing and values:
            anchor=next((x for x in values if x['matter']==expected[0]),None)
            if anchor:
                stored=db.execute("""SELECT * FROM scope_final_decisions WHERE anchor_module_id=?
                    AND anchor_student_id=? AND session=? ORDER BY id DESC LIMIT 1""",
                    (anchor['module_id'],anchor['student_id'],session)).fetchone()
                if stored:
                    decision=dict(stored)
                    snapshot=json.loads(decision.pop('snapshot_json'))
                    decision['current']=not blockers and snapshot['grade_ids']==[x['id'] for x in values]
        rows.append({'student':dict(st),'matters':values,'blockers':blockers,
                     'calculation':calculation,'decision':decision})
    return {'module_id':mid,'ambito':meta['ambito'],'course':course,'group':m['group_name'],
            'academic_year':m['academic_year'],'session':session,'matches':matches,
            'missing_or_duplicate':missing,'rows':rows,'source_url':grading.SOURCE}


def record_decision(db,mid,raw):
    if not isinstance(raw,dict) or raw.get('team_confirmed') is not True:
        raise ValueError('Confirme expresamente la decisión del equipo docente.')
    session=session_key(raw.get('session'))
    if session not in ('ordinaria','extraordinaria'):
        raise ValueError('El cierre colegiado se registra en las convocatorias finales.')
    result=report(db,mid,session)
    row=next((x for x in result['rows'] if x['student']['id']==raw.get('student_id')),None)
    if not row or not row['calculation']:
        raise ValueError('Faltan materias, identidad o valoraciones consolidadas.')
    ids=[x['id'] for x in row['matters']]
    if raw.get('grade_ids')!=ids:
        raise ValueError('Las valoraciones han cambiado. Actualice el informe antes de cerrar.')
    grade=raw.get('grade')
    if grade not in grading.CONVERSION or (grade!='IN')!=row['calculation']['passed']:
        raise ValueError('La calificación cualitativa debe ser coherente con la regla de superación.')
    rationale=cs.clean_text(raw.get('rationale',''),4000)
    meeting=cs.clean_text(raw.get('meeting_ref',''),500)
    if not rationale or not meeting:
        raise ValueError('Indique la motivación y la referencia de la sesión del equipo docente.')
    anchor=row['matters'][0]
    snap={'grade_ids':ids,'matters':row['matters'],'calculation':row['calculation']}
    cur=db.execute("""INSERT INTO scope_final_decisions(anchor_module_id,anchor_student_id,session,
        grade,rationale,meeting_ref,snapshot_json,created_at) VALUES(?,?,?,?,?,?,?,?)""",
        (anchor['module_id'],anchor['student_id'],session,grade,rationale,meeting,
         json.dumps(snap,ensure_ascii=False),data.now()))
    data.log(db,'scope_team_decision_recorded','module',anchor['module_id'],
             {'decision_id':cur.lastrowid,'session':session})
    return cur.lastrowid
