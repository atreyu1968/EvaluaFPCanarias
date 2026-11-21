"""Informes Excel de ámbitos comunes, sin notas profesionales ni actas oficiales."""
import io
import xlsxwriter
import common_scope_notebook as book
import common_scope_recovery as recovery
import common_scope_consolidation as consolidation
import database as data

MIME='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def export(db,mid,session='ordinaria',student_id=None):
    notebook=book.load(db,mid)
    plans=recovery.load(db,mid)['plans']
    if student_id is not None:
        recovery.student(db,mid,student_id)
    students=[x for x in notebook['students'] if student_id is None or x['id']==student_id]
    by_student={x['id']:x for x in students}
    activities={x['id']:x for x in notebook['activities']}
    module=db.execute('SELECT name,academic_year,group_name FROM modules WHERE id=?',(mid,)).fetchone()
    report=None
    warning=''
    try:
        report=consolidation.report(db,mid,session)
    except ValueError as exc:
        warning=str(exc)
    out=io.BytesIO()
    with xlsxwriter.Workbook(out,{'in_memory':True,'strings_to_formulas':False,'strings_to_urls':False}) as wb:
        wb.set_properties({'title':'EvaluaFP Canarias - seguimiento competencial'})
        head=wb.add_format({'bold':True,'bg_color':'#142D4E','font_color':'white','text_wrap':True,'valign':'vcenter'})
        body=wb.add_format({'text_wrap':True,'valign':'top','font_size':10})
        def sheet(name,headers,rows,widths):
            sh=wb.add_worksheet(name)
            sh.freeze_panes(1,0)
            sh.set_row(0,30)
            for i,h in enumerate(headers):
                sh.write_string(0,i,h,head)
                sh.set_column(i,i,widths[i])
            n=0
            for n,row in enumerate(rows,1):
                for col,v in enumerate(row):
                    if v is None:
                        sh.write_blank(n,col,None,body)
                    elif isinstance(v,(int,float)) and not isinstance(v,bool):
                        sh.write_number(n,col,v,body)
                    else:
                        # write_string prevents formula/URL injection even with untrusted text.
                        sh.write_string(n,col,str(v),body)
            if n:
                sh.autofilter(0,0,n,len(headers)-1)
        sheet('Ficha',['Campo','Valor'],[
            ('Materia',module['name']),('Ámbito',notebook['profile']['ambito']),
            ('Curso académico',module['academic_year']),('Grupo',module['group_name']),
            ('Evaluación',session),('Generado',data.now()),
            ('Alcance','Individual' if student_id is not None else 'Colectivo de la materia'),
            ('Aviso','Documento interno de seguimiento. No constituye acta oficial.'),
            ('Consolidación',warning or 'Consultar el estado de los acuerdos en la hoja Consolidación')],
            [28,90])
        sheet('Alumnado',['Código','Alumno'],[(x['code'],x['name']) for x in students],[20,40])
        sheet('Currículo',['Competencia','Criterio','Enunciado','Descriptores'],[
            (x['competency_code'],x['code'],x['description'],x['descriptors']) for x in notebook['criteria']],
            [18,16,90,30])
        sheet('Evidencias',['Código','Alumno','Actividad','Fecha','Evaluación','Criterio','Valoración',
             'Observación','Referencia','Registro','Estado curricular'],[
            (by_student[e['student_id']]['code'],by_student[e['student_id']]['name'],
             activities[e['activity_id']]['title'],activities[e['activity_id']]['activity_date'],
             activities[e['activity_id']]['term'],e['criterion_code'],e['level'],e['notes'],e['evidence_ref'],
             e['created_at'],'Actual' if activities[e['activity_id']]['criteria_current'] else 'Histórico')
            for e in notebook['latest_evidence'] if e['student_id'] in by_student],
            [18,35,35,14,12,15,15,55,35,25,18])
        chosen=[p for p in plans if p['student_id'] in by_student]
        sheet('Planes',['ID','Código','Alumno','Tipo','Criterios','Objetivos','Actuaciones','Instrumentos',
                        'Revisión prevista','Estado','Materia de origen (ID)','Acuerdo de origen (ID)'],[
            (p['id'],by_student[p['student_id']]['code'],by_student[p['student_id']]['name'],
             p['kind'],', '.join(c['code'] for c in p['snapshot']['criteria']),p['objectives'],p['actions'],
             p['instruments'],p['due_date'],p['status'],p['origin_module_id'],p['snapshot']['origin_decision_id'])
            for p in chosen],[10,18,32,20,20,50,65,40,18,18,18,18])
        sheet('Revisiones',['ID plan','Código','Alumno','Estado','Observaciones','Evidencias (ID)','Fecha'],[
            (p['id'],by_student[p['student_id']]['code'],by_student[p['student_id']]['name'],
             r['status'],r['observations'],', '.join(str(e['id']) for e in r['evidence']),r['created_at'])
            for p in chosen for r in p['reviews']],[12,18,32,20,65,30,24])
        rows=[r for r in (report or {}).get('rows',[]) if r['student']['id'] in by_student]
        sheet('Consolidación',['Código','Alumno','Valoraciones por materia','Media orientativa (texto exacto)',
             'Superación orientativa','Acuerdo vigente','Estado','Advertencias'],[
            (r['student']['code'],r['student']['name'],
             '; '.join(x['module_name']+': '+x['grade']+' ('+x['hours']+' h)' for x in r['matters']),
             r['calculation']['mean'] if r['calculation'] else '',
             ('Sí' if r['calculation']['passed'] else 'No') if r['calculation'] else '',
             r['decision']['grade'] if r['decision'] and r['decision']['current'] else '',
             'Acuerdo vigente' if r['decision'] and r['decision']['current'] else
             'Acuerdo desactualizado' if r['decision'] else 'Sin acuerdo final',
             '; '.join(r['blockers']))
            for r in rows],[18,35,65,25,22,20,30,55])
    filename=f'EvaluaFP_Ambitos_{mid}'+(f'_Alumno_{student_id}' if student_id is not None else '_Grupo')+'.xlsx'
    return out.getvalue(),MIME,filename
