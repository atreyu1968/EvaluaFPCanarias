"""Recuperación y comprobación curricular desde el BOE (fuente oficial).

No deduce ponderaciones de exámenes ni altera SQLite sin confirmación docente.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import hashlib
import urllib.request
import unicodedata

# Nueve módulos específicos del título de Gestión Administrativa.
# Recuentos del anexo I de la publicación ORIGINAL de 2009, nunca del
# currículo autonómico certificado para un año académico.
SUPPORTED = {
    'comunicacion empresarial y atencion al cliente': ('BOE-A-2009-19148', '0437'),
    'operaciones administrativas de compraventa': ('BOE-A-2009-19148', '0438'),
    'empresa y administracion': ('BOE-A-2009-19148', '0439'),
    'tratamiento informatico de la informacion': ('BOE-A-2009-19148', '0440'),
    'tecnica contable': ('BOE-A-2009-19148', '0441'),
    'operaciones administrativas de recursos humanos': ('BOE-A-2009-19148', '0442'),
    'tratamiento de la documentacion contable': ('BOE-A-2009-19148', '0443'),
    'empresa en el aula': ('BOE-A-2009-19148', '0446'),
    'operaciones auxiliares de gestion de tesoreria': ('BOE-A-2009-19148', '0448'),
}
# Administración y Finanzas: recuentos por RA del anexo I original de 2011.
AF_SUPPORTED = {
    'gestion de la documentacion juridica y empresarial': ('BOE-A-2011-19533', '0647'),
    'recursos humanos y responsabilidad social corporativa': ('BOE-A-2011-19533', '0648'),
    'ofimatica y proceso de la informacion': ('BOE-A-2011-19533', '0649'),
    'proceso integral de la actividad comercial': ('BOE-A-2011-19533', '0650'),
    'comunicacion y atencion al cliente': ('BOE-A-2011-19533', '0651'),
    'gestion de recursos humanos': ('BOE-A-2011-19533', '0652'),
    'gestion financiera': ('BOE-A-2011-19533', '0653'),
    'contabilidad y fiscalidad': ('BOE-A-2011-19533', '0654'),
    'gestion logistica y comercial': ('BOE-A-2011-19533', '0655'),
    'simulacion empresarial': ('BOE-A-2011-19533', '0656'),
}
EXPECTED_COVERAGE = {
    ('BOE-A-2011-19533', '0647'): (6, 7, 8, 8, 11),
    ('BOE-A-2011-19533', '0648'): (6, 5, 8, 8, 10),
    ('BOE-A-2011-19533', '0649'): (8, 10, 11, 10, 8, 8, 5, 10, 6),
    ('BOE-A-2011-19533', '0650'): (7, 9, 9, 9, 6, 10, 10),
    ('BOE-A-2011-19533', '0651'): (10, 10, 11, 11, 7, 10, 10),
    ('BOE-A-2011-19533', '0652'): (9, 6, 8, 10),
    ('BOE-A-2011-19533', '0653'): (7, 7, 9, 8, 7, 8),
    ('BOE-A-2011-19533', '0654'): (8, 10, 10, 11, 7, 9),
    ('BOE-A-2011-19533', '0655'): (10, 8, 8, 9, 8),
    ('BOE-A-2011-19533', '0656'): (7, 8, 9, 8, 9, 10),
    ('BOE-A-2009-19148', '0437'): (9, 10, 11, 10, 9, 10, 7, 10),
    ('BOE-A-2009-19148', '0438'): (9, 10, 7, 9, 8),
    ('BOE-A-2009-19148', '0439'): (7, 6, 7, 8, 6, 10, 6),
    ('BOE-A-2009-19148', '0440'): (10, 8, 7, 8, 7, 9, 6, 7),
    ('BOE-A-2009-19148', '0441'): (7, 9, 9, 7, 9),
    ('BOE-A-2009-19148', '0442'): (10, 10, 10, 9, 6, 5),
    ('BOE-A-2009-19148', '0443'): (7, 8, 9, 10),
    ('BOE-A-2009-19148', '0446'): (6, 8, 6, 7, 6, 6, 10),
    ('BOE-A-2009-19148', '0448'): (9, 10, 7, 9),
}
TITLE_AMENDMENT = 'https://www.boe.es/eli/es/rd/2024/05/21/499'
TITLE_CONSOLIDATED_REFERENCE = 'https://www.boe.es/eli/es/rd/2009/10/30/1631/con'
GA_CYCLE = 'CFGM Gestión Administrativa'
AF_CYCLE = 'CFGS Administración y Finanzas'
AD_CYCLE = 'CFGS Asistencia a la Dirección'
ORIGINAL_TITLE_BY_CYCLE = {
    GA_CYCLE: 'BOE-A-2009-19148',
    AF_CYCLE: 'BOE-A-2011-19533',
    AD_CYCLE: 'BOE-A-2011-19531',
}
TITLE_LINKS = {
    'BOE-A-2009-19148': {
        'state_title': TITLE_CONSOLIDATED_REFERENCE,
        'state_amendment': TITLE_AMENDMENT,
        'state_amendment_2010':'https://www.boe.es/eli/es/rd/2010/09/10/1126',
    },
    'BOE-A-2011-19533': {
        'state_title':'https://www.boe.es/eli/es/rd/2011/11/04/1584/con',
        'state_amendment':'https://www.boe.es/eli/es/rd/2024/05/21/500',
    },
}
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


def _module_key(value):
    name = " ".join(_norm(value).strip(" .").split())
    name = re.sub(r'\s*\.?\s*equivalencia en creditos ects\.?$', '', name).strip(' .')
    aliases = {
        'operaciones administrativas de compra-venta': 'operaciones administrativas de compraventa',
        'operaciones administrativas de la compra-venta': 'operaciones administrativas de compraventa',
        'operaciones administrativas de la compraventa': 'operaciones administrativas de compraventa',
    }
    return aliases.get(name,name)


def _cycle_key(cycle):
    if not cycle:
        return None
    import canarias_ag
    try:
        return canarias_ag.canonical_cycle(cycle)
    except ValueError:
        if _norm(cycle).strip() in ('gm','cfgm'):
            return GA_CYCLE
        return str(cycle)


def _template_for(module_name, cycle=None):
    key = _module_key(module_name)
    cycle = _cycle_key(cycle)
    if cycle == GA_CYCLE:
        return SUPPORTED.get(key)
    if cycle == AF_CYCLE:
        return AF_SUPPORTED.get(key)
    if cycle is None:  # Compatibilidad para las llamadas previas sin título.
        return SUPPORTED.get(key) or AF_SUPPORTED.get(key)
    return None


def source_hint(module_name, cycle=None):
    """Fuente original del título seleccionado, sin consulta ni confirmación."""
    record = _template_for(module_name, cycle)
    if not record:
        return None
    boe_id, code = record
    counts = EXPECTED_COVERAGE[(boe_id, code)]
    return {
        'boe_id': boe_id, 'module_code': code,
        'source_url': 'https://www.boe.es/diario_boe/txt.php?id=' + boe_id,
        'expected_ra': len(counts), 'expected_ce': sum(counts),
        'status': 'original_state_source_requires_review',
    }


def parse_curriculum(document_text, module_name, expected_code=None):
    """Extrae solo enunciados numerados y CE literales del bloque del módulo."""
    txt=_plain(document_text).replace('\xa0',' ')
    txt=re.sub(r'(?m)[ \t]+',' ',txt)
    # El bloque debe contener un encabezado inequívoco con nombre y código del módulo.
    marker=re.compile(
        r'M[oó]dulo\s+Profesional\s*:\s*([^\r\n]{1,220}?)'
        r'\s*\.?\s*(?:Equivalencia\s+en\s+cr[eé]ditos\s+ECTS\s*:\s*\d{1,3}\s*)?'
        r'C[oó]digo\s*:\s*(\d{4})(?!\d)', re.IGNORECASE)
    wanted = _module_key(module_name)
    found = [match for match in marker.finditer(txt)
             if _module_key(match.group(1)) == wanted]
    if not found:
        raise ValueError('El BOE consultado no contiene un encabezado acreditado para este módulo y código.')
    block=None;code=None
    for match in found:
        candidate=txt[match.end():]
        following=re.search(r'M[oó]dulo\s+Profesional\s*:',candidate,re.IGNORECASE)
        if following:candidate=candidate[:following.start()]
        if re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',candidate,re.I):
            block=candidate;code=match.group(2);break
    if block is None:raise ValueError('No se ha localizado el apartado oficial de RA y CE del módulo.')
    if expected_code and code!=expected_code:
        raise ValueError(f'El código de este módulo en la norma es {code}, no {expected_code}.')
    heading=re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',block,re.I)
    block=block[heading.end():]
    block=re.split(r'(?im)^[ \t]*(?:Duraci[oó]n\s*:|Contenidos b[aá]sicos\b|Orientaciones pedag[oó]gicas\b)',block,maxsplit=1)[0]
    lines=[re.sub(r'\s+',' ',x.strip()) for x in block.splitlines()]
    lines=[x for x in lines if x and x not in {'Criterios de evaluación:', 'Criterios de evaluación'}]
    ras=[];current=None;criterion=None
    for line in lines:
        # El RA4 de 0651 se publica sin punto después del número.
        m=re.match(r'^([1-9]\d?)(?:\.\s+|\s+(?=[A-ZÁÉÍÓÚÜÑ]))(.+)',line)
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
    if any(not r['criteria'] for r in ras):
        raise ValueError('La extracción contiene un RA sin CE; revise la disposición.')
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


def fetch_official(module_name, boe_id=None, consent=False, cycle=None):
    if not consent:raise ValueError('Debe confirmar la consulta a la fuente oficial.')
    template=_template_for(module_name, cycle)
    if boe_id is None or not str(boe_id).strip():
        if not template:
            raise ValueError('Para este módulo indique el identificador BOE-A-AAAA-NNN de la norma aplicable.')
        boe_id=template[0]
    boe_id=str(boe_id).strip().upper()
    if not BOE_PATTERN.fullmatch(boe_id):
        raise ValueError('Introduzca un identificador oficial BOE-A-AAAA-NNN válido.')
    title_source = ORIGINAL_TITLE_BY_CYCLE.get(_cycle_key(cycle))
    if title_source and boe_id in ORIGINAL_TITLE_BY_CYCLE.values() and boe_id != title_source:
        raise ValueError('La disposición original corresponde a otro ciclo formativo.')
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
        parsed['verification_links']=dict(TITLE_LINKS.get(boe_id, {}))
    parsed.update({'source':'BOE','source_url':url,'source_id':boe_id,
        'source_sha256':hashlib.sha256(raw).hexdigest(),
        'cycle':_cycle_key(cycle),
        'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'warnings':['Propuesta de la publicación original del BOE, no certificación de vigencia. Contraste sus modificaciones y las normas autonómicas aplicables antes de confirmarla.',
                    'Conserve literalmente los RA/CE; contextualice los supuestos tributarios con IGIC cuando corresponda, sin sustituir el texto normativo.',
                    'La normativa no asigna ponderaciones a los RA y CE de la programación. Se mantienen sin completar.'],
        'coverage':{'ra_cited':len(parsed['outcomes']),'ra_accepted':len(parsed['outcomes']),
                    'ce_proposed':sum(len(x['criteria']) for x in parsed['outcomes']),
                    'ce_accepted':sum(len(x['criteria']) for x in parsed['outcomes']),
                    'ce_discarded':0}})
    return parsed
