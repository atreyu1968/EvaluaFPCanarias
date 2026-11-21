"""Lectura acotada del anexo 1 del Decreto canario 9/2023.

La descarga se realiza solo con consentimiento y desde la URL institucional.
El resultado es una referencia del ámbito completo; no se asigna a materias
o cursos ni se modifica un borrador hasta que el docente seleccione y guarde.
"""
import hashlib
import re
import urllib.request
from datetime import datetime, timezone

import common_scopes as cs

MAX_BYTES=12_000_000
DESCRIPTOR=r'(?:CCEC|CPSAA|CCL|STEM|CP|CD|CC|CE)\s*\d+'
DESCRIPTOR_LINE=re.compile(r'^\s*'+DESCRIPTOR+r'(?:\s*[,;]?\s*'+DESCRIPTOR+r')*\s*[,;.]?\s*$')
HEAD=re.compile(r'(?im)^\s*Competencia espec[ií]fica\s+(\d+)\s*:\s*')
CRITERION=re.compile(r'^(\d+\.\d+)\.\s*(.*)$')
EXPLAIN=re.compile(r'(?im)^\s*Explicaci[oó]n del bloque competencial\s*:')
DESCR_HEAD=re.compile(r'(?im)^\s*Descriptores operativos de las competencias clave\.\s*Perfil de salida\.\s*')
CRITERIA_HEAD=re.compile(r'(?im)^\s*Criterios de evaluaci[oó]n\s*:\s*')


def clean_page(text):
    result=[]
    for raw in text.splitlines():
        line=raw.strip().replace('\u0002','-').replace('\u00ad','')
        if not line or re.match(r'(?i)^(?:boc-a-2023-025-402|Boletín Oficial de Canarias núm\.|https?://sede\.gobiernodecanarias\.org/boc)',line):
            continue
        if re.fullmatch(r'\d{1,4}',line):
            continue
        result.append(line)
    return '\n'.join(result)


def descriptors(text):
    result=re.findall(DESCRIPTOR,text)
    return ', '.join(dict.fromkeys(re.sub(r'\s+','',x) for x in result))


def parse_blocks(text, expected):
    markers=list(HEAD.finditer(text))
    if [int(m.group(1)) for m in markers]!=list(range(1,expected+1)):
        raise ValueError('No se localizaron todos los bloques del ámbito en orden. Revise el PDF.')
    outcomes=[]
    for i,m in enumerate(markers):
        code=m.group(1)
        body=text[m.end():markers[i+1].start() if i+1<len(markers) else len(text)]
        d=DESCR_HEAD.search(body)
        c=CRITERIA_HEAD.search(body)
        e=EXPLAIN.search(body)
        if not d or not c or not e or not d.start()<c.start()<e.start():
            raise ValueError('No se identifican las tres secciones de la competencia '+code+'.')
        description=' '.join(body[:d.start()].split())
        descr=descriptors(body[d.end():c.start()])
        if not description or not descr:
            raise ValueError('Enunciado o descriptores incompletos en competencia '+code+'.')
        rows=[]
        current=None
        for line in body[c.end():e.start()].splitlines():
            line=line.strip()
            if not line:
                continue
            match=CRITERION.match(line)
            if match:
                if match.group(1)!=code+'.'+str(len(rows)+1):
                    raise ValueError('Numeración de criterios inesperada en competencia '+code+'.')
                current={'code':match.group(1),'description':match.group(2).strip(),'descriptors':''}
                rows.append(current)
            elif current and DESCRIPTOR_LINE.fullmatch(line):
                current['descriptors']=descriptors(current['descriptors']+', '+line)
            elif current:
                # El PDF tiene una columna de texto y otra de descriptores.
                # Si la extracción intercala descriptores dentro de una línea,
                # se exige revisión manual en vez de incorporarlos al enunciado.
                if re.search(DESCRIPTOR,line):
                    raise ValueError('Columnas mezcladas en el criterio '+current['code']+'.')
                current['description']+=' '+line
            else:
                raise ValueError('Texto no identificado antes del primer criterio '+code+'.')
        if not rows or any(not x['description'].strip() or not x['descriptors'] for x in rows):
            raise ValueError('Criterios o descriptores incompletos en competencia '+code+'.')
        outcomes.append({'code':code,'description':description,'descriptors':descr,'criteria':rows})
    return outcomes


def parse_pdf(raw, meta):
    import fitz
    with fitz.open(stream=raw,filetype='pdf') as doc:
        if len(doc)!=83 or 'ANEXO 1' not in doc[0].get_text():
            raise ValueError('La versión del anexo no coincide con la referencia de 83 páginas.')
        # Páginas PDF 15–31 (Ciencias) y 60–74 (Comunicación).
        # Las listas de la sección 5 no son las tablas del currículo.
        start,end=(14,31) if meta['ambito']==cs.SCI else (59,74)
        text='\n'.join(clean_page(doc[i].get_text()) for i in range(start,end))
        start_sab,end_sab=(31,46) if meta['ambito']==cs.SCI else (73,83)
        saberes='\n'.join(clean_page(doc[i].get_text()) for i in range(start_sab,end_sab))
        marker=re.search(r'(?im)^\s*8\.\s+Saberes b[aá]sicos propios del [aá]mbito',saberes)
        if not marker:
            raise ValueError('No se localiza el apartado de saberes básicos.')
        # Los saberes se muestran exclusivamente como referencia textual del
        # ámbito y requieren selección de materia/curso por el docente.
        return {'competencies':parse_blocks(text,meta['max_competencies']),
                'saberes_reference':saberes[marker.start():]}


def fetch(meta, consent=False):
    if consent is not True:
        raise ValueError('Autorice expresamente la consulta del anexo oficial.')
    req=urllib.request.Request(cs.ANNEX_URL,headers={'User-Agent':'EvaluaFP-ConsultaCurricular/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(MAX_BYTES+1)
    except (OSError,TimeoutError) as exc:
        raise ValueError('No se pudo descargar el anexo curricular. Compruebe la conexión.') from exc
    if len(raw)>MAX_BYTES or not raw.startswith(b'%PDF-'):
        raise ValueError('La respuesta no es un PDF del tamaño permitido.')
    parsed=parse_pdf(raw,meta)
    return {**parsed,'ambito':meta['ambito'],'source_url':cs.ANNEX_URL,
            'source_id':cs.SOURCE_ID,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'notice':'Referencia del ámbito completo, pendiente de cotejo con el PDF firmado. Seleccione solo las competencias y saberes de su materia y curso.'}
