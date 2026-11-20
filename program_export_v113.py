"""Exportación con portada, índice y Gantt de la programación editable de FP."""
from __future__ import annotations
from datetime import date
from html import escape
import io
import calendar

MONTH_NAMES = ('enero','febrero','marzo','abril','mayo','junio',
               'julio','agosto','septiembre','octubre','noviembre','diciembre')
TABLE_SECTIONS = {
 'Resultados de aprendizaje y criterios','Secuenciación de unidades',
 'Temporalización y calendario escolar','Formación en empresa (FEOE)',
 'Instrumentos y recursos por unidad','Instrumentos, evidencias y recursos por evaluación',
 'Matriz FEOE: CE, tareas y evidencias','Actividades complementarias y extraescolares',
}


def _n2(v):
    """Presentational rounding (keeps raw arithmetic in schedule_engine)."""
    return format(float(v), '.2f').replace('.', ',')


def _month_label(ym):
    y,m = ym.split('-')
    return f'{MONTH_NAMES[int(m)-1].capitalize()} {y}'


def _date_label(iso):
    dt = date.fromisoformat(iso)
    return dt.strftime('%d/%m')


def _month_groups(weeks):
    result=[]
    for index,w in enumerate(weeks):
        ym=w['start'][:7]
        if result and result[-1][0]==ym:
            result[-1]=(ym,result[-1][1],index)
        else:
            result.append((ym,index,index))
    return result


def _short(s, maxlen=40):
    s = str(s or '')
    return s if len(s) <= maxlen else s[:maxlen-1]+'…'


def _months(plan):
    weeks = plan.get('gantt_weeks', [])
    result = []
    for w in weeks:
        stamp = w['start'][:7]
        if stamp not in result:
            result.append(stamp)
    return result


def _overlaps(a,b,x,y):
    return bool(a and b and x and y and a <= y and b >= x)


def export(result, sections, module_id, fmt):
    if fmt == 'docx':
        return _docx(result, sections, module_id)
    return _pdf(result, sections, module_id)


def _docx(result, sections, module_id):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_ORIENT, WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.1);sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.1);sec.right_margin = Cm(2.1)
    normal = doc.styles['Normal']
    normal.font.name = 'Aptos'
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    m=result['module'];draft=result['draft'];plan=result['calendar_plan']
    cover=doc.add_paragraph()
    cover.paragraph_format.space_before=Pt(155)
    cover.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=cover.add_run('PROGRAMACIÓN DIDÁCTICA')
    r.bold=True;r.font.size=Pt(23);r.font.color.rgb=RGBColor(15,57,84)
    for line in [m['name'],m['cycle'], 'Curso académico '+m['academic_year'],
                 draft['center'] or 'Centro pendiente de indicar',
                 'Profesorado: '+(draft['teacher'] or 'Pendiente de indicar')]:
        p=doc.add_paragraph(line);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if line == m['name']:
            for run in p.runs:run.bold=True;run.font.size=Pt(17)
    p=doc.add_paragraph('BORRADOR · Documento pendiente de revisión y aprobación docente')
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()
    doc.add_heading('Índice de contenidos',0)
    for i,(heading,_) in enumerate(sections,1):
        doc.add_paragraph(f'{i}. {heading}',style='List Number')
    doc.add_paragraph(f'{len(sections)+1}. Diagrama de Gantt de la temporalización',style='List Number')
    p=doc.add_paragraph('La paginación se actualiza en el editor tras las modificaciones del docente.')
    p.style='Caption'
    doc.add_page_break()
    for i,(heading,fields) in enumerate(sections,1):
        doc.add_heading(f'{i}. {heading}',level=1)
        if not fields: doc.add_paragraph('Pendiente de completar.')
        if heading in TABLE_SECTIONS and fields:
            tabinfo=doc.add_table(rows=1,cols=2)
            tabinfo.style='Light Shading Accent 1'
            tabinfo.rows[0].cells[0].text='Concepto / unidad / RA-CE'
            tabinfo.rows[0].cells[1].text='Información programada'
            trpr=tabinfo.rows[0]._tr.get_or_add_trPr()
            tblhdr=OxmlElement('w:tblHeader');tblhdr.set(qn('w:val'),'true');trpr.append(tblhdr)
            for key,value in fields:
                cells=tabinfo.add_row().cells
                cells[0].text=str(key)
                cells[1].text=str(value or '[Pendiente de completar]')
            doc.add_paragraph('')
        else:
            for key,value in fields:
                p=doc.add_paragraph()
                p.add_run(str(key)+': ').bold=True
                p.add_run(str(value or '[Pendiente de completar]'))
    # A dedicated landscape A4 page keeps the entire monthly Gantt table readable.
    gantt_sec=doc.add_section(WD_SECTION.NEW_PAGE)
    gantt_sec.orientation=WD_ORIENT.LANDSCAPE
    gantt_sec.page_width=Cm(29.7);gantt_sec.page_height=Cm(21.0)
    gantt_sec.left_margin=Cm(1.5);gantt_sec.right_margin=Cm(1.5)
    gantt_sec.top_margin=Cm(1.6);gantt_sec.bottom_margin=Cm(1.6)
    doc.add_heading(f'{len(sections)+1}. Diagrama de Gantt de la temporalización',level=1)
    months = _months(plan)
    if not months: doc.add_paragraph('El diagrama se generará al indicar el calendario lectivo y las unidades.')
    else:
        doc.add_paragraph('En Word el Gantt se muestra agrupado por MES Y AÑO; las columnas no representan horas ni semanas. La escala semanal detallada, con fechas de inicio y fin, se incluye en el PDF.',style='Caption')
        tab = doc.add_table(rows=1,cols=len(months)+2)
        tab.style='Table Grid';tab.alignment=WD_TABLE_ALIGNMENT.CENTER
        tab.autofit = False
        width_first=Cm(3.4)
        width_hours=Cm(1.55)
        available=26.7-3.4-1.55
        width_other=Cm(available/max(len(months),1))
        for j,col in enumerate(tab.columns):col.width=width_first if j==0 else width_hours if j==1 else width_other
        labels=['Unidad didáctica','Horas (h)']+[f'{int(x[5:]):02d}/{x[:4]}' for x in months]
        for col,label in enumerate(labels):
            tab.rows[0].cells[col].text=label
            tab.rows[0].cells[col].width=width_first if col==0 else width_hours if col==1 else width_other
        trpr=tab.rows[0]._tr.get_or_add_trPr()
        tblhdr=OxmlElement('w:tblHeader');tblhdr.set(qn('w:val'),'true');trpr.append(tblhdr)
        for u in plan['units']:
            cells=tab.add_row().cells
            cells[0].text=_short(u['code']+' '+u['title'],29)
            cells[1].text=_n2(u['hours'])+' h'
            for j,cell in enumerate(cells):cell.width=width_first if j==0 else width_hours if j==1 else width_other
            for j,month in enumerate(months):
                month_start=date.fromisoformat(month+'-01')
                month_end=date(month_start.year,month_start.month,calendar.monthrange(month_start.year,month_start.month)[1])
                if _overlaps(u['start'],u['end'],month_start.isoformat(),month_end.isoformat()):
                    color={1:'317FA8',2:'1F9D99',3:'7268AD'}.get(int(u['term']),'317FA8')
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),color)
                    cells[j+2]._tc.get_or_add_tcPr().append(shade)
        if plan['feoe']['start'] and plan['feoe']['end']:
            cells=tab.add_row().cells;cells[0].text='FEOE (propuesta)';cells[1].text='—'
            for j,cell in enumerate(cells):cell.width=width_first if j==0 else width_hours if j==1 else width_other
            for j,month in enumerate(months):
                st=date.fromisoformat(month+'-01')
                en=date(st.year,st.month,calendar.monthrange(st.year,st.month)[1])
                if _overlaps(plan['feoe']['start'],plan['feoe']['end'],st.isoformat(),en.isoformat()):
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'64A542')
                    cells[j+2]._tc.get_or_add_tcPr().append(shade)
    doc.add_paragraph('Leyenda: azul = 1.ª evaluación; verde azulado = 2.ª; morado = 3.ª; verde = FEOE. Cada celda coloreada muestra un intervalo del calendario, NO las horas impartidas en ese mes. Las horas por unidad se expresan en la segunda columna.',style='Caption')
    sec.footer.paragraphs[0].text='EvalúaFP 1.1.7 · BORRADOR pendiente de validación institucional'
    buf=io.BytesIO();doc.save(buf)
    return buf.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document',f'EvaluaFP_Programacion_{module_id}.docx'


def _pdf(result, sections, module_id):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, A3, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                    PageBreak, NextPageTemplate, Table, TableStyle, KeepTogether)
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_CENTER
    from pathlib import Path
    import os

    FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if os.path.isfile(FONT) and 'EFDejaVu' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('EFDejaVu',FONT))
        pdfmetrics.registerFont(TTFont('EFDejaVuBold',BOLD))
        pdfmetrics.registerFontFamily('EFDejaVu',normal='EFDejaVu',bold='EFDejaVuBold')
    fn='EFDejaVu' if 'EFDejaVu' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
    bold='EFDejaVuBold' if fn=='EFDejaVu' else 'Helvetica-Bold'
    W,H=A4; navy=colors.HexColor('#143854');teal=colors.HexColor('#1D8E90')
    small=ParagraphStyle('small',fontName=fn,fontSize=8.6,leading=13.3,spaceAfter=8)
    title=ParagraphStyle('title',fontName=bold,fontSize=21,leading=28,alignment=TA_CENTER,textColor=navy,spaceAfter=19)
    body=ParagraphStyle('body',fontName=fn,fontSize=9.0,leading=14.7,spaceAfter=9,splitLongWords=True)
    h1=ParagraphStyle('h1',fontName=bold,fontSize=13,leading=19,textColor=navy,spaceBefore=15,spaceAfter=11,keepWithNext=True)
    cap=ParagraphStyle('cap',fontName=fn,fontSize=8,leading=12,textColor=colors.HexColor('#597181'),spaceAfter=9)
    tocstyle=ParagraphStyle('toc',fontName=fn,fontSize=10,leading=18,leftIndent=20,firstLineIndent=-10)
    stream=io.BytesIO()
    class EFDoc(BaseDocTemplate):
        def __init__(self, buff):
            super().__init__(buff,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=54,bottomMargin=50)
            frame=Frame(42,50,W-84,H-104,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
            wide=landscape(A3)
            wide_frame=Frame(42,50,wide[0]-84,wide[1]-104,
                             leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
            self.addPageTemplates([
               PageTemplate(id='normal',frames=[frame],onPage=self.footer,pagesize=A4),
               PageTemplate(id='gantt',frames=[wide_frame],onPage=self.footer,pagesize=wide),
            ])
            self._toc_counter=0
        def beforeDocument(self):
            self._toc_counter=0
        def footer(self, canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#DFE7EC'))
            canvas.line(42,40,canvas._pagesize[0]-42,40)
            canvas.setFont(fn,8);canvas.setFillColor(colors.HexColor('#698192'))
            canvas.drawString(42,27,'EvalúaFP · BORRADOR pendiente de validación docente')
            canvas.drawRightString(canvas._pagesize[0]-42,27,str(doc.page))
            canvas.restoreState()
        def afterFlowable(self, flowable):
            if getattr(flowable,'_ef_toc_title',None):
                txt=flowable._ef_toc_title
                key=f'section{self._toc_counter}'
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry',(0,txt,self.page,key))
                self._toc_counter+=1
    doc=EFDoc(stream)
    m=result['module'];draft=result['draft'];plan=result['calendar_plan']
    story=[Spacer(1,142),Paragraph('PROGRAMACIÓN DIDÁCTICA',title),
           Paragraph(escape(m['name']),ParagraphStyle('course',parent=title,fontSize=17,leading=23)),
           Paragraph(escape(m['cycle']),ParagraphStyle('degree',parent=small,alignment=TA_CENTER)),
           Paragraph('Curso académico '+escape(m['academic_year']),ParagraphStyle('year',parent=small,alignment=TA_CENTER)),
           Spacer(1,45),
           Paragraph(escape(draft['center'] or 'Centro pendiente de indicar'),ParagraphStyle('center',parent=small,alignment=TA_CENTER)),
           Paragraph('Docente: '+escape(draft['teacher'] or 'Pendiente de indicar'),ParagraphStyle('center2',parent=small,alignment=TA_CENTER)),
           Spacer(1,45),Paragraph('BORRADOR · Pendiente de revisión y aprobación',ParagraphStyle('notice',parent=cap,alignment=TA_CENTER)),
           PageBreak(),Paragraph('Índice de contenidos',title)]
    toc=TableOfContents();toc.levelStyles=[tocstyle];toc.dotsMinLevel=0
    story.append(toc)
    story.append(PageBreak())
    for idx,(heading,fields) in enumerate(sections,1):
        para=Paragraph(escape(f'{idx}. {heading}'),h1)
        para._ef_toc_title=f'{idx}. {heading}'
        story.append(para)
        if not fields: story.append(Paragraph('Pendiente de completar.',body))
        if heading in TABLE_SECTIONS and fields:
            width=W-84
            tabledata=[[Paragraph('<b>Concepto / unidad / RA-CE</b>',small),Paragraph('<b>Información programada</b>',small)]]
            for key,value in fields:
                tabledata.append([Paragraph(escape(str(key)),small),
                                  Paragraph(escape(str(value or '[Pendiente de completar]')).replace('\n','<br/>'),small)])
            tab=Table(tabledata,colWidths=[width*.31,width*.69],repeatRows=1,hAlign='LEFT')
            tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
               ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E0EDF4')),
               ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F9FB')]),
               ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D5E3EA')),
               ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
               ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.append(tab)
            story.append(Spacer(1,11))
        else:
            for key,value in fields:
                txt='<b>'+escape(str(key))+'</b>: '+escape(str(value or '[Pendiente de completar]')).replace('\n','<br/>')
                story.append(Paragraph(txt,body))
    # Gantt is printed on a dedicated horizontal A3 page. Weeks get full dates
    # and months/year are grouped, not displayed as unexplained 1..N indexes.
    story.append(NextPageTemplate('gantt'))
    story.append(PageBreak())
    heading=f'{len(sections)+1}. Diagrama de Gantt (calendario semanal)'
    para=Paragraph(heading,h1);para._ef_toc_title=heading
    story.append(para)
    weeks=plan.get('gantt_weeks',[])
    story.append(Paragraph('Escala horizontal: MESES Y AÑOS (fila superior); SEMANAS NATURALES de lunes a domingo (fila inferior). '
                           'En cada columna se muestran la fecha de INICIO y la de FIN en formato día/mes. '
                           'Las horas son el valor de la segunda columna, no los números del encabezado.',cap))
    if weeks:
        wide=landscape(A3)
        chart_width=wide[0]-84
        first, hour_col, eval_col=184,61,60
        col_w=(chart_width-first-hour_col-eval_col)/len(weeks)
        if col_w >= 10:
            months=_month_groups(weeks)
            monthrow=['Mes / año','','']+['']*len(weeks)
            for ym,first_idx,last_idx in months:
                monthrow[3+first_idx]=_month_label(ym)
            weekrow=[Paragraph('<b>Unidad didáctica</b>',cap),
                     Paragraph('<b>Horas (h)</b>',cap),
                     Paragraph('<b>Evaluación</b>',cap)]
            for w in weeks:
                weekrow.append(Paragraph(f'{_date_label(w["start"])}<br/>{_date_label(w["end"])}',
                     ParagraphStyle('weeklabel',fontName=fn,fontSize=5.1,leading=7.0,alignment=TA_CENTER,splitLongWords=False)))
            data=[monthrow,weekrow]
            shades=[]
            for u in plan['units']:
                data.append([Paragraph(escape(_short(u['code']+' · '+u['title'],63)),small),
                            _n2(u['hours'])+' h',str(u['term'])+'.ª']+['']*len(weeks))
                ridx=len(data)-1
                for j,w in enumerate(weeks,3):
                    if _overlaps(u['start'],u['end'],w['start'],w['end']):
                        color={1:'#317FA8',2:'#1F9D99',3:'#7268AD'}.get(int(u['term']),'#317FA8')
                        shades.append(('BACKGROUND',(j,ridx),(j,ridx),colors.HexColor(color)))
            if plan['feoe']['start'] and plan['feoe']['end']:
                data.append(['FEOE (propuesta)','—','—']+['']*len(weeks))
                ridx=len(data)-1
                for j,w in enumerate(weeks,3):
                    if _overlaps(plan['feoe']['start'],plan['feoe']['end'],w['start'],w['end']):
                        shades.append(('BACKGROUND',(j,ridx),(j,ridx),colors.HexColor('#64A542')))
            tab=Table(data,colWidths=[first,hour_col,eval_col]+[col_w]*len(weeks),
                      rowHeights=[23,31]+[32]*(len(data)-2),repeatRows=2,hAlign='LEFT')
            spans=[('SPAN',(0,0),(2,0))]
            spans.extend([('SPAN',(3+fi,0),(3+li,0)) for ym,fi,li in months if li>fi])
            tab.setStyle(TableStyle([
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('FONTNAME',(0,0),(-1,-1),fn),
                ('FONTSIZE',(0,0),(-1,-1),7.5),
                ('FONTSIZE',(3,0),(-1,0),8.0),
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEBF1')),
                ('BACKGROUND',(0,1),(-1,1),colors.HexColor('#EDF4F7')),
                ('ALIGN',(3,0),(-1,1),'CENTER'),
                ('ALIGN',(1,2),(2,-1),'CENTER'),
                ('GRID',(0,0),(-1,-1),.32,colors.HexColor('#C8D7DE')),
                ('LINEBELOW',(0,1),(-1,1),.6,navy),
                ('LEFTPADDING',(0,0),(-1,-1),3),
                ('RIGHTPADDING',(0,0),(-1,-1),3),
                # Date labels need all five characters dd/mm in narrow week cells.
                ('LEFTPADDING',(3,1),(-1,1),0),
                ('RIGHTPADDING',(3,1),(-1,1),0),
                ('TOPPADDING',(0,0),(-1,-1),4),
                ('BOTTOMPADDING',(0,0),(-1,-1),4),
            ]+spans+shades))
            story.append(tab)
            story.append(Spacer(1,12))
            summarydata=[['Indicador','Valor','Unidad'],
                 ['Horas semanales',_n2(plan['config']['weekly_hours']),'h/semana'],
                 ['Horas disponibles',_n2(plan['capacity']),'h'],
                 ['Horas programadas',_n2(plan['planned']),'h'],
                 ['CE propuestos para FEOE',str(plan['feoe'].get('count',0)),_n2(plan['feoe'].get('percent',0))+' %']]
            summary=Table(summarydata,colWidths=[238,90,120],repeatRows=1,hAlign='LEFT')
            summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEBF1')),
                     ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D5E3EA')),
                     ('FONTNAME',(0,0),(-1,-1),fn),('FONTSIZE',(0,0),(-1,-1),8),
                     ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFB')]),
                     ('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),
                     ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.append(summary)
            story.append(Spacer(1,13))
            story.append(Paragraph('Leyenda: AZUL = 1.ª evaluación; VERDE AZULADO = 2.ª; VIOLETA = 3.ª; '
                                   'VERDE = periodo FEOE. Cada barra coloreada indica un intervalo del calendario, '
                                   'NO las horas impartidas en cada semana.',cap))
            story.append(Paragraph('La temporalización se calcula con las sesiones y festivos registrados; '
                                   'compruebe los días no lectivos y las fechas del centro antes de aprobar la programación.',cap))
        else:
            story.append(Paragraph('El periodo supera la anchura disponible para rotular las semanas con claridad. '
                                   'Revise el periodo seleccionado en el asistente.',body))
    else:
        story.append(Paragraph('Configure el calendario lectivo para generar el Gantt.',body))
    doc.multiBuild(story,maxPasses=5)
    return stream.getvalue(),'application/pdf',f'EvaluaFP_Programacion_{module_id}.pdf'
