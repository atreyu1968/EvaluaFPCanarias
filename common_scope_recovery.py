"""Planes de refuerzo y recuperación de materias de ámbitos comunes.

Los planes y sus revisiones no cambian calificaciones ni acreditan promoción.
Los pendientes de primero se vinculan manualmente a una materia de origen y
a un alumno del curso anterior, con comprobación de identidad y procedencia.
"""
import datetime
import json
import re
import common_scopes as cs
import common_scope_notebook as book
import common_scope_consolidation as consolidation
import database as data

KINDS=('refuerzo','recuperacion','pendiente_primero')
STATUSES=('en_curso','revisado','finalizado','no_superado')


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS scope_recovery_plans(
        id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
        student_id INTEGER NOT NULL REFERENCES students(id), kind TEXT NOT NULL,
        origin_module_id INTEGER REFERENCES modules(id), origin_student_id INTEGER REFERENCES students(id),
        criteria_json TEXT NOT NULL, objectives TEXT NOT NULL, actions TEXT NOT NULL,
        instruments TEXT NOT NULL, due_date TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS scope_recovery_reviews(
        id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES scope_recovery_plans(id),
        status TEXT NOT NULL, observations TEXT NOT NULL, evidence_json TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    db.execute("""CREATE INDEX IF NOT EXISTS ix_scope_recovery_reviews
        ON scope_recovery_reviews(plan_id,id)""")


def student(db,mid,sid):
    if type(sid) is not int:
        raise ValueError('Seleccione un alumno.')
    row=db.execute('SELECT id,code,name FROM students WHERE id=? AND module_id=?',(sid,mid)).fetchone()
    if not row:
        raise ValueError('Alumno ajeno a la materia.')
    return dict(row)


def previous_year(year):
    m=re.fullmatch(r'(\d{4})-(\d{4})',year)
    if not m or int(m[2])!=int(m[1])+1:
        raise ValueError('Curso académico no identificado.')
    return f'{int(m[1])-1}-{m[1]}'


def origins(db,mid,sid):
    m,meta,course,expected=consolidation.context(db,mid)
    st=student(db,mid,sid)
    if course!=2:
        return []
    out=[]
    for row in db.execute("""SELECT * FROM modules WHERE academic_year=? AND cycle=?
        AND territory=? ORDER BY id""",(previous_year(m['academic_year']),m['cycle'],m['territory'])):
        p=cs.profile(row['name'],row['cycle'],row['territory'])
        if not p or p['ambito']!=meta['ambito']:
            continue
        ref=consolidation.refs.read(db,row['id'])
        if not ref or ref['course']!=1:
            continue
        other=db.execute('SELECT id,name FROM students WHERE module_id=? AND code=?',
                         (row['id'],st['code'])).fetchone()
        if not other or cs.key(other['name'])!=cs.key(st['name']):
            continue
        result=consolidation.report(db,row['id'],'extraordinaria')
        record=next((x for x in result['rows'] if x['student']['id']==other['id']),None)
        decision=record['decision'] if record else None
        # No inferir pendientes de la falta de nota, de una media provisional
        # ni de una decisión desactualizada.
        if decision and decision['current'] and decision['grade']=='IN':
            scope=cs.load(db,row['id'])
            if scope['draft']['teacher_reviewed']:
                out.append({'module_id':row['id'],'student_id':other['id'],
                            'name':row['name'],'academic_year':row['academic_year'],
                            'group':row['group_name'],'decision_id':decision['id'],
                            'criteria':list(book.criterion_map(scope['draft']).values())})
    return out


def required_text(raw,key,limit):
    value=cs.clean_text(raw.get(key,''),limit)
    if not value:
        raise ValueError('Complete objetivos, actuaciones e instrumentos del plan.')
    return value


def create(db,mid,raw):
    scope,criteria=book.context(db,mid)
    book.need_review(scope)
    migrate(db)
    if not isinstance(raw,dict):
        raise ValueError('Plan incorrecto.')
    st=student(db,mid,raw.get('student_id'))
    kind=raw.get('kind')
    if kind not in KINDS:
        raise ValueError('Seleccione el tipo de plan.')
    omid=osid=None
    decision_id=None
    if kind=='pendiente_primero':
        if raw.get('origin_confirmed') is not True:
            raise ValueError('Confirme la identidad y el pendiente oficial de origen.')
        match=next((x for x in origins(db,mid,st['id'])
                    if x['module_id']==raw.get('origin_module_id') and
                    x['student_id']==raw.get('origin_student_id') and
                    x['decision_id']==raw.get('origin_decision_id')),None)
        if not match:
            raise ValueError('No existe una decisión final extraordinaria insuficiente vigente en el curso anterior.')
        omid,osid,decision_id=match['module_id'],match['student_id'],match['decision_id']
        criteria={x['code']:x for x in match['criteria']}
    codes=raw.get('criterion_codes')
    if not isinstance(codes,list) or not codes or len(codes)>100 or any(not isinstance(x,str) for x in codes):
        raise ValueError('Seleccione criterios objeto del plan.')
    if len(set(codes))!=len(codes) or any(x not in criteria for x in codes):
        raise ValueError('Criterios ajenos o duplicados.')
    due=cs.clean_text(raw.get('due_date',''),10)
    try:
        if datetime.date.fromisoformat(due).isoformat()!=due:
            raise ValueError()
    except ValueError:
        raise ValueError('Fecha de revisión incorrecta.') from None
    snapshot={'criteria':[criteria[x] for x in codes],
              'origin_decision_id':decision_id,'source_id':cs.SOURCE_ID}
    cur=db.execute("""INSERT INTO scope_recovery_plans(module_id,student_id,kind,origin_module_id,
        origin_student_id,criteria_json,objectives,actions,instruments,due_date,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(mid,st['id'],kind,omid,osid,json.dumps(snapshot,ensure_ascii=False),
        required_text(raw,'objectives',4000),required_text(raw,'actions',8000),
        required_text(raw,'instruments',4000),due,data.now()))
    data.log(db,'scope_recovery_plan_created','module',mid,{'plan_id':cur.lastrowid,'kind':kind})
    return cur.lastrowid


def review(db,mid,raw):
    book.context(db,mid)
    migrate(db)
    if not isinstance(raw,dict) or raw.get('teacher_confirmed') is not True:
        raise ValueError('Confirme la revisión del plan.')
    pid=raw.get('plan_id')
    if type(pid) is not int:
        raise ValueError('Seleccione un plan.')
    plan=db.execute('SELECT * FROM scope_recovery_plans WHERE id=? AND module_id=?',(pid,mid)).fetchone()
    if not plan:
        raise ValueError('Plan ajeno a la materia.')
    status=raw.get('status')
    if status not in STATUSES:
        raise ValueError('Estado de seguimiento incorrecto.')
    observations=required_text(raw,'observations',8000)
    ids=raw.get('evidence_ids',[])
    if not isinstance(ids,list) or len(ids)>200 or any(type(x) is not int for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('Seleccione evidencias válidas y distintas.')
    codes={x['code']:x for x in json.loads(plan['criteria_json'])['criteria']}
    snapshots=[]
    # Los pendientes pueden citar evidencias del curso actual y del curso
    # de origen solo si pertenecen al alumno y al mismo criterio literal.
    allowed={(mid,plan['student_id'])}
    if plan['origin_module_id']:
        allowed.add((plan['origin_module_id'],plan['origin_student_id']))
    for eid in ids:
        row=db.execute("""SELECT e.*,a.module_id,a.criteria_json,a.title AS activity_title
            FROM scope_evidence e JOIN scope_activities a ON a.id=e.activity_id WHERE e.id=?""",(eid,)).fetchone()
        if not row or (row['module_id'],row['student_id']) not in allowed or row['criterion_code'] not in codes:
            raise ValueError('Evidencia ajena al alumno o al plan.')
        criterion=next((x for x in json.loads(row['criteria_json']) if x['code']==row['criterion_code']),None)
        if not criterion or book.fingerprint(criterion)!=book.fingerprint(codes[row['criterion_code']]):
            raise ValueError('La evidencia corresponde a otra versión del criterio.')
        if row['level']=='NE':
            raise ValueError('Una evidencia no evaluada no acredita una revisión.')
        item=dict(row)
        item.pop('criteria_json')
        snapshots.append(item)
    cur=db.execute("""INSERT INTO scope_recovery_reviews(plan_id,status,observations,evidence_json,created_at)
        VALUES(?,?,?,?,?)""",(pid,status,observations,json.dumps(snapshots,ensure_ascii=False),data.now()))
    data.log(db,'scope_recovery_plan_reviewed','module',mid,{'plan_id':pid,'review_id':cur.lastrowid,'status':status})
    return cur.lastrowid


def load(db,mid):
    scope,criteria=book.context(db,mid)
    migrate(db)
    plans=[]
    for row in db.execute('SELECT * FROM scope_recovery_plans WHERE module_id=? ORDER BY id DESC',(mid,)):
        p=dict(row)
        p['snapshot']=json.loads(p.pop('criteria_json'))
        p['reviews']=[]
        for rev in db.execute('SELECT * FROM scope_recovery_reviews WHERE plan_id=? ORDER BY id DESC',(p['id'],)):
            item=dict(rev)
            item['evidence']=json.loads(item.pop('evidence_json'))
            p['reviews'].append(item)
        p['status']=p['reviews'][0]['status'] if p['reviews'] else 'en_curso'
        plans.append(p)
    return {'plans':plans,'notice':'Seguimiento de recuperación; no modifica notas ni decisiones de promoción.'}
