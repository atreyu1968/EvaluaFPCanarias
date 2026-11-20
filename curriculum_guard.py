"""Control de procedencia curricular, sin completar CE a partir de supuestos."""
import re
import unicodedata
import ia

def _source_normalize(value):
    """Texto comparable sin modificar el contenido original presentado al docente."""
    value=unicodedata.normalize('NFKC',str(value or '')).casefold()
    return re.sub(r'\s+', ' ', value).strip()


def _criterion_is_grounded(source_text, description, ra_number, letter):
    """Un CE exige su enunciado literal y una etiqueta a)/RA2.a próxima.

    No basta con que una frase sobre el mismo tema exista en cualquier sección.
    """
    text=_source_normalize(source_text)
    desc=_source_normalize(description)
    if len(desc)<20 or len(desc.split())<4:return False
    offset=0
    while True:
        at=text.find(desc,offset)
        if at<0:return False
        before=text[max(0,at-100):at].rstrip()
        marker=(rf'(?:ra\s*{ra_number}\s*[.:\-]?\s*)?{letter}\s*[).:\-]\s*\|?\s*$'
                rf'|ra\s*{ra_number}\s*[.:\-]?\s*{letter}\s*$')
        if re.search(marker,before,re.IGNORECASE):return True
        offset=at+len(desc)


def analyze_program(program_text):
    """Propuestas auditables: los CE nunca se completan desde conocimiento general."""
    if not program_text.strip():
        raise ValueError('El archivo no contiene texto extraíble; convierta un escaneo a texto antes de analizarlo.')
    if len(program_text)>110000:
        raise ValueError('Programación extensa. Divídala en documentos de hasta 110.000 caracteres para no omitir criterios.')
    prompt = f"""Analiza la programación de FP y EXTRAe solo RA/CE cuya DESCRIPCIÓN COMPLETA sea literal del documento.
JSON: {{"outcomes":[{{"code":"RA1","description":"enunciado literal completo del RA","weight":null,"criteria":[{{"code":"RA1.a","description":"enunciado literal completo del CE","weight":null}}]}}],"warnings":[]}}.
- No reconstruyas CE a partir de letras a)-f), referencias RA1a, actividades, objetivos o conocimientos generales.
- Si un RA o CE solo está citado por código o resumido, NO inventes su descripción. Comunica la ausencia en warnings.
- Para cada CE debe figurar literalmente su enunciado completo y un código identificable (RAx.a o a) en la programación.
- Copia las descripciones literalmente, sin parafrasearlas ni completarlas. El programa verificará su coincidencia.
- Los pesos se extraen SOLO si aparecen expresamente y son inequívocos. En ausencia de peso explícito: null. RA.weight se refiere al módulo, CE.weight al RA.
- No confundas formación en empresa con un RA adicional. Señala toda suma incompatible con 100 % y toda contradicción curricular.
DOCUMENTO:
{program_text}"""
    result,model=ia.chat('analysis',prompt)
    if not isinstance(result,dict) or not isinstance(result.get('outcomes'),list):
        raise ValueError('La IA no devolvió una lista válida de RA/CE; revise la programación.')
    source=_source_normalize(program_text)
    observed=set(re.findall(r'(?<![a-z0-9])ra\s*([1-9]\d?)(?!\d)',source,re.I))
    # Los currículos oficiales pueden numerar los RA como «1. ...», sin prefijo RA.
    heading=re.search(r'(?i)resultados de aprendizaje y criterios de evaluaci[oó]n',program_text)
    if heading:
        block=program_text[heading.end():]
        block=re.split(r'(?im)^\s*(?:duraci[oó]n\s*:|m[oó]dulo profesional\s*:)',block,maxsplit=1)[0]
        for num,description in re.findall(r'(?m)^\s*([1-9]\d?)\.\s+([^\n]{25,})',block):
            observed.add(num)

    warnings=[str(w) for w in result.get('warnings',[]) if isinstance(w,str)][:30]
    if 'técnica contable' in source and re.search(r'(?:código(?: del módulo)?|c[oó]digo)\s*[:|]?\s*0299\b',source,re.I):
        warnings.append('Código curricular por revisar: el documento asigna 0299 a Técnica Contable; el módulo del título de Gestión Administrativa figura como 0441 en el RD 1631/2009. Compruébelo con la normativa aplicable.')
    if re.search(r'\bRA204\b',program_text,re.I):
        warnings.append('Referencia ambigua RA204: compruebe si es un error de identificación de RA2/RA4.')
    if len(observed)==5 and re.search(r'cada\s+ra.{0,100}20\s*%',source,re.I) and re.search(r'formaci[oó]n en empresa.{0,220}25\s*%',source,re.I):
        warnings.append('Ponderación incoherente: 5 RA x 20 % más 25 % de formación en empresa suman 125 %. Debe aclararse antes de calificar.')
    valid=[];discarded_ra=0;discarded_ce=0;seen=set();ce_total=0
    for item in result['outcomes'][:100]:
        if not isinstance(item,dict):continue
        code=str(item.get('code','')).strip().upper().replace(' ','')
        match=re.fullmatch(r'RA([1-9]\d?)',code)
        if not match or code in seen or match.group(1) not in observed:
            discarded_ra+=1;continue
        description=str(item.get('description','')).strip()
        if len(description)<18 or _source_normalize(description) not in source:
            discarded_ra+=1
            warnings.append(f'{code}: descripción no reproducida literalmente en la programación; se omite para evitar inventar datos.')
            continue
        seen.add(code)
        ra=dict(item,code=code,description=description)
        criteria=[];letters=set()
        for criterion in item.get('criteria',[]) if isinstance(item.get('criteria',[]),list) else []:
            ce_total+=1
            if not isinstance(criterion,dict):discarded_ce+=1;continue
            raw_code=str(criterion.get('code','')).strip()
            m=re.fullmatch(r'(?:RA\s*'+match.group(1)+r'\s*[.:\-]?\s*)?([a-z])\)?',raw_code,re.I)
            if not m:
                discarded_ce+=1;continue
            letter=m.group(1).lower()
            full_code=f'{code}.{letter}'
            desc=str(criterion.get('description','')).strip()
            if letter in letters or not _criterion_is_grounded(program_text,desc,match.group(1),letter):
                discarded_ce+=1;continue
            letters.add(letter)
            criteria.append(dict(criterion,code=full_code,description=desc))
        ra['criteria']=criteria
        valid.append(ra)
        if not criteria:
            warnings.append(f'{code}: sin CE con descripción literal y código verificables; debe completarse desde la programación o fuente normativa oficial.')
    if discarded_ce:
        warnings.append(f'Se han descartado {discarded_ce} CE propuestos por IA: su texto o código no está acreditado en el documento.')
    if discarded_ra:
        warnings.append(f'Se han descartado {discarded_ra} RA con datos ausentes, repetidos o no verificables.')
    missing=sorted((f'RA{n}' for n in observed if f'RA{n}' not in seen),key=lambda x:int(x[2:]))
    if missing:
        warnings.append('RA citados sin descripción literal completa verificable: '+', '.join(missing)+'.')
    if sum(len(r['criteria']) for r in valid)==0:
        warnings.append('No hay enunciados completos de CE verificables en este documento. No se generarán criterios inventados: incorpore la programación detallada o importe el currículo oficial y valide sus ponderaciones.')
    # Los pesos no se reinterpretan ni se convierten automáticamente.
    return {'outcomes':valid,'warnings':list(dict.fromkeys(warnings)), 'model':model,
            'coverage':{'ra_cited':len(observed),'ra_accepted':len(valid),'ce_proposed':ce_total,
                        'ce_accepted':sum(len(r['criteria']) for r in valid),'ce_discarded':discarded_ce}}

