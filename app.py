"""EvalúaFP: aplicación de escritorio Windows, interfaz HTML y SQLite local."""
from __future__ import annotations
import email
import email.policy
import hashlib
import html
import io
import math
import json
import mimetypes
import os
import re
import shutil
import secrets
import sqlite3
import sys
import threading
import urllib.parse
import webbrowser
import zipfile
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import database as data
import ia
import logic
import materiales
import storage_config
import evaluacion
import weight_defaults
import exportaciones
import manual_alignment
import curriculum_official
import program_builder
import territorial_profiles as territories
import canarias_ag as ag
import schedule_engine
import program_importer
import program_assistant

APP_VERSION = "1.2.10-AG-CN-beta.2"
TOKEN = secrets.token_urlsafe(32)
WEB = (Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'web')

def read_json(handler, max_bytes=3_000_000):
    size = int(handler.headers.get('Content-Length','0'))
    if size <= 0 or size > max_bytes:
        raise ValueError('Tamaño de solicitud JSON no permitido.')
    if 'application/json' not in handler.headers.get('Content-Type',''):
        raise ValueError('Se requiere Content-Type: application/json')
    return json.loads(handler.rfile.read(size))


def multipart(handler):
    size=int(handler.headers.get('Content-Length','0'))
    if size <= 0 or size > logic.MAX_BATCH+4_000_000:
        raise ValueError('Carga vacía o superior al límite de 240 MB.')
    ct=handler.headers.get('Content-Type','')
    if not ct.startswith('multipart/form-data'):
        raise ValueError('Se requiere una carga multipart/form-data.')
    raw=handler.rfile.read(size)
    # Navegadores envían nombres UTF-8 en Content-Disposition (tildes, guiones, etc.).
    # La política MIME antigua ('compat32') devuelve email.header.Header y rompe re.search.
    mime=email.message_from_bytes(
        f'MIME-Version: 1.0\r\nContent-Type: {ct}\r\n\r\n'.encode()+raw,
        policy=email.policy.default.clone(utf8=True))
    if not mime.is_multipart():
        raise ValueError('Formulario multipart no válido.')
    fields={}; files=[]
    for part in mime.get_payload():
        # get_param descodifica y maneja encabezados Unicode y parámetros RFC 2231.
        name=part.get_param('name', header='content-disposition')
        if not isinstance(name, str) or not name: continue
        filename=part.get_filename()
        if filename is not None:
            files.append((name,Path(filename.replace('\\','/')).name, part.get_payload(decode=True) or b''))
        else:
            fields[name]=(part.get_payload(decode=True) or b'').decode('utf-8','replace')
    return fields, files


def must_row(d,query,args=()):
    row=d.execute(query,args).fetchone()
    if row is None: raise ValueError('No se ha encontrado el registro solicitado.')
    return row


def parse_weight(raw):
    if raw is None or str(raw).strip()=='':return None
    w=float(raw)
    if not (0<=w<=100): raise ValueError('Las ponderaciones deben situarse entre 0 y 100.')
    return w


def fields_safe(d, module_id):
    module=must_row(d,'SELECT * FROM modules WHERE id=?',(module_id,))
    outcome_rows=data.dicts(d.execute('''SELECT o.*,
       COALESCE((SELECT origin FROM weight_origins WHERE kind='ra' AND record_id=o.id),
       CASE WHEN o.weight IS NULL THEN 'pending' ELSE 'existing' END) AS weight_origin
       FROM outcomes o WHERE o.module_id=? ORDER BY o.id''',(module_id,)))
    criteria=data.dicts(d.execute('''SELECT c.*,o.code AS outcome_code,o.description AS outcome_description,
           o.weight AS outcome_weight,
           COALESCE((SELECT origin FROM weight_origins WHERE kind='ce' AND record_id=c.id),
             CASE WHEN c.weight IS NULL THEN 'pending' ELSE 'existing' END) AS weight_origin
           FROM criteria c JOIN outcomes o ON o.id=c.outcome_id
           WHERE o.module_id=? ORDER BY o.id,c.id''',(module_id,)))
    students=data.dicts(d.execute('SELECT * FROM students WHERE module_id=? ORDER BY name',(module_id,)))
    programs=data.dicts(d.execute('SELECT id,filename,uploaded_at,LENGTH(extracted_text) AS text_length FROM programmings WHERE module_id=? ORDER BY id DESC',(module_id,)))
    return {'module':dict(module), 'outcomes':outcome_rows,'criteria':criteria,
            'students':students, 'programmings':programs, 'materials':data.dicts(d.execute('''SELECT id,programming_id,filename,sha256,unit_count,chunk_count,uploaded_at,active FROM materials WHERE module_id=? ORDER BY id DESC''',(module_id,)))}


def list_exams(d):
    return data.dicts(d.execute('''SELECT e.*,m.name AS module_name,m.academic_year,
       (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id=e.id) AS question_count,
       (SELECT COUNT(*) FROM submissions s WHERE s.exam_id=e.id) AS submissions_count,
       (SELECT bank_size FROM exam_batches b WHERE b.id=e.batch_id) AS bank_size
       FROM exams e JOIN modules m ON m.id=e.module_id ORDER BY e.id DESC'''))


def exam_detail(d,exam_id):
    exam=must_row(d,'SELECT * FROM exams WHERE id=?',(exam_id,))
    qs=data.dicts(d.execute('''SELECT q.*,c.code AS criterion_code, o.code AS outcome_code FROM exam_questions q
      JOIN criteria c ON c.id=q.criterion_id JOIN outcomes o ON o.id=c.outcome_id
      WHERE q.exam_id=? ORDER BY q.number''',(exam_id,)))
    for q in qs:
        q['criteria_allocations']=data.dicts(d.execute("""SELECT qc.criterion_id,qc.weight_pct,
                qc.confidence,qc.rationale,c.code AS criterion_code,o.code AS ra_code
                FROM exam_question_criteria qc JOIN criteria c ON c.id=qc.criterion_id
                JOIN outcomes o ON o.id=c.outcome_id WHERE qc.question_id=?
                ORDER BY qc.weight_pct DESC""",(q['id'],)))
        q['options']=json.loads(q.pop('options_json'))
        q['rubric']=json.loads(q.pop('rubric_json'))
        q['source_refs']=json.loads(q.pop('source_refs_json'))
    sub=data.dicts(d.execute('''SELECT s.*, st.name AS student_name,st.code AS student_code,
      (SELECT COUNT(*) FROM pages p WHERE p.submission_id=s.id) AS page_count
      FROM submissions s JOIN students st ON st.id=s.student_id WHERE s.exam_id=? ORDER BY st.name''',(exam_id,)))
    related=data.dicts(d.execute('''SELECT m.id,m.filename,m.programming_id,m.sha256 FROM materials m JOIN exam_materials em ON m.id=em.material_id WHERE em.exam_id=? ORDER BY m.id''',(exam_id,)))
    return {'exam':dict(exam),'questions':qs,'submissions':sub,'materials':related}


def sub_detail(d,sid):
    s=must_row(d,'''SELECT s.*,e.title AS exam_title,e.total_points,e.module_id,st.name AS student_name,st.code AS student_code
                 FROM submissions s JOIN exams e ON e.id=s.exam_id JOIN students st ON st.id=s.student_id WHERE s.id=?''',(sid,))
    pages=data.dicts(d.execute('''SELECT p.id,p.page_number,p.source_page,f.original_name,p.file_id FROM pages p JOIN source_files f ON f.id=p.file_id
                                  WHERE p.submission_id=? ORDER BY p.page_number''',(sid,)))
    corrections=data.dicts(d.execute('''SELECT c.*,q.number,q.prompt,q.points,q.kind,q.source_refs_json,cr.code AS criterion_code,o.code AS outcome_code
      FROM corrections c JOIN exam_questions q ON q.id=c.question_id
      JOIN criteria cr ON cr.id=q.criterion_id JOIN outcomes o ON o.id=cr.outcome_id
      WHERE c.run_id=? ORDER BY q.number''',(s['current_run_id'],))) if s['current_run_id'] else []
    for r in corrections:
        r['page_numbers']=json.loads(r.pop('page_numbers_json'))
        r['rubric_result']=json.loads(r.pop('rubric_result_json'))
        r['source_refs']=json.loads(r.pop('source_refs_json'))
    source=data.dicts(d.execute('SELECT id,sequence,original_name,sha256,page_count FROM source_files WHERE submission_id=? ORDER BY sequence',(sid,)))
    unknown=[]
    if s['current_run_id']:
        unknown=data.dicts(d.execute('''SELECT ps.text,ps.notes,p.page_number FROM page_segments ps
             JOIN pages p ON p.id=ps.page_id WHERE ps.run_id=? AND ps.question_number IS NULL ORDER BY p.page_number''',(s['current_run_id'],)))
    return {'submission':dict(s),'pages':pages,'sources':source,'corrections':corrections, 'unassigned':unknown}


def apply_extraction(d,module_id,outcomes):
    if not isinstance(outcomes,list) or len(outcomes)>200:
        raise ValueError('Listado de resultados incorrecto.')
    count=0
    for item in outcomes:
        code=str(item.get('code','')).strip()
        desc=str(item.get('description','')).strip()
        if not code or not desc or len(code)>50 or len(desc)>12000:raise ValueError('RA incompleto.')
        w=parse_weight(item.get('weight'))
        prior=d.execute('SELECT id,weight FROM outcomes WHERE module_id=? AND code=?',(module_id,code)).fetchone()
        previous_origin=weight_defaults.origin(d,'ra',prior['id']) if prior else None
        # Un ajuste manual ya realizado no se pisa al reimportar la programación.
        if previous_origin=='manual':w=prior['weight']
        d.execute('''INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)
                     ON CONFLICT(module_id,code) DO UPDATE SET description=excluded.description,weight=COALESCE(excluded.weight,outcomes.weight)''',
                  (module_id,code,desc,w))
        oid=must_row(d,'SELECT id FROM outcomes WHERE module_id=? AND code=?',(module_id,code))['id']
        if previous_origin!='manual' and (w is not None or not prior):
            weight_defaults.mark(d,'ra',oid,'programming' if w is not None else 'default')
        for c in item.get('criteria',[]):
            cc=str(c.get('code','')).strip()
            cd=str(c.get('description','')).strip()
            if not cc or not cd or len(cc)>50 or len(cd)>12000:raise ValueError('CE incompleto.')
            cw=parse_weight(c.get('weight'))
            prior_ce=d.execute('SELECT id,weight FROM criteria WHERE outcome_id=? AND code=?',(oid,cc)).fetchone()
            previous_ce_origin=weight_defaults.origin(d,'ce',prior_ce['id']) if prior_ce else None
            if previous_ce_origin=='manual':cw=prior_ce['weight']
            d.execute('''INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)
                         ON CONFLICT(outcome_id,code) DO UPDATE SET description=excluded.description,weight=COALESCE(excluded.weight,criteria.weight)''',
                      (oid,cc,cd,cw))
            cid=must_row(d,'SELECT id FROM criteria WHERE outcome_id=? AND code=?',(oid,cc))['id']
            if previous_ce_origin!='manual' and (cw is not None or not prior_ce):
                weight_defaults.mark(d,'ce',cid,'programming' if cw is not None else 'default')
            count+=1
    weight_defaults.recalculate(d,module_id)
    data.log(d,'programming_criteria_confirmed','module',module_id,{'outcomes':len(outcomes),'criteria':count})
    return count



def validate_header(body):
    """Datos opcionales del encabezado. Compatible con exámenes antiguos."""
    center=str(body.get('center_name') or '').strip()
    if len(center)>140:raise ValueError('El nombre del centro es demasiado largo.')
    date=str(body.get('exam_date') or '').strip()
    if date:
        from datetime import date as _date
        try:_date.fromisoformat(date)
        except ValueError:raise ValueError('Fecha de examen incorrecta (AAAA-MM-DD).')
    try:duration=int(body.get('duration_minutes') or 60)
    except (TypeError,ValueError):raise ValueError('Duración de examen no válida.')
    if not 10<=duration<=480:raise ValueError('La duración debe estar entre 10 y 480 minutos.')
    return {'center_name':center,'exam_date':date,'duration_minutes':duration}

def create_exam(d,body):
    module_id=int(body['module_id'])
    must_row(d,'SELECT id FROM modules WHERE id=?',(module_id,))
    selected=[int(x) for x in body.get('criteria_ids',[])]
    if not selected or len(selected)>30 or len(set(selected))!=len(selected):
        raise ValueError('Seleccione entre 1 y 30 criterios distintos.')
    marks=','.join('?'*len(selected))
    criteria=data.dicts(d.execute(f'''SELECT c.*,o.weight AS outcome_weight,
       c.weight AS criterion_weight, o.code AS outcome_code FROM criteria c
       JOIN outcomes o ON o.id=c.outcome_id WHERE o.module_id=? AND c.id IN ({marks})''',
        [module_id,*selected]))
    if len(criteria)!=len(selected): raise ValueError('Algunos CE no pertenecen al módulo seleccionado.')
    kind=body.get('kind')
    if kind not in ('test','desarrollo','mixto','problemas'):raise ValueError('Tipo de examen desconocido.')
    title=str(body.get('title','')).strip()
    if not title or len(title)>180:raise ValueError('Introduzca un título de examen válido.')
    total=float(body.get('total_points',10))
    if not total.is_integer() and round(total,2)!=total:raise ValueError('Máximo dos decimales en la puntuación.')
    count=int(body.get('question_count',len(criteria)))
    slots=logic.allocate_slots(criteria,count,kind,total,body.get('problem_count',0))
    return title,kind,total,slots


def html_doc(body,title):
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
    <style>@page{{size:A4;margin:18mm}}body{{font:11pt/1.5 Arial;color:#111;max-width:800px;margin:auto}}
    .top{{border-bottom:2px solid #111;margin-bottom:20px}}.question{{break-inside:avoid;margin:24px 0}}
    .lines{{height:110px;background:repeating-linear-gradient(#fff 0px,#fff 27px,#bbb 28px);margin-top:15px}}
    .small{{font-size:9pt;color:#555}}@media print{{button{{display:none}}}}</style></head>
    <body><button onclick="print()">Imprimir / Guardar como PDF</button>{body}</body></html>'''


def gradebook(d):
    """Registro consolidado sin confundir notas provisionales con definitivas."""
    rows=data.dicts(d.execute('''SELECT s.id AS submission_id,s.status,e.id AS exam_id,e.title AS exam_title,
       e.total_points,m.name AS module_name,m.academic_year,st.name AS student_name,st.code AS student_code,
       (SELECT COUNT(*) FROM exam_questions WHERE exam_id=e.id) AS question_count,
       (SELECT COUNT(*) FROM corrections c WHERE c.run_id=s.current_run_id AND c.status='validated') AS validated_questions,
       (SELECT ROUND(SUM(c.teacher_score),2) FROM corrections c WHERE c.run_id=s.current_run_id AND c.status='validated') AS score
       FROM submissions s JOIN exams e ON e.id=s.exam_id
       JOIN modules m ON m.id=e.module_id JOIN students st ON st.id=s.student_id
       ORDER BY m.name,st.name,e.id'''))
    for r in rows:
        r['final_score']=round(float(r['score']),2) if r['status']=='validated' and r['validated_questions']==r['question_count'] and r['score'] is not None else None
        r['out_of_ten']=round(10*r['final_score']/r['total_points'],2) if r['final_score'] is not None and r['total_points'] else None
        r.pop('score',None)
    by_criterion=data.dicts(d.execute('''SELECT st.code AS student_code,st.name AS student_name,
         m.name AS module_name,o.code AS outcome_code,cr.code AS criterion_code,
         ROUND(SUM(c.teacher_score*qc.weight_pct/100.0),2) AS scored,
         ROUND(SUM(q.points*qc.weight_pct/100.0),2) AS maximum,
         COUNT(*) AS evaluated_questions
         FROM corrections c JOIN submissions s ON s.id=c.submission_id AND c.run_id=s.current_run_id
         JOIN exam_questions q ON q.id=c.question_id
         JOIN exam_question_criteria qc ON qc.question_id=q.id
         JOIN criteria cr ON cr.id=qc.criterion_id
         JOIN outcomes o ON o.id=cr.outcome_id
         JOIN students st ON st.id=s.student_id JOIN modules m ON m.id=st.module_id
         WHERE s.status='validated' AND c.status='validated'
         GROUP BY st.id,cr.id ORDER BY m.name,st.name,o.code,cr.code'''))
    return {'exams':rows,'criteria':by_criterion}

def print_exam(d,eid):
    item=exam_detail(d,eid)
    e=item['exam']
    module=must_row(d,'SELECT * FROM modules WHERE id=?',(e['module_id'],))
    parts=[f'''<div class="top"><h1>{html.escape(e['title'])}</h1><p>{html.escape(module['name'])} — {html.escape(module['academic_year'])}</p>
    <p>Alumno/a: __________________________________ Grupo: ______________ Fecha: __________</p>
    <p>Modelo: {html.escape(e['variant_label'])} · Dificultad: {html.escape(e['difficulty'])}</p>
    <p>Calificación máxima: {e['total_points']:g} puntos</p><p>{html.escape(e['instructions'] or '')}</p></div>''']
    for q in item['questions']:
        parts.append(f'<div class="question"><b>Pregunta {q["number"]} · {q["points"]:g} puntos</b><p>{html.escape(q["prompt"])}</p>')
        if q['kind']=='test':
            parts.append(''.join(f'<p>☐ {html.escape(str(option))}</p>' for option in q['options']))
        else:parts.append('<div class="lines"></div>')
        parts.append('</div>')
    parts.append('<p class="small">Examen generado desde criterios de evaluación. Las soluciones y rúbricas no se imprimen para el alumnado.</p>')
    return html_doc(''.join(parts),e['title'])


def print_report(d,sid):
    item=sub_detail(d,sid);s=item['submission']
    e=must_row(d,'SELECT * FROM exams WHERE id=?',(s['exam_id'],))
    rows=[];final=True;total=0
    for r in item['corrections']:
        validated=r['status']=='validated'
        final &= validated
        score=r['teacher_score'] if validated else r['ai_score']
        if validated: total+=score
        cell=f'''<section class="question"><h3>Pregunta {r['number']} · {html.escape(r['criterion_code'])} ·
        {html.escape(r['outcome_code'])}</h3><p>{html.escape(r['prompt'])}</p>
        <p><strong>Máximo:</strong> {r['points']:g} · <strong>Propuesta IA:</strong> {r['ai_score'] if r['ai_score'] is not None else 'No disponible'} ·
        <strong>Nota validada:</strong> {r['teacher_score'] if validated else 'Pendiente'}</p>
        <p><strong>Páginas:</strong> {', '.join(map(str,r['page_numbers'])) or 'No identificadas'}</p>
        <p><strong>Transcripción:</strong></p><blockquote>{html.escape(r['transcription']) or 'No identificada'}</blockquote>
        <p><strong>Justificación de la IA:</strong> {html.escape(r['ai_feedback'] or '')}</p>'''
        if r.get('source_refs'):
            for src in r['source_refs']:
                cell+=f'<p class="small"><strong>Fuente didáctica del enunciado:</strong> {html.escape(src["filename"])} · {html.escape(src["location_kind"])} {src["location_number"]}. <strong>Fragmento:</strong> «{html.escape(src["evidence"])}»</p>'
        for indicator in r['rubric_result']:
            cell+=f'''<p class="small">• {html.escape(str(indicator.get('criterion','')))}:
            {html.escape(str(indicator.get('points','')))} / {html.escape(str(indicator.get('max_points','')))}.
            {html.escape(str(indicator.get('justification','')))}.
            Evidencia: «{html.escape(str(indicator.get('evidence','')))}»</p>'''
        cell+=f'<p><strong>Observación docente:</strong> {html.escape(r["teacher_comment"] or "—")}</p></section>'
        rows.append(cell)
    status='VALIDADO POR EL DOCENTE' if final and rows else 'BORRADOR · NO ES UNA CALIFICACIÓN DEFINITIVA'
    display_score=f'{round(total,2):g} / {e["total_points"]:g} puntos' if final and rows else 'Pendiente de validación total'
    top=f'''<div class="top"><h1>Informe justificativo de evaluación</h1><p><strong>{html.escape(e['title'])}</strong></p>
    <p>Alumno/a: {html.escape(s['student_name'])} ({html.escape(s['student_code'])})</p>
    <p>Estado: {status}</p><p>Resultado final: {display_score}
    {f'({round(total/e["total_points"]*10,2):g} / 10)' if final and rows and e['total_points'] else ' — pendiente de validación'}</p></div>'''
    return html_doc(top+''.join(rows)+'<p>Este informe incorpora propuestas automáticas que requieren revisión humana y las valoraciones registradas por el docente.</p>',
                    'Informe de evaluación')


def create_backup():
    from datetime import datetime
    name='copia_evaluafp_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip'
    location=data.BACKUPS/name
    tmp=data.DB_DIR/'backup_temp.sqlite3'
    with data.connect() as origin:
        dest=sqlite3.connect(tmp)
        try:
            origin.backup(dest)
        finally:
            dest.close()
    try:
        with zipfile.ZipFile(location,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(tmp,'datos/evaluafp.sqlite3')
            for root,_,files in os.walk(data.STORAGE):
                for fname in files:
                    f=Path(root)/fname
                    z.write(f,'almacen/'+str(f.relative_to(data.STORAGE)).replace('\\','/'))
            encrypted_key=ia.secret_file()
            if storage_config.PORTABLE and encrypted_key.exists():
                z.write(encrypted_key,'seguridad/api_cifrada.json')
        return location
    finally:
        tmp.unlink(missing_ok=True)

class MissingStudentsError(ValueError):
    """Falta alumnado para el ZIP. No se importa ninguna entrega."""
    def __init__(self, module_id, codes):
        self.module_id = int(module_id)
        self.codes = sorted(set(codes))
        super().__init__('Falta registrar alumnado antes de continuar con la importación.')


def register_students(db, module_id, incoming):
    """Alta de alumnado atómica; validación previa y sin duplicados."""
    must_row(db, 'SELECT id FROM modules WHERE id=?', (module_id,))
    if not isinstance(incoming, list) or not (1 <= len(incoming) <= 100):
        raise ValueError('Debe indicar entre 1 y 100 alumnos.')
    cleaned = []
    seen = set()
    for row in incoming:
        if not isinstance(row, dict):
            raise ValueError('La lista de alumnos contiene un registro no válido.')
        code = str(row.get('code','')).strip()
        name = str(row.get('name','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,59}', code):
            raise ValueError(f'Código de alumno no válido: {code[:60]}.')
        if not name or len(name) > 160:
            raise ValueError(f'Introduzca nombre y apellidos para {code}.')
        if code in seen:
            raise ValueError('Se ha repetido el código ' + code)
        seen.add(code)
        cleaned.append((code,name))
    # Verifica primero todo el lote, para no crear altas parciales.
    existing={r['code'] for r in db.execute('SELECT code FROM students WHERE module_id=?',(module_id,))}
    repeated=existing.intersection(seen)
    if repeated:
        raise ValueError('Ya están registrados estos códigos: '+', '.join(sorted(repeated)))
    created=[]
    for code,name in cleaned:
        db.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(module_id,code,name))
        sid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
        data.log(db,'student_created','student',sid,{'module_id':module_id,'via':'creation_prompt'})
        created.append({'id':sid,'code':code,'name':name})
    return created


class Handler(BaseHTTPRequestHandler):
    server_version='EvaluaFPCanarias/1.2.10-beta'
    def log_message(self,format,*args):
        # No vuelca tokens, claves ni datos de alumnado en stdout.
        return

    def send(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False,default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)

    def send_file(self,path,mime='application/octet-stream',filename=None):
        path=Path(path)
        if not path.is_file():raise ValueError('Archivo no encontrado en el almacenamiento.')
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','private, no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(path.stat().st_size))
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{data.slug(filename)}"')
        self.end_headers()
        with path.open('rb') as f:
            while chunk:=f.read(65536):self.wfile.write(chunk)

    def send_bytes(self,blob,mime,filename):
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','private, no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Disposition',f'attachment; filename="{data.slug(filename)}"')
        self.send_header('Content-Length',str(len(blob)))
        self.end_headers();self.wfile.write(blob)

    def ensure_auth(self):
        if self.headers.get('X-App-Token')==TOKEN:return
        cookies=SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except Exception:pass
        if 'efp_session' in cookies and cookies['efp_session'].value==TOKEN:return
        raise PermissionError('Sesión local no autorizada. Abra la aplicación desde su icono.')

    def route(self):
        parsed=urllib.parse.urlsplit(self.path)
        path=parsed.path
        args=urllib.parse.parse_qs(parsed.query)
        if path=='/' and self.command=='GET':
            if args.get('launch')!=[TOKEN]:
                self.ensure_auth()
            src=(WEB/'index.html').read_text(encoding='utf-8').replace('%%TOKEN%%',TOKEN)
            raw=src.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Set-Cookie',f'efp_session={TOKEN}; HttpOnly; SameSite=Strict; Path=/')
            self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'")
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
            return
        if path in ('/app.js','/style.css','/logo.svg','/favicon.ico') and self.command=='GET':
            types={'/app.js':'application/javascript','/style.css':'text/css','/logo.svg':'image/svg+xml','/favicon.ico':'image/x-icon'}
            self.send_file(WEB/path[1:],types[path])
            return
        self.ensure_auth()
        if self.command=='GET':
            with data.connect() as d:
                if path=='/api/health':return self.send({'ok':True,'database':str(data.DB_FILE),'storage':str(data.STORAGE)})
                if path=='/api/dashboard':
                    stats={}
                    for table in ('modules','criteria','students','exams','submissions','pages','corrections','materials'):
                        stats[table]=d.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                    return self.send(stats)
                if path=='/api/modules':return self.send(data.dicts(d.execute('SELECT * FROM modules ORDER BY id DESC')))
                if path=='/api/national/boe-monitor':
                    import normative_monitor
                    mid=int((args.get('module_id') or ['0'])[0])
                    return self.send(normative_monitor.list_sources(d,mid))
                if path=='/api/curriculum/history':
                    import curriculum_history
                    mid=int((args.get('module_id') or ['0'])[0])
                    draft=program_builder.load(d,mid)['draft']
                    if not str(draft.get('official_module_code') or '').strip():
                        return self.send({'versions':[],'count':0,
                                          'notice':'Indique y guarde primero el código oficial del módulo para consultar su historial.'})
                    return self.send(curriculum_history.list_snapshots(d,mid))
                if path=='/api/curriculum/history-compare':
                    import curriculum_history
                    mid=int((args.get('module_id') or ['0'])[0])
                    old=int((args.get('old') or ['0'])[0])
                    new=int((args.get('new') or ['0'])[0])
                    return self.send(curriculum_history.compare_snapshots(d,mid,old,new))
                if path=='/api/curriculum/catalog':
                    import curriculum_history
                    region=(args.get('region') or [''])[0]
                    year=(args.get('academic_year') or [''])[0]
                    query=(args.get('q') or [''])[0]
                    return self.send(curriculum_history.catalog(d,region,year,query))
                if path=='/api/national/catalog':
                    import fp_catalog
                    region=(args.get('region') or [''])[0]
                    ag.ensure_territory(region)
                    year=(args.get('academic_year') or [''])[0]
                    search_term=(args.get('q') or [''])[0]
                    return self.send(fp_catalog.search(d,region,year,search_term))
                if path=='/api/national/general-calendar':
                    import general_calendar_library
                    mid=int((args.get('module_id') or ['0'])[0])
                    return self.send(general_calendar_library.list_for_module(d,mid))
                if path=='/api/national/general-calendar/compare':
                    import general_calendar_library
                    mid=int((args.get('module_id') or ['0'])[0])
                    old=int((args.get('old') or ['0'])[0])
                    new=int((args.get('new') or ['0'])[0])
                    return self.send(general_calendar_library.compare(d,mid,old,new))
                if path=='/api/national/calendar/versions':
                    import calendar_versions
                    mid=int((args.get('module_id') or ['0'])[0])
                    return self.send(calendar_versions.list_versions(d,mid))
                if path=='/api/national/calendar/compare':
                    import calendar_versions
                    mid=int((args.get('module_id') or ['0'])[0])
                    old=int((args.get('old') or ['0'])[0])
                    new=int((args.get('new') or ['0'])[0])
                    return self.send(calendar_versions.compare_versions(d,mid,old,new))
                if path=='/api/national/sources':
                    import national_registry
                    mid=int((args.get('module_id') or ['0'])[0])
                    return self.send(national_registry.propose_module_sources(d,mid))
                if path=='/api/canarias-ag/catalog':
                    return self.send(ag.public_catalog())
                if path=='/api/territories':
                    return self.send({'territories':[{'code':'CN','label':'Canarias'}]})
                if path=='/api/territories/calendar':
                    region=(args.get('region') or [''])[0]
                    year=(args.get('academic_year') or [''])[0]
                    island=(args.get('island') or [''])[0]
                    ag.ensure_territory(region)
                    info=territories.public_profile(region,year,island)
                    info['schedule_defaults']=schedule_engine.defaults(info['academic_year'],info['territory'],island)
                    return self.send(info)
                m_import=re.fullmatch(r'/api/programmings/(\d+)/import-preview',path)
                if m_import:
                    program=must_row(d,'SELECT id,filename,local_path,extracted_text,module_id FROM programmings WHERE id=?',(int(m_import[1]),))
                    proposal=program_importer.analyze_document(program['local_path'],program['extracted_text'])
                    proposal['filename']=program['filename']
                    proposal['programming_id']=program['id']
                    proposal['module_id']=program['module_id']
                    existing=program_builder.load(d,program['module_id'])['draft']
                    proposal['existing_fields']={key:bool(existing.get(key)) for key in program_importer.FIELD_NAMES}
                    proposal['existing_units']=bool(existing.get('units'))
                    return self.send(proposal)
                m_hours=re.fullmatch(r'/api/programming-builder/(\d+)/hours-reference',path)
                if m_hours:
                    module=program_assistant.module_context(d,int(m_hours[1]))[0]
                    draft=program_builder.load(d,int(m_hours[1]))['draft']
                    return self.send({'proposal':program_assistant.hours_proposal(module,draft['region']),
                                      'schedule':draft['schedule']})
                m_feoe=re.fullmatch(r'/api/programming-builder/(\d+)/feoe-minimum',path)
                if m_feoe:
                    import feoe_minimum
                    return self.send(feoe_minimum.propose(d,int(m_feoe[1])))
                m_feoe_export=re.fullmatch(r'/api/programming-builder/(\d+)/feoe-minimum\.(docx|pdf|md)',path)
                if m_feoe_export:
                    import feoe_minimum
                    blob,mime,filename=feoe_minimum.export(d,int(m_feoe_export[1]),m_feoe_export[2])
                    return self.send_bytes(blob,mime,filename)
                m_draft=re.fullmatch(r'/api/programming-builder/(\d+)',path)
                if m_draft:return self.send(program_builder.diagnose(d,int(m_draft[1])))
                m_export=re.fullmatch(r'/api/programming-builder/(\d+)/export\.(pdf|docx|md)',path)
                if m_export:
                    blob,mime,filename=program_builder.export(d,int(m_export[1]),m_export[2])
                    return self.send_bytes(blob,mime,filename)
                m=re.fullmatch(r'/api/modules/(\d+)',path)
                if m:return self.send(fields_safe(d,int(m[1])))
                if path=='/api/exams':return self.send(list_exams(d))
                m=re.fullmatch(r'/api/exam-batches/(\d+)',path)
                if m:
                    bid=int(m[1]);batch=must_row(d,'SELECT * FROM exam_batches WHERE id=?',(bid,))
                    rows=data.dicts(d.execute('''SELECT b.id,b.criterion_id,b.kind,b.prompt,b.assigned_variant,
                      c.code AS criterion_code FROM question_bank_items b
                      JOIN criteria c ON c.id=b.criterion_id WHERE b.batch_id=? ORDER BY b.id''',(bid,)))
                    return self.send({'batch':dict(batch),'questions':rows})
                # PDFs auténticos A4 (no impresión HTML) y lote completo por modelos.
                m_pdf=re.fullmatch(r'/api/exams/(\d+)/(pdf|soluciones\.pdf)',path)
                if m_pdf:
                    import exam_pdf
                    eid=int(m_pdf[1]);solution=m_pdf[2]=='soluciones.pdf'
                    exam=must_row(d,'SELECT title,variant_label FROM exams WHERE id=?',(eid,))
                    blob=exam_pdf.build_exam_pdf(d,eid,solution)
                    name=f'EvaluaFP_{exam["id"] if "id" in exam.keys() else eid}_Modelo_{exam["variant_label"]}'
                    return self.send_bytes(blob,'application/pdf',name+('_soluciones' if solution else '')+'.pdf')
                m_zip=re.fullmatch(r'/api/exam-batches/(\d+)/(pdf|soluciones)\.zip',path)
                if m_zip:
                    import exam_pdf
                    bid=int(m_zip[1])
                    teacher_only=m_zip[2]=='soluciones'
                    blob=exam_pdf.build_batch_zip(d,bid,teacher_only=teacher_only)
                    return self.send_bytes(blob,'application/zip',f'EvaluaFP_{"Soluciones" if teacher_only else "Modelos"}_{bid}.zip')
                if path=='/api/gradebook':return self.send(gradebook(d))
                if path=='/api/evaluation':
                    mod=int(args.get('module_id',[0])[0]);return self.send(evaluacion.summary(d,mod))
                export_match=re.fullmatch(r'/api/evaluation/(\d+)/export/(xlsx|xls|additio-alumnos\.xlsx|additio-alumnos\.csv|additio-notas\.csv|additio-pegar\.tsv|additio-seguimiento\.csv|additio-estado\.csv|additio-ra\.xlsx|additio-ce\.xlsx|additio-ce-detalle\.xlsx|additio-notas\.xlsx|additio-configuracion\.zip)',path)
                if export_match:
                    mid=int(export_match[1]);kind=export_match[2]
                    if kind in ('xlsx','xls'):
                        blob,mime,filename=exportaciones.export_excel(d,mid,kind)
                    elif kind == 'additio-configuracion.zip':
                        blob,mime,filename=exportaciones.additio_curriculum_zip(d,mid)
                    elif kind in ('additio-ra.xlsx','additio-ce.xlsx','additio-ce-detalle.xlsx','additio-notas.xlsx'):
                        k={'additio-ra.xlsx':'ra','additio-ce.xlsx':'ce','additio-ce-detalle.xlsx':'detalle','additio-notas.xlsx':'notas'}[kind]
                        blob,mime,filename=exportaciones.additio_curriculum_xlsx(d,mid,k)
                    elif kind == 'additio-alumnos.xlsx':
                        blob,mime,filename=exportaciones.additio_students_xlsx(d,mid)
                    else:
                        what={'additio-alumnos.csv':'alumnos','additio-notas.csv':'notas','additio-pegar.tsv':'pegar','additio-seguimiento.csv':'seguimiento','additio-estado.csv':'estado'}[kind]
                        blob,mime,filename=exportaciones.export_additio(d,mid,what)
                    return self.send_bytes(blob,mime,filename)
                eval_pdf_match=re.fullmatch(r'/api/evaluation/(\d+)/student/(\d+)\.pdf',path)
                if eval_pdf_match:
                    import eval_pdf
                    mid=int(eval_pdf_match[1]);sid=int(eval_pdf_match[2])
                    blob=eval_pdf.report(d,mid,sid)
                    return self.send_bytes(blob,'application/pdf',f'EvaluaFP_Informe_Modulo_{mid}_Alumno_{sid}.pdf')
                if path=='/api/submissions':
                    return self.send(data.dicts(d.execute('''SELECT s.id,s.exam_id,s.student_id,s.status,s.created_at,
                    e.title AS exam_title,st.name AS student_name,st.code AS student_code,
                    (SELECT COUNT(*) FROM pages p WHERE p.submission_id=s.id) AS page_count
                    FROM submissions s JOIN exams e ON e.id=s.exam_id
                    JOIN students st ON st.id=s.student_id ORDER BY s.id DESC''')))
                m=re.fullmatch(r'/api/exams/(\d+)',path)
                if m:return self.send(exam_detail(d,int(m[1])))
                m=re.fullmatch(r'/api/submissions/(\d+)',path)
                if m:return self.send(sub_detail(d,int(m[1])))
                if path=='/api/settings':
                    return self.send({**ia.settings(),**ia.secret_status(), 'api_key_configured':ia.key_available(),
                                      **storage_config.get_info()})
                m=re.fullmatch(r'/api/pages/(\d+)/image',path)
                if m:
                    row=must_row(d,'SELECT image_path FROM pages WHERE id=?',(int(m[1]),))
                    return self.send_file(row['image_path'],'image/jpeg')
                m=re.fullmatch(r'/api/materials/(\d+)/original',path)
                if m:
                    row=must_row(d,'SELECT local_path,mime,filename FROM materials WHERE id=?',(int(m[1]),))
                    return self.send_file(row['local_path'],row['mime'],row['filename'])
                m=re.fullmatch(r'/api/source/(\d+)',path)
                if m:
                    row=must_row(d,'SELECT local_path,mime,original_name FROM source_files WHERE id=?',(int(m[1]),))
                    return self.send_file(row['local_path'],row['mime'],row['original_name'])
                m=re.fullmatch(r'/print/exam/(\d+)',path)
                if m:return self.print_html(print_exam(d,int(m[1])))
                m=re.fullmatch(r'/print/report/(\d+)',path)
                if m:return self.print_html(print_report(d,int(m[1])))
                m=re.fullmatch(r'/api/audit/(\d+)',path)
                if m:
                    return self.send(data.dicts(d.execute('''SELECT * FROM audit_log WHERE (entity='submission' AND entity_id=?)
                        OR (entity='correction' AND entity_id IN (SELECT id FROM corrections WHERE submission_id=?)) ORDER BY id DESC LIMIT 150''',
                             (int(m[1]),int(m[1])))))
            if path=='/api/backup':
                location=create_backup()
                return self.send_file(location,'application/zip',location.name)
            raise ValueError('Ruta GET desconocida.')
        if self.command!='POST':raise ValueError('Método no permitido')
        if path in ('/api/programmings/upload','/api/materials/upload','/api/submissions/upload','/api/submissions/batch','/api/evaluation/import','/api/national/document-preview','/api/national/calendar-document-preview','/api/curriculum/review-preview','/api/curriculum/history/store'):
            if path=='/api/national/calendar-document-preview' and int(self.headers.get('Content-Length','0'))>16*1024*1024:
                raise ValueError('El calendario supera el límite de 15 MB más los campos del formulario.')
            fields,files=multipart(self)
        else:
            body=read_json(self)
        if path=='/api/settings':
            for required in ('provider','base_url','model_generation','model_vision','model_correction','model_analysis'):
                if not str(body.get(required,'')).strip():raise ValueError(f'Falta el ajuste {required}')
            body['base_url']=ia.check_url(body['base_url'])
            keep={key:str(body[key]).strip() for key in ('provider','base_url','model_generation','model_vision','model_correction','model_analysis')}
            with data.connect() as d:
                data.set_pref(d,'ai',keep)
                data.log(d,'ai_settings_modified','settings',None,{'provider':keep['provider'],'base_url':keep['base_url']})
            persistent=None
            if 'api_key' in body:
                _,persistent=ia.set_secret(body['api_key'], body.get('master_password'))
            return self.send({'ok':True, **ia.secret_status(), 'api_key_configured':ia.key_available()})
        if path=='/api/storage/change':
            # La base actual permanece intacta: se crea una copia y solo se activa al reiniciar.
            result=storage_config.relocate(body.get('data_dir',''),body.get('backup_dir',''))
            return self.send({'ok':True, **result})
        if path=='/api/settings/unlock':
            ia.unlock_secret(body.get('master_password',''))
            return self.send({'ok':True, **ia.secret_status()})
        if path=='/api/settings/lock':
            ia.lock_secret()
            return self.send({'ok':True, **ia.secret_status()})
        if path=='/api/evaluation/import':
            iid=int(fields.get('instrument_id',0))
            uploads=[(name,bytes_) for field,name,bytes_ in files if field=='csv']
            if len(uploads)!=1 or not uploads[0][0].lower().endswith('.csv'):
                raise ValueError('Seleccione un único fichero CSV con notas por criterio.')
            with data.connect() as d:
                count=evaluacion.import_csv(d,iid,uploads[0][1])
            return self.send({'ok':True,'imported':count})
        if path=='/api/evaluation/unit':
            with data.connect() as d:uid=evaluacion.add_unit(d,body)
            return self.send({'ok':True,'id':uid})
        if path=='/api/evaluation/instrument':
            with data.connect() as d:iid=evaluacion.add_instrument(d,body)
            return self.send({'ok':True,'id':iid})
        if path=='/api/evaluation/score':
            with data.connect() as d:evaluacion.put_score(d,body)
            return self.send({'ok':True})
        if path=='/api/evaluation/policy':
            with data.connect() as d:evaluacion.update_settings(d,body)
            return self.send({'ok':True})
        if path=='/api/evaluation/close':
            with data.connect() as d:
                result=evaluacion.close_student(d,body['module_id'],body['student_id'],body.get('justification',''))
            return self.send({'ok':True,**result})
        if path=='/api/evaluation/sync-exam':
            with data.connect() as d:
                result=evaluacion.sync_exam(d,int(body['instrument_id']),bool(body.get('replace',False)))
            return self.send({'ok':True,**result})
        if path=='/api/national/boe-monitor/check':
            import normative_monitor
            with data.connect() as d:
                result=normative_monitor.check_source(d,body.get('module_id'),body.get('boe_id'),
                    body.get('teacher_confirmed') is True)
            return self.send(result)
        if path=='/api/national/boe-monitor/ack':
            import normative_monitor
            with data.connect() as d:
                result=normative_monitor.acknowledge_change(d,body.get('module_id'),
                    body.get('boe_id'),body.get('note'),body.get('teacher_confirmed') is True)
            return self.send(result)
        if path=='/api/national/todofp/search-titles':
            import official_title_index
            return self.send(official_title_index.search(
                body.get('grade'),body.get('query',''),body.get('region'),body.get('academic_year')))
        if path=='/api/national/todofp/explore':
            import todofp_discovery
            result=todofp_discovery.explore(body.get('url'),body.get('region'),body.get('academic_year'),
                cycle_name=body.get('cycle_name',''),module_name=body.get('module_name',''))
            return self.send(result)
        if path=='/api/national/catalog/preview':
            import fp_catalog
            # El ámbito de la tabla procede del formulario: solo se guarda tras confirmación.
            ag.ensure_territory(body.get('region',''))
            territories.year_code(body.get('academic_year',''))
            return self.send(fp_catalog.preview_table(body.get('table')))
        if path=='/api/national/catalog/import':
            import fp_catalog
            ag.ensure_territory(body.get('region',''))
            with data.connect() as d:
                result=fp_catalog.import_table(d,body.get('table'),
                    body.get('region',''),body.get('academic_year',''),
                    body.get('source_url',''),body.get('source_title',''),
                    teacher_confirmed=body.get('teacher_confirmed') is True,
                    replace_existing=body.get('replace_existing') is True)
            return self.send(result)
        if path=='/api/modules':
            year=str(body.get('academic_year','')).strip();cycle=str(body.get('cycle','')).strip();name=str(body.get('name','')).strip()
            region=ag.ensure_territory(body.get('territory') or 'Canarias')
            cycle=ag.canonical_cycle(cycle)
            year=territories.year_code(year)
            if not year or not cycle or not name or len(cycle)>180 or len(name)>150:
                raise ValueError('Curso, ciclo y módulo son obligatorios.')
            with data.connect() as d:
                catalog_record=None
                if body.get('catalog_entry_id') not in (None,''):
                    import fp_catalog
                    catalog_record=fp_catalog.get_entry(d,body['catalog_entry_id'],region,year)
                    if ag._fold(catalog_record['family']) != ag._fold(ag.FAMILY):
                        raise ValueError('La ficha local no pertenece a Administración y Gestión.')
                    if cycle != ag.canonical_cycle(catalog_record['title_name']) or name != catalog_record['module_name']:
                        raise ValueError('El módulo seleccionado no coincide con la ficha curricular local. Repita la búsqueda.')
                d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',
                          (year,cycle,name,str(body.get('group_name','')),data.now(),region))
                mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                if catalog_record:
                    # Importa SOLO la identificación y procedencia de la ficha.
                    # El currículo, los RA/CE y las horas siguen SIN confirmar.
                    draft=program_builder.load(d,mid)['draft']
                    draft.update({'official_cycle_code':catalog_record['title_code'],
                                  'official_module_code':catalog_record['module_code'],
                                  'curriculum_source_url':catalog_record['source_url'],
                                  'curriculum_source_description':catalog_record['source_title'],
                                  'curriculum_confirmed':False})
                    program_builder.save(d,mid,draft)
                data.log(d,'module_created','module',mid,{'name':name,'catalog_entry_id':catalog_record['id'] if catalog_record else None})
            return self.send({'id':mid,'catalog_used':bool(catalog_record)})
        if path=='/api/curriculum/history/store':
            import curriculum_history
            mid=int(fields.get('module_id','0'))
            uploads=[(name,blob) for field,name,blob in files if field=='document']
            if len(uploads)!=1:
                raise ValueError('Seleccione exactamente un documento curricular oficial.')
            with data.connect() as d:
                result=curriculum_history.store_document(d,mid,uploads[0][0],uploads[0][1],
                    str(fields.get('module_code','')).strip(),
                    fields.get('document_kind',''),fields.get('source_url',''),
                    fields.get('source_title',''),fields.get('teacher_confirmed')=='true')
            return self.send(result)
        if path=='/api/curriculum/review-preview':
            # Vista previa no destructiva y sin IA: no guarda el documento ni
            # cambia RA/CE, pesos, notas, exámenes o programaciones existentes.
            import tempfile
            import curriculum_review
            mid=int(fields.get('module_id','0'))
            uploads=[(name,blob) for field,name,blob in files if field=='document']
            if len(uploads)!=1:
                raise ValueError('Seleccione exactamente un documento PDF, DOCX, TXT o MD.')
            filename,blob=uploads[0]
            if not blob or len(blob)>curriculum_review.MAX_FILE:
                raise ValueError('El documento no puede superar 15 MB.')
            kind=fields.get('document_kind','programacion')
            code=str(fields.get('module_code','')).strip()
            with data.connect() as d:
                module=must_row(d,'SELECT id,name FROM modules WHERE id=?',(mid,))
                saved=program_builder.load(d,mid)['draft'].get('official_module_code','').strip()
                if saved and code!=saved:
                    raise ValueError('El código indicado no coincide con el código curricular registrado para este módulo.')
                existing=data.dicts(d.execute('SELECT id,code,description,weight FROM outcomes WHERE module_id=? ORDER BY id',(mid,)))
                for outcome in existing:
                    outcome['criteria']=data.dicts(d.execute(
                        'SELECT code,description,weight FROM criteria WHERE outcome_id=? ORDER BY id',
                        (outcome['id'],)))
            suffix=Path(filename).suffix.lower()
            if suffix not in ('.pdf','.docx','.txt','.md'):
                raise ValueError('Solo se permiten documentos PDF, DOCX, TXT o MD.')
            with tempfile.TemporaryDirectory(prefix='evaluafp_ra_ce_') as folder:
                target=Path(folder)/('curriculo'+suffix)
                target.write_bytes(blob)
                report=curriculum_review.preview(target,module['name'],code,document_kind=kind)
            report['comparison']=curriculum_review.compare(report,existing)
            report['default_weight_proposal']=curriculum_review.propose_equal_weights(report)
            report['existing_ra_count']=len(existing)
            report['can_auto_apply']=False
            return self.send(report)
        if path=='/api/national/calendar-ai-interpret':
            import calendar_ai
            if body.get('authorize_ai') is not True:
                raise ValueError('Debe autorizar expresamente el envío del fragmento de calendario.')
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                module=must_row(d,'SELECT territory,academic_year FROM modules WHERE id=?',(mid,))
                region=territories.require_territory(body.get('region',''))
                year=territories.year_code(body.get('academic_year',''))
                if territories.require_territory(module['territory'])!=region or module['academic_year']!=year:
                    raise ValueError('Territorio o curso distinto del módulo guardado. Guarde primero los cambios.')
            # No almacena el fragmento ni las propuestas; solo transmite el texto autorizado.
            return self.send(calendar_ai.interpret(body.get('fragment',''),region,year,True))
        if path=='/api/national/calendar-document-preview':
            import calendar_document
            mid=int(fields.get('module_id','0'))
            with data.connect() as d:
                module=must_row(d,'SELECT territory,academic_year FROM modules WHERE id=?',(mid,))
                region=territories.require_territory(fields.get('region',''))
                year=territories.year_code(fields.get('academic_year',''))
                if module['academic_year']!=year or territories.require_territory(module['territory'])!=region:
                    raise ValueError('El archivo no se corresponde con el territorio o curso del módulo. Guarde primero el ámbito correcto.')
            uploads=[(name,blob) for field,name,blob in files if field=='document']
            if len(uploads)!=1:
                raise ValueError('Seleccione exactamente un calendario oficial PDF, Word o texto.')
            # Solo vista previa local. Nunca se modifica la programación desde esta ruta.
            return self.send(calendar_document.preview_document(
                uploads[0][0],uploads[0][1],region,year,fields.get('allow_ocr')=='true'))
        if path=='/api/national/document-preview':
            import official_document_tables
            uploads=[(name,blob) for field,name,blob in files if field=='document']
            if len(uploads)!=1:
                raise ValueError('Seleccione exactamente un PDF o Word con la tabla horaria.')
            # Solicitud local protegida por token y sin envío a servicios de IA.
            return self.send(official_document_tables.preview_document(
                uploads[0][0],uploads[0][1],fields.get('allow_ocr')=='true'))
        if path=='/api/national/boe-search':
            import boe_discovery
            return self.send(boe_discovery.search_title(body.get('cycle',''),
                body.get('region',''),body.get('academic_year','')))
        if path=='/api/national/boe-inspect':
            import boe_discovery
            return self.send(boe_discovery.inspect_boe_id(body.get('boe_id','')))
        if path=='/api/national/table-preview':
            import national_registry
            return self.send(national_registry.preview_hours_table(body.get('table')))
        if path=='/api/national/table-import':
            import national_registry
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=national_registry.import_hours_table(d,mid,body.get('table'),
                    body.get('source_url'),body.get('source_title'),
                    body.get('teacher_confirmed') is True,body.get('replace_existing') is True)
            return self.send(result)
        if path=='/api/national/extract-hours':
            import national_registry
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=national_registry.extract_hours_with_ai(d,mid,body.get('fragment'),body.get('authorize_ai') is True)
            return self.send(result)
        if path=='/api/national/save-hours':
            import national_registry
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=national_registry.save_hours(d,mid,body)
            return self.send({'saved':True,'record':result})
        if path=='/api/national/general-calendar/save':
            import general_calendar_library
            with data.connect() as d:
                record=general_calendar_library.save_from_module(
                    d,int(body.get('module_id',0)),body)
            # Responder únicamente DESPUÉS de confirmar la transacción SQLite.
            return self.send({'record':record})
        if path=='/api/national/save-calendar':
            import national_registry
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=national_registry.save_calendar(d,mid,body)
            return self.send({'saved':True,'record':result})
        if path=='/api/programming-builder/propose':
            if body.get('mode')=='ai' and body.get('authorize_ai') is not True:
                raise ValueError('Debe autorizar expresamente el uso de IA antes de generar contenido.')
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_assistant.propose(d,mid,str(body.get('region','Canarias')),
                        str(body.get('mode','base')),body.get('fields'))
            return self.send(result)
        if path=='/api/programming-builder/improve':
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_assistant.improve_text(d,mid,body.get('field'),body.get('text'),
                                                   body.get('authorize_ai') is True)
            return self.send(result)
        if path=='/api/programming-builder/enrich-units':
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_assistant.enrich_unit_details(d,mid,body.get('units'),body.get('authorize_ai') is True)
            return self.send(result)
        if path=='/api/programming-builder/enrich-planning':
            import planning_matrix
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=planning_matrix.ai_enrich(d,mid,body.get('units'),None,
                        body.get('term_assessments'),body.get('feoe_tasks'),
                        body.get('authorize_ai') is True)
            return self.send(result)
        if path=='/api/programming-builder/weights':
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_assistant.update_weights(d,mid,body.get('mode'),body.get('rows'),body.get('teacher_confirmed') is True)
            return self.send(result)
        if path=='/api/programming-builder/propose-units':
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_assistant.propose_units(d,mid,body.get('schedule'),str(body.get('region','Canarias')))
            return self.send(result)
        if path=='/api/programming-builder/feoe-minimum/ai':
            import feoe_minimum
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                response=feoe_minimum.propose(d,mid,'ai',body.get('authorize_ai') is True)
            return self.send(response)
        if path=='/api/programming-builder/feoe-minimum/accept':
            import feoe_minimum
            if body.get('teacher_confirmed') is not True:
                raise ValueError('Confirme los criterios y las tareas del programa formativo antes de guardarlos.')
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                response=feoe_minimum.accept(d,mid,body.get('rows'))
            return self.send(response)
        if path=='/api/programming-builder/save':
            mid=int(body.get('module_id',0))
            with data.connect() as d:
                result=program_builder.save(d,mid,body.get('draft'))
            return self.send(result)
        if path=='/api/students':
            mid=int(body['module_id']); code=str(body.get('code','')).strip();name=str(body.get('name','')).strip()
            if not name or not code: raise ValueError('Indique código y nombre del alumno.')
            with data.connect() as d:
                must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,code,name))
                sid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                data.log(d,'student_created','student',sid,{'module_id':mid})
            return self.send({'id':sid})
        if path=='/api/students/bulk':
            mid=int(body['module_id'])
            with data.connect() as d:
                created=register_students(d,mid,body.get('students'))
            return self.send({'created':created})
        if path=='/api/outcomes':
            mid=int(body['module_id']); code=str(body.get('code','')).strip();desc=str(body.get('description','')).strip()
            if not code or not desc: raise ValueError('Complete código y descripción del RA')
            weight=parse_weight(body.get('weight'))
            with data.connect() as d:
                must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                if body.get('id'):
                    rid=int(body['id']);must_row(d,'SELECT id FROM outcomes WHERE id=? AND module_id=?',(rid,mid))
                    d.execute('UPDATE outcomes SET code=?,description=?,weight=? WHERE id=?',(code,desc,weight,rid))
                else:
                    d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,code,desc,weight))
                    rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                weight_defaults.mark(d,'ra',rid,'manual' if weight is not None else 'default')
                weight_defaults.recalculate(d,mid)
                data.log(d,'outcome_saved','outcome',rid,{'weight':weight,'origin':'manual' if weight is not None else 'default'})
            return self.send({'id':rid})
        if path=='/api/criteria':
            oid=int(body['outcome_id']); code=str(body.get('code','')).strip();desc=str(body.get('description','')).strip()
            if not code or not desc:raise ValueError('Complete código y descripción del CE.')
            weight=parse_weight(body.get('weight'))
            with data.connect() as d:
                must_row(d,'SELECT id FROM outcomes WHERE id=?',(oid,))
                if body.get('id'):
                    cid=int(body['id']);must_row(d,'SELECT id FROM criteria WHERE id=? AND outcome_id=?',(cid,oid))
                    d.execute('UPDATE criteria SET code=?,description=?,weight=? WHERE id=?',(code,desc,weight,cid))
                else:
                    d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(oid,code,desc,weight))
                    cid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                weight_defaults.mark(d,'ce',cid,'manual' if weight is not None else 'default')
                mid=d.execute('SELECT module_id FROM outcomes WHERE id=?',(oid,)).fetchone()['module_id']
                weight_defaults.recalculate(d,mid)
                data.log(d,'criterion_saved','criterion',cid,{'weight':weight,'origin':'manual' if weight is not None else 'default'})
            return self.send({'id':cid})
        if path=='/api/programmings/upload':
            mid=int(fields['module_id']); docfiles=[x for x in files if x[0]=='document']
            if len(docfiles)!=1:raise ValueError('Seleccione un solo archivo de programación.')
            _,name,blob=docfiles[0]
            ext=logic.check_signature(name,blob,programming=True)
            with data.connect() as d:
                must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                location=data.STORAGE/'programaciones'/str(mid)
                location.mkdir(parents=True,exist_ok=True)
                fn=f'{hashlib.sha256(blob).hexdigest()[:16]}_{data.slug(Path(name).stem)}{ext}'
                file=location/fn
                file.write_bytes(blob)
                try:text=logic.extract_program(file)
                except Exception:
                    file.unlink(missing_ok=True)
                    raise
                d.execute('INSERT INTO programmings(module_id,filename,local_path,sha256,extracted_text,uploaded_at) VALUES(?,?,?,?,?,?)',
                          (mid,name,str(file),logic.sha(file),text,data.now()))
                pid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                data.log(d,'programming_uploaded','programming',pid,{'module_id':mid,'characters':len(text)})
            return self.send({'id':pid,'characters':len(text),'warning': 'Documento sin texto extraíble' if not text.strip() else None})
        if path=='/api/materials/upload':
            mid=int(fields['module_id']);pid=int(fields['programming_id'])
            incoming=[(name,blob) for field,name,blob in files if field=='documents']
            if not incoming or len(incoming)>15:raise ValueError('Adjunte entre 1 y 15 documentos de material didáctico.')
            # Sin transacción multiarchivo parcial: en caso de error deshacer toda la carga.
            created=[]
            paths=[]
            try:
                with data.connect() as d:
                    for name,blob in incoming:
                        info=materiales.save_material(d,mid,pid,name,blob)
                        created.append(info)
                        paths.append(must_row(d,'SELECT local_path FROM materials WHERE id=?',(info['id'],))['local_path'])
            except Exception:
                # No borrar originales que ya existieran al comenzar la operación.
                for name in paths:
                    if not data.DB_FILE.exists():continue
                    with data.connect() as d:
                        if not d.execute('SELECT id FROM materials WHERE local_path=?',(name,)).fetchone():Path(name).unlink(missing_ok=True)
                raise
            return self.send({'created':created})
        if path=='/api/materials/active':
            mid=int(body['module_id']);pid=int(body['material_id']);active=bool(body.get('active',True))
            with data.connect() as d:
                must_row(d,'SELECT id FROM materials WHERE id=? AND module_id=?',(pid,mid))
                d.execute('UPDATE materials SET active=? WHERE id=?',(int(active),pid))
                data.log(d,'material_status_changed','material',pid,{'active':active})
            return self.send({'ok':True,'active':active})
        if path=='/api/curriculum/official':
            mid=int(body['module_id'])
            with data.connect() as d:
                module=must_row(d,'SELECT name FROM modules WHERE id=?',(mid,))
                proposal=curriculum_official.fetch_official(module['name'],body.get('boe_id'),
                      consent=body.get('authorize_official_query') is True)
                data.log(d,'official_curriculum_consulted','module',mid,
                         {'source_url':proposal['source_url'],'source_id':proposal['source_id'],
                          'consulted_at':proposal['consulted_at'],
                          'outcomes':len(proposal['outcomes'])})
            return self.send(proposal)
        if path=='/api/programmings/apply-content':
            pid=int(body.get('programming_id') or 0)
            chosen=body.get('accepted_fields') or []
            edited=body.get('edited_fields') or {}
            if not isinstance(chosen,list) or not isinstance(edited,dict):
                raise ValueError('Selección de apartados incorrecta.')
            if len(chosen)!=len(set(chosen)) or set(chosen)-set(program_importer.FIELD_NAMES):
                raise ValueError('Selección de apartados no válida.')
            with data.connect() as d:
                program=must_row(d,'SELECT * FROM programmings WHERE id=?',(pid,))
                extracted=program_importer.analyze_document(program['local_path'],program['extracted_text'])
                original=program_builder.load(d,program['module_id'])['draft']
                merged=json.loads(json.dumps(original))
                for key in chosen:
                    if key not in extracted['fields']:raise ValueError('Apartado no encontrado en el documento: '+key)
                    val=edited.get(key,extracted['fields'][key])
                    if not isinstance(val,str) or len(val)>12000:raise ValueError('El apartado '+key+' supera el tamaño permitido.')
                    merged[key]=val
                # Solo cambia los datos seleccionados y deja todos los demás intactos.
                if body.get('keep_source_sections',True) is True:
                    older=[s for s in merged.get('imported_sections',[]) if int(s.get('programming_id') or 0)!=pid]
                    merged['imported_sections']=older+[{**sec,'programming_id':pid} for sec in extracted['sections']]
                if body.get('accept_document_hours',False) is True:
                    proposed=extracted['proposed_hours']
                    if proposed['total_hours'] is None or proposed['weekly_hours'] is None:
                        raise ValueError('El archivo no contiene horas inequívocas.')
                    merged['schedule']['total_hours']=proposed['total_hours']
                    merged['schedule']['weekly_hours']=proposed['weekly_hours']
                    merged['schedule']['weekday_hours']=[0,0,0,0,0]
                if body.get('accept_units',False) is True:
                    proposed=extracted['proposed_units']
                    hours=body.get('unit_hours',[])
                    if not isinstance(hours,list) or len(hours)!=len(proposed) or not proposed:
                        raise ValueError('Indique las horas de todas las unidades detectadas.')
                    validated=[]
                    for unit,amount in zip(proposed,hours):
                        try: n=float(amount)
                        except (ValueError,TypeError):raise ValueError('Las horas de cada unidad deben ser números válidos.') from None
                        if not math.isfinite(n) or n<=0 or n>1000:raise ValueError('Horas incorrectas en '+unit['code'])
                        validated.append({**unit,'hours':round(n,2),'criteria_codes':[],
                                          'resources':'','instruments':''})
                    merged['units']=validated
                if body.get('accept_feoe_criteria',False) is True:
                    feoe=extracted['proposed_feoe_criteria']
                    if not feoe:raise ValueError('No se han localizado CE FEOE inequívocos en el documento.')
                    merged['schedule']['feoe_criteria_codes']=[item['code'] for item in feoe]
                merged['source_type']='import'
                merged['import_info']={'programming_id':pid,'filename':program['filename'],
                                       'applied_fields':chosen,'source_type':'documento_importado'}
                result=program_builder.save(d,program['module_id'],merged)
                data.log(d,'programming_full_content_applied','programming',pid,
                         {'mapped_fields':chosen,'sections':len(extracted['sections']),
                          'hours_imported':body.get('accept_document_hours',False) is True,
                          'units_imported':body.get('accept_units',False) is True,
                          'feoe_proposed_imported':body.get('accept_feoe_criteria',False) is True})
            return self.send({'ok':True,'saved_fields':chosen,
                              'sections_preserved':len(extracted['sections']) if body.get('keep_source_sections',True) else 0,
                              'module_id':program['module_id'],'diagnosis':result['diagnosis']})
        if path=='/api/programmings/analyze':
            with data.connect() as d:
                program=must_row(d,'SELECT * FROM programmings WHERE id=?',(int(body['programming_id']),))
                result=logic.analyze_program(program['extracted_text'])
                data.log(d,'programming_analyzed','programming',program['id'],{'model':result['model'],'outcomes_proposed':len(result['outcomes'])})
            return self.send(result)
        if path=='/api/programmings/apply':
            mid=int(body['module_id']);out=body.get('outcomes',[])
            with data.connect() as d:
                must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                count=apply_extraction(d,mid,out)
                if body.get('source_url'):
                    source=str(body['source_url'])
                    if not source.startswith(('https://www.boe.es/diario_boe/txt.php?id=BOE-A-',)):
                        raise ValueError('La referencia de la fuente debe pertenecer al BOE.')
                    data.log(d,'official_curriculum_approved_by_teacher','module',mid,
                        {'source_url':source,'consulted_at':body.get('consulted_at'),
                         'teacher_approved':True,'criteria_saved':count})
            return self.send({'ok':True,'criteria_saved':count})
        if path=='/api/exams/generate':
            with data.connect() as d:
                title,kind,total,slots=create_exam(d,body)
                difficulty=str(body.get('difficulty','medio')).strip().lower()
                if difficulty not in ('bajo','medio','alto'):
                    raise ValueError('Seleccione nivel de dificultad bajo, medio o alto.')
                try: model_count=int(body.get('model_count',1))
                except (TypeError,ValueError):raise ValueError('El número de modelos no es válido.')
                if not 1<=model_count<=6:raise ValueError('Se permiten entre 1 y 6 modelos.')
                selected_programming=body.get('programming_id')
                if selected_programming in ('',None):
                    programrow=d.execute('SELECT id FROM programmings WHERE module_id=? ORDER BY id DESC LIMIT 1',(int(body['module_id']),)).fetchone()
                    selected_programming=programrow['id'] if programrow else None
                else:
                    selected_programming=int(selected_programming)
                    must_row(d,'SELECT id FROM programmings WHERE module_id=? AND id=?',(int(body['module_id']),selected_programming))
                source_map,materials_used=materiales.retrieve_for_slots(d,int(body['module_id']),slots,selected_programming)
                module_materials=d.execute('SELECT COUNT(*) FROM materials WHERE module_id=? AND active=1',(int(body['module_id']),)).fetchone()[0]
                if module_materials and not materials_used:
                    raise ValueError('Existen materiales activos de otra programación. Seleccione la programación adecuada o desactive el material.')
                if materials_used and body.get('authorize_external_transfer') is not True:
                    raise ValueError('Autorice expresamente el envío de los pasajes al proveedor de IA.')
                models,bank,model=logic.build_exam_models(title,kind,total,slots,model_count,difficulty,
                                           body.get('instructions',''),source_map)
                header=validate_header(body)
                # Un único COMMIT atómico tras generar y validar íntegramente todo el banco.
                d.execute('''INSERT INTO exam_batches(module_id,title,difficulty,model_count,questions_per_model,bank_size,created_at,ai_model)
                  VALUES(?,?,?,?,?,?,?,?)''',(int(body['module_id']),title,difficulty,model_count,len(slots),len(bank),data.now(),model))
                batch_id=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                bank_item_ids={}
                for question in bank:
                    fingerprint=logic.question_fingerprint(question['prompt'])
                    d.execute('''INSERT INTO question_bank_items(batch_id,criterion_id,kind,prompt,fingerprint,
                        options_json,correct_option,ideal_answer,rubric_json,source_refs_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''',(batch_id,question['criterion_id'],question['kind'],
                        question['prompt'],fingerprint,json.dumps(question['options'],ensure_ascii=False),
                        question['correct_option'],question['ideal_answer'],json.dumps(question['rubric'],ensure_ascii=False),
                        json.dumps(question['source_refs'],ensure_ascii=False)))
                    bank_item_ids[fingerprint]=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                ids=[]
                for k,questions in enumerate(models):
                    variant_label=chr(ord('A')+k)
                    name=title+(' · Modelo '+variant_label if model_count>1 else '')
                    d.execute('''INSERT INTO exams(module_id,title,kind,total_points,instructions,created_at,status,ai_model,
                      source_mode,batch_id,variant_label,difficulty,center_name,exam_date,duration_minutes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (int(body['module_id']),name,kind,total,str(body.get('instructions','')),
                       data.now(),'ready',model,'materials' if materials_used else 'criteria',batch_id,variant_label,difficulty,
                       header['center_name'],header['exam_date'],header['duration_minutes']))
                    eid=d.execute('SELECT last_insert_rowid()').fetchone()[0];ids.append(eid)
                    if materials_used:
                        d.executemany('INSERT INTO exam_materials(exam_id,material_id) VALUES(?,?)',
                                      [(eid,m['id']) for m in materials_used])
                    for q in questions:
                        bid=bank_item_ids[logic.question_fingerprint(q['prompt'])]
                        d.execute('''INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points,
                            options_json,correct_option,ideal_answer,rubric_json,source_refs_json,bank_item_id)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (eid,q['criterion_id'],q['number'],q['kind'],q['prompt'],q['points'],
                             json.dumps(q['options'],ensure_ascii=False),q['correct_option'],q['ideal_answer'],
                             json.dumps(q['rubric'],ensure_ascii=False),json.dumps(q['source_refs'],ensure_ascii=False),bid))
                        d.execute('UPDATE question_bank_items SET assigned_variant=? WHERE id=?',(variant_label,bid))
                    data.log(d,'exam_generated','exam',eid,{'batch_id':batch_id,'difficulty':difficulty,
                       'variant':variant_label,'model':model,'questions':len(questions),'criteria':body['criteria_ids']})
                data.log(d,'exam_bank_generated','exam_batch',batch_id,{'model_count':model_count,
                     'bank_size':len(bank),'questions_per_model':len(slots),'exam_ids':ids,
                     'materials':[m['id'] for m in materials_used]})
            return self.send({'id':ids[0],'exam_ids':ids,'batch_id':batch_id,
                              'model_count':model_count,'bank_size':len(bank)})
        if path=='/api/exams/manual/classify':
            mid=int(body['module_id'])
            with data.connect() as d:
                must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                proposal=manual_alignment.suggest(d,mid,body.get('questions',[]))
                data.log(d,'manual_exam_curricular_proposal','module',mid,
                         {'questions':len(proposal['assignments']),'needs_review':proposal['needs_review'],
                          'model':proposal['model']})
            return self.send(proposal)
        if path=='/api/exams/manual':
            # Permite pruebas y creación de exámenes manuales cuando no exista API.
            with data.connect() as d:
                mid=int(body['module_id']);must_row(d,'SELECT id FROM modules WHERE id=?',(mid,))
                qs=body.get('questions',[])
                if not qs or len(qs)>40:raise ValueError('Se requieren entre 1 y 40 preguntas.')
                title=str(body.get('title','')).strip()
                if not title:raise ValueError('Indique título de examen.')
                total=round(sum(float(x['points']) for x in qs),2)
                if total<=0 or total>100:raise ValueError('Puntos totales no válidos.')
                valid_catalogue={c['criterion_id']:c for c in manual_alignment.catalogue(d,mid)}
                if not valid_catalogue:raise ValueError('El módulo no tiene CE confirmados.')
                allocations=[manual_alignment.validate_allocations(q,valid_catalogue) for q in qs]
                if any('criteria_allocations' in q for q in qs) and not body.get('teacher_confirmed_curriculum'):
                    raise ValueError('Confirme como docente la correspondencia entre preguntas y RA/CE.')
                header=validate_header(body)
                d.execute('''INSERT INTO exams(module_id,title,kind,total_points,instructions,created_at,status,ai_model,center_name,exam_date,duration_minutes)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(mid,title,'manual',total,str(body.get('instructions','')),data.now(),'ready','',
                     header['center_name'],header['exam_date'],header['duration_minutes']))
                eid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                for i,q in enumerate(qs,1):
                    links=allocations[i-1]
                    primary=max(links,key=lambda x:x['weight_pct'])['criterion_id']
                    points=float(q['points'])
                    if points<=0:raise ValueError('Puntuaciones deben ser positivas')
                    kind=q.get('kind','desarrollo')
                    if kind not in ('test','desarrollo','problema'):raise ValueError('Tipo no permitido')
                    if kind=='problema' and (len(str(q.get('prompt','')).strip())<60 or not str(q.get('ideal_answer','')).strip()):
                        raise ValueError('El problema manual necesita enunciado completo y solución.')
                    if kind=='problema' and abs(sum(float(r.get('weight_pct',0)) for r in q.get('rubric',[]))-100)>.01:
                        raise ValueError('La rúbrica del problema debe sumar el 100 %.')
                    d.execute('''INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points,
                            options_json,correct_option,ideal_answer,rubric_json) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                        (eid,primary,i,kind,str(q['prompt']),points,
                         json.dumps(q.get('options',[]),ensure_ascii=False),str(q.get('correct_option','')),
                         str(q.get('ideal_answer','')),json.dumps(q.get('rubric',[]),ensure_ascii=False)))
                    qid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                    # El disparador creó una asignación por defecto; reemplazarla por la revisión docente.
                    d.execute('DELETE FROM exam_question_criteria WHERE question_id=?',(qid,))
                    d.executemany('''INSERT INTO exam_question_criteria
                        (question_id,criterion_id,weight_pct,confidence,rationale)
                        VALUES(?,?,?,?,?)''',[(qid,x['criterion_id'],x['weight_pct'],x['confidence'],x['rationale']) for x in links])
                data.log(d,'exam_manually_created','exam',eid,{'questions':len(qs),
                    'curricular_allocation_confirmed':True,
                    'criteria_by_question':[[{'criterion_id':x['criterion_id'],
                        'weight_pct':x['weight_pct'],'rationale':x['rationale']} for x in links]
                        for links in allocations]})
            return self.send({'id':eid})
        if path=='/api/submissions/upload':
            eid=int(fields['exam_id']);student_id=int(fields['student_id'])
            relevant=[(name,blob) for field,name,blob in files if field=='pages']
            with data.connect() as d:
                exam=must_row(d,'SELECT * FROM exams WHERE id=?',(eid,))
                student=must_row(d,'SELECT * FROM students WHERE id=? AND module_id=?',(student_id,exam['module_id']))
                sid,count=logic.ingest(d,exam,student,relevant)
            return self.send({'id':sid,'page_count':count})
        if path=='/api/submissions/batch':
            eid=int(fields['exam_id'])
            incoming=[(name,blob) for field,name,blob in files if field=='archive']
            if len(incoming)!=1 or not incoming[0][0].lower().endswith('.zip'):
                raise ValueError('Seleccione un único ZIP con carpetas por código de alumno.')
            raw=incoming[0][1]
            groups={}
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                entries=[inf for inf in z.infolist() if not inf.is_dir() and not inf.filename.startswith('__MACOSX/')]
                if len(entries)>1200 or sum(e.file_size for e in entries)>500*1024*1024:
                    raise ValueError('ZIP demasiado grande o con demasiados documentos.')
                for inf in entries:
                    path=Path(inf.filename)
                    if len(path.parts)!=2 or '..' in path.parts or path.parts[0].startswith('.'):
                        raise ValueError('El ZIP debe contener carpetas CÓDIGO_ALUMNO/archivo, sin rutas adicionales.')
                    code=path.parts[0];filename=path.name
                    if Path(filename).suffix.lower() not in logic.MIME:
                        raise ValueError(f'Formato no admitido en ZIP: {filename}')
                    blob=z.read(inf)
                    logic.check_signature(filename,blob)
                    groups.setdefault(code,[]).append((filename,blob))
            if not groups:raise ValueError('ZIP sin documentos.')
            # Los archivos por carpeta deben usar prefijo correlativo 001,002,...
            for code,group in groups.items():
                group.sort(key=lambda pair:[int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)',pair[0])])
                if sum(len(b) for _,b in group)>logic.MAX_BATCH:
                    raise ValueError(f'La entrega {code} supera el límite por alumno.')
            created=[]
            cleanup=[]
            try:
                with data.connect() as d:
                    exam=must_row(d,'SELECT * FROM exams WHERE id=?',(eid,))
                    module=must_row(d,'SELECT * FROM modules WHERE id=?',(exam['module_id'],))
                    registered={row['code']:row for row in d.execute('SELECT id,code FROM students WHERE module_id=?',(exam['module_id'],))}
                    missing=[code for code in groups if code not in registered]
                    if missing:
                        raise MissingStudentsError(exam['module_id'],missing)
                    for code,group in groups.items():
                        student=must_row(d,'SELECT * FROM students WHERE module_id=? AND code=?',(exam['module_id'],code))
                        if d.execute('SELECT id FROM submissions WHERE exam_id=? AND student_id=?',(eid,student['id'])).fetchone():
                            raise ValueError(f'Ya existe la entrega del alumno con código {code}. Ningún archivo se importó.')
                        if logic.folder_for(exam,student,module).exists():
                            raise ValueError(f'La carpeta de almacenamiento para {code} ya existe sin registro. Revise el disco.')
                    for code,group in groups.items():
                        student=must_row(d,'SELECT * FROM students WHERE module_id=? AND code=?',(exam['module_id'],code))
                        sid,count=logic.ingest(d,exam,student,group)
                        cleanup.append(logic.folder_for(exam,student,module))
                        created.append({'id':sid,'code':code,'pages':count})
            except Exception:
                for path_to_remove in cleanup:
                    shutil.rmtree(path_to_remove,ignore_errors=True)
                raise
            return self.send({'created':created})
        if path in ('/api/submissions/transcribe','/api/submissions/correct'):
            if body.get('authorize_external_transfer') is not True:
                raise ValueError('Debe confirmar el envío de las imágenes o textos al proveedor de IA elegido.')
            with data.connect() as d:
                s=must_row(d,'SELECT * FROM submissions WHERE id=?',(int(body['submission_id']),))
                if path.endswith('/transcribe'):
                    run_id,count=logic.transcribe(d,s)
                    result={'run_id':run_id,'segments':count}
                else:
                    count=logic.grade(d,s)
                    result={'questions':count}
            return self.send(result)
        if path=='/api/corrections/transcription':
            cid=int(body['correction_id']);txt=str(body.get('transcription',''))
            with data.connect() as d:
                c=must_row(d,'SELECT * FROM corrections WHERE id=?',(cid,))
                d.execute('''UPDATE corrections SET transcription=?,ai_score=NULL,teacher_score=NULL,
                 ai_feedback='',rubric_result_json='[]',needs_review=1,status='transcribed',validated_at=NULL WHERE id=?''',(txt,cid))
                d.execute('UPDATE submissions SET status=? WHERE id=?',('transcribed',c['submission_id']))
                data.log(d,'teacher_transcription_edited','correction',cid,{'previous_text':c['transcription'],'new_text':txt})
            return self.send({'ok':True})
        if path=='/api/corrections/validate':
            cid=int(body['correction_id']);score=float(body['score']);comment=str(body.get('comment',''))
            with data.connect() as d:
                c=must_row(d,'''SELECT c.*,q.points FROM corrections c
                       JOIN exam_questions q ON q.id=c.question_id WHERE c.id=?''',(cid,))
                if not (0<=score<=c['points']):raise ValueError('La nota excede el máximo de la pregunta.')
                if c['ai_score'] is not None and abs(score-c['ai_score'])>0.005 and not comment.strip():
                    raise ValueError('Cuando se modifica la nota de la IA, el docente debe justificar el cambio.')
                d.execute('''UPDATE corrections SET teacher_score=?,teacher_comment=?,status='validated',validated_at=?
                             WHERE id=?''',(score,comment,data.now(),cid))
                data.log(d,'teacher_grade_validated','correction',cid,
                         {'previous_score':c['teacher_score'],'ai_score':c['ai_score'],'validated_score':score,'comment':comment})
                left=d.execute('''SELECT COUNT(*) FROM corrections WHERE submission_id=? AND run_id=? AND status!='validated' ''',
                               (c['submission_id'],c['run_id'])).fetchone()[0]
                if left==0:d.execute('UPDATE submissions SET status=? WHERE id=?',('validated',c['submission_id']))
            return self.send({'ok':True,'pending_questions':left})
        raise ValueError('Ruta POST desconocida.')

    def print_html(self,src):
        raw=src.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Cache-Control','private, no-store')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)

    def do_GET(self):self.dispatch()
    def do_POST(self):self.dispatch()
    def dispatch(self):
        try:
            if self.headers.get('Host','').split(':')[0] not in ('127.0.0.1','localhost','[::1]'):
                raise PermissionError('Host no autorizado.')
            origin=self.headers.get('Origin','')
            if origin:
                p=urllib.parse.urlparse(origin)
                if p.hostname not in ('localhost','127.0.0.1','::1') or p.port!=self.server.server_port:
                    raise PermissionError('Origen de solicitud no autorizado.')
            self.route()
        except (BrokenPipeError,ConnectionResetError):pass
        except MissingStudentsError as ex:self.send({'error':str(ex),'code':'MISSING_STUDENTS','module_id':ex.module_id,'missing_students':ex.codes},409)
        except PermissionError as ex:self.send({'error':str(ex)},403)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError,sqlite3.IntegrityError,zipfile.BadZipFile) as ex:
            self.send({'error':str(ex)},400)
        except Exception as ex:
            # Error controlado sin exponer el contenido de documentos ni la clave API.
            print('Error interno EvaluaFP:',repr(ex),file=sys.stderr)
            self.send({'error':'Error interno; consulte la consola de ejecución.'},500)


def start():
    data.init()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    address=f'http://127.0.0.1:{server.server_port}/'
    print(f'EvalúaFP iniciado en el puerto local {server.server_port} (sesión protegida).')
    print(f'Datos locales: {data.DATA}')
    print(f'Copias locales: {data.BACKUPS}')
    return server,address

def open_interface(url):
    """Modo navegador, disponible solamente si el usuario lo solicita."""
    # os.startfile utiliza el navegador asociado a HTTP en Windows (sin WebView2).
    if os.name == 'nt':
        try:
            os.startfile(url+'?launch='+TOKEN)
            return True
        except OSError as exc:
            print(f'Windows no pudo abrir el navegador: {exc}', flush=True)
    try:
        return bool(webbrowser.open(url+'?launch='+TOKEN, new=2))
    except Exception as exc:
        print(f'El navegador no pudo iniciarse: {exc}', flush=True)
        return False


def run_desktop_window(url):
    """Abrir la ventana nativa del sistema (WebView2, WebKit o Qt).

    La importación deliberadamente ocurre en tiempo de ejecución para que
    --selftest no necesite una sesión gráfica y para conservar los modos alternativos.
    """
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            'Falta el componente pywebview. Recompile con las dependencias del sistema operativo correspondiente.'
        ) from exc

    window_title = 'EvalúaFP · Evaluación inteligente'
    webview.create_window(
        window_title, url+'?launch='+TOKEN,
        width=1390, height=900, min_size=(900, 650),
        resizable=True, confirm_close=False,
    )
    try:
        if sys.platform == 'win32':
            # Windows: conservar WebView2 y la barra de título azul marino.
            from desktop_caption import colorize_caption
            webview.start(func=lambda: colorize_caption(window_title), gui='edgechromium')
        elif sys.platform == 'darwin':
            # macOS: el motor Cocoa / WKWebView usa el WebKit del sistema.
            webview.start()
        elif sys.platform.startswith('linux'):
            # Linux: QtWebEngine, incluido en la distribución generada.
            webview.start(gui='qt')
        else:
            raise RuntimeError('Sistema operativo no admitido para la ventana nativa.')
    except Exception as exc:
        hints = {
            'win32': 'Compruebe Microsoft Edge WebView2 Runtime.',
            'darwin': 'Compruebe que la aplicación macOS está completa y dispone de permisos.',
        }
        hint = hints.get(sys.platform, 'Compruebe las bibliotecas gráficas Qt y el entorno de escritorio Linux.')
        raise RuntimeError(f'No se ha podido abrir EvalúaFP. {hint} Detalle técnico: {exc}') from exc


def main():
    server, url = start()
    try:
        if '--browser' in sys.argv:
            # Modo alternativo explícito. Nunca se activa por defecto.
            print('Modo navegador solicitado.', flush=True)
            if not open_interface(url):
                print('Abra manualmente la dirección anterior.', flush=True)
            while True:
                threading.Event().wait(3600)
        elif '--no-browser' in sys.argv:
            print('Servidor local sin ventana.', flush=True)
            while True:
                threading.Event().wait(3600)
        else:
            # Inicio normal, incluido EvaluaFP.exe: ventana propia.
            print('Abriendo ventana de escritorio EvalúaFP...', flush=True)
            run_desktop_window(url)
            print('Ventana cerrada. Finalizando servidor local.', flush=True)
    except KeyboardInterrupt:
        print('Cerrando EvalúaFP...', flush=True)
    finally:
        server.shutdown()
        server.server_close()


def selftest():
    """Prueba de arranque local para comprobar el EXE empaquetado sin abrir el navegador."""
    if not (WEB / 'index.html').is_file() or not (WEB / 'app.js').is_file() or not (WEB / 'favicon.ico').is_file():
        raise RuntimeError('La interfaz HTML no se ha incluido en el ejecutable.')
    data.init()
    # Asegura que también funciona la exportación PDF del EXE.
    import exam_pdf
    if not callable(getattr(exam_pdf, 'build_exam_pdf',None)):
        raise RuntimeError('Falta el módulo de generación PDF.')
    # Comprobar también los generadores reales incluidos en el EXE.
    import exportaciones
    import xlsxwriter
    import xlwt
    if not callable(getattr(exportaciones,'export_excel',None)):
        raise RuntimeError('La exportación Excel no está incluida en el EXE.')
    # Asegura que PyInstaller ha incluido la biblioteca de interfaz nativa.
    if os.name == 'nt' or getattr(sys, 'frozen', False):
        try:
            import webview
            if not callable(getattr(webview, 'create_window', None)):
                raise RuntimeError('pywebview no proporciona create_window.')
        except Exception as exc:
            raise RuntimeError('Falta pywebview en la distribución de escritorio.') from exc
    with data.connect() as db:
        if db.execute('SELECT 1').fetchone()[0] != 1:
            raise RuntimeError('SQLite no responde.')
        if db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='modules'").fetchone()[0] != 1:
            raise RuntimeError('No se ha inicializado el esquema de SQLite.')
    print('PRUEBA DE ARRANQUE CORRECTA', flush=True)


if __name__ == '__main__':
    if getattr(sys,'frozen',False) and os.name=='nt':
        # PyInstaller --windowed sets stdout/stderr to None on Windows.
        # Redirect them before the first print: otherwise the EXE would quit silently.
        if sys.stdout is None or sys.stderr is None:
            log_stream = (data.DATA / 'registro_aplicacion.log').open('a', encoding='utf-8', buffering=1)
            if sys.stdout is None: sys.stdout = log_stream
            if sys.stderr is None: sys.stderr = log_stream
        try:
            if '--selftest' in sys.argv:
                selftest()
            else:
                main()
        except Exception as exc:
            import traceback
            logfile=data.DATA/'errores_inicio.log'
            logfile.write_text(traceback.format_exc(),encoding='utf-8')
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(None,
                    'EvalúaFP no ha podido iniciarse.\n\nDetalle: '+str(exc)[:400]+
                    '\n\nSe ha guardado un diagnóstico en:\n'+str(logfile),
                    'EvalúaFP - Error de inicio',0x10)
            except Exception:pass
            raise
    else:
        if '--selftest' in sys.argv:
            selftest()
        else:
            main()
