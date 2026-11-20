"""Vista previa local de tablas horarias en PDF/DOCX, sin envío a una IA.

Solo acepta filas con código, módulo, horas totales y horas semanales visibles.
Nunca asume que las cifras leídas están vigentes ni las guarda automáticamente.
"""
from __future__ import annotations

import csv
import io
import re

import national_registry as registry

MAX_FILE = 15 * 1024 * 1024
MAX_PAGES = 80
MAX_ROWS = 300
HEADER = ['Código','Módulo','Horas totales','Horas semanales']


def _fold(value):
    import territorial_profiles as territory
    return re.sub(r'[^a-z0-9]+',' ',territory.fold(value)).strip()


def _index(header):
    semantic={
     'code':('codigo','codigo modulo','cod','cod modulo','codigo del modulo'),
     'name':('modulo','modulo profesional','denominacion','nombre modulo','denominacion modulo'),
     'annual':('horas totales','horas anuales','total horas','horas curso','duracion en horas'),
     'weekly':('horas semanales','h semanales','horas semana','horas por semana','horas sem'),
    }
    cols={}
    for key,options in semantic.items():
        matches=[i for i,s in enumerate(header) if _fold(s) in options]
        if len(matches)!=1:return None
        cols[key]=matches[0]
    if len(set(cols.values())) !=4:return None
    return cols


def _rows_from_table(matrix):
    """Cabeceras claras y completas obligatorias. No se adivina el sentido de columnas."""
    if not matrix:return []
    for h,heading in enumerate(matrix[:8]):
        cols=_index([str(x or '').replace('\n',' ') for x in heading])
        if not cols:continue
        result=[]
        for cells in matrix[h+1:]:
            if max(cols.values())>=len(cells):continue
            vals=[str(cells[cols[k]] or '').replace('\n',' ').strip() for k in ('code','name','annual','weekly')]
            if not any(vals):continue
            if not vals[0] or not vals[1]:continue
            if not re.fullmatch(r'[A-Za-z0-9_.-]{2,30}', vals[0]):continue
            # Conserva filas completas para el validador ya existente.
            result.append(vals)
        return result
    return []


def _rows_from_text(text):
    """Fallback estricto para PDF sin líneas de tabla pero con columnas en la misma línea."""
    rows=[]
    for line in text.splitlines():
        line=line.strip()
        if len(line)>280 or len(line)<12:continue
        # Código 4 dígitos, título, número total (20-2500), número semanal (1-40).
        m=re.fullmatch(r'(\d{4})\s+(.{5,180}?)\s+(\d{2,4}(?:[,.]\d{1,2})?)\s+(\d{1,2}(?:[,.]\d{1,2})?)',line)
        if not m:continue
        try:
            registry.number(m[3],'Horas totales',2500)
            registry.number(m[4],'Horas semanales',40)
        except ValueError:continue
        rows.append([m[1],m[2],m[3],m[4]])
    return rows


def _parse_docx(blob):
    from docx import Document
    document=Document(io.BytesIO(blob))
    rows=[]
    for table in document.tables:
        matrix=[[cell.text for cell in row.cells] for row in table.rows]
        rows.extend(_rows_from_table(matrix))
    return rows,0,False


def _parse_pdf(blob, allow_ocr):
    import fitz
    rows=[]; pages_scanned=0;used_ocr=False
    try:
        doc=fitz.open(stream=blob,filetype='pdf')
    except Exception as exc:
        raise ValueError('El archivo PDF no se puede leer.') from exc
    with doc:
        if doc.is_encrypted:raise ValueError('El PDF está protegido. Facilite una copia con lectura permitida.')
        if doc.page_count>MAX_PAGES:raise ValueError('El documento supera el máximo de 80 páginas.')
        for page in doc:
            text=page.get_text('text')
            if len(text.strip())<70 and allow_ocr:
                if pages_scanned>=8:raise ValueError('El OCR de prueba admite ocho páginas escaneadas por archivo.')
                try:
                    text=page.get_text(textpage=page.get_textpage_ocr(language='spa',dpi=170,full=True))
                except Exception as exc:
                    raise ValueError('No se ha podido realizar OCR en este equipo. Necesita los datos españoles de Tesseract; también puede convertir el PDF a texto fuera de EvalúaFP.') from exc
                pages_scanned+=1;used_ocr=True
            if text.strip():rows.extend(_rows_from_text(text))
            # La extracción tabular de MuPDF aporta cabeceras y celdas más fiables.
            if hasattr(page,'find_tables'):
                try:
                    for table in page.find_tables().tables:
                        rows.extend(_rows_from_table(table.extract()))
                except Exception:pass
    return rows,pages_scanned,used_ocr


def preview_document(filename, blob, allow_ocr=False):
    if not isinstance(filename,str) or not isinstance(blob,bytes) or len(blob)==0 or len(blob)>MAX_FILE:
        raise ValueError('Adjunte un documento PDF o Word de hasta 15 MB.')
    name=filename.lower()
    if name.endswith('.docx'):
        if not blob.startswith(b'PK'):
            raise ValueError('El archivo no es un DOCX válido.')
        try:rows,ocr_pages,used_ocr=_parse_docx(blob)
        except Exception as exc:
            raise ValueError('No se han podido leer las tablas de Word.') from exc
    elif name.endswith('.pdf'):
        if not blob.startswith(b'%PDF-'):
            raise ValueError('El archivo no es un PDF válido.')
        rows,ocr_pages,used_ocr=_parse_pdf(blob,allow_ocr)
    else:
        raise ValueError('Solo se admiten documentos PDF y Word (.docx).')
    # Evita mostrar fichas contradictorias por el mismo código.
    unique={}
    for row in rows:
        code=row[0].strip()
        if code not in unique:unique[code]=row
        elif unique[code] != row:
            raise ValueError(f'El documento presenta varias filas incompatibles para {code}. Revise su versión.')
    if not unique:
        raise ValueError('No se han identificado tablas con código, nombre, horas totales y semanales. Compruebe la disposición o copie su tabla con encabezados. El OCR puede ayudar si el PDF es una imagen.')
    if len(unique)>MAX_ROWS:raise ValueError('Se han detectado más de 300 módulos; divida el documento.')
    out=io.StringIO();writer=csv.writer(out,delimiter=';',lineterminator='\n')
    writer.writerow(HEADER);writer.writerows(unique.values())
    # Usa el validador nacional ya existente antes de devolver la propuesta.
    preview=registry.preview_hours_table(out.getvalue())
    return {**preview,'table':out.getvalue(),'ocr_used':used_ocr,'ocr_pages':ocr_pages,
            'source_type':'.pdf' if name.endswith('.pdf') else '.docx',
            'requires_teacher_confirmation':True,
            'notice':'Filas LEÍDAS del documento, no horas verificadas ni necesariamente vigentes. Debe confirmar norma, territorio, ciclo y curso antes de incorporarlas a la biblioteca.'}
