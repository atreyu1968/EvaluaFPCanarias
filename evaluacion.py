"""Evaluación continua por unidades/RA/CE, instrumentos externos y evidencias.

No publica una nota final cuando faltan evidencias o la programación presenta
ponderaciones incompatibles. Las calificaciones requieren validación del docente.
"""
from __future__ import annotations

import csv
import json
import hashlib
import io
import math
from collections import defaultdict

import database as data

TYPES={'examen','practica','problemas','portfolio','proyecto','observacion','empresa','externo'}


def migrate(d):
    d.executescript('''
    CREATE TABLE IF NOT EXISTS evaluation_units(
      id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
      code TEXT NOT NULL, title TEXT NOT NULL, term INTEGER NOT NULL CHECK(term BETWEEN 1 AND 3),
      UNIQUE(module_id,code));
    CREATE TABLE IF NOT EXISTS evaluation_unit_criteria(
      unit_id INTEGER NOT NULL REFERENCES evaluation_units(id),
      criterion_id INTEGER NOT NULL REFERENCES criteria(id),
      PRIMARY KEY(unit_id,criterion_id));
    CREATE TABLE IF NOT EXISTS evaluation_settings(
      module_id INTEGER PRIMARY KEY REFERENCES modules(id),
      enterprise_mode TEXT NOT NULL DEFAULT 'unresolved',
      enterprise_weight REAL NOT NULL DEFAULT 25,
      criterion_pass_mark REAL NOT NULL DEFAULT 5,
      ra_min_criteria_pct REAL NOT NULL DEFAULT 50,
      validated INTEGER NOT NULL DEFAULT 0,
      teacher_note TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS evaluation_instruments(
      id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
      unit_id INTEGER REFERENCES evaluation_units(id),
      term INTEGER NOT NULL CHECK(term BETWEEN 1 AND 3),
      title TEXT NOT NULL, kind TEXT NOT NULL,
      exam_id INTEGER REFERENCES exams(id), created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS evaluation_instrument_criteria(
      instrument_id INTEGER NOT NULL REFERENCES evaluation_instruments(id),
      criterion_id INTEGER NOT NULL REFERENCES criteria(id),
      weight REAL NOT NULL CHECK(weight>0 AND weight<=100),
      PRIMARY KEY(instrument_id,criterion_id));
    CREATE TABLE IF NOT EXISTS evaluation_scores(
      id INTEGER PRIMARY KEY, instrument_id INTEGER NOT NULL REFERENCES evaluation_instruments(id),
      criterion_id INTEGER NOT NULL REFERENCES criteria(id),
      student_id INTEGER NOT NULL REFERENCES students(id),
      score REAL NOT NULL CHECK(score>=0 AND score<=10),
      comment TEXT NOT NULL DEFAULT '', origin TEXT NOT NULL DEFAULT 'manual',
      source_ref TEXT NOT NULL DEFAULT '', teacher_validated INTEGER NOT NULL DEFAULT 1,
      changed_at TEXT NOT NULL, UNIQUE(instrument_id,criterion_id,student_id));
    CREATE INDEX IF NOT EXISTS ix_evaluation_scores ON evaluation_scores(student_id,instrument_id);
    CREATE TABLE IF NOT EXISTS evaluation_closures(
      id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES modules(id),
      student_id INTEGER NOT NULL REFERENCES students(id),
      score REAL NOT NULL,teacher_justification TEXT NOT NULL,
      evidence_sha256 TEXT NOT NULL, snapshot_json TEXT NOT NULL,
      validated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS ix_evaluation_closures ON evaluation_closures(module_id,student_id,validated_at);
    ''')


def _check_ce(d,module_id,criteria):
    ids=set(int(x) for x in criteria)
    if not ids:raise ValueError('Seleccione al menos un criterio de evaluación.')
    rows=d.execute('''SELECT c.id FROM criteria c JOIN outcomes o ON c.outcome_id=o.id
                      WHERE o.module_id=?''',(module_id,))
    permitted={r[0] for r in rows}
    if not ids.issubset(permitted):raise ValueError('Algún CE no pertenece al módulo seleccionado.')
    return sorted(ids)


def add_unit(d,body):
    mid=int(body['module_id']);code=str(body.get('code','')).strip().upper()
    title=str(body.get('title','')).strip();term=int(body.get('term',0))
    if not code or not title or len(code)>30 or len(title)>180 or term not in (1,2,3):
        raise ValueError('Código, nombre y trimestre (1,2,3) obligatorios.')
    ids=_check_ce(d,mid,body.get('criteria_ids',[]))
    d.execute('INSERT INTO evaluation_units(module_id,code,title,term) VALUES(?,?,?,?)',(mid,code,title,term))
    uid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
    d.executemany('INSERT INTO evaluation_unit_criteria(unit_id,criterion_id) VALUES(?,?)',[(uid,c) for c in ids])
    data.log(d,'evaluation_unit_created','evaluation_unit',uid,{'code':code,'term':term,'criteria_ids':ids})
    return uid


def add_instrument(d,body):
    mid=int(body['module_id']);term=int(body.get('term',0));title=str(body.get('title','')).strip()
    kind=str(body.get('kind','externo')).lower();unitid=int(body['unit_id']) if body.get('unit_id') else None
    eid=int(body['exam_id']) if body.get('exam_id') else None
    if not title or len(title)>180 or term not in (1,2,3) or kind not in TYPES:
        raise ValueError('Nombre, tipo de instrumento y trimestre obligatorios.')
    if not d.execute('SELECT 1 FROM modules WHERE id=?',(mid,)).fetchone():raise ValueError('Módulo no encontrado.')
    if unitid:
        r=d.execute('SELECT term FROM evaluation_units WHERE id=? AND module_id=?',(unitid,mid)).fetchone()
        if not r or r['term']!=term:raise ValueError('La unidad debe pertenecer al módulo y trimestre seleccionados.')
    if eid and not d.execute('SELECT 1 FROM exams WHERE id=? AND module_id=?',(eid,mid)).fetchone():
        raise ValueError('El examen no pertenece al módulo.')
    weights=body.get('targets') or []
    if not isinstance(weights,list) or not weights:raise ValueError('Asocie CE y porcentajes de instrumento.')
    ids=_check_ce(d,mid,[t['criterion_id'] for t in weights])
    if len(set(ids))!=len(weights):raise ValueError('Criterio repetido en el instrumento.')
    if unitid:
        assigned={r[0] for r in d.execute('SELECT criterion_id FROM evaluation_unit_criteria WHERE unit_id=?',(unitid,))}
        if not set(ids).issubset(assigned):raise ValueError('El instrumento contiene CE no incluidos en la unidad.')
    targets=[]
    for x in weights:
        weight=float(x['weight'])
        if not math.isfinite(weight) or weight<=0 or weight>100:raise ValueError('Peso de instrumento: más de 0 y hasta 100 %.')
        targets.append((int(x['criterion_id']),weight))
    d.execute('''INSERT INTO evaluation_instruments(module_id,unit_id,term,title,kind,exam_id,created_at)
                 VALUES(?,?,?,?,?,?,?)''',(mid,unitid,term,title,kind,eid,data.now()))
    instrument=d.execute('SELECT last_insert_rowid()').fetchone()[0]
    d.executemany('INSERT INTO evaluation_instrument_criteria(instrument_id,criterion_id,weight) VALUES(?,?,?)',
                  [(instrument,c,w) for c,w in targets])
    data.log(d,'evaluation_instrument_created','instrument',instrument,{'kind':kind,'targets':targets,'exam_id':eid})
    return instrument


def put_score(d,body):
    iid=int(body['instrument_id']);cid=int(body['criterion_id']);sid=int(body['student_id'])
    score=float(body['score']);comment=str(body.get('comment','')).strip()[:3000]
    if not math.isfinite(score) or not 0<=score<=10:raise ValueError('La nota debe estar entre 0 y 10.')
    r=d.execute('''SELECT i.module_id FROM evaluation_instruments i
                   JOIN evaluation_instrument_criteria ic ON ic.instrument_id=i.id AND ic.criterion_id=?
                   WHERE i.id=?''',(cid,iid)).fetchone()
    if not r:raise ValueError('El instrumento no evalúa ese criterio.')
    if not d.execute('SELECT 1 FROM students WHERE id=? AND module_id=?',(sid,r['module_id'])).fetchone():
        raise ValueError('El alumno no pertenece al módulo.')
    old=d.execute('''SELECT score,origin FROM evaluation_scores WHERE instrument_id=? AND criterion_id=? AND student_id=?''',
                  (iid,cid,sid)).fetchone()
    d.execute('''INSERT INTO evaluation_scores(instrument_id,criterion_id,student_id,score,comment,origin,teacher_validated,changed_at)
                 VALUES(?,?,?,?,?,'manual',1,?)
                 ON CONFLICT(instrument_id,criterion_id,student_id) DO UPDATE SET
                 score=excluded.score,comment=excluded.comment,origin='manual',
                 source_ref='',teacher_validated=1,changed_at=excluded.changed_at''',
              (iid,cid,sid,round(score,4),comment,data.now()))
    data.log(d,'evaluation_score_validated','student',sid,
             {'instrument_id':iid,'criterion_id':cid,'new_score':score,'previous_score':old['score'] if old else None})


def import_csv(d,instrument_id,raw):
    instrument_id=int(instrument_id)
    instr=d.execute('SELECT * FROM evaluation_instruments WHERE id=?',(instrument_id,)).fetchone()
    if not instr:raise ValueError('Instrumento no encontrado.')
    if len(raw)>4_000_000:raise ValueError('El CSV supera el límite de 4 MB.')
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:raise ValueError('CSV: guarde el documento en UTF-8.') from exc
    if not text.strip():raise ValueError('CSV vacío.')
    try:dialect=csv.Sniffer().sniff(text[:4096],delimiters=';,\t')
    except csv.Error:
        class Fallback(csv.excel):
            delimiter=';' if ';' in text.splitlines()[0] else ','
        dialect=Fallback
    reader=csv.DictReader(io.StringIO(text),dialect=dialect)
    rows=list(reader)
    if not rows or len(rows)>10000:raise ValueError('CSV vacío o demasiado extenso.')
    keys={'codigo_alumno','criterio','nota'}
    if not keys.issubset({(s or '').strip().lower() for s in reader.fieldnames or []}):
        raise ValueError('CSV: encabezados obligatorios codigo_alumno;criterio;nota;comentario')
    mapping=defaultdict(set)
    for r in d.execute('SELECT id,code FROM students WHERE module_id=?',(instr['module_id'],)):
        mapping[r['code'].strip().casefold()].add(r['id'])
    criteria=defaultdict(set)
    valid={r[0] for r in d.execute('SELECT criterion_id FROM evaluation_instrument_criteria WHERE instrument_id=?',(instrument_id,))}
    for r in d.execute('''SELECT c.id,c.code,o.code AS ra_code FROM criteria c JOIN outcomes o
                        ON o.id=c.outcome_id WHERE o.module_id=?''',(instr['module_id'],)):
        if r['id'] not in valid:continue
        code=r['code'].strip().casefold()
        ra=r['ra_code'].strip().casefold()
        criteria[code].add(r['id'])
        criteria[ra+'·'+code].add(r['id'])
        criteria[ra+'/'+code].add(r['id'])
    prepared=[];seen=set()
    for n,row in enumerate(rows,2):
        row={(k or '').strip().lower():str(v or '').strip() for k,v in row.items()}
        students=mapping.get(row.get('codigo_alumno','').casefold(),set())
        candidates=criteria.get(row.get('criterio','').casefold(),set())
        if len(students)>1 or len(candidates)>1:
            raise ValueError(f'Fila {n}: código ambiguo. Use un código de alumno inequívoco y RA/CE, por ejemplo RA1/a.')
        if not students or not candidates:raise ValueError(f'Fila {n}: alumno o CE inexistente/no vinculado.')
        sid=next(iter(students));cid=next(iter(candidates))
        try:score=float(row['nota'].replace(',','.'))
        except Exception:raise ValueError(f'Fila {n}: nota no numérica.')
        if not math.isfinite(score) or not 0<=score<=10:raise ValueError(f'Fila {n}: nota fuera de 0-10.')
        if (sid,cid) in seen:raise ValueError(f'Fila {n}: registro duplicado.')
        seen.add((sid,cid));prepared.append((sid,cid,score,row.get('comentario','')[:3000]))
    for sid,cid,score,comment in prepared:
        put_score(d,{'instrument_id':instrument_id,'criterion_id':cid,'student_id':sid,'score':score,'comment':comment})
        d.execute("UPDATE evaluation_scores SET origin='csv' WHERE instrument_id=? AND student_id=? AND criterion_id=?",
                  (instrument_id,sid,cid))
    data.log(d,'evaluation_csv_imported','instrument',instrument_id,{'rows':len(prepared)})
    return len(prepared)


def sync_exam(d,instrument_id,replace=False):
    instrument=d.execute('SELECT * FROM evaluation_instruments WHERE id=?',(instrument_id,)).fetchone()
    if not instrument or not instrument['exam_id']:raise ValueError('El instrumento no está vinculado a un examen.')
    allowed={r['criterion_id'] for r in d.execute(
        'SELECT criterion_id FROM evaluation_instrument_criteria WHERE instrument_id=?',(instrument_id,))}
    records=d.execute('''SELECT s.student_id,s.id AS submission_id,qc.criterion_id,
                        SUM(c.teacher_score*qc.weight_pct/100.0) AS scored,
                        SUM(q.points*qc.weight_pct/100.0) AS maximum
                        FROM submissions s JOIN corrections c ON c.run_id=s.current_run_id
                        JOIN exam_questions q ON q.id=c.question_id
                        JOIN exam_question_criteria qc ON qc.question_id=q.id
                        WHERE s.exam_id=? AND s.status='validated' AND c.status='validated'
                        GROUP BY s.student_id,s.id,qc.criterion_id''',(instrument['exam_id'],)).fetchall()
    count=0;skipped=0
    for r in records:
        if r['criterion_id'] not in allowed or not r['maximum']:continue
        old=d.execute('''SELECT id FROM evaluation_scores WHERE instrument_id=? AND student_id=? AND criterion_id=?''',
                      (instrument_id,r['student_id'],r['criterion_id'])).fetchone()
        if old and not replace:skipped+=1;continue
        score=round(10*float(r['scored'])/float(r['maximum']),4)
        put_score(d,{'instrument_id':instrument_id,'criterion_id':r['criterion_id'],
                     'student_id':r['student_id'],'score':score,
                     'comment':f'Examen validado; entrega #{r["submission_id"]}'})
        d.execute('''UPDATE evaluation_scores SET origin='exam',source_ref=? WHERE instrument_id=? AND student_id=? AND criterion_id=?''',
                  (str(r['submission_id']),instrument_id,r['student_id'],r['criterion_id']))
        count+=1
    data.log(d,'evaluation_exam_synced','instrument',instrument_id,{'added':count,'skipped':skipped})
    return {'imported':count,'skipped':skipped}


def update_settings(d,body):
    mid=int(body['module_id']);mode=str(body['enterprise_mode']).lower()
    if mode not in {'unresolved','integrated','separate'}:raise ValueError('Modo de empresa no reconocido.')
    fe=float(body.get('enterprise_weight',25));pass_mark=float(body.get('criterion_pass_mark',5))
    min_pct=float(body.get('ra_min_criteria_pct',50));confirmed=body.get('validated',False) is True
    note=str(body.get('teacher_note','')).strip()[:1000]
    if not all(math.isfinite(x) for x in (fe,pass_mark,min_pct)) or not 0<=fe<=100 or not 0<=pass_mark<=10 or not 0<=min_pct<=100:
        raise ValueError('Porcentajes y umbrales fuera de rango.')
    if confirmed and (mode=='unresolved' or not note):
        raise ValueError('Antes de validar, seleccione un tratamiento de empresa y justifíquelo.')
    d.execute('''INSERT INTO evaluation_settings(module_id,enterprise_mode,enterprise_weight,criterion_pass_mark,
                  ra_min_criteria_pct,validated,teacher_note) VALUES(?,?,?,?,?,?,?)
                  ON CONFLICT(module_id) DO UPDATE SET enterprise_mode=excluded.enterprise_mode,
                  enterprise_weight=excluded.enterprise_weight, criterion_pass_mark=excluded.criterion_pass_mark,
                  ra_min_criteria_pct=excluded.ra_min_criteria_pct,validated=excluded.validated,
                  teacher_note=excluded.teacher_note''',
              (mid,mode,fe,pass_mark,min_pct,int(confirmed),note))
    data.log(d,'evaluation_policy_changed','module',mid,{'mode':mode,'validated':confirmed,'note':note})


def summary(d,module_id,student_id=None):
    mid=int(module_id)
    if not d.execute('SELECT 1 FROM modules WHERE id=?',(mid,)).fetchone():raise ValueError('Módulo no encontrado.')
    policyrow=d.execute('SELECT * FROM evaluation_settings WHERE module_id=?',(mid,)).fetchone()
    policy=dict(policyrow) if policyrow else {'module_id':mid,'enterprise_mode':'unresolved',
            'enterprise_weight':25,'criterion_pass_mark':5,'ra_min_criteria_pct':50,'validated':0,'teacher_note':''}
    ras=data.dicts(d.execute('SELECT * FROM outcomes WHERE module_id=? ORDER BY id',(mid,)))
    ces=data.dicts(d.execute('''SELECT c.*,o.code AS ra_code,o.id AS ra_id FROM criteria c
                                JOIN outcomes o ON o.id=c.outcome_id WHERE o.module_id=? ORDER BY o.id,c.id''',(mid,)))
    units=data.dicts(d.execute('SELECT * FROM evaluation_units WHERE module_id=? ORDER BY term,code',(mid,)))
    for u in units:u['criteria_ids']=[r['criterion_id'] for r in d.execute('SELECT criterion_id FROM evaluation_unit_criteria WHERE unit_id=?',(u['id'],))]
    instrs=data.dicts(d.execute('''SELECT i.*,u.code AS unit_code FROM evaluation_instruments i
                  LEFT JOIN evaluation_units u ON u.id=i.unit_id WHERE i.module_id=? ORDER BY term,id''',(mid,)))
    by_inst={}
    for i in instrs:
        i['targets']=data.dicts(d.execute('SELECT criterion_id,weight FROM evaluation_instrument_criteria WHERE instrument_id=?',(i['id'],)))
        by_inst[i['id']]=i
    students=data.dicts(d.execute('SELECT id,code,name FROM students WHERE module_id=? ORDER BY name',(mid,)))
    scores=data.dicts(d.execute('''SELECT s.* FROM evaluation_scores s JOIN evaluation_instruments i
                                  ON i.id=s.instrument_id WHERE i.module_id=?''',(mid,)))
    check_warnings=[]
    if not ras:check_warnings.append('No hay resultados de aprendizaje configurados.')
    def valid_weight(value):
        return isinstance(value,(int,float)) and math.isfinite(value) and 0<=value<=100
    if any(not valid_weight(x['weight']) for x in ras+ces):
        check_warnings.append('Existen ponderaciones RA/CE ausentes o fuera de 0–100 %.')
    ra_sum=sum(float(r['weight']) for r in ras if r['weight'] is not None)
    expected_ra=100-policy['enterprise_weight'] if policy['enterprise_mode']=='separate' else 100
    if any(r['weight'] is None for r in ras) or abs(ra_sum-expected_ra)>0.01:
        check_warnings.append(f'Ponderaciones de RA incompletas/no suman {expected_ra:g} % (actual: {ra_sum:g} %).')
    for ra in ras:
        setce=[c for c in ces if c['ra_id']==ra['id']]
        ws=sum(float(c['weight']) for c in setce if c['weight'] is not None)
        if not setce or any(c['weight'] is None for c in setce) or abs(ws-100)>0.01:
            check_warnings.append(f'{ra["code"]}: pesos de CE incompletos/no suman 100 % ({ws:g} %).')
    if not policy['validated'] or policy['enterprise_mode']=='unresolved':
        check_warnings.append('La política de ponderación de empresa no está validada por el docente.')
    if policy['enterprise_mode']=='separate' and abs(ra_sum+policy['enterprise_weight']-100)>0.01:
        check_warnings.append(f'Conflicto: RA {ra_sum:g} % + empresa {policy["enterprise_weight"]:g} % = {ra_sum+policy["enterprise_weight"]:g} %.')
    by_ce_instr=defaultdict(list)
    for i in instrs:
        for t in i['targets']:by_ce_instr[t['criterion_id']].append((i,t['weight']))
    for ce in ces:
        total=sum(w for i,w in by_ce_instr[ce['id']] if policy['enterprise_mode']!='separate' or i['kind']!='empresa')
        if abs(total-100)>0.01:check_warnings.append(f'{ce["ra_code"]}·{ce["code"]}: los instrumentos suman {total:g} % (deben sumar 100 %).')
    scores_by= {(s['student_id'],s['instrument_id'],s['criterion_id']):s for s in scores if s['teacher_validated']}

    # Solo consultar FEOE cuando existe el esquema (compatibilidad con bases
    # antiguas y pruebas mínimas). No transformar superado/no superado en nota.
    feoe_by_student=defaultdict(list)
    if d.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='feoe_targets'").fetchone():
        import canarias_feoe
        for evidence in canarias_feoe.module_evidence(d,mid):
            feoe_by_student[evidence['student_id']].append(evidence)

    def student_result(student):
        sid=student['id'];ce_scores={};ce_details=[]
        for ce in ces:
            uses=[(i,w) for i,w in by_ce_instr[ce['id']] if policy['enterprise_mode']!='separate' or i['kind']!='empresa']
            recorded=[(i,w,scores_by.get((sid,i['id'],ce['id']))) for i,w in uses]
            achieved=sum((w*s['score'] for i,w,s in recorded if s))
            covered=sum(w for i,w,s in recorded if s)
            valid=abs(sum(w for i,w in uses)-100)<.01 and abs(covered-100)<.01
            grade=round(achieved/covered,2) if covered else None
            ce_scores[ce['id']]=grade
            ce_details.append({'criterion_id':ce['id'],'code':ce['code'],'ra_code':ce['ra_code'],
                               'score':grade,'complete':valid,'weight_covered':round(covered,2),
                               'passed':valid and grade is not None and achieved/covered>=policy['criterion_pass_mark']})
        ra_details=[];ra_values={}
        for ra in ras:
            subs=[(ce, next(x for x in ce_details if x['criterion_id']==ce['id'])) for ce in ces if ce['ra_id']==ra['id']]
            if not subs:grade=None;complete=False;passed=False;coverage=0
            else:
                denom=sum(ce['weight'] or 0 for ce,r in subs)
                valid=all(x['complete'] for ce,x in subs) and abs(denom-100)<.01
                weight_present=sum((ce['weight'] or 0) for ce,x in subs if x['score'] is not None)
                grade=round(sum((ce['weight'] or 0)*x['score'] for ce,x in subs if x['score'] is not None)/weight_present,2) if weight_present else None
                coverage=round(100*sum(x['passed'] for ce,x in subs)/len(subs),2)
                complete=valid
                passed=complete and grade is not None and grade>=5 and coverage>=policy['ra_min_criteria_pct']
            ra_details.append({'id':ra['id'],'code':ra['code'],'weight':ra['weight'],'score':grade,
                               'complete':complete,'criteria_passed_pct':coverage,'passed':passed})
            ra_values[ra['id']]=grade
        terms=[]
        for term in (1,2,3):
            selected_inst=[i for i in instrs if i['term']==term]
            present=[(i,t,scores_by.get((sid,i['id'],t['criterion_id']))) for i in selected_inst for t in i['targets']]
            scorevals=[(s['score'],t['weight']) for i,t,s in present if s]
            term_grade=round(sum(g*w for g,w in scorevals)/sum(w for g,w in scorevals),2) if scorevals else None
            terms.append({'term':term,'score':term_grade,'completed':len([1 for i,t,s in present if s]),'expected':len(present),
                          'provisional':True})
        fe_planned=[(i,t) for i in instrs if i['kind']=='empresa' for t in i['targets']]
        fe_records=[(s['score'],t['weight']) for i,t in fe_planned
                    if (s:=scores_by.get((sid,i['id'],t['criterion_id']))) is not None]
        fe_complete=bool(fe_planned) and len(fe_records)==len(fe_planned)
        fe_score=round(sum(g*w for g,w in fe_records)/sum(w for g,w in fe_records),2) if fe_records else None
        company_evidence=feoe_by_student[sid]
        company_pending=any(not e['current_curriculum'] or not e['valuation'] or not e['teacher_review']
                            for e in company_evidence)
        complete=not check_warnings and all(r['complete'] for r in ra_details) and not company_pending
        if policy['enterprise_mode']=='separate' and not fe_complete:complete=False
        final=None
        if complete:
            final=round(sum((ra['weight'] or 0)*ra_values[ra['id']] for ra in ras)/100
                        +(policy['enterprise_weight']*fe_score/100 if policy['enterprise_mode']=='separate' else 0),2)
        closure_row=d.execute('SELECT id,score,teacher_justification,evidence_sha256,validated_at FROM evaluation_closures WHERE module_id=? AND student_id=? ORDER BY id DESC LIMIT 1',(mid,sid)).fetchone()
        closure=dict(closure_row) if closure_row else None
        current_digest=_student_digest(policy,ras,ces,instrs,[s for s in scores if s['student_id']==sid])
        if company_evidence:
            # Incluye identidad, versión curricular, valoración y revisión.
            # Cualquier nueva valoración/revisión obliga a contrastar el cierre.
            current_digest=hashlib.sha256(json.dumps({'base':current_digest,
                'feoe':sorted(company_evidence,key=lambda e:e['id'])},
                sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')).hexdigest()
        if closure:
            closure['current']=bool(complete and closure['score']==final and closure['evidence_sha256']==current_digest)
        return {'student_id':sid,'code':student['code'],'name':student['name'],'criteria':ce_details,
                'outcomes':ra_details,'terms':terms,'enterprise_score':fe_score,
                'final_score':final,'status':'calculable (pendiente de cierre docente)' if complete else 'incompleta',
                'warnings':([] if complete else ['Faltan ponderaciones, instrumentos o evidencias validadas.'])+(['Hay valoraciones FEOE pendientes de revisión o de cotejo curricular.'] if company_pending else []),
                'closure':closure,'evidence_sha256':current_digest}
    if student_id:
        students=[s for s in students if s['id']==int(student_id)]
        if not students:raise ValueError('El alumno no pertenece a este módulo.')
    return {'module_id':mid,'settings':policy,'warnings':check_warnings,'outcomes':ras,'criteria':ces,
            'units':units,'instruments':instrs,'students':[student_result(x) for x in students],
            'raw_students':students,'scores':scores}


def _student_digest(policy,ras,ces,instruments,scores):
    """Firma de evidencias para detectar cierres que hayan quedado obsoletos."""
    payload={'policy':policy,'outcomes':ras,'criteria':ces,'instruments':instruments,
             'scores':sorted(scores,key=lambda r:(r['instrument_id'],r['criterion_id'],r['id']))}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')).hexdigest()


def close_student(d,module_id,student_id,justification):
    reason=str(justification or '').strip()
    if len(reason)<10 or len(reason)>4000:
        raise ValueError('La justificación docente del cierre debe tener entre 10 y 4000 caracteres.')
    result=summary(d,module_id,student_id)
    st=result['students'][0]
    if st['final_score'] is None:
        raise ValueError('No puede cerrarse la nota: faltan evidencias, pesos o validación de la política.')
    snap={'criteria':st['criteria'],'outcomes':st['outcomes'],'terms':st['terms'],
          'grade':st['final_score'],'enterprise_score':st['enterprise_score'],
          'policy':result['settings']}
    d.execute('''INSERT INTO evaluation_closures(module_id,student_id,score,teacher_justification,
           evidence_sha256,snapshot_json,validated_at) VALUES(?,?,?,?,?,?,?)''',
        (int(module_id),int(student_id),st['final_score'],reason,st['evidence_sha256'],
         json.dumps(snap,ensure_ascii=False),data.now()))
    eid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
    data.log(d,'evaluation_final_closed','student',int(student_id),
             {'module_id':int(module_id),'grade':st['final_score'],'closure_id':eid,'justification':reason})
    return {'id':eid,'score':st['final_score']}
