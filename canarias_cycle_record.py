"""Expediente interno de ciclo, con cierres docentes y acuerdos trazables.

La identidad se contrasta por código y nombre. Las notas de años anteriores
son candidatos, no equivalencias oficiales. El índice horario histórico no
acredita la totalidad de la matrícula ni asigna convocatorias a cierres.
"""
import hashlib
import json
import re
import canarias_ag as ag
import canarias_modules as catalog
import canarias_reference as refs
import canarias_academic_decisions as rules
import common_scopes as cs
import common_scope_consolidation as scopes
import evaluacion
import database as data

SESSIONS=('ordinaria','extraordinaria')


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS cycle_decision_records(
        id INTEGER PRIMARY KEY, anchor_module_id INTEGER NOT NULL REFERENCES modules(id),
        anchor_student_id INTEGER NOT NULL REFERENCES students(id),
        action TEXT NOT NULL, session TEXT NOT NULL, report_sha256 TEXT NOT NULL,
        input_json TEXT NOT NULL, result_json TEXT NOT NULL, snapshot_json TEXT NOT NULL,
        agreement TEXT NOT NULL, meeting_ref TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE INDEX IF NOT EXISTS ix_cycle_decisions
        ON cycle_decision_records(anchor_module_id,anchor_student_id,id)""")


def context(db,mid):
    row=db.execute('SELECT * FROM modules WHERE id=?',(mid,)).fetchone()
    if not row:
        raise ValueError('Materia o módulo no encontrado.')
    m=dict(row)
    ref=refs.read(db,mid)
    if m['territory']!='Canarias' or not ref or ref['course'] not in (1,2):
        raise ValueError('Seleccione un módulo canario creado desde el índice con curso de referencia.')
    if not str(m.get('group_name') or '').strip():
        raise ValueError('El módulo necesita un grupo identificado.')
    return m,ref['course']


def student(db,mid,sid):
    row=db.execute('SELECT id,code,name FROM students WHERE id=? AND module_id=?',(sid,mid)).fetchone()
    if not row:
        raise ValueError('El alumno no pertenece al módulo seleccionado.')
    return dict(row)


def roster(db,mid):
    m,course=context(db,mid)
    return {'module':m,'course':course,
            'students':data.dicts(db.execute('SELECT id,code,name FROM students WHERE module_id=? ORDER BY name,id',(mid,)))}


def identity(db,mid,st):
    row=db.execute('SELECT id,code,name FROM students WHERE module_id=? AND code=?',(mid,st['code'])).fetchone()
    if not row or cs.key(row['name'])!=cs.key(st['name']):
        return None
    return dict(row)


def item_key(name,code):
    return (str(code or ''),cs.key(name))


def module_state(db,m,st,session):
    match=identity(db,m['id'],st)
    if not match:
        return {'status':'identidad_pendiente','score':None}
    meta=cs.profile(m['name'],m['cycle'],m['territory'])
    if meta:
        try:
            report=scopes.report(db,m['id'],session)
        except ValueError as exc:
            return {'status':'pendiente','score':None,'warning':str(exc)}
        row=next((x for x in report['rows'] if x['student']['id']==match['id']),None)
        decision=row.get('decision') if row else None
        if not decision or not decision['current']:
            return {'status':'pendiente','score':None,'ambito':meta['ambito'],
                    'warning':'Falta acuerdo vigente del ámbito y convocatoria.'}
        return {'status':'no_superado' if decision['grade']=='IN' else 'superado',
                'score':decision['grade'],'ambito':meta['ambito'],
                'closure_id':decision['id'],'closure_kind':'acuerdo_ambito',
                'student_id':match['id'],'validated_at':decision['created_at']}
    result=evaluacion.summary(db,m['id'],match['id'])['students'][0]
    closure=result.get('closure')
    if not closure or not closure['current'] or closure['score'] is None:
        return {'status':'pendiente','score':None,
                'warning':'Falta cierre docente vigente; no se usa la nota provisional.'}
    # El cierre profesional actual no identifica la convocatoria. No se
    # presenta como nota de ordinaria/extraordinaria sin contraste externo.
    return {'status':'cierre_sin_convocatoria','score':closure['score'],
            'closure_id':closure['id'],'closure_kind':'cierre_modulo',
            'student_id':match['id'],'validated_at':closure['validated_at'],
            'evidence_sha256':closure['evidence_sha256'],
            'warning':'Cierre docente vigente; confirme su convocatoria y efectos en el expediente.'}


def previous_year(year):
    match=re.fullmatch(r'(\d{4})-(\d{4})',year)
    if not match or int(match[2])!=int(match[1])+1:
        raise ValueError('Curso académico no válido.')
    return f'{int(match[1])-1}-{match[1]}'


def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def report(db,mid,sid,session):
    if session not in SESSIONS:
        raise ValueError('Seleccione convocatoria final.')
    m,course=context(db,mid)
    st=student(db,mid,sid)
    index=catalog.list_modules(m['cycle'],m['academic_year'],course)
    available={}
    unclassified=[]
    for row in db.execute("""SELECT * FROM modules WHERE academic_year=? AND cycle=?
        AND territory=? AND group_name=? ORDER BY id""",
        (m['academic_year'],m['cycle'],m['territory'],m['group_name'])):
        ref=refs.read(db,row['id'])
        if not ref:
            unclassified.append({'id':row['id'],'name':row['name']})
        elif ref['course']==course:
            available.setdefault(item_key(row['name'],ref['module_code']),[]).append(dict(row))
    items=[]
    for expected in index['modules']:
        k=item_key(expected['name'],expected['code'])
        candidates=available.pop(k,[])
        base={'name':expected['name'],'code':expected['code'],
              'reference_weekly_hours':expected['reference_weekly_hours']}
        if len(candidates)!=1:
            items.append({**base,'status':'ausente' if not candidates else 'duplicado',
                          'score':None,'candidate_ids':[x['id'] for x in candidates]})
        else:
            row=candidates[0]
            items.append({**base,'module_id':row['id'],**module_state(db,row,st,session)})
    for candidates in available.values():
        for row in candidates:
            unclassified.append({'id':row['id'],'name':row['name']})
    history=[]
    if course==2:
        for row in db.execute("""SELECT * FROM modules WHERE academic_year=? AND cycle=?
            AND territory=? ORDER BY id""",(previous_year(m['academic_year']),m['cycle'],m['territory'])):
            ref=refs.read(db,row['id'])
            if not ref or ref['course']!=1 or not identity(db,row['id'],st):
                continue
            history.append({'module_id':row['id'],'name':row['name'],'group':row['group_name'],
                            'academic_year':row['academic_year'],
                            **module_state(db,dict(row),st,session)})
    snapshot={'module_id':mid,'student':st,'cycle':m['cycle'],'academic_year':m['academic_year'],
              'group':m['group_name'],'course':course,'session':session,
              'items':items,'unclassified':unclassified,'previous_candidates':history,
              'index_source':index['source_url'],
              'notice':'Índice histórico no exhaustivo: revise optativas, convalidaciones, exenciones, pendientes y convocatoria.'}
    snapshot['sha256']=digest(snapshot)
    migrate(db)
    records=[]
    for row in db.execute("""SELECT id,action,session,report_sha256,agreement,meeting_ref,created_at,
        result_json FROM cycle_decision_records WHERE anchor_module_id=? AND anchor_student_id=?
        ORDER BY id DESC""",(mid,sid)):
        item=dict(row)
        item['result']=json.loads(item.pop('result_json'))
        item['current_snapshot']=item['report_sha256']==snapshot['sha256']
        records.append(item)
    return {**snapshot,'records':records}


def record(db,mid,sid,raw):
    if not isinstance(raw,dict) or raw.get('teacher_confirmed') is not True:
        raise ValueError('Confirme el contraste del expediente y el acuerdo del equipo docente.')
    session=raw.get('session')
    current=report(db,mid,sid,session)
    if raw.get('report_sha256')!=current['sha256']:
        raise ValueError('El expediente ha cambiado. Vuelva a consultarlo.')
    facts=raw.get('facts')
    if not isinstance(facts,dict):
        raise ValueError('Introduzca los datos del expediente contrastados.')
    facts={**facts,'cycle':current['cycle'],'academic_year':current['academic_year'],
           'session':session,'modality':'presencial_ordinaria'}
    if facts.get('action')=='promotion' and current['course']!=1:
        raise ValueError('La comprobación de promoción corresponde a primero.')
    if facts.get('action')=='graduation' and current['course']!=2:
        raise ValueError('La propuesta de titulación corresponde al cierre de segundo.')
    if facts.get('action')=='feoe':
        facts['course']=current['course']
    result=rules.evaluate(facts)
    agreement=cs.clean_text(raw.get('agreement',''),8000)
    meeting=cs.clean_text(raw.get('meeting_ref',''),500)
    if not agreement or not meeting:
        raise ValueError('Indique el acuerdo o actuación de revisión y su referencia documental.')
    snap={k:v for k,v in current.items() if k!='records'}
    cur=db.execute("""INSERT INTO cycle_decision_records(anchor_module_id,anchor_student_id,
        action,session,report_sha256,input_json,result_json,snapshot_json,agreement,meeting_ref,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(mid,sid,facts['action'],session,current['sha256'],
        json.dumps(facts,ensure_ascii=False),json.dumps(result,ensure_ascii=False),
        json.dumps(snap,ensure_ascii=False),agreement,meeting,data.now()))
    data.log(db,'cycle_decision_recorded','module',mid,{'record_id':cur.lastrowid,'action':facts['action']})
    return {'id':cur.lastrowid,'result':result}
