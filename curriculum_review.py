"""EvalúaFP — extraction, provenance and safe comparison of RA/CE.

Stand-alone additive module. No LLM, no network, no automatic legal approval.
Only explicit RA/CE blocks; everything remains subject to teacher review.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import json
import re
import unicodedata

MAX_FILE = 15 * 1024 * 1024
MAX_PAGES = 200
MAX_RA = 40
MAX_CE = 250


class CurriculumError(ValueError):
    pass


@dataclass(frozen=True)
class SourceLine:
    text: str
    location: str


def fold(text: str) -> str:
    text = unicodedata.normalize('NFKD', str(text or '').casefold())
    return ' '.join(''.join(ch for ch in text if not unicodedata.combining(ch)).split())


def _read_pdf(blob: bytes) -> list[SourceLine]:
    try:
        import fitz
    except ImportError as ex:
        raise CurriculumError('Se necesita PyMuPDF para leer PDF: pip install pymupdf.') from ex
    try:
        doc = fitz.open(stream=blob, filetype='pdf')
    except Exception as ex:
        raise CurriculumError('No ha sido posible abrir el PDF.') from ex
    with doc:
        if doc.is_encrypted:
            raise CurriculumError('El PDF está protegido contra lectura.')
        if doc.page_count > MAX_PAGES:
            raise CurriculumError('Se admiten como máximo 200 páginas.')
        result: list[SourceLine] = []
        for i, page in enumerate(doc):
            for line in page.get_text('text', sort=True).splitlines():
                line = ' '.join(line.replace('\xa0', ' ').split())
                if line:
                    result.append(SourceLine(line, f'página {i+1}'))
        return result


def _read_docx(blob: bytes) -> list[SourceLine]:
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as ex:
        raise CurriculumError('Se necesita python-docx: pip install python-docx.') from ex
    try:
        doc = Document(__import__('io').BytesIO(blob))
    except Exception as ex:
        raise CurriculumError('El archivo Word no se puede abrir.') from ex
    lines: list[SourceLine] = []
    n = 0
    # Mantener el orden de párrafos y tablas (sin inferir páginas inexistentes en DOCX).
    for element in doc.element.body.iterchildren():
        if element.tag == qn('w:p'):
            n += 1
            text = Paragraph(element, doc).text
            for value in text.splitlines():
                if value.strip():
                    lines.append(SourceLine(' '.join(value.split()), f'párrafo {n}'))
        elif element.tag == qn('w:tbl'):
            table = Table(element, doc)
            for row in table.rows:
                n += 1
                for cell in row.cells:
                    for value in cell.text.splitlines():
                        if value.strip():
                            lines.append(SourceLine(' '.join(value.split()), f'tabla, fila {n}'))
    return lines


def read_source(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise CurriculumError('No existe el documento indicado.')
    if p.stat().st_size > MAX_FILE:
        raise CurriculumError('El documento supera el límite de 15 MB.')
    blob = p.read_bytes()
    ext = p.suffix.lower()
    if ext == '.pdf':
        if not blob.startswith(b'%PDF'):
            raise CurriculumError('La cabecera no corresponde a un PDF.')
        lines = _read_pdf(blob)
    elif ext == '.docx':
        if not blob.startswith(b'PK'):
            raise CurriculumError('La cabecera no corresponde a un DOCX.')
        lines = _read_docx(blob)
    elif ext in ('.txt', '.md'):
        try:
            content = blob.decode('utf-8-sig')
        except UnicodeError as ex:
            raise CurriculumError('Utilice texto UTF-8 para archivos TXT y MD.') from ex
        lines = [SourceLine(' '.join(line.split()), f'línea {i}')
                 for i, line in enumerate(content.splitlines(), 1) if line.strip()]
    else:
        raise CurriculumError('Solo se admiten archivos PDF, DOCX, TXT o MD.')
    if not lines:
        raise CurriculumError('Documento sin texto legible: convierta o reconozca el PDF mediante OCR.')
    return {'filename': p.name, 'sha256': sha256(blob).hexdigest(), 'lines': lines,
            'format': ext[1:], 'bytes': len(blob)}


BEGIN = re.compile(r'^resultados?\s+de\s+aprendizaje\s+y\s+criterios?\s+de\s+evaluacion(?:\s*[.:]\s*contenidos)?[.:]?\s*$')
END = re.compile(r'^(?:contenidos(?:\s+basicos)?|orientaciones\s+pedagogicas|metodologia|evaluacion\s+y\s+calificacion|distribucion\s+de\s+las\s+actividades\s+de\s+aprendizaje)\s*(?:[.:]|$)')
RA_NUMBERED = re.compile(r'^\s*(?:[-–•]\s*)?RA\s*(\d{1,2})\s*[.:\-]\s*(.*)$', re.I)
RA_LEGAL = re.compile(r'^\s*(\d{1,2})\s*[.]\s+(.+)$')
CE_MARK = re.compile(r'^\s*([a-zñ])\)\s*(.*)$', re.I)
CE_HEADING = re.compile(r'^criterios?\s+de\s+evaluacion\s*[:.]?\s*$')
BOE_MODULE = re.compile(r'^modulo\s+profesional\s*:', re.I)


def _sections(lines: list[SourceLine]):
    starts = [i for i, row in enumerate(lines) if BEGIN.fullmatch(fold(row.text))]
    if not starts:
        raise CurriculumError('No se ha identificado un apartado explícito de resultados de aprendizaje y criterios de evaluación.')
    for index in starts:
        selected = []
        for row in lines[index + 1:]:
            normal = fold(row.text).strip(' .:')
            if END.fullmatch(normal):
                break
            if BOE_MODULE.match(normal) and selected:
                break
            selected.append(row)
        yield index, selected


def _parse_block(block: list[SourceLine], allow_numbered: bool):
    outcomes = []
    current = None
    current_criterion = None
    ce_zone = False

    def flush():
        nonlocal current
        if current:
            outcomes.append(current)

    for row in block:
        text = row.text.strip()
        normal = fold(text)
        ra = RA_NUMBERED.match(text)
        if not ra and allow_numbered:
            ra = RA_LEGAL.match(text)
        if ra:
            flush()
            current = {'code': 'RA'+str(int(ra.group(1))), 'description':ra.group(2).strip(),
                       'locations':[row.location], 'criteria':[]}
            current_criterion=None
            ce_zone=False
            continue
        if CE_HEADING.fullmatch(normal):
            if current:
                ce_zone=True
                current_criterion=None
            continue
        if not current:
            continue
        ce = CE_MARK.match(text) if ce_zone else None
        if ce:
            current_criterion = {'code':current['code']+'.'+ce.group(1).lower(),
                                 'description':ce.group(2).strip(),
                                 'locations':[row.location]}
            current['criteria'].append(current_criterion)
            continue
        if ce_zone and current_criterion:
            current_criterion['description'] += ' '+text
            if row.location not in current_criterion['locations']:
                current_criterion['locations'].append(row.location)
        elif not ce_zone:
            current['description'] += ' '+text
            if row.location not in current['locations']:
                current['locations'].append(row.location)
    flush()
    return outcomes


def _validate(outcomes: list, expected_min_ra: int = 1):
    if not expected_min_ra <= len(outcomes) <= MAX_RA:
        raise CurriculumError('La extracción no presenta una cantidad fiable de RA.')
    codes=[x['code'] for x in outcomes]
    if len(set(codes)) != len(codes):
        raise CurriculumError('Hay RA repetidos en el apartado seleccionado.')
    # Omitir un RA intermedio es demasiado peligroso: no permitir confirmar.
    values=sorted(int(x[2:]) for x in codes)
    if values != list(range(1,len(values)+1)):
        raise CurriculumError('Los RA no forman una secuencia completa desde RA1; revise el documento.')
    ce_total=0
    for ra in outcomes:
        if len(ra['description']) < 18:
            raise CurriculumError(f"El enunciado de {ra['code']} está incompleto.")
        criteria=ra['criteria']
        if not criteria:
            raise CurriculumError(f"No se han encontrado CE en {ra['code']}.")
        names = [x['code'] for x in criteria]
        if len(set(names)) != len(names):
            raise CurriculumError(f"Existen CE duplicados en {ra['code']}.")
        abc = 'abcdefghijklmnñopqrstuvwxyz'
        letters = [name.split('.')[-1] for name in names]
        if letters != list(abc[:len(letters)]):
            raise CurriculumError(f"Los criterios de {ra['code']} no siguen una secuencia alfabética completa desde a).")
        for ce in criteria:
            if len(ce['description']) < 12:
                raise CurriculumError(f"El criterio {ce['code']} parece incompleto.")
        ce_total+=len(criteria)
    if ce_total > MAX_CE:
        raise CurriculumError('Se ha superado el máximo de 250 criterios.')
    return ce_total


def _identification(lines: list[SourceLine], module_name: str, module_code: str):
    # La fuente tiene que contener el código y el nombre. En un título estatal
    # con múltiples módulos no basta con mencionar el código en otro apartado.
    if not isinstance(module_name,str) or len(module_name.strip()) < 5:
        raise CurriculumError('Introduzca la denominación oficial completa del módulo.')
    if not isinstance(module_code,str) or not re.fullmatch(r'\d{4}',module_code):
        raise CurriculumError('Indique el código oficial de cuatro cifras del módulo.')
    all_text=' '.join(fold(row.text) for row in lines)
    if fold(module_name) not in all_text:
        raise CurriculumError('La denominación indicada no figura en el documento.')
    if not re.search(r'(?<!\d)'+re.escape(module_code)+r'(?!\d)',all_text):
        raise CurriculumError('El código oficial indicado no figura en el documento.')


def preview(path: str | Path, module_name: str, module_code: str,
            *, document_kind: str = 'programacion') -> dict:
    """Produce borrador con citas, sin consultar Internet ni tocar notas.

    Para una norma oficial multímódulo exige un único bloque verificable.
    Esta función no afirma que una norma esté vigente.
    """
    if document_kind not in ('programacion','norma_oficial'):
        raise CurriculumError('Seleccione programación o norma oficial.')
    source = read_source(path)
    lines = source.pop('lines')
    _identification(lines,module_name,module_code)
    candidates=[]
    for i, section in _sections(lines):
        if document_kind == 'norma_oficial':
            # Cada bloque jurídico pertenece al ÚLTIMO encabezado de módulo
            # previo. Que el nombre y código aparezcan en otro lugar del PDF
            # no autoriza importar los RA/CE de un módulo diferente.
            indices = [j for j in range(i) if BOE_MODULE.match(fold(lines[j].text))]
            if not indices:
                continue
            previous = indices[-1]
            context = fold(' '.join(row.text for row in lines[previous:i]))
            if (fold(module_name) not in context or
                    not re.search(r'(?<!\d)'+re.escape(module_code)+r'(?!\d)',context)):
                continue
        ras = _parse_block(section, allow_numbered=(document_kind=='norma_oficial'))
        if ras:
            candidates.append((i,ras))
    if not candidates:
        raise CurriculumError('El apartado identificado no contiene RA y CE explícitos.')
    # No escoger arbitrariamente entre varios bloques jurídicos o tablas internas.
    if len(candidates)!=1:
        raise CurriculumError('Se han encontrado varios apartados de RA/CE; seleccione un extracto inequívoco del módulo.')
    _, ras=candidates[0]
    ce_count=_validate(ras)
    return {'schema':'evaluafp-ra-ce-preview/1','status':'pendiente_revision_docente',
            'module_name': module_name.strip(),'module_code':module_code,
            'document_kind':document_kind,
            'source':source, 'extracted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'outcomes':ras,'summary':{'ra':len(ras),'ce':ce_count},
            'warnings':['La coincidencia estructural no confirma la vigencia del currículo ni su desarrollo autonómico.',
                        'Los datos y las ponderaciones existentes no se modifican sin una confirmación docente explícita.']}


def _weights(n):
    """Céntimos que cierran exactamente 100,00 % en orden determinista."""
    if n<1:
        return []
    cents=10000
    base,rest=divmod(cents,n)
    return [Decimal(base+(i<rest))/100 for i in range(n)]


def propose_equal_weights(report: dict):
    """Regla por defecto: todos los CE tienen el mismo peso GLOBAL.

    El RA se pondera por número de CE y cada CE tiene igual peso en el RA.
    No cambia ni confirma una programación existente.
    """
    ras = report['outcomes']
    _validate(ras)
    all_ce = [ce for ra in ras for ce in ra['criteria']]
    global_ce = _weights(len(all_ce))
    cursor=0
    result=[]
    for ra in ras:
        chunk = global_ce[cursor:cursor+len(ra['criteria'])]
        cursor+=len(chunk)
        ra_weight=sum(chunk,Decimal(0))
        local_ce=_weights(len(chunk))
        result.append({'code':ra['code'],'module_weight_pct':str(ra_weight),
                       'criteria':[{'code':ce['code'],'module_weight_pct':str(global_weight),
                                   'ra_weight_pct':str(local_weight)}
                                   for ce,global_weight,local_weight in zip(ra['criteria'],chunk,local_ce)]})
    assert sum(Decimal(x['module_weight_pct']) for x in result)==Decimal('100')
    return result


def compare(report:dict, existing_outcomes:list[dict]):
    """Diff sin mutaciones. Los existentes pueden tener CE, notas y pesos manuales."""
    def desc(x):return fold(x.get('description',''))
    new={r['code']:r for r in report['outcomes']}
    old={str(r['code']).replace(' ','').upper():r for r in existing_outcomes}
    rows=[]
    for code in sorted(set(new)|set(old), key=lambda s: (int(re.search(r'\d+',s).group()) if re.search(r'\d+',s) else 999,s)):
        old_ra=old.get(code); new_ra=new.get(code)
        if old_ra is None:
            rows.append({'code':code,'state':'nuevo_ra','old':'','new':new_ra['description']})
            for item in new_ra['criteria']:
                rows.append({'code':item['code'],'state':'nuevo_ce','old':'','new':item['description']})
            continue
        if new_ra is None:
            rows.append({'code':code,'state':'faltante_ra','old':old_ra.get('description',''),'new':''})
            for item in old_ra.get('criteria',[]):
                rows.append({'code':item['code'],'state':'faltante_ce','old':item.get('description',''),'new':''})
            continue
        if desc(old_ra)!=desc(new_ra):
            rows.append({'code':code,'state':'cambio_enunciado_ra','old':old_ra['description'],
                        'new':new_ra['description'],
                        'similarity':round(SequenceMatcher(None,desc(old_ra),desc(new_ra)).ratio(),3)})
        old_ce={str(c['code']).lower().replace(' ',''):c for c in old_ra.get('criteria',[])}
        new_ce={c['code'].lower():c for c in new_ra.get('criteria',[])}
        for criterion in sorted(set(old_ce)|set(new_ce)):
            a=old_ce.get(criterion);b=new_ce.get(criterion)
            if a is None: rows.append({'code':criterion,'state':'nuevo_ce','old':'','new':b['description']})
            elif b is None: rows.append({'code':criterion,'state':'faltante_ce','old':a['description'],'new':''})
            elif desc(a)!=desc(b):
                rows.append({'code':criterion,'state':'cambio_enunciado_ce','old':a['description'],
                            'new':b['description'],
                            'similarity':round(SequenceMatcher(None,desc(a),desc(b)).ratio(),3)})
    statuses=Counter(x['state'] for x in rows)
    return {'differences':rows,'counts':dict(statuses),
            'blocking':bool(existing_outcomes),
            'notice':'Si ya existen RA/CE, las diferencias deben revisarse; no se sobrescriben calificaciones ni pesos manuales.'}


def dump_report(report,path):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return p
