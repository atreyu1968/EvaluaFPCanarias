"""Exportación A4 de modelos de examen y solucionarios. No usa navegador ni API externa."""
from __future__ import annotations
import html
import io
import re
import zipfile
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable, HRFlowable, KeepTogether

import database as dbm

NAVY=colors.HexColor('#102B45')
BLUE=colors.HexColor('#255E7B')
MUTED=colors.HexColor('#5D6F7C')
PAGE_W,PAGE_H=A4
CONTENT_W=PAGE_W-36*mm

def esc(value):
    return html.escape(str(value if value is not None else ''), quote=False).replace('\n','<br/>')

STYLES={
 'heading':ParagraphStyle('efp_title',fontName='Helvetica-Bold',fontSize=15,leading=19,textColor=NAVY,spaceAfter=8),
 'subhead':ParagraphStyle('efp_subhead',fontName='Helvetica-Bold',fontSize=10,leading=15,textColor=NAVY,spaceAfter=3),
 'body':ParagraphStyle('efp_body',fontName='Helvetica',fontSize=9.5,leading=14,spaceAfter=7),
 'small':ParagraphStyle('efp_small',fontName='Helvetica',fontSize=8.5,leading=12,textColor=MUTED,spaceAfter=4),
 'meta':ParagraphStyle('efp_meta',fontName='Helvetica',fontSize=8.3,leading=13,spaceAfter=0),
 'right':ParagraphStyle('efp_right',fontName='Helvetica-Bold',fontSize=9,leading=13,textColor=BLUE),
}

class AnswerLines(Flowable):
    """Renglones de trabajo, divididos en grupos para no cortar la paginación."""
    def __init__(self,count=8):
        super().__init__();self.count=count;self.width=CONTENT_W;self.height=count*19+4
    def draw(self):
        self.canv.setStrokeColor(colors.HexColor('#BECBD5'));self.canv.setLineWidth(.45)
        for i in range(self.count):
            y=self.height-19*(i+1)
            self.canv.line(0,y,self.width,y)


def on_page(canvas,doc,exam,module,solutions):
    canvas.saveState()
    canvas.setStrokeColor(NAVY);canvas.setLineWidth(1.1)
    canvas.line(18*mm,PAGE_H-17*mm,PAGE_W-18*mm,PAGE_H-17*mm)
    canvas.setFont('Helvetica-Bold',8)
    canvas.setFillColor(NAVY)
    canvas.drawString(18*mm,PAGE_H-14*mm,'EVALÚAFP · '+ ('SOLUCIONARIO DOCENTE' if solutions else 'EXAMEN DEL ALUMNADO'))
    canvas.setFont('Helvetica',8);canvas.setFillColor(MUTED)
    footer=f'{module["name"]} · Modelo {exam["variant_label"]} · Página {doc.page}'
    canvas.drawString(18*mm,13*mm,footer[:90])
    canvas.drawRightString(PAGE_W-18*mm,13*mm,'EvalúaFP Local')
    canvas.restoreState()


def _table(items):
    rows=[]
    for a,b in items:
        rows.append([Paragraph(esc(a),STYLES['small']),Paragraph(esc(b),STYLES['meta'])])
    t=Table(rows,colWidths=[36*mm,CONTENT_W-36*mm],hAlign='LEFT',splitByRow=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5),
                           ('TOPPADDING',(0,0),(-1,-1),3),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#CCD7E0'))]))
    return t


def build_exam_pdf(db, exam_id, solutions=False):
    from app import exam_detail  # evita ciclo de importación durante arranque
    item=exam_detail(db,exam_id)
    exam=item['exam']
    module=db.execute('SELECT * FROM modules WHERE id=?',(exam['module_id'],)).fetchone()
    if not module:raise ValueError('Módulo no encontrado.')
    module=dict(module)
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,topMargin=23*mm,bottomMargin=21*mm,
                          leftMargin=18*mm,rightMargin=18*mm,
                          title=exam['title']+(' - Solucionario' if solutions else ''),
                          author='EvalúaFP Local - Francisco Javier Gonzalez Rolo')
    story=[]
    center=(exam.get('center_name') or '').strip()
    story.append(Paragraph(esc(center or 'Centro educativo: ____________________________'),STYLES['subhead']))
    story.append(Paragraph(esc(exam['title']),STYLES['heading']))
    criteria=[];outcomes=[]
    for q in item['questions']:
        if q['criterion_code'] not in criteria:criteria.append(q['criterion_code'])
        if q['outcome_code'] not in outcomes:outcomes.append(q['outcome_code'])
    dt=exam.get('exam_date') or ''
    if dt:
        try:
            from datetime import date
            dt=date.fromisoformat(dt).strftime('%d/%m/%Y')
        except ValueError:pass
    details=[('Curso académico',module.get('academic_year','')),
             ('Enseñanza / grupo',f'{module.get("cycle","")} · {module.get("group_name","")}'),
             ('Módulo profesional',module['name']),
             ('RA / CE',', '.join(outcomes)+' / '+', '.join(criteria)),
             ('Modelo / dificultad',f'{exam.get("variant_label","A")} · {exam.get("difficulty","medio").capitalize()}'),
             ('Duración / puntuación',f'{exam.get("duration_minutes",60)} minutos · {exam["total_points"]:g} puntos'),
             ('Fecha de la prueba',dt or '________________')]
    story.append(_table(details));story.append(Spacer(1,7*mm))
    if not solutions:
        story.append(Paragraph('Nombre y apellidos: _____________________________________________________________',STYLES['body']))
        story.append(Paragraph('Número / código: ______________________  Firma: __________________________',STYLES['body']))
    else:
        story.append(Paragraph('SOLUCIONARIO Y RÚBRICAS · DOCUMENTO EXCLUSIVO DEL DOCENTE',STYLES['subhead']))
    instructions=(exam.get('instructions') or '').strip()
    if instructions:
        story.append(Paragraph('<b>Indicaciones:</b> '+esc(instructions),STYLES['body']))
    story.append(HRFlowable(width='100%',thickness=1,color=BLUE,spaceBefore=4,spaceAfter=11))
    for q in item['questions']:
        is_problem=q['kind']=='problema'
        title=('Problema práctico' if is_problem else 'Pregunta')+f' {q["number"]} · {q["points"]:g} puntos · {q["criterion_code"]}'
        # El enunciado y su encabezado viajan juntos a la página siguiente.
        story.append(KeepTogether([Paragraph(esc(title),STYLES['subhead']),
                                   Paragraph(esc(q['prompt']),STYLES['body'])]))
        if q['kind']=='test':
            for choice in q['options']:
                story.append(Paragraph('[  ]  '+esc(choice),STYLES['body']))
        if solutions:
            if q['kind']=='test':
                story.append(Paragraph('<b>Opción correcta:</b> '+esc(q['correct_option']),STYLES['body']))
            story.append(Paragraph('<b>Solución desarrollada:</b> '+esc(q.get('ideal_answer','')),STYLES['body']))
            rub_rows=[['Indicador de la rúbrica','Peso','Máximo']]
            for rubric in q.get('rubric',[]):
                weight=float(rubric.get('weight_pct',0))
                rub_rows.append([Paragraph(esc(rubric.get('criterion','')),STYLES['meta']),
                                  f'{weight:g} %',f'{q["points"]*weight/100:.2f}'])
            table=Table(rub_rows,colWidths=[CONTENT_W-56*mm,23*mm,33*mm],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7EFF5')),
              ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),8),
              ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#CAD6E0')),
              ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story.append(table)
        elif q['kind']!='test':
            story.append(Paragraph('Espacio de resolución'+(' y operaciones:' if is_problem else ':'),STYLES['small']))
            # Renglones divididos: cada bloque puede moverse a la página siguiente sin cortarse.
            for _ in range(3 if is_problem else 1):story.append(AnswerLines(7))
        story.append(Spacer(1,6*mm))
    doc.build(story,onFirstPage=lambda c,d:on_page(c,d,exam,module,solutions),
              onLaterPages=lambda c,d:on_page(c,d,exam,module,solutions))
    return buffer.getvalue()


def build_batch_zip(db,batch_id,teacher_only=False):
    batch=db.execute('SELECT id,title,model_count FROM exam_batches WHERE id=?',(batch_id,)).fetchone()
    if not batch:raise ValueError('No se encuentra el conjunto de modelos.')
    rows=db.execute('SELECT id,variant_label FROM exams WHERE batch_id=? ORDER BY variant_label',(batch_id,)).fetchall()
    if len(rows)!=batch['model_count']:raise ValueError('El conjunto no contiene todos los modelos esperados.')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zipf:
        for row in rows:
            label=str(row['variant_label'])
            if teacher_only:
                zipf.writestr(f'Modelo_{label}_soluciones_y_rubrica.pdf',build_exam_pdf(db,row['id'],True))
            else:
                zipf.writestr(f'Modelo_{label}_alumnado.pdf',build_exam_pdf(db,row['id'],False))
        zipf.writestr('LEAME.txt','EvalúaFP Local - Modelos del examen\n'+str(batch['title'])+
                      '\nEste ZIP contiene exclusivamente '+('SOLUCIONES Y RÚBRICAS para el profesorado.' if teacher_only else 'exámenes sin soluciones para el alumnado.')+'\n'+
                      'Revise las preguntas y las soluciones generadas con IA antes de distribuirlas.\n')
    return buffer.getvalue()
