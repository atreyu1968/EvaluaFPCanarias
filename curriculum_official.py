"""Recuperación y comprobación curricular desde el BOE (fuente oficial).

No deduce ponderaciones de exámenes ni altera SQLite sin confirmación docente.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import urllib.request
import unicodedata

SUPPORTED = {
    'tecnica contable': ('BOE-A-2009-19148', '0441'),
    'tratamiento de la documentacion contable': ('BOE-A-2009-19148', '0443'),
}
# Integridad de la publicación original, no certificación de vigencia.
EXPECTED_COVERAGE = {
    ('BOE-A-2009-19148', '0441'): (7, 9, 9, 7, 9),
    ('BOE-A-2009-19148', '0443'): (7, 8, 9, 10),
}
TITLE_AMENDMENT = 'https://www.boe.es/eli/es/rd/2024/05/21/499'
TITLE_CONSOLIDATED_REFERENCE = 'https://www.boe.es/eli/es/rd/2009/10/30/1631/con'
BOE_PATTERN = re.compile(r'BOE-A-[12]\d{3}-\d{1,7}\Z', re.IGNORECASE)


class _Text(HTMLParser):
    BLOCKS={'p','div','li','h1','h2','h3','h4','h5','h6','br','tr','article','section'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'style','script'}:self.skip+=1
        if not self.skip and tag in self.BLOCKS:self.words.append('\n')
        if tag in {'td','th'} and not self.skip:self.words.append(' | ')
    def handle_endtag(self,tag):
        if not self.skip and tag in self.BLOCKS:self.words.append('\n')
        if tag in {'script','style'} and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.words.append(data)


def _plain(value):
    if '<html' not in value[:4000].lower() and '<!doctype' not in value[:4000].lower():
        return value
    parser=_Text();parser.feed(value);return ''.join(parser.words)


def _norm(value):
    value=unicodedata.normalize('NFKD',str(value)).casefold()
    return ''.join(c for c in value if not unicodedata.combining(c))


def parse_curriculum(document_text, module_name, expected_code=None):
    """Extrae solo enunciados numerados y CE literales del bloque del módulo."""
    txt=_plain(document_text).replace('\xa0',' ')
    txt=re.sub(r'(?m)[ \t]+',' ',txt)
    # El bloque debe contener un encabezado inequívoco con nombre y código del módulo.
    marker=re.compile(r'M[oó]dulo\s+Profesional\s*:\s*'+re.escape(module_name)+
                      r'\s*\.?\s*C[oó]digo\s*:\s*(\d{4})',re.IGNORECASE)
    found=list(marker.finditer(txt))
    if not found:
        raise ValueError('El BOE consultado no contiene un encabezado acreditado para este módulo y código.')
    block=None;code=None
    for match in found:
        candidate=txt[match.end():]
        following=re.search(r'M[oó]dulo\s+Profesional\s*:',candidate,re.IGNORECASE)
        if following:candidate=candidate[:following.start()]
        if re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',candidate,re.I):
            block=candidate;code=match.group(1);break
    if block is None:raise ValueError('No se ha localizado el apartado oficial de RA y CE del módulo.')
    if expected_code and code!=expected_code:
        raise ValueError(f'El código de este módulo en la norma es {code}, no {expected_code}.')
    heading=re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',block,re.I)
    block=block[heading.end():]
    block=re.split(r'(?im)^\s*(?:Duraci[oó]n\s*:|Contenidos b[aá]sicos\s*:|Orientaciones pedag[oó]gicas\s*:)',block,maxsplit=1)[0]
    lines=[re.sub(r'\s+',' ',x.strip()) for x in block.splitlines()]
    lines=[x for x in lines if x and x not in {'Criterios de evaluación:', 'Criterios de evaluación'}]
    ras=[];current=None;criterion=None
    for line in lines:
        m=re.match(r'^([1-9]\d?)\.\s+(.+)',line)
        if m:
            current={'code':'RA'+m.group(1),'description':m.group(2),'weight':None,'criteria':[]}
            ras.append(current);criterion=None;continue
        c=re.match(r'^([a-z])\)\s+(.+)',line,re.I)
        if c and current:
            criterion={'code':current['code']+'.'+c.group(1).lower(),
                       'description':c.group(2),'weight':None}
            current['criteria'].append(criterion);continue
        if criterion and current and not line.lower().startswith(('módulo profesional','resultados de aprendizaje')):
            # Las líneas partidas por maquetación pertenecen al mismo criterio.
            if len(line)>12 and not re.match(r'^[—−-]',line):
                criterion['description']+=' '+line
        elif current and not criterion and len(line)>12 and len(current['description'])<250:
            current['description']+=' '+line
    ras=[r for r in ras if r['criteria']]
    if len(ras)<2 or sum(len(r['criteria']) for r in ras)<8:
        raise ValueError('El texto obtenido no contiene suficientes RA/CE verificables; consulte la norma original.')
    # No inventamos ponderaciones: son propias de la programación y su política de calificación.
    return {'outcomes':ras,'module_code':code}


def check_coverage(outcomes, expected):
    """Rechaza extracciones parciales, duplicadas o con saltos."""
    if len(outcomes) != len(expected):
        raise ValueError('La fuente no ofrece todos los RA esperados.')
    for i, (ra, count) in enumerate(zip(outcomes, expected), 1):
        code = 'RA' + str(i)
        if ra.get('code') != code or [c.get('code') for c in ra.get('criteria', [])] != [
            code + '.' + chr(97 + j) for j in range(count)
        ]:
            raise ValueError('La fuente no ofrece todos los CE consecutivos de ' + code +
                             '. No se admite una extracción parcial.')


def fetch_official(module_name, boe_id=None, consent=False):
    if not consent:raise ValueError('Debe confirmar la consulta a la fuente oficial.')
    normalized=' '.join(_norm(module_name).split())
    template=SUPPORTED.get(normalized)
    if boe_id is None or not str(boe_id).strip():
        if not template:
            raise ValueError('Para este módulo indique el identificador BOE-A-AAAA-NNN de la norma aplicable.')
        boe_id=template[0]
    boe_id=str(boe_id).strip().upper()
    if not BOE_PATTERN.fullmatch(boe_id):
        raise ValueError('Introduzca un identificador oficial BOE-A-AAAA-NNN válido.')
    url='https://www.boe.es/diario_boe/txt.php?id='+boe_id
    req=urllib.request.Request(url,headers={'User-Agent':'EvaluaFP-ConsultaCurricular/1.0',
                                              'Accept':'text/html, text/plain'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            charset=r.headers.get_content_charset() or 'utf-8'
            raw=r.read(6_000_001)
            if len(raw)>6_000_000:raise ValueError('La disposición supera el tamaño máximo permitido.')
            document=raw.decode(charset,'replace')
    except (OSError,TimeoutError) as exc:
        raise ValueError('No se puede consultar el BOE. Revise la conexión y vuelva a intentarlo.') from exc
    expected=template[1] if template else None
    parsed=parse_curriculum(document,module_name,expected)
    counts=EXPECTED_COVERAGE.get((boe_id, parsed['module_code']))
    if counts:
        check_coverage(parsed['outcomes'], counts)
        parsed['reference_coverage']={
            'expected_ra':len(counts), 'expected_ce':sum(counts),
            'criteria_per_ra':list(counts),
            'complete_for_original_source':True,
            'territorial_curriculum_confirmed':False,
        }
        parsed['verification_links']={
            'state_title':TITLE_CONSOLIDATED_REFERENCE,
            'state_amendment':TITLE_AMENDMENT,
        }
    parsed.update({'source':'BOE','source_url':url,'source_id':boe_id,
        'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'warnings':['Propuesta de la publicación original del BOE, no certificación de vigencia. Contraste sus modificaciones y las normas autonómicas aplicables antes de confirmarla.',
                    'Conserve literalmente los RA/CE; contextualice los supuestos tributarios con IGIC cuando corresponda, sin sustituir el texto normativo.',
                    'La normativa no asigna ponderaciones a los RA y CE de la programación. Se mantienen sin completar.'],
        'coverage':{'ra_cited':len(parsed['outcomes']),'ra_accepted':len(parsed['outcomes']),
                    'ce_proposed':sum(len(x['criteria']) for x in parsed['outcomes']),
                    'ce_accepted':sum(len(x['criteria']) for x in parsed['outcomes']),
                    'ce_discarded':0}})
    return parsed
