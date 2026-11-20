"""Exportación de evaluación local a Excel y formatos tabulares para Additio.

No presupone una plantilla oficial única de Additio: permite la importación
controlada de alumnado mediante CSV y pegar las notas en el cuaderno existente.
Nunca presenta una nota provisional como validada.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict

import evaluacion


def safe_cell(value):
    """Neutraliza CSV/TSV/Excel formula injection en textos de usuarios."""
    if value is None:
        return ''
    if isinstance(value, (int,float)) and not isinstance(value,bool):
        return value
    text=str(value)
    if text and (text.lstrip(' \t\r\n')[:1] in ('=', '+', '-', '@')):
        return "'"+text
    return text


def csv_blob(headers, rows, delimiter=';', bom=True):
    output=io.StringIO(newline='')
    w=csv.writer(output,delimiter=delimiter,lineterminator='\r\n',quoting=csv.QUOTE_MINIMAL)
    w.writerow([safe_cell(x) for x in headers])
    for row in rows:
        w.writerow([safe_cell(x) for x in row])
    return ('\ufeff' if bom else '').encode('utf-8')+output.getvalue().encode('utf-8')


def _parts(name):
    whole=(name or '').strip()
    if not whole:return '',''
    # Reconocemos únicamente el formato inequívoco «Apellidos, Nombre».
    if "," in whole:
        surname,given=whole.split(",",1)
        if surname.strip() and given.strip():return given.strip(),surname.strip()
    # No inventamos la separación de apellidos en nombres compuestos.
    return whole, ''


def _bundle(d,module_id):
    state=evaluacion.summary(d,int(module_id))
    module=d.execute('SELECT * FROM modules WHERE id=?',(int(module_id),)).fetchone()
    if not module:raise ValueError('Módulo no encontrado.')
    by_criterion={r['id']:r for r in state['criteria']}
    by_inst={r['id']:r for r in state['instruments']}
    scored=defaultdict(dict)
    for r in state['scores']:
        scored[r['student_id']][(r['instrument_id'],r['criterion_id'])]=r
    return dict(module),state,by_criterion,by_inst,scored


def _is_final(student):
    c=student.get('closure') or {}
    return bool(c.get('current')) and c.get('score') is not None


def _round(v):
    return '' if v is None else round(float(v),2)


def student_rows(state):
    for st in state['students']:
        name,surname=_parts(st['name'])
        yield [st['code'],name,surname]


def additio_codes(state, module_id):
    """Códigos coherentes para evitar RA1 ambiguos entre módulos en Additio.

    La sigla usada para el RA se reutiliza al importar sus CE. Los códigos
    originales permanecen sin alteración en la base de datos SQLite.
    """
    prefix=f'EFP{int(module_id)}'
    ra_alias={r['id']:f'{prefix}_{re.sub(r"[^A-Za-z0-9_-]+", "_", r["code"].strip())}'
              for r in state['outcomes']}
    if len(set(ra_alias.values()))!=len(ra_alias):
        raise ValueError('Existen códigos RA incompatibles con identificadores únicos de Additio.')
    ce_alias={}
    for ce in state['criteria']:
        # El importador documentado para FP utiliza códigos como «1.a.».
        # Solo simplificamos cuando existe un RA reconocido al principio.
        source=str(ce['code']).strip()
        ra=str(ce['ra_code']).strip()
        if source.startswith(ra+'.') and source[len(ra)+1:]:
            additio=ra.removeprefix('RA')+'.'+source[len(ra)+1:]
        else:
            additio=source
        ce_alias[ce['id']]=additio
    if len(set(ce_alias.values()))!=len(ce_alias):
        raise ValueError('Hay códigos CE duplicados al preparar Additio. Revise la programación.')
    return ra_alias,ce_alias


def additio_curriculum(state,module_id):
    """Devuelve RA y CE de la programación, sin inventar descripciones ni pesos."""
    ra_alias,ce_alias=additio_codes(state,module_id)
    ra_by_id={r['id']:r for r in state['outcomes']}
    ra_rows=[[ra_alias[ra['id']],ra['code'],ra['description'],
              _round(ra['weight'])] for ra in state['outcomes']]
    ce_rows=[]
    for ce in state['criteria']:
        ra=ra_by_id.get(ce['ra_id'])
        if not ra:raise ValueError('Criterio sin RA asociado.')
        attached=[u for u in state['units'] if ce['id'] in u.get('criteria_ids',[])]
        unit_labels=', '.join(f'{u["code"]}' for u in attached)
        terms=', '.join(str(u['term']) for u in attached)
        ce_rows.append([ce_alias[ce['id']],ce['code'],ce['description'],
                        ra_alias[ra['id']],ra['code'],_round(ce['weight']),unit_labels,terms])
    return ra_rows,ce_rows


def _safe_curriculum_text(v):
    """Una celda no puede introducir columnas o fórmulas al pegarse en Additio."""
    raw=' '.join(str(v or '').split())
    return str(safe_cell(raw))


def _ce_import_lines(state,module_id):
    """Plantilla de una columna: «CÓDIGO. DESCRIPCIÓN. SIGLA_RA».

    Formato descrito en el tutorial de FP de la Consejería de Cantabria.
    Debe comprobarse con el asistente de importación de cada cuenta Additio.
    """
    _,ces=additio_curriculum(state,module_id)
    result=[]
    for code,original,desc,ra_alias,ra_orig,weight,*unit_fields in ces:
        if not str(desc).strip():
            raise ValueError(f'El CE {original} carece de descripción; no se exporta una entrada ficticia.')
        result.append(f'{_safe_curriculum_text(code).rstrip(".")}. {_safe_curriculum_text(desc).rstrip(".")}. {_safe_curriculum_text(ra_alias)}')
    return result


def grades_table(state, *,validated_only=True, module_id=None):
    """Matriz curricular RA/CE (NO INCLUYE INSTRUMENTOS NI PRUEBAS).

    validated_only=True solo libera RA/CE con cierre docente vigente.
    False es para seguimiento: solo exporta RA/CE con evidencias docentes
    completamente validadas, sin declarar notas parciales como definitivas.
    """
    ras=state['outcomes'];ces=state['criteria']
    ra_alias,ce_alias=additio_codes(state,module_id or state['module_id'])
    header=['Codigo','Alumno']
    header += [ra_alias[ra['id']] for ra in ras]
    header += [ce_alias[ce['id']] for ce in ces]
    values=[]
    for st in state['students']:
        final=_is_final(st)
        def visible(entry):
            return final if validated_only else bool(entry.get('complete'))
        row=[st['code'],st['name']]
        row += [_round(r['score']) if visible(r) else '' for r in st['outcomes']]
        row += [_round(c['score']) if visible(c) else '' for c in st['criteria']]
        values.append(row)
    return header,values


def grade_status_table(state):
    """Auditoría separada, nunca incorporada a la matriz para Additio."""
    return ['Codigo','Alumno','Cierre docente','Nota final (0-10)','Advertencias'],[
        [s['code'],s['name'],'VALIDADA' if _is_final(s) else 'PENDIENTE',
         _round(s['closure']['score']) if _is_final(s) else '',
         '; '.join(s['warnings'])] for s in state['students']]


def _xlsx_table_one_sheet(title, headers, rows, *,widths=None, header=True):
    import xlsxwriter
    output=io.BytesIO()
    with xlsxwriter.Workbook(output,{'in_memory':True}) as wb:
        sh=wb.add_worksheet(title[:31])
        sh.freeze_panes(1 if header else 0,0)
        f_head=wb.add_format({'bold':True,'font_color':'#FFFFFF','bg_color':'#142D4E',
                              'text_wrap':True,'valign':'vcenter'})
        f_body=wb.add_format({'text_wrap':True,'valign':'top'})
        for i,w in enumerate(widths or [24]*max(len(headers),1)):
            sh.set_column(i,i,w)
        if header:
            for c,item in enumerate(headers):sh.write_string(0,c,str(safe_cell(item)),f_head)
        for ridx,row in enumerate(rows,1 if header else 0):
            for c,item in enumerate(row):
                if isinstance(item,(int,float)) and not isinstance(item,bool):
                    sh.write_number(ridx,c,item,f_body)
                else:
                    sh.write_string(ridx,c,str(safe_cell(item)),f_body)
    return output.getvalue()


def additio_curriculum_xlsx(d,module_id,kind):
    module,state,*_=_bundle(d,module_id)
    ras,ces=additio_curriculum(state,module_id)
    if kind=='ra':
        blob=_xlsx_table_one_sheet('RA configuración',
              ['Sigla Additio','Código RA original','Descripción','Ponderación RA (%)'],
              ras,widths=[25,20,72,24])
        return blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'Additio_RA_Configuracion_Modulo_{module_id}.xlsx'
    if kind=='ce':
        # Solo una columna y sin cabecera para respetar el formato del tutorial FP.
        lines=[[line] for line in _ce_import_lines(state,module_id)]
        blob=_xlsx_table_one_sheet('Importar criterios',[],lines,widths=[120],header=False)
        return blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'Additio_CE_Importar_Modulo_{module_id}.xlsx'
    if kind=='detalle':
        blob=_xlsx_table_one_sheet('Relación RA CE',
             ['Código CE Additio','Código CE original','Descripción CE',
              'Sigla RA Additio','RA original','Ponderación CE dentro RA (%)',
              'Unidades vinculadas','Trimestres'],
             ces,widths=[23,23,72,27,19,32,28,18])
        return blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'Additio_RA_CE_Detalle_Modulo_{module_id}.xlsx'
    if kind=='notas':
        h,r=grades_table(state,validated_only=True,module_id=module_id)
        blob=_xlsx_table_one_sheet('Notas por RA CE',h,r,widths=[18,38]+[18]*(len(h)-2))
        return blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'Additio_Notas_RA_CE_Modulo_{module_id}.xlsx'
    raise ValueError('Exportación curricular Additio no reconocida.')


def additio_curriculum_zip(d,module_id):
    """Incluye archivos independientes de RA, CE importable y equivalencias."""
    import zipfile
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for kind in ('ra','ce','detalle'):
            blob,_,filename=additio_curriculum_xlsx(d,module_id,kind)
            z.writestr(filename,blob)
        z.writestr('LEER_ANTES_DE_IMPORTAR.txt',
          'EVALUAFP / ADDITIO - CONFIGURACION DE RA Y CE\n'
          '1. Cree las competencias especificas de Additio con las siglas y descripciones de Additio_RA_Configuracion.\n'
          '2. Acceda a Instrumentos de evaluacion > Criterios de evaluacion > ... > Importacion desde Excel.\n'
          '3. Seleccione el libro Additio_CE_Importar (una columna de CODIGO. DESCRIPCION. SIGLA).\n'
          '4. Revise las asociaciones de cada criterio a su RA en Additio y aplique las ponderaciones del libro de detalle.\n'
          '5. Las siglas incluyen el ID del modulo de EvaluaFP para evitar colisiones RA1 entre modulos.\n'
          '6. Compruebe la suma de pesos y las advertencias de la programacion antes de utilizar las calificaciones.\n'
          '7. La importacion de RA y las ponderaciones requieren verificacion manual: no se garantiza importacion automatica.\n'
          'Fuente tutorial FP: https://codigoescuelaeducantabria.es/cursos/TUTORIAL_DE_ADDITIO/d_especial_fp_importar_currculo_desde_excel.html\n')
    return out.getvalue(),'application/zip',f'Additio_Configuracion_RA_CE_Modulo_{module_id}.zip'

def score_detail(state):
    criterion={r['id']:r for r in state['criteria']}
    inst={r['id']:r for r in state['instruments']}
    student={s['student_id']:s for s in state['students']}
    headers=['Codigo','Alumno','Trimestre','Unidad','Instrumento','Tipo','RA','CE',
             'Ponderacion instrumento CE (%)','Nota instrumento CE (0-10)',
             'Validada por docente','Origen','Comentario','Fecha']
    out=[]
    for s in sorted(state['scores'],key=lambda r:(r['student_id'],r['instrument_id'],r['criterion_id'])):
        st=student.get(s['student_id']);i=inst.get(s['instrument_id']);c=criterion.get(s['criterion_id'])
        if not st or not i or not c:continue
        weight=next((x['weight'] for x in i['targets'] if x['criterion_id']==s['criterion_id']),None)
        out.append([st['code'],st['name'],i['term'],i.get('unit_code') or '',i['title'],i['kind'],
                    c['ra_code'],c['code'],_round(weight),_round(s['score']),
                    'Sí' if s['teacher_validated'] else 'No',s['origin'],s['comment'],s['changed_at']])
    return headers,out


def export_additio(d,module_id,kind):
    module,state,*_= _bundle(d,module_id)
    if kind=='alumnos':
        return csv_blob(['Codigo','Nombre','Apellidos'],student_rows(state)),'text/csv; charset=utf-8',f'Additio_Alumnado_Modulo_{module_id}.csv'
    if kind in ('notas','pegar','seguimiento'):
        h,r=grades_table(state,validated_only=(kind!='seguimiento'),module_id=module_id)
        delim='\t' if kind=='pegar' else ';'
        ext='tsv' if kind=='pegar' else 'csv'
        mime='text/tab-separated-values; charset=utf-8' if kind=='pegar' else 'text/csv; charset=utf-8'
        name=('Additio_RA_CE_SEGUIMIENTO_' if kind=='seguimiento' else 'Additio_RA_CE_VALIDADAS_')
        return csv_blob(h,r,delimiter=delim),mime,f'{name}Modulo_{module_id}.{ext}'
    if kind=='estado':
        h,r=grade_status_table(state)
        return csv_blob(h,r),'text/csv; charset=utf-8',f'Additio_RA_CE_Estado_Modulo_{module_id}.csv'
    raise ValueError('Formato Additio desconocido.')

def additio_students_xlsx(d,module_id):
    """Libro con una sola hoja, destinado al asistente de importación de alumnos."""
    import xlsxwriter
    module,state,*_=_bundle(d,module_id)
    out=io.BytesIO()
    with xlsxwriter.Workbook(out,{'in_memory':True}) as wb:
        sh=wb.add_worksheet('Alumnado')
        sh.freeze_panes(1,0)
        sh.set_column('A:A',18);sh.set_column('B:B',32);sh.set_column('C:C',32)
        heading=wb.add_format({'bold':True,'bg_color':'#142D4E','font_color':'white'})
        headers=['Codigo','Nombre','Apellidos']
        for c,val in enumerate(headers):sh.write_string(0,c,val,heading)
        for rowidx,row in enumerate(student_rows(state),1):
            for col,val in enumerate(row):sh.write_string(rowidx,col,str(safe_cell(val)))
    return out.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'Additio_Alumnado_Modulo_{module_id}.xlsx'


def export_excel(d,module_id,format='xlsx'):
    module,state,*_=_bundle(d,module_id)
    heads,rows=grades_table(state,validated_only=False,module_id=module_id)
    h_details,details=score_detail(state)
    matrix_headers,matrix_rows=grades_table(state,validated_only=True,module_id=module_id)
    warnings=state['warnings']
    # La cabecera del libro se construye de forma estable aun sin advertencias.
    overview=[['EVALUAFP · EVALUACION DEL MODULO'],['Curso académico',module['academic_year']],
              ['Módulo',module['name']],['Grupo',module['group_name']],['Ciclo',module['cycle']],
              ['Política de ponderación','Con advertencias' if warnings else 'Sin advertencias'],
              ['Regla de cierre','Solo la columna FINAL VALIDADA tiene carácter definitivo'],
              ['Aviso','Los trimestres pueden ser provisionales y no sustituyen al cierre docente']]
    overview.extend([['ADVERTENCIA',msg] for msg in warnings])
    sheets=[('Resumen',overview),('Alumnado',[['Código','Nombre','Apellidos'],*student_rows(state)]),
            ('Evaluaciones',[heads,*rows]),('Evidencias',[h_details,*details]),
            ('Additio RA CE',[matrix_headers,*matrix_rows]),
            ('RA configuración',[['Sigla Additio','Código RA original','Descripción','Peso RA (%)'],*additio_curriculum(state,module_id)[0]]),
            ('CE configuración',[['Código CE Additio','Código CE original','Descripción','Sigla RA Additio','RA original','Peso CE (%)','Unidades vinculadas','Trimestres'],*additio_curriculum(state,module_id)[1]]),
            ('Instrucciones',[
              ['EXPORTACION ADDITIO - GUIA'],
              ['1','Importe el CSV de alumnado desde la herramienta de Excel de Additio; asigne las columnas en su asistente.'],
              ['2','En un grupo existente, compruebe que el orden del alumnado coincida antes de pegar valores.'],
              ['3','El archivo TSV ofrece valores separados por tabuladores para copiar y pegar columnas.'],
              ['4','La matriz para Additio incluye SOLO columnas de RA y CE; no contiene instrumentos.'],
              ['5','Los RA se configuran con la hoja RA configuración; los CE se importan con el archivo exclusivo de una columna.'],
              ['6','Sin cierre docente vigente la calificación final permanece vacía.'],
              ['7','No utilice los datos exportados para publicar calificaciones sin su comprobación.']])]
    if format=='xlsx':
        import xlsxwriter
        blob=io.BytesIO()
        with xlsxwriter.Workbook(blob,{'in_memory':True}) as wb:
            wb.set_properties({'title':f'EvalúaFP - {module["name"]}','author':'EvalúaFP Local'})
            navy=wb.add_format({'bold':True,'font_color':'#FFFFFF','bg_color':'#142D4E','text_wrap':True,'valign':'vcenter','border':1,'border_color':'#DFE5EC'})
            normal=wb.add_format({'font_size':10,'valign':'vcenter','border':1,'border_color':'#E8ECF0'})
            numeric=wb.add_format({'font_size':10,'num_format':'0.00','border':1,'border_color':'#E8ECF0'})
            warning=wb.add_format({'font_color':'#A94400','text_wrap':True})
            for title,table in sheets:
                ws=wb.add_worksheet(title)
                ws.freeze_panes(1,2 if len(table[0])>2 else 1)
                ws.set_row(0,28)
                ws.set_column(0,0,20)
                ws.set_column(1,1,33)
                ws.set_column(2,max(2,len(table[0])-1),18)
                for ix,row in enumerate(table):
                    for col,v in enumerate(row):
                        if isinstance(v,(float,int)) and not isinstance(v,bool):
                            ws.write_number(ix,col,v,numeric)
                        else:
                            ws.write_string(ix,col,str(safe_cell(v)),navy if ix==0 else (warning if title=='Resumen' and row and row[0]=='ADVERTENCIA' else normal))
                if title in ('Evaluaciones','Evidencias','Alumnado','Additio RA CE','RA configuración','CE configuración') and len(table)>1:
                    ws.autofilter(0,0,len(table)-1,len(table[0])-1)
                if title=='Resumen':ws.set_column(1,1,85)
                if title=='Instrucciones':ws.set_column(1,1,105)
        return blob.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',f'EvaluaFP_Evaluacion_Modulo_{module_id}.xlsx'
    if format=='xls':
        try:import xlwt
        except ImportError as exc:raise RuntimeError('Falta la dependencia xlwt para generar un XLS auténtico. Recompile EvalúaFP.') from exc
        for title,table in sheets:
            if len(table)>65536 or any(len(row)>256 for row in table):
                raise ValueError('La exportación XLS clásico excede 65.536 filas o 256 columnas. Utilice XLSX para evitar pérdida de datos.')
        wb=xlwt.Workbook(encoding='utf-8')
        style=xlwt.easyxf('font: bold on, color white; pattern: pattern solid, fore_colour dark_blue; align: vert centre;')
        for title,table in sheets:
            sh=wb.add_sheet(title[:31]);sh.col(0).width=6200;sh.col(1).width=9600
            for ix,row in enumerate(table):
                for col,v in enumerate(row):
                    sh.write(ix,col, safe_cell(v),style if ix==0 else xlwt.Style.default_style)
        blob=io.BytesIO();wb.save(blob)
        return blob.getvalue(),'application/vnd.ms-excel',f'EvaluaFP_Evaluacion_Modulo_{module_id}.xls'
    raise ValueError('Formato de Excel no admitido.')
