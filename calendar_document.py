"""Vista previa conservadora de calendarios escolares (PDF/DOCX/TXT/MD).

No consulta una IA ni acredita la vigencia de normas. Lee únicamente fechas
LITERALES con contexto; exige cotejo de comunidad, curso y etapa y no escribe
nunca en SQLite. Los documentos escaneados necesitan OCR opcional.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

import territorial_profiles as territories
import calendar_annex

MAX_FILE = 15 * 1024 * 1024
MAX_PAGES = 80
MAX_OCR_PAGES = 8
MAX_RECORDS = 6000
MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
}
MONTH_RX = '|'.join(MONTHS)
DATE_RX = (r'(?:20\d{2}-\d{2}-\d{2}|'
           r'\d{1,2}[/-]\d{1,2}[/-]20\d{2}|'
           rf'\d{{1,2}}\s+de\s+(?:{MONTH_RX})\s+de\s+20\d{{2}})')
DATE_RE = re.compile(rf'(?<!\w)({DATE_RX})(?!\w)', re.I)
RANGE_RE = re.compile(
    rf'\b(?:del|desde\s+el|desde|entre\s+el)\s+({DATE_RX})\s+'
    rf'(?:al|hasta\s+el|hasta|y\s+el)\s+({DATE_RX})', re.I)
COURSE_RE = re.compile(r'(?<!\d)(20\d{2})\s*[-/–]\s*(20\d{2})(?!\d)')
FP_RE = re.compile(r'(?<!\w)(?:fp|formacion profesional|grado d|ciclos? formativos?)(?!\w)')
OTHER_STAGE_RE = re.compile(r'\b(?:infantil|primaria|eso|bachillerato|secundaria|educacion especial)\b')
START_RE = re.compile(r'\b(?:inicio|iniciacion|comienzo|comienzan|comenzaran|comenzara|'
                      r'empezaran|empiezan|inicio de actividad(?:es)? lectiv(?:a|as))\b')
END_RE = re.compile(r'\b(?:fin|final|finalizacion|finalizan|terminaran|conclusion|'
                    r'termino|acaban|ultimo dia)\b')
SCHOOL_RE = re.compile(r'\b(?:clases|lectiv[oa]s?|curso|actividad(?:es)? educativas?)\b')
VACATION_RE = re.compile(r'\b(?:vacaciones|navidad|semana santa|periodo no lectivo)\b')
HOLIDAY_RE = re.compile(r'\b(?:festiv[oa]|fiesta|dia no lectivo|no lectiv[oa]|inhabil)\b')
EVAL_RE = re.compile(r'\b(?:evaluacion|trimestre)\b')
TERRITORY_ALIASES = {
    'AN': ('andalucia',), 'AR': ('aragon',), 'AS': ('asturias',),
    'IB': ('illes balears', 'islas baleares', 'baleares'),
    'CN': ('canarias', 'islas canarias'), 'CB': ('cantabria',),
    'CM': ('castilla-la mancha', 'castilla la mancha'),
    'CL': ('castilla y leon',), 'CT': ('cataluna', 'catalunya'),
    'VC': ('comunitat valenciana', 'comunidad valenciana'),
    'EX': ('extremadura',), 'GA': ('galicia',),
    'MD': ('comunidad de madrid', 'madrid'),
    'MC': ('region de murcia', 'murcia'),
    'NC': ('navarra',), 'PV': ('pais vasco', 'euskadi'),
    'RI': ('la rioja', 'rioja'), 'CE': ('ceuta',), 'ML': ('melilla',),
}


def _parse_date(value):
    v = territories.fold(value)
    if re.fullmatch(r'20\d{2}-\d{2}-\d{2}', v):
        return date.fromisoformat(v)
    m = re.fullmatch(r'(\d{1,2})[/-](\d{1,2})[/-](20\d{2})', v)
    if m:
        return date(int(m[3]), int(m[2]), int(m[1]))
    m = re.fullmatch(rf'(\d{{1,2}}) de ({MONTH_RX}) de (20\d{{2}})', v)
    if m:
        return date(int(m[3]), MONTHS[m[2]], int(m[1]))
    raise ValueError('Fecha no reconocida en el documento.')


def _records_from_docx(blob):
    from docx import Document
    try:
        doc = Document(BytesIO(blob))
        records = []
        for i, paragraph in enumerate(doc.paragraphs, 1):
            if paragraph.text.strip():
                records.append({'text': paragraph.text, 'location': f'párrafo {i}'})
        for j, table in enumerate(doc.tables, 1):
            matrix=[[cell.text for cell in row.cells] for row in table.rows]
            for i, cells in enumerate(matrix, 1):
                value=' | '.join(c.strip().replace('\n',' ') for c in cells)
                if value.strip(' |'):
                    records.append({'text': value, 'location': f'tabla {j}, fila {i}'})
            records.extend(calendar_annex.table_records(matrix,f'tabla {j}'))
        return records, False, 0, []
    except Exception as exc:
        raise ValueError('No se puede leer el documento Word; compruebe el archivo.') from exc


def _records_from_pdf(blob, allow_ocr):
    import fitz
    try:
        doc=fitz.open(stream=blob,filetype='pdf')
    except Exception as exc:
        raise ValueError('No se puede leer el PDF.') from exc
    records=[];warnings=[];scanned=0;used=False
    with doc:
        if doc.is_encrypted:
            raise ValueError('El PDF está cifrado; facilite una copia con lectura permitida.')
        if doc.page_count>MAX_PAGES:
            raise ValueError('El PDF supera las 80 páginas admitidas.')
        for n,page in enumerate(doc,1):
            value=page.get_text('text')
            if len(value.strip())<35:
                if allow_ocr:
                    if scanned>=MAX_OCR_PAGES:
                        raise ValueError('El OCR admite hasta ocho páginas escaneadas por archivo.')
                    try:
                        value=page.get_text(textpage=page.get_textpage_ocr(language='spa',dpi=170,full=True))
                    except Exception as exc:
                        raise ValueError('Falta Tesseract con el idioma español o no se ha podido completar el OCR.') from exc
                    scanned+=1;used=True
                else:
                    warnings.append(f'Página {n}: sin texto seleccionable; no se ha aplicado OCR.')
            page_records=[{'text':line,'location':f'página {n}'}
                          for line in value.splitlines() if line.strip()]
            records.extend(calendar_annex.stitched_records(
                page_records,DATE_RE,RANGE_RE,START_RE,END_RE,SCHOOL_RE,VACATION_RE))
            if hasattr(page,'find_tables'):
                try:
                    for j,table in enumerate(page.find_tables().tables,1):
                        records.extend(calendar_annex.table_records(table.extract(),
                                     f'página {n}, tabla {j}'))
                except Exception:
                    warnings.append(f'Página {n}: no se pudieron inspeccionar las tablas; revise el texto y las celdas.')
    return records,used,scanned,warnings


def _records_from_text(blob):
    try:
        text=blob.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Utilice texto UTF-8 para el calendario.') from exc
    return ([{'text':x,'location':f'línea {n}'} for n,x in enumerate(text.splitlines(),1) if x.strip()],False,0,[])


def _within_course(value, academic_year):
    start=int(academic_year[:4]);end=int(academic_year[5:])
    return date(start,9,1)<=value<=date(end,8,31)


def _period_label(context):
    if 'navidad' in context:return 'Vacaciones de Navidad'
    if 'semana santa' in context:return 'Vacaciones de Semana Santa'
    return 'Periodo no lectivo (revisar denominación)'


def _candidates(records, academic_year):
    candidates=[];warnings=[]
    # Conserva la etapa identificada por los últimos encabezados cortos de la
    # misma página. Una fecha de Bachillerato en la línea posterior a su
    # encabezado no debe atribuirse automáticamente a FP.
    active_stage=None
    previous_page=None
    # Se limita la extracción a líneas/filas que ofrezcan una relación explícita
    # con el concepto. No se rellena nunca un año ausente en el texto.
    for row in records[:MAX_RECORDS]:
        text=' '.join(row['text'].split())[:450]
        original=' '.join(row.get('excerpt',row['text']).split())[:450]
        if not text:continue
        folded=territories.fold(text)
        current_page=row['location'] if row['location'].startswith('página ') else None
        if current_page and previous_page and current_page!=previous_page:
            active_stage=None
        previous_page=current_page
        if not DATE_RE.search(folded) and len(folded)<=140:
            if OTHER_STAGE_RE.search(folded) and not FP_RE.search(folded):
                active_stage='other'
            elif FP_RE.search(folded):
                active_stage='fp'
        if OTHER_STAGE_RE.search(folded) and not FP_RE.search(folded):
            continue
        if active_stage=='other' and not FP_RE.search(folded):
            continue
        found=list(DATE_RE.finditer(folded))
        if not found:continue
        loc=row['location']
        def add(field, value, label):
            candidates.append({'field':field,'value':value,'label':label,
                'excerpt':original[:300],'location':loc})
        matches=list(RANGE_RE.finditer(folded))
        if VACATION_RE.search(folded):
            for match in matches:
                try:
                    start,end=_parse_date(match[1]),_parse_date(match[2])
                except ValueError:
                    warnings.append(f'{loc}: intervalo de fechas inválido; se descarta.')
                    continue
                if (not _within_course(start,academic_year) or
                    not _within_course(end,academic_year) or
                    end<start or (end-start).days>100):
                    warnings.append(f'{loc}: intervalo fuera del curso o demasiado extenso; se descarta.')
                    continue
                label=_period_label(folded)
                add('vacation_periods',{'start':start.isoformat(),
                    'end':end.isoformat(),'label':label},label)
        if len(found)==1 and SCHOOL_RE.search(folded) and not EVAL_RE.search(folded) and not VACATION_RE.search(folded):
            try:when=_parse_date(found[0][1])
            except ValueError:continue
            if not _within_course(when,academic_year):
                continue
            if START_RE.search(folded) and not END_RE.search(folded):
                add('start_date',when.isoformat(),'Inicio de clases/actividad lectiva')
            if END_RE.search(folded) and not START_RE.search(folded):
                add('end_date',when.isoformat(),'Fin de clases/actividad lectiva')
        if HOLIDAY_RE.search(folded) and not VACATION_RE.search(folded):
            # No se copia un periodo entero como una lista de festivos.
            if len(found)==1:
                try:when=_parse_date(found[0][1])
                except ValueError:continue
                if _within_course(when,academic_year):
                    add('regional_non_teaching_days',{'date':when.isoformat(),
                         'reason':original[:120]},'Día festivo o no lectivo')
    # No se devuelve una propuesta única si hay fuentes conflictivas.
    unique={};grouped={}
    for c in candidates:
        key=(c['field'],repr(c['value']))
        unique.setdefault(key,c)
    for c in unique.values():grouped.setdefault(c['field'],[]).append(c)
    for key in ('start_date','end_date'):
        if len(grouped.get(key,[]))>1:
            warnings.append(f'{key}: hay fechas incompatibles en el documento; se omite la propuesta automática.')
            grouped[key]=[]
    if grouped.get('start_date') and grouped.get('end_date'):
        if grouped['start_date'][0]['value']>=grouped['end_date'][0]['value']:
            warnings.append('Las fechas extraídas de inicio y fin son incompatibles; ambas se omiten.')
            grouped['start_date']=[];grouped['end_date']=[]
    vacations=grouped.get('vacation_periods',[])
    by_label={}
    for c in vacations:by_label.setdefault(c['value']['label'],[]).append(c)
    grouped['vacation_periods']=[v[0] for v in by_label.values() if len(v)==1]
    for label,choices in by_label.items():
        if len(choices)>1:warnings.append(f'{label}: intervalos incompatibles; se descartan hasta la revisión docente.')
    for field in ('vacation_periods','regional_non_teaching_days'):
        grouped[field]=grouped.get(field,[])[:100]
    return grouped,warnings


def _fragment_for_optional_ai(records, region, academic_year):
    """Prepara únicamente texto local para revisión; jamás lo envía a la IA.

    Conserva el contexto territorial/etapa/año y fragmentos de fechas/tablas,
    sin usar cifras sueltas como si fueran confirmadas. El docente lo edita.
    """
    terms=TERRITORY_ALIASES[territories.territory_code(region)]
    selected=[];seen=set()
    for index,row in enumerate(records):
        raw=' '.join(row.get('excerpt',row['text']).split())[:450]
        folded=territories.fold(raw)
        scoped=(any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',folded) for term in terms)
                or academic_year in folded or bool(FP_RE.search(folded)))
        date_related=bool(DATE_RE.search(folded)) or (
            bool(START_RE.search(folded) or END_RE.search(folded) or VACATION_RE.search(folded))
            and bool(SCHOOL_RE.search(folded) or VACATION_RE.search(folded)))
        if not ((scoped and index<100) or date_related):continue
        if raw in seen:continue
        seen.add(raw)
        if len('\n'.join(selected))+len(raw)>10500:break
        selected.append(raw)
        if len(selected)>=95:break
    return '\n'.join(selected)


def preview_document(filename, blob, region, academic_year, allow_ocr=False):
    """Analiza un archivo local, sin guardar originales ni tocar calificaciones.

    La procedencia no se confunde con vigencia jurídica y la etapa FP sigue
    sujeta a confirmación humana incluso si existe coincidencia textual.
    """
    region=territories.require_territory(region)
    academic_year=territories.year_code(academic_year)
    if not isinstance(filename,str) or not isinstance(blob,bytes) or not blob or len(blob)>MAX_FILE:
        raise ValueError('Adjunte un calendario PDF, DOCX, TXT o MD de hasta 15 MB.')
    if len(filename)>255 or '\x00' in filename or '\\' in filename or '/' in filename:
        raise ValueError('Nombre de archivo no válido.')
    kind=Path(filename).suffix.lower()
    if kind=='.pdf':
        if not blob.startswith(b'%PDF-'):raise ValueError('El archivo no tiene cabecera PDF.')
        records,ocr,ocr_pages,warnings=_records_from_pdf(blob,allow_ocr is True)
    elif kind=='.docx':
        if not blob.startswith(b'PK'):raise ValueError('El documento no tiene cabecera DOCX.')
        records,ocr,ocr_pages,warnings=_records_from_docx(blob)
    elif kind in ('.txt','.md'):
        records,ocr,ocr_pages,warnings=_records_from_text(blob)
    else:
        raise ValueError('Solo se admiten PDF, DOCX, TXT y MD.')
    if len(records)>MAX_RECORDS:
        raise ValueError('Documento demasiado extenso para extraer un calendario sin omisiones; divídalo.')
    full=territories.fold('\n'.join(row['text'] for row in records))
    terms=TERRITORY_ALIASES[territories.territory_code(region)]
    territory_match=any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',full) for term in terms)
    years={f'{a}-{b}' for a,b in COURSE_RE.findall(full)}
    year_match=academic_year in years
    stage_match=bool(FP_RE.search(full))
    scope_ok=territory_match and year_match and stage_match
    if not territory_match:
        warnings.append('No se acredita literalmente el territorio seleccionado en el texto: solo lectura orientativa.')
    if not year_match:
        warnings.append('No se acredita literalmente el curso académico seleccionado en el texto: no se podrán aplicar propuestas.')
    if not stage_match:
        warnings.append('No aparece una referencia explícita a Formación Profesional/FP: verifique la etapa.')
    values,extraction_warnings=_candidates(records,academic_year)
    warnings+=extraction_warnings
    count=sum(len(x) for x in values.values())
    if not count:warnings.append('No se han localizado fechas inequívocas. Introduzca los datos manualmente desde la resolución.')
    return {'filename':filename,'sha256':sha256(blob).hexdigest(),
            'region':region,'academic_year':academic_year,'scope_ok':scope_ok,
            'scope':{'territory_match':territory_match,'academic_year_match':year_match,'fp_match':stage_match,
                     'courses_in_document':sorted(years)},
            'candidates':values,'candidate_count':count,'warnings':list(dict.fromkeys(warnings))[:40],
            'ocr_used':ocr,'ocr_pages':ocr_pages,
            'suggested_ai_fragment':_fragment_for_optional_ai(records,region,academic_year) if scope_ok else '',
            'requires_teacher_confirmation':True,
            'no_changes_saved':True,'source_type':kind,
            'notice':('Vista previa textual, no comprobación de vigencia. Compruebe que las fechas corresponden a FP Grado D, '
                      'a su centro y a la última disposición/corrección. No se incorporarán horas, evaluaciones, FEOE ni notas.')}