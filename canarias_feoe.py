"""Registro local FEOE: planes, asistencia y valoración cualitativa.
No autoriza estancias, no expide anexos oficiales ni modifica calificaciones.
"""
import datetime
import json
from decimal import Decimal, InvalidOperation
import common_scopes as cs
import canarias_cycle_record as cycle
import database as data

SOURCES=['https://www.gobiernodecanarias.org/boc/2024/230/3794.html',
         'https://www.gobiernodecanarias.org/boc/2025/118/2219.html']


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_companies(
       id INTEGER PRIMARY KEY,name TEXT NOT NULL,contact TEXT NOT NULL,
       workplace TEXT NOT NULL,created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_stays(
       id INTEGER PRIMARY KEY,module_id INTEGER NOT NULL REFERENCES modules(id),
       student_id INTEGER NOT NULL REFERENCES students(id),
       company_id INTEGER NOT NULL REFERENCES feoe_companies(id),
       center_tutor TEXT NOT NULL,company_tutor TEXT NOT NULL,
       regime TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,
       planned_hours TEXT NOT NULL,schedule TEXT NOT NULL,
       documents_json TEXT NOT NULL,created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_targets(
       id INTEGER PRIMARY KEY,stay_id INTEGER NOT NULL REFERENCES feoe_stays(id),
       module_id INTEGER NOT NULL REFERENCES modules(id),student_id INTEGER NOT NULL REFERENCES students(id),
       outcome_id INTEGER NOT NULL REFERENCES outcomes(id),
       snapshot_json TEXT NOT NULL,location TEXT NOT NULL,activities TEXT NOT NULL,
       UNIQUE(stay_id,outcome_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_plan_confirmations(
       stay_id INTEGER PRIMARY KEY REFERENCES feoe_stays(id),reference TEXT NOT NULL,
       confirmed_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_attendance(
       id INTEGER PRIMARY KEY,stay_id INTEGER NOT NULL REFERENCES feoe_stays(id),
       day TEXT NOT NULL,hours TEXT NOT NULL,status TEXT NOT NULL,
       notes TEXT NOT NULL,created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_valuations(
       id INTEGER PRIMARY KEY,target_id INTEGER NOT NULL REFERENCES feoe_targets(id),
       status TEXT NOT NULL,observations TEXT NOT NULL,report_ref TEXT NOT NULL,
       created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS feoe_teacher_reviews(
       id INTEGER PRIMARY KEY,valuation_id INTEGER NOT NULL REFERENCES feoe_valuations(id),
       notes TEXT NOT NULL,created_at TEXT NOT NULL)""")


def required(raw,key,limit=500):
    v=cs.clean_text(raw.get(key,''),limit)
    if not v:
        raise ValueError('Complete el campo '+key+'.')
    return v


def row(db,sql,args):
    r=db.execute(sql,args).fetchone()
    if not r:
        raise ValueError('Registro no encontrado.')
    return dict(r)


def date(raw):
    if not isinstance(raw,str):
        raise ValueError('Fecha inválida.')
    try:
        if datetime.date.fromisoformat(raw).isoformat()==raw:
            return raw
    except ValueError:
        pass
    raise ValueError('Fecha inválida.')


def hours(raw,maximum,allow_zero=False):
    try:
        n=Decimal(str(raw))
    except (InvalidOperation,ValueError):
        raise ValueError('Horas inválidas.') from None
    if not n.is_finite() or n<0 or n>maximum or (not allow_zero and n==0) or n.as_tuple().exponent < -2:
        raise ValueError('Horas inválidas.')
    return str(n)


def company(db,raw):
    migrate(db)
    cur=db.execute('INSERT INTO feoe_companies(name,contact,workplace,created_at) VALUES(?,?,?,?)',
        (required(raw,'name'),cs.clean_text(raw.get('contact',''),500),
         required(raw,'workplace'),data.now()))
    data.log(db,'feoe_company_created','company',cur.lastrowid,{})
    return cur.lastrowid


def stay(db,raw):
    migrate(db)
    mid,sid,cid=raw['module_id'],raw['student_id'],raw['company_id']
    m,course=cycle.context(db,mid)
    cycle.student(db,mid,sid)
    row(db,'SELECT id FROM feoe_companies WHERE id=?',(cid,))
    start,end=date(raw.get('start_date')),date(raw.get('end_date'))
    if end<start:
        raise ValueError('Fechas incoherentes.')
    regime=raw.get('regime')
    if regime not in ('general','intensivo'):
        raise ValueError('Seleccione régimen.')
    docs={}
    for k in ('convenio','plan','prl','anexo_v','edad','incorporacion'):
        docs[k]=cs.clean_text(raw.get(k,''),500)
    cur=db.execute("""INSERT INTO feoe_stays(module_id,student_id,company_id,center_tutor,
       company_tutor,regime,start_date,end_date,planned_hours,schedule,documents_json,created_at)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(mid,sid,cid,required(raw,'center_tutor'),
       required(raw,'company_tutor'),regime,start,end,hours(raw.get('planned_hours'),2000),
       required(raw,'schedule',4000),json.dumps(docs,ensure_ascii=False),data.now()))
    data.log(db,'feoe_stay_created','module',mid,{'stay_id':cur.lastrowid})
    return cur.lastrowid


def stay_row(db,stay_id):
    migrate(db)
    return row(db,'SELECT * FROM feoe_stays WHERE id=?',(stay_id,))


def curriculum(db,stay_id):
    s=stay_row(db,stay_id)
    anchor,course=cycle.context(db,s['module_id'])
    st=cycle.student(db,s['module_id'],s['student_id'])
    out=[]
    for m in db.execute("""SELECT * FROM modules WHERE cycle=? AND territory=?
        AND academic_year=? AND group_name=? ORDER BY id""",
        (anchor['cycle'],anchor['territory'],anchor['academic_year'],anchor['group_name'])):
        ref=cycle.refs.read(db,m['id'])
        other=cycle.identity(db,m['id'],st)
        if not ref or ref['course']!=course or not other or cs.profile(m['name'],m['cycle'],m['territory']):
            continue
        for ra in db.execute('SELECT id,code,description FROM outcomes WHERE module_id=? ORDER BY id',(m['id'],)):
            item=dict(ra)
            item.update(module_id=m['id'],module_name=m['name'],student_id=other['id'])
            item['criteria']=data.dicts(db.execute('SELECT id,code,description FROM criteria WHERE outcome_id=? ORDER BY id',(ra['id'],)))
            out.append(item)
    return out


def add_target(db,raw):
    s=stay_row(db,raw['stay_id'])
    if db.execute('SELECT 1 FROM feoe_plan_confirmations WHERE stay_id=?',(s['id'],)).fetchone():
        raise ValueError('Plan confirmado; las modificaciones requieren una revisión documental externa.')
    target=next((v for v in curriculum(db,s['id']) if v['id']==raw.get('outcome_id')),None)
    if not target:
        raise ValueError('RA ajeno a la estancia o identidad no contrastada.')
    location=raw.get('location')
    if location not in ('empresa','compartido','centro'):
        raise ValueError('Seleccione lugar de desarrollo.')
    ids=raw.get('criterion_ids',[])
    if not isinstance(ids,list) or any(type(v) is not int for v in ids) or len(set(ids))!=len(ids):
        raise ValueError('Criterios incorrectos.')
    if not set(ids)<={x['id'] for x in target['criteria']}:
        raise ValueError('Criterios ajenos al RA.')
    snapshot={**target,'selected_criterion_ids':ids}
    cur=db.execute("""INSERT INTO feoe_targets(stay_id,module_id,student_id,outcome_id,snapshot_json,location,activities)
        VALUES(?,?,?,?,?,?,?)""",(s['id'],target['module_id'],target['student_id'],target['id'],
        json.dumps(snapshot,ensure_ascii=False),location,required(raw,'activities',8000)))
    data.log(db,'feoe_target_added','module',target['module_id'],{'target_id':cur.lastrowid})
    return cur.lastrowid


def confirm_plan(db,raw):
    s=stay_row(db,raw['stay_id'])
    if raw.get('teacher_confirmed') is not True:
        raise ValueError('Confirme el contraste documental.')
    if not all(json.loads(s['documents_json']).values()):
        raise ValueError('Faltan referencias de convenio, plan, PRL, anexo V, edad o incorporación. Contraste su aplicabilidad.')
    targets=data.dicts(db.execute('SELECT * FROM feoe_targets WHERE stay_id=?',(s['id'],)))
    if not any(t['location']!='centro' for t in targets):
        raise ValueError('El plan necesita al menos un RA en empresa.')
    current={x['id']:x for x in curriculum(db,s['id'])}
    for t in targets:
        snap=json.loads(t['snapshot_json'])
        snap.pop('selected_criterion_ids')
        if current.get(t['outcome_id'])!=snap:
            raise ValueError('El currículo ha cambiado; revise el plan antes de confirmarlo.')
    db.execute('INSERT INTO feoe_plan_confirmations VALUES(?,?,?)',
               (s['id'],required(raw,'reference'),data.now()))
    data.log(db,'feoe_plan_confirmed','module',s['module_id'],{'stay_id':s['id']})
    return s['id']


def confirmed(db,sid):
    if not db.execute('SELECT 1 FROM feoe_plan_confirmations WHERE stay_id=?',(sid,)).fetchone():
        raise ValueError('Confirme el registro documental del plan antes de registrar seguimiento.')


def attendance(db,raw):
    s=stay_row(db,raw['stay_id'])
    confirmed(db,s['id'])
    day=date(raw.get('day'))
    if not s['start_date']<=day<=s['end_date']:
        raise ValueError('Fecha fuera de la estancia.')
    status=raw.get('status')
    h=hours(raw.get('hours'),24,True)
    if status not in ('asistencia','ausencia_justificada','ausencia_no_justificada','parcial') or (
        status.startswith('ausencia') and Decimal(h)!=0) or (
        status in ('asistencia','parcial') and Decimal(h)==0):
        raise ValueError('Estado y horas de asistencia incoherentes.')
    cur=db.execute('INSERT INTO feoe_attendance(stay_id,day,hours,status,notes,created_at) VALUES(?,?,?,?,?,?)',
        (s['id'],day,h,status,cs.clean_text(raw.get('notes',''),4000),data.now()))
    return cur.lastrowid


def valuation(db,raw):
    migrate(db)
    t=row(db,'SELECT * FROM feoe_targets WHERE id=?',(raw['target_id'],))
    confirmed(db,t['stay_id'])
    if t['location']=='centro':
        raise ValueError('El RA es exclusivo del centro.')
    if raw.get('teacher_confirmed') is not True or raw.get('status') not in ('superado','no_superado'):
        raise ValueError('Transcriba y confirme la valoración cualitativa del tutor de empresa.')
    cur=db.execute('INSERT INTO feoe_valuations(target_id,status,observations,report_ref,created_at) VALUES(?,?,?,?,?)',
                   (t['id'],raw['status'],required(raw,'observations',4000),required(raw,'report_ref'),data.now()))
    return cur.lastrowid


def teacher_review(db,raw):
    migrate(db)
    v=row(db,'SELECT * FROM feoe_valuations WHERE id=?',(raw['valuation_id'],))
    latest=db.execute('SELECT MAX(id) FROM feoe_valuations WHERE target_id=?',(v['target_id'],)).fetchone()[0]
    if v['id']!=latest or raw.get('teacher_confirmed') is not True:
        raise ValueError('Revise la última valoración y confirme expresamente.')
    cur=db.execute('INSERT INTO feoe_teacher_reviews(valuation_id,notes,created_at) VALUES(?,?,?)',
        (v['id'],required(raw,'notes',4000),data.now()))
    return cur.lastrowid


def load(db,stay_id=None):
    migrate(db)
    result={'companies':data.dicts(db.execute('SELECT * FROM feoe_companies ORDER BY name,id')),
            'stays':data.dicts(db.execute("""SELECT s.id,s.module_id,s.student_id,s.start_date,s.end_date,
                st.name AS student_name,c.name AS company_name FROM feoe_stays s
                JOIN students st ON st.id=s.student_id JOIN feoe_companies c ON c.id=s.company_id ORDER BY s.id DESC""")),
            'sources':SOURCES}
    if stay_id is None:
        return result
    s=stay_row(db,stay_id)
    s['documents']=json.loads(s.pop('documents_json'))
    result['stay']=s
    result['curriculum']=curriculum(db,stay_id)
    result['confirmation']=db.execute('SELECT 1 FROM feoe_plan_confirmations WHERE stay_id=?',(stay_id,)).fetchone() is not None
    targets=data.dicts(db.execute('SELECT * FROM feoe_targets WHERE stay_id=? ORDER BY id',(stay_id,)))
    for t in targets:
        t['snapshot']=json.loads(t.pop('snapshot_json'))
        t['valuations']=data.dicts(db.execute('SELECT * FROM feoe_valuations WHERE target_id=? ORDER BY id DESC',(t['id'],)))
        for v in t['valuations']:
            v['reviews']=data.dicts(db.execute('SELECT * FROM feoe_teacher_reviews WHERE valuation_id=? ORDER BY id DESC',(v['id'],)))
    result['targets']=targets
    result['attendance_history']=data.dicts(db.execute('SELECT * FROM feoe_attendance WHERE stay_id=? ORDER BY id DESC',(stay_id,)))
    latest={}
    for a in result['attendance_history']:
        latest.setdefault(a['day'],a)
    result['attendance']=list(latest.values())
    result['actual_hours']=str(sum((Decimal(a['hours']) for a in latest.values()),Decimal(0)))
    result['notice']='Registro interno: no autoriza incorporación ni modifica las notas de módulos.'
    return result
