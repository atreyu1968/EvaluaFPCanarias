"""Cuaderno local de evidencias de materias de ámbitos comunes.

No calcula notas oficiales, no utiliza IA y no escribe en outcomes, criteria,
exams ni en las tablas de calificación de módulos profesionales.
"""
import hashlib
import json
import datetime
import common_scopes as cs
import database as data

LEVELS=('NE','IN','SU','BI','NT','SB')
INSTRUMENTS=('observacion','rubrica','lista_cotejo','prueba','portfolio','proyecto','otro')


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS scope_activities(
        id INTEGER PRIMARY KEY,
        module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
        title TEXT NOT NULL, situation TEXT NOT NULL, instrument TEXT NOT NULL,
        term INTEGER NOT NULL CHECK(term BETWEEN 1 AND 3), activity_date TEXT NOT NULL,
        criteria_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS scope_evidence(
        id INTEGER PRIMARY KEY,
        activity_id INTEGER NOT NULL REFERENCES scope_activities(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        criterion_code TEXT NOT NULL, level TEXT NOT NULL, notes TEXT NOT NULL,
        evidence_ref TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE INDEX IF NOT EXISTS ix_scope_evidence_latest
        ON scope_evidence(activity_id,student_id,criterion_code,id)""")


def criterion_map(draft):
    return {x['code']:{'code':x['code'],'description':x['description'],
                       'competency_code':c['code'],'competency_description':c['description'],
                       'descriptors':x.get('descriptors',''),
                       'competency_descriptors':c.get('descriptors','')}
            for c in draft['competencies'] for x in c['criteria']}


def fingerprint(criterion):
    return hashlib.sha256(json.dumps(criterion,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def context(db,mid):
    scope=cs.load(db,mid)
    migrate(db)
    return scope,criterion_map(scope['draft'])


def need_review(scope):
    if not scope['draft']['teacher_reviewed']:
        raise ValueError('Revise y guarde el currículo de la materia antes de registrar evidencias.')


def create_activity(db,mid,raw):
    scope,criteria=context(db,mid)
    need_review(scope)
    if not isinstance(raw,dict):
        raise ValueError('Actividad no válida.')
    title=cs.clean_text(raw.get('title',''),250)
    situation=cs.clean_text(raw.get('situation',''),2000)
    instrument=raw.get('instrument')
    term=raw.get('term')
    if not title or not situation or instrument not in INSTRUMENTS or type(term) is not int or term not in (1,2,3):
        raise ValueError('Indique actividad, situación de aprendizaje, instrumento y evaluación.')
    date=cs.clean_text(raw.get('activity_date',''),10)
    try:
        if datetime.date.fromisoformat(date).isoformat()!=date:
            raise ValueError()
    except ValueError:
        raise ValueError('Fecha de actividad incorrecta.') from None
    codes=raw.get('criterion_codes')
    if not isinstance(codes,list) or not codes or len(codes)>100 or any(not isinstance(x,str) for x in codes):
        raise ValueError('Seleccione al menos un criterio de la materia.')
    if len(set(codes))!=len(codes) or any(x not in criteria for x in codes):
        raise ValueError('Criterios duplicados o ajenos al currículo de la materia.')
    snapshot=[criteria[x] for x in codes]
    cur=db.execute("""INSERT INTO scope_activities(module_id,title,situation,instrument,term,
        activity_date,criteria_json,created_at) VALUES(?,?,?,?,?,?,?,?)""",
        (mid,title,situation,instrument,term,date,json.dumps(snapshot,ensure_ascii=False),data.now()))
    data.log(db,'scope_activity_created','module',mid,{'activity_id':cur.lastrowid,'criteria':codes})
    return cur.lastrowid


def record_evidence(db,mid,raw):
    scope,criteria=context(db,mid)
    need_review(scope)
    if not isinstance(raw,dict):
        raise ValueError('Evidencia no válida.')
    aid=raw.get('activity_id')
    sid=raw.get('student_id')
    if type(aid) is not int or type(sid) is not int:
        raise ValueError('Seleccione una actividad y un alumno.')
    activity=db.execute('SELECT criteria_json FROM scope_activities WHERE id=? AND module_id=?',(aid,mid)).fetchone()
    student=db.execute('SELECT id FROM students WHERE id=? AND module_id=?',(sid,mid)).fetchone()
    if not activity or not student:
        raise ValueError('Actividad o alumno ajeno a la materia.')
    code=cs.clean_text(raw.get('criterion_code',''),20)
    snapshot={x['code']:x for x in json.loads(activity['criteria_json'])}
    if code not in snapshot or code not in criteria or fingerprint(snapshot[code])!=fingerprint(criteria[code]):
        raise ValueError('Criterio ajeno o modificado desde la actividad. Cree una actividad con el currículo actualizado.')
    level=raw.get('level')
    if level not in LEVELS:
        raise ValueError('Seleccione una valoración de la evidencia.')
    notes=cs.clean_text(raw.get('notes',''),4000)
    ref=cs.clean_text(raw.get('evidence_ref',''),500)
    if not notes and not ref:
        raise ValueError('Indique una observación o referencia de la evidencia.')
    cur=db.execute("""INSERT INTO scope_evidence(activity_id,student_id,criterion_code,level,
        notes,evidence_ref,created_at) VALUES(?,?,?,?,?,?,?)""",
        (aid,sid,code,level,notes,ref,data.now()))
    data.log(db,'scope_evidence_recorded','module',mid,
             {'activity_id':aid,'evidence_id':cur.lastrowid,'criterion_code':code})
    return cur.lastrowid


def load(db,mid):
    scope,criteria=context(db,mid)
    students=data.dicts(db.execute('SELECT id,code,name FROM students WHERE module_id=? ORDER BY name,id',(mid,)))
    activities=[]
    for row in db.execute('SELECT * FROM scope_activities WHERE module_id=? ORDER BY activity_date DESC,id DESC',(mid,)):
        item=dict(row)
        item['criteria']=json.loads(item.pop('criteria_json'))
        item['criteria_current']=all(x['code'] in criteria and fingerprint(x)==fingerprint(criteria[x['code']])
                                    for x in item['criteria'])
        activities.append(item)
    evidence=data.dicts(db.execute("""SELECT e.* FROM scope_evidence e
        JOIN scope_activities a ON a.id=e.activity_id
        JOIN students s ON s.id=e.student_id AND s.module_id=a.module_id
        WHERE a.module_id=? ORDER BY e.id DESC""",(mid,)))
    # La última valoración sustituye únicamente la visualización, no el historial.
    latest={}
    for e in evidence:
        k=(e['activity_id'],e['student_id'],e['criterion_code'])
        latest.setdefault(k,e)
    return {'profile':scope['profile'],'teacher_reviewed':scope['draft']['teacher_reviewed'],
            'criteria':list(criteria.values()),'students':students,'activities':activities,
            'latest_evidence':list(latest.values()),'history':evidence,
            'notice':'Valoraciones de evidencias, no calificaciones oficiales de materia o ámbito.'}
