"""Informe de evaluación individual, generado exclusivamente a partir de SQLite."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether

import evaluacion


def report(d,module_id,student_id):
    data=evaluacion.summary(d,module_id,student_id)
    student=data['students'][0]
    module=d.execute('SELECT name,academic_year,cycle,group_name FROM modules WHERE id=?',(module_id,)).fetchone()
    if not module:raise ValueError('Módulo no encontrado.')
    buf=io.BytesIO()
    document=SimpleDocTemplate(buf,pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,
                               topMargin=18*mm,bottomMargin=19*mm,title='Informe de evaluación EvalúaFP')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HeadFP',parent=styles['Heading1'],fontSize=16,leading=21,textColor=colors.HexColor('#102b45'),spaceAfter=12))
    styles.add(ParagraphStyle(name='BodyFP',parent=styles['Normal'],fontSize=9,leading=13,spaceAfter=6))
    styles.add(ParagraphStyle(name='SmallFP',parent=styles['Normal'],fontSize=8,leading=11))
    story=[Paragraph('EVALÚAFP · INFORME JUSTIFICATIVO',styles['HeadFP']),
           Paragraph(escape(f'{module["name"]} · {module["academic_year"]} · {module["cycle"]}'),styles['BodyFP']),
           Paragraph(f'<b>Alumno/a:</b> {escape(student["name"])} ({escape(student["code"])})',styles['BodyFP'])]
    closure=student.get('closure')
    status=('CALIFICACIÓN FINAL VALIDADA' if closure and closure['current']
            else 'CIERRE ANTERIOR OBSOLETO: REQUIERE NUEVA VALIDACIÓN' if closure else 'BORRADOR · NO VALIDADO')
    grade=(f'{closure["score"]:g} / 10' if closure and closure['current'] else
           f'{student["final_score"]:g} / 10 (calculable, no validada)' if student['final_score'] is not None else 'Pendiente')
    story.append(Paragraph(f'<b>Estado:</b> {status} &nbsp;&nbsp; <b>Nota:</b> {grade}',styles['BodyFP']))
    if closure and closure['current']:
        story.append(Paragraph(f'<b>Validada el:</b> {escape(closure["validated_at"])}',styles['BodyFP']))
        story.append(Paragraph('<b>Justificación docente:</b> '+escape(closure['teacher_justification']),styles['BodyFP']))
    if data['warnings']:
        story.append(Paragraph('<b>Incidencias de la programación / evaluación:</b>',styles['BodyFP']))
        for note in data['warnings']:
            story.append(Paragraph('• '+escape(note),styles['SmallFP']))
    story.append(Spacer(1,7*mm))
    story.append(Paragraph('Resumen por trimestres',styles['Heading2']))
    trows=[['Evaluación','Nota provisional','Evidencias']]
    for t in student['terms']:
        trows.append([f'{t["term"]}.ª',str(t['score']) if t['score'] is not None else '—',f'{t["completed"]} de {t["expected"]}'])
    story.append(_table(trows,[48*mm,58*mm,56*mm]))
    story.append(Spacer(1,5*mm))
    story.append(Paragraph('Resultados de aprendizaje',styles['Heading2']))
    ra=[['RA','Nota','CE superados','Estado']]
    for r in student['outcomes']:
        ra.append([r['code'],str(r['score']) if r['score'] is not None else '—',
                   f'{r["criteria_passed_pct"]:.0f} %','Superado' if r['passed'] else 'Pendiente'])
    story.append(_table(ra,[33*mm,33*mm,51*mm,45*mm]))
    story.append(Spacer(1,5*mm))
    story.append(Paragraph('Detalle por criterios de evaluación',styles['Heading2']))
    ce=[['RA / CE','Nota','Peso evidenciado','Completo']]
    for c in student['criteria']:
        ce.append([f'{c["ra_code"]} / {c["code"]}',str(c['score']) if c['score'] is not None else '—',
                  f'{c["weight_covered"]:g} %','Sí' if c['complete'] else 'No'])
    story.append(_table(ce,[53*mm,32*mm,48*mm,29*mm]))
    story.append(Spacer(1,5*mm))
    story.append(Paragraph('Evidencias de los instrumentos',styles['Heading2']))
    ins={i['id']:i for i in data['instruments']}
    cecodes={c['id']:c['code'] for c in data['criteria']}
    evidence=[s for s in data['scores'] if s['student_id']==int(student_id)]
    if evidence:
        for e in evidence:
            i=ins.get(e['instrument_id'])
            if not i:continue
            chunk=[Paragraph(f'<b>{escape(i["title"])} ({escape(i["kind"])}) · {escape(cecodes.get(e["criterion_id"],"CE"))}</b>: '
                  f'{e["score"]:g} / 10 · {escape(e["origin"])}',styles['BodyFP'])]
            if e['comment']:chunk.append(Paragraph('Justificación / observación: '+escape(e['comment']),styles['SmallFP']))
            story.append(KeepTogether(chunk))
    else:story.append(Paragraph('No hay calificaciones registradas.',styles['BodyFP']))
    story.append(Spacer(1,7*mm))
    story.append(Paragraph('Evaluación asistida: toda corrección automática de examen requiere validación docente. '
                           'La nota provisional no equivale al cierre oficial de evaluación.',styles['SmallFP']))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#687889'))
        canvas.drawString(18*mm,12*mm,'EvalúaFP Local · Registro docente de evaluación')
        canvas.drawRightString(192*mm,12*mm,f'Página {doc.page}')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()


def _table(rows,widths):
    table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#102b45')),
       ('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f6fa')]),
       ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
       ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
       ('LINEBELOW',(0,-1),(-1,-1),.3,colors.HexColor('#dce6ed'))]))
    return table
