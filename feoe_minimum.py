"""Programa mínimo FEOE separado: selecciona CE reales y propone tareas accesibles.

NO es un plan individual aprobado, NO acredita criterios y NO sustituye el
modelo oficial ni los acuerdos entre centro y empresa.
"""
from __future__ import annotations

import io
import json
import math
import re
from html import escape
from math import ceil

import ia

OFFICIAL_CANARIAS = 'https://www.gobiernodecanarias.org/boc/archivo/2025/176/pda/3174.html'
OFFICIAL_STATE = 'https://www.boe.es/buscar/act.php?id=BOE-A-2023-16889'

# Códigos curriculares procedentes de la base de datos; nunca redactados por IA.
ACCESSIBLE = ('identific', 'reconoc', 'clasific', 'organiza', 'localiz', 'compar',
              'seleccion', 'comprueb', 'verific', 'registr', 'archiv', 'observ',
              'comunic', 'cumpliment', 'elabor', 'utiliz', 'describ', 'disting',
              'relacion', 'aplica', 'gestion', 'document', 'atend')
SPECIALIZED = ('circuito electr', 'soldadur', 'radiacion', 'quirurg', 'diagnostic',
               'medicamento', 'vehiculo', 'maquinaria pesada', 'peligros',
               'tratamiento sanitario', 'intervencion', 'autorizacion',
               'conduc', 'monta', 'instalacion', 'equipos de alta tension',
               'prescrib', 'manejo de sustancias', 'trabajos en altura')


def _words(value):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def suitability(criterion):
    """Valor ORIENTATIVO para ordenar tareas comunes; no certifica factibilidad."""
    norm = _words(criterion['description'])
    score = 0
    for term in ACCESSIBLE:
        if term in norm:score += 2
    for term in SPECIALIZED:
        if term in norm:score -= 7
    if any(x in norm for x in ('dato', 'informacion', 'registro', 'procedimiento', 'documento')):
        score += 2
    if any(x in norm for x in ('seguridad', 'confidencial', 'calidad')):score += 1
    return score


def _general_task(criterion):
    """Lenguaje llano adaptable con anclaje al CE, sin afirmar logro inexistente."""
    detail = re.sub(r'\s+', ' ', criterion['description']).strip().rstrip('.')
    norm = _words(detail)
    if any(x in norm for x in ('identific', 'reconoc', 'distingu', 'clasific', 'compar')):
        action = ('Observar un ejemplo cotidiano del trabajo, señalar o clasificar sus elementos '
                  'y explicar de forma sencilla cómo se relacionan con el criterio.')
        proof = 'Lista breve de elementos identificados, explicación oral o lista de cotejo del tutor.'
    elif any(x in norm for x in ('document', 'archiv', 'registr', 'cumpliment', 'comunic')):
        action = ('Revisar o completar, con supervisión, un ejemplo de registro, documento '
                  'o comunicación habitual de la organización; se pueden utilizar datos ficticios.')
        proof = 'Ejemplo ficticio o anonimizado y verificación de los pasos realizados.'
    elif any(x in norm for x in ('utiliz', 'aplic', 'realiz', 'elabor', 'gestion')):
        action = ('Participar en una tarea sencilla y supervisada relacionada con el criterio, '
                  'utilizando un ejemplo o simulación si la empresa no puede facilitar el caso real.')
        proof = 'Lista de pasos aplicados y valoración del resultado por la persona tutora.'
    else:
        action = ('Observar una tarea habitual y comentar con la persona tutora cómo se relaciona '
                  'con el aprendizaje descrito en el criterio.')
        proof = 'Nota breve de observación y explicación verbal registrada por la tutoría.'
    return {'activity': action, 'evidence': proof,
            'support': 'Con instrucciones paso a paso, apoyo del tutor y progresiva autonomía, sin rebajar el CE.',
            'relation': detail[:600]}


def _get(db,module_id):
    module = db.execute('SELECT id,name,cycle,academic_year,territory FROM modules WHERE id=?', (module_id,)).fetchone()
    if module is None:raise ValueError('El módulo no existe.')
    criteria = [dict(row) for row in db.execute('''SELECT c.code,c.description,o.code AS ra_code,o.description AS ra_description
         FROM criteria c JOIN outcomes o ON c.outcome_id=o.id WHERE o.module_id=? ORDER BY o.id,c.id''',(module_id,))]
    if not criteria:raise ValueError('Para crear el programa FEOE debe incorporar y confirmar los RA y CE del módulo.')
    from program_builder import load
    draft = load(db,module_id)['draft']
    result=dict(module)
    result['territory']=draft.get('region') or result['territory']
    result['fp_regime']=draft.get('fp_regime') or 'pendiente'
    return result,criteria,draft


def _count(total,target):
    # Cuando no cabe un porcentaje 10-20 % exacto se informa, no se finge.
    expected=max(1,min(total,round(total*target/100)))
    candidates=[x for x in range(1,total+1) if 10-1e-9 <= 100*x/total <= 20+1e-9]
    return min(candidates,key=lambda x:(abs(x-total*target/100),-x)) if candidates else expected


def _shortlist(criteria,target):
    n=_count(len(criteria),target)
    sorted_ce=sorted(criteria,key=lambda c:(-suitability(c), c['ra_code'],c['code']))
    chosen=[];covered=set()
    # Priorizar CE sencillos y distribuir entre RA cuando la facilidad sea comparable.
    for item in sorted_ce:
        if len(chosen)>=n:break
        if item['ra_code'] in covered:continue
        chosen.append(item);covered.add(item['ra_code'])
    for item in sorted_ce:
        if len(chosen)>=n:break
        if item['code'] not in {c['code'] for c in chosen}:chosen.append(item)
    return chosen


def propose(db,module_id,mode='local',authorize_ai=False):
    module,criteria,draft=_get(db,module_id)
    cfg=draft.get('schedule') or {}
    chosen_codes=cfg.get('feoe_criteria_codes') or []
    known={c['code'].casefold():c for c in criteria}
    if chosen_codes:
        unknown=[k for k in chosen_codes if k.casefold() not in known]
        if unknown:raise ValueError('La selección FEOE contiene CE que ya no existen: '+', '.join(unknown))
        chosen=[known[k.casefold()] for k in chosen_codes]
        selection='Criterios ya seleccionados por el docente (no sustituidos)'
    else:
        chosen=_shortlist(criteria,float(cfg.get('feoe_target_percent',15)))
        selection='Selección inicial por transferibilidad y sencillez; requiere aprobación docente'
    existing={r['criteria_code'].casefold():r for r in draft.get('feoe_tasks',[])}
    rows=[]
    for c in chosen:
        suggested=_general_task(c)
        entry=existing.get(c['code'].casefold(),{})
        score=suitability(c)
        rows.append({'criteria_code':c['code'],'ra_code':c['ra_code'],'ra_description':c['ra_description'],
                     'description':c['description'], 'activity':entry.get('activity') or suggested['activity'],
                     'evidence':entry.get('evidence') or suggested['evidence'],
                     'support':entry.get('support') or suggested['support'],
                     'assessment_role':entry.get('assessment_role') or 'Tutoría de empresa observa y comunica; docente valora la evidencia.',
                     'fit':'Necesita entorno/tarea específica' if score<0 else 'Posible en muchos entornos, pendiente de confirmar',
                     'selection_score':score})
    if mode=='ai':
        if authorize_ai is not True:raise ValueError('Autorice expresamente el envío de RA y CE al proveedor de IA.')
        if not ia.key_available():raise ValueError('Configure y desbloquee su API de IA antes de solicitar la redacción.')
        ai_may_select=not bool(chosen_codes)
        desired_count=len(rows)
        pool=criteria if ai_may_select else chosen
        prompt={
          'instruccion': ('Elabora un PROGRAMA FORMATIVO MINIMO FEOE. Si no hay selección previa, elige exactamente '
            +str(desired_count)+' CE oficiales de esta lista que sean los MÁS TRANSFERIBLES a empresas de diferentes sectores. '
            'Si ya hay CE elegidos por el docente, CONSÉRVALOS y mejora solamente tareas y evidencias. '
            'Devuelve JSON estricto {"rows":[{"criteria_code":"...","activity":"...","evidence":"...","support":"..."}]}.'),
          'restricciones': [
             'Selecciona únicamente códigos de la lista oficial facilitada; nunca inventes, mezcles ni modifiques RA/CE.',
             'Da preferencia a identificar, organizar o comprobar información, comunicación y tareas habituales; evita actuaciones que requieran equipos o habilitaciones especializados.',
             'Redacta tareas observables, concretas pero flexibles, con apoyo progresivo según el nivel del alumnado.',
             'No consideres acreditado un CE técnico por simple observación: se necesita evidencia suficiente y valoración docente.',
             'No des por hecho que todas las empresas pueden cumplir todas las actividades.',
             'No inventes fechas, porcentajes, normativa, alumnado, empresas, resultados ni notas.',
             'Cada tarea debe estar claramente relacionada con la exigencia del criterio concreto; máximo 350 caracteres por texto.'
          ], 'modulo':module['name'],'ciclo':module['cycle'],
          'criterios_confirmados':[{'criteria_code':r['code'],'ra_code':r['ra_code'],
              'description':r['description'][:440]} for r in pool],
          'criterios_ya_elegidos_por_docente':[r['code'] for r in chosen] if chosen_codes else [],
          'numero_de_criterios_exigido':desired_count}
        obj,model=ia.chat('generation',json.dumps(prompt,ensure_ascii=False),limit=14000)
        if not isinstance(obj,dict) or not isinstance(obj.get('rows'),list):raise ValueError('La IA no devolvió el programa estructurado.')
        ai_rows=obj['rows']
        codes=[str(x.get('criteria_code','')).casefold() for x in ai_rows if isinstance(x,dict)]
        valid_codes={r['code'].casefold() for r in pool}
        if (len(ai_rows)!=desired_count or len(codes)!=desired_count or len(set(codes))!=desired_count or
                not set(codes).issubset(valid_codes) or (chosen_codes and set(codes)!={r['code'].casefold() for r in chosen})):
            raise ValueError('La IA ha propuesto una selección FEOE inválida, incompleta o distinta de la aprobada. No se ha aplicado.')
        by_id={r['criteria_code'].casefold():r for r in ai_rows}
        if ai_may_select:
            # Reutilizar tareas locales de base solo para criterios realmente elegidos.
            rows=[]
            for key in codes:
                c=known[key];score=suitability(c);suggested=_general_task(c)
                rows.append({'criteria_code':c['code'],'ra_code':c['ra_code'],'ra_description':c['ra_description'],
                    'description':c['description'], 'activity':suggested['activity'],
                    'evidence':suggested['evidence'],'support':suggested['support'],
                    'assessment_role':'Tutoría de empresa observa y comunica; docente valora la evidencia.',
                    'fit':'Necesita entorno/tarea específica' if score<0 else 'Posible en muchos entornos, pendiente de confirmar',
                    'selection_score':score})
            selection='CE propuestos por IA entre todos los oficiales confirmados; pendientes de aceptación docente'
        for row in rows:
            candidate=by_id[row['criteria_code'].casefold()]
            for field in ('activity','evidence','support'):
                value=candidate.get(field)
                if not isinstance(value,str) or not (10<=len(value.strip())<=1000):
                    raise ValueError('La IA ha generado un apartado FEOE vacío o excesivo.')
                row[field]=value.strip()
        source='Propuesta redactada por IA ('+str(model)+') — aceptación expresa requerida'
    elif mode=='local':source='Reglas locales de sugerencia — sin llamada a IA'
    else:raise ValueError('Modo de generación desconocido.')
    count=len(rows);total=len(criteria)
    warnings=[]
    if not chosen_codes:
        warnings.append('La selección de CE es una propuesta y no está guardada ni aprobada.')
    if not (10<=100*count/total<=20):
        warnings.append('Por granularidad del número de CE no se alcanza exactamente el 10–20 % orientativo; se muestran las cifras reales.')
    if any(x['selection_score']<0 for x in rows):
        warnings.append('Algún CE puede requerir un entorno o habilitación específicos. Compruebe su viabilidad con cada empresa.')
    warnings.extend(['La selección del 10–20 % de CE es orientativa y NO acredita el porcentaje de RA exigido por el régimen de FP Dual.',
                     'El centro y la empresa deben concretar las tareas y valorar su adecuación a cada alumno; el programa no acredita por sí mismo el logro de los CE.'])
    return {'module':module,'rows':rows,'count':count,'total_criteria':total,'percentage':round(100*count/total,2),
            'source':source,'selection':selection,'warnings':warnings,
            'schedule':{'start':cfg.get('feoe_start',''),'end':cfg.get('feoe_end',''),
                        'hours_confirmed':bool(cfg.get('hours_confirmed')),
                        'calendar_confirmed':bool(cfg.get('calendar_confirmed'))},
            'official_reference':OFFICIAL_CANARIAS if module['territory']=='Canarias' else '',
            'territory_notice':('Modelo autonómico de Canarias: comprobar vigencia y aplicación al curso.' if module['territory']=='Canarias' else
                                'Adaptar el documento al plan de formación oficial y procedimientos de '+module['territory']+'.'),
            'approved':False}


def validate_rows(db,module_id,proposed):
    """Aceptación docente: CE de currículo real, unicidad y todos los campos obligatorios."""
    _,criteria,_=_get(db,module_id)
    allowed={c['code'].casefold():c['code'] for c in criteria}
    if not isinstance(proposed,list) or not 1<=len(proposed)<=500:raise ValueError('Seleccione al menos un criterio FEOE.')
    out=[];used=set()
    for item in proposed:
        if not isinstance(item,dict):raise ValueError('Fila FEOE no válida.')
        code=item.get('criteria_code','')
        if not isinstance(code,str) or code.casefold() not in allowed:raise ValueError('El programa incluye un CE no confirmado.')
        if code.casefold() in used:raise ValueError('No puede repetir un CE en el programa formativo.')
        used.add(code.casefold())
        record={'criteria_code':allowed[code.casefold()]}
        for field,length in (('activity',1500),('evidence',1500),('assessment_role',250),('support',1000)):
            val=item.get(field,'')
            if not isinstance(val,str) or len(val)>length or len(val.strip())<10:
                raise ValueError('Revise la tarea, evidencia y responsables para '+code+'.')
            record[field]=val.strip()
        out.append(record)
    return out


def accept(db,module_id,rows):
    """Guarda selección y matriz sin modificar RA, CE, ponderaciones ni notas."""
    from program_builder import load,save
    cleaned=validate_rows(db,module_id,rows)
    draft=load(db,module_id)['draft']
    draft['feoe_tasks']=cleaned
    draft['schedule']['feoe_criteria_codes']=[x['criteria_code'] for x in cleaned]
    save(db,module_id,draft)
    return {'saved':True,'criteria_codes':[x['criteria_code'] for x in cleaned],
            'count':len(cleaned),'approved':False}


def _title_and_table(result):
    lines=[('Identificación', [('Curso académico',result['module']['academic_year']),
       ('Ciclo',result['module']['cycle']),('Módulo profesional',result['module']['name']),
       ('Administración educativa',result['module'].get('territory') or 'Por confirmar'),
       ('Régimen FP Dual',result['module'].get('fp_regime','pendiente')),
       ('Alumno/a','Pendiente de asignar'),('Empresa u organismo equiparado','Pendiente de asignar'),
       ('Tutor/a del centro','Pendiente de asignar'),('Tutor/a de empresa','Pendiente de asignar'),
       ('Estancia prevista',((result['schedule']['start'] or 'Fecha por confirmar')+' — '+(result['schedule']['end'] or 'Fecha por confirmar')))]),
       ('Resumen de la selección',[('CE incluidos',str(result['count'])+' de '+str(result['total_criteria'])),
       ('Porcentaje orientativo',f'{result["percentage"]:.2f} %'),('Origen',result['source']),
       ('Estado','PROPUESTA SIN APROBAR — pendiente de acuerdo del centro y la empresa')])]
    return lines


def _word(result):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Cm, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    doc=Document()
    section=doc.sections[0];section.page_width=Cm(29.7);section.page_height=Cm(21)
    section.left_margin=Cm(1.6);section.right_margin=Cm(1.6)
    section.top_margin=Cm(1.5);section.bottom_margin=Cm(1.4)
    styles=doc.styles;styles['Normal'].font.name='Aptos';styles['Normal'].font.size=Pt(9)
    doc.add_heading('PROGRAMA FORMATIVO MÍNIMO EN EMPRESA',0)
    doc.add_paragraph('EvalúaFP · Documento independiente de trabajo · Propuesta editable')
    w=doc.add_paragraph('BORRADOR: NO SUSTITUYE EL PLAN DE FORMACIÓN OFICIAL NI SU VALIDACIÓN CON LA EMPRESA.')
    for run in w.runs:run.bold=True;run.font.color.rgb=RGBColor(146,58,41)
    for heading,fields in _title_and_table(result):
        doc.add_heading(heading,level=1)
        table=doc.add_table(rows=0,cols=2);table.style='Light Shading Accent 1'
        for key,value in fields:
            cells=table.add_row().cells;cells[0].text=str(key);cells[1].text=str(value)
    doc.add_heading('Tareas y evidencias propuestas por criterio',level=1)
    doc.add_paragraph('Tareas breves y adaptables, siempre supeditadas al contenido completo del CE oficial. La propuesta no demuestra, por sí sola, que el criterio se haya alcanzado.')
    headers=['RA / CE','Criterio oficial','Ejemplo de tarea sencilla','Evidencia de aprendizaje','Apoyo previsto']
    table=doc.add_table(rows=1,cols=len(headers));table.style='Table Grid';table.autofit=False;table.alignment=WD_TABLE_ALIGNMENT.CENTER
    widths=[Cm(2.0),Cm(7),Cm(7.6),Cm(6.4),Cm(3.5)]
    for i,label in enumerate(headers):table.rows[0].cells[i].text=label
    for item in result['rows']:
        values=[item['ra_code']+' / '+item['criteria_code'],item['description'],item['activity'],item['evidence'],item['support']]
        cells=table.add_row().cells
        for i,v in enumerate(values):cells[i].text=v
    for row_index,row in enumerate(table.rows):
        # No dividir un criterio y su tarea entre dos páginas.
        trPr=row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))
        if row_index==0:trPr.append(OxmlElement('w:tblHeader'))
        for i,cell in enumerate(row.cells):
            cell.width=widths[i]
            for par in cell.paragraphs:
                par.paragraph_format.space_after=Pt(2)
                for run in par.runs:run.font.size=Pt(8)
    doc.add_heading('Seguimiento orientativo',level=1)
    track=doc.add_table(rows=1,cols=4);track.style='Table Grid'
    for i,key in enumerate(['CE','¿Realizada?','Observación/evidencia de empresa','Valoración docente']):track.cell(0,i).text=key
    for row in result['rows']:
        cells=track.add_row().cells;cells[0].text=row['criteria_code'];cells[1].text='☐ Sí   ☐ No';cells[2].text='Pendiente';cells[3].text='Pendiente'
    doc.add_paragraph('Adaptación al alumnado: las instrucciones y apoyos pueden variar según las necesidades, pero no se considera logrado un criterio si no se obtiene evidencia suficiente de sus exigencias.')
    doc.add_heading('Confirmación',level=1)
    for line in ['Tareas acordadas con la empresa: ____________________________________',
                 'Fecha de revisión: ___________________',
                 'Tutor/a del centro: ______________________  Tutor/a de empresa: ______________________']:
        doc.add_paragraph(line)
    doc.add_paragraph('Referencias: '+OFFICIAL_STATE+(' · '+result['official_reference'] if result['official_reference'] else ''))
    doc.add_paragraph(result['territory_notice'])
    doc.sections[0].footer.paragraphs[0].text='EvalúaFP · Programa mínimo orientativo · Pendiente de confirmación'
    stream=io.BytesIO();doc.save(stream)
    return stream.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def _pdf(result):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph,Spacer,KeepTogether
    s=io.BytesIO();doc=SimpleDocTemplate(s,pagesize=landscape(A4),leftMargin=1.2*cm,rightMargin=1.2*cm,topMargin=1.3*cm,bottomMargin=1.4*cm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='EFBody',parent=styles['BodyText'],fontName='Helvetica',fontSize=8,leading=11,spaceAfter=4))
    styles.add(ParagraphStyle(name='EFTiny',parent=styles['BodyText'],fontName='Helvetica',fontSize=7.1,leading=9))
    styles.add(ParagraphStyle(name='EFHead',parent=styles['Heading2'],textColor=colors.HexColor('#16587b'),fontSize=13,spaceBefore=10,spaceAfter=6))
    P=lambda val,sty='EFTiny':Paragraph(escape(str(val)).replace('\n','<br/>'),styles[sty])
    elems=[P('PROGRAMA FORMATIVO MÍNIMO EN EMPRESA','EFHead'),
           P('EvalúaFP · DOCUMENTO INDEPENDIENTE · BORRADOR SIN APROBAR','EFBody'),
           P('Propuesta adaptable que NO sustituye el Plan de Formación Oficial ni acredita la adquisición de CE.','EFBody')]
    for name,fields in _title_and_table(result):
        elems.append(P(name,'EFHead'))
        data=[[P(k),P(v,'EFBody')] for k,v in fields]
        t=Table(data,colWidths=[4.2*cm,20*cm],hAlign='LEFT')
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#d0dae0')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f1f6fa')),
                ('LEFTPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        elems.extend([t,Spacer(1,5)])
    elems.append(P('Criterios, tareas mínimas y evidencias','EFHead'))
    headers=['RA / CE','Descripción del criterio','Ejemplo de tarea sencilla','Evidencia observable','Apoyos']
    tab=[[P(v) for v in headers]]
    for r in result['rows']:
        tab.append([P(r['ra_code']+' / '+r['criteria_code']),P(r['description']),P(r['activity']),P(r['evidence']),P(r['support'])])
    t=Table(tab, colWidths=[1.9*cm,6.0*cm,7.1*cm,5.2*cm,4.0*cm], repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5f0f4')),
         ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#c7d4d9')),
         ('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafb')]),
         ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    elems.append(t)
    elems.append(P('Seguimiento y adaptación individual','EFHead'))
    for x in result['rows']:
        elems.append(P(x['criteria_code']+' · Realizada: [ ] Sí  [ ] No   |   Evidencia: ________________________   |   Valoración docente: _____________________','EFBody'))
    elems.append(P('El centro y la empresa concretarán las tareas y los apoyos. La evaluación final es responsabilidad docente.','EFBody'))
    elems.append(P('Confirmación: Tutor/a del centro __________________   Tutor/a de empresa __________________  Fecha __________','EFBody'))
    elems.append(P('Normativa de referencia: '+OFFICIAL_STATE+(' / '+result['official_reference'] if result['official_reference'] else ''),'EFTiny'))
    elems.append(P(result['territory_notice'],'EFTiny'))
    def footer(canvas,record):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#516c7a'))
        canvas.drawString(1.2*cm,0.8*cm,'EvalúaFP · Propuesta FEOE · No oficial / sin aprobar')
        canvas.drawRightString(landscape(A4)[0]-1.2*cm,0.8*cm,'Página '+str(record.page));canvas.restoreState()
    doc.build(elems,onFirstPage=footer,onLaterPages=footer)
    return s.getvalue(),'application/pdf'


def export(db,module_id,fmt):
    if fmt not in ('docx','pdf','md'):raise ValueError('Formato no admitido.')
    result=propose(db,module_id)
    if fmt=='docx':blob,mime=_word(result)
    elif fmt=='pdf':blob,mime=_pdf(result)
    else:
        text=['# PROGRAMA FORMATIVO MÍNIMO EN EMPRESA',
              '> BORRADOR; no sustituye el modelo oficial ni acredita los CE.',
              f'**Módulo:** {result["module"]["name"]}',f'**Ciclo:** {result["module"]["cycle"]}',
              f'**CE propuestos:** {result["count"]} / {result["total_criteria"]} ({result["percentage"]:.2f} %)',
              '', '| RA / CE | Criterio oficial | Tarea propuesta | Evidencia |',
              '|---|---|---|---|']
        for r in result['rows']:
            fix=lambda v:str(v).replace('|','/').replace('\n',' ')
            text.append('| '+ ' | '.join(fix(v) for v in (r['ra_code']+' / '+r['criteria_code'],r['description'],r['activity'],r['evidence']))+' |')
        text.extend(['','## Revisión obligatoria']+[('- '+w) for w in result['warnings']])
        blob='\n'.join(text).encode('utf-8');mime='text/markdown; charset=utf-8'
    return blob,mime,f'EvaluaFP_Programa_Minimo_Empresa_{module_id}.{fmt}'
