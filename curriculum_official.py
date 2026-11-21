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
# Asistencia a la Dirección: fuente propia, incluso para módulos comunes.
AD_SUPPORTED = {
    'gestion de la documentacion juridica y empresarial': ('BOE-A-2011-19531', '0647'),
    'recursos humanos y responsabilidad social corporativa': ('BOE-A-2011-19531', '0648'),
    'ofimatica y proceso de la informacion': ('BOE-A-2011-19531', '0649'),
    'proceso integral de la actividad comercial': ('BOE-A-2011-19531', '0650'),
    'comunicacion y atencion al cliente': ('BOE-A-2011-19531', '0651'),
    'segunda lengua extranjera': ('BOE-A-2011-19531', '0180'),
    'protocolo empresarial': ('BOE-A-2011-19531', '0661'),
    'organizacion de eventos empresariales': ('BOE-A-2011-19531', '0662'),
    'gestion avanzada de la informacion': ('BOE-A-2011-19531', '0663'),
}
# Servicios Administrativos: solo módulos profesionales del anexo I.
GB_SUPPORTED = {
    'tratamiento informatico de datos': ('BOE-A-2014-2360', '3001'),
    'aplicaciones basicas de ofimatica': ('BOE-A-2014-2360', '3002'),
    'tecnicas administrativas basicas': ('BOE-A-2014-2360', '3003'),
    'archivo y comunicacion': ('BOE-A-2014-2360', '3004'),
    'atencion al cliente': ('BOE-A-2014-2360', '3005'),
    'preparacion de pedidos y venta de productos': ('BOE-A-2014-2360', '3006'),
}
EXPECTED_COVERAGE = {
    ('BOE-A-2023-16889', '3159'): (5, 5, 3, 3, 4),
    ('BOE-A-2023-16889', '1709'): (3, 9, 7, 11, 9),
    ('BOE-A-2023-16889', '1710'): (4, 7, 6, 9, 9),
    ('BOE-A-2023-16889', '1664'): (6, 6, 5, 8, 8),
    ('BOE-A-2023-16889', '1665'): (7, 7, 5, 6, 9, 11),
    ('BOE-A-2023-16889', '1708'): (6, 5, 3, 6, 9, 5),
    ('BOE-A-2023-16889', '0156'): (9, 9, 13, 10, 5),
    ('BOE-A-2023-16889', '0179'): (8, 10, 11, 8, 6),
    ('BOE-A-2024-10683', '3160'): (9, 5, 5, 4, 4),
    ('BOE-A-2024-10684', '1713'): (9, 11, 9, 6, 4),
    ('BOE-A-2011-19533', '0657'): (9, 9, 8, 7),
    ('BOE-A-2011-19531', '0664'): (9, 9, 8, 7),
    ('BOE-A-2014-2360', '3001'): (7, 10, 7, 10),
    ('BOE-A-2014-2360', '3002'): (7, 7, 6, 6),
    ('BOE-A-2014-2360', '3003'): (5, 9, 9, 8),
    ('BOE-A-2014-2360', '3004'): (9, 10, 8, 8),
    ('BOE-A-2014-2360', '3005'): (9, 8, 8, 6),
    ('BOE-A-2014-2360', '3006'): (6, 7, 6, 6),
    ('BOE-A-2011-19531', '0647'): (6, 7, 8, 8, 11),
    ('BOE-A-2011-19531', '0648'): (6, 5, 8, 8, 10),
    ('BOE-A-2011-19531', '0649'): (8, 10, 11, 10, 8, 8, 5, 10, 6),
    ('BOE-A-2011-19531', '0650'): (7, 9, 9, 9, 6, 10, 10),
    ('BOE-A-2011-19531', '0651'): (10, 10, 11, 11, 7, 10, 10),
    ('BOE-A-2011-19531', '0180'): (7, 7, 9, 7, 6),
    ('BOE-A-2011-19531', '0661'): (7, 11, 11, 10, 8, 10),
    ('BOE-A-2011-19531', '0662'): (11, 8, 9, 10, 8),
    ('BOE-A-2011-19531', '0663'): (7, 8, 9, 7, 9),
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
GB_CYCLE = 'CFGB Servicios Administrativos'
GA_CYCLE = 'CFGM Gestión Administrativa'
AF_CYCLE = 'CFGS Administración y Finanzas'
AD_CYCLE = 'CFGS Asistencia a la Dirección'
# Fuentes transversales de la ordenación vigente, separadas por nivel.
TRANSVERSAL_BY_CYCLE = {
    GB_CYCLE: {
        'itinerario personal para la empleabilidad': ('BOE-A-2023-16889', '3159'),
        'proyecto intermodular de aprendizaje colaborativo': ('BOE-A-2024-10683', '3160'),
    },
    GA_CYCLE: {
        'itinerario personal para la empleabilidad i': ('BOE-A-2023-16889', '1709'),
        'itinerario personal para la empleabilidad ii': ('BOE-A-2023-16889', '1710'),
        'digitalizacion aplicada a los sectores productivos (gm)': ('BOE-A-2023-16889', '1664'),
        'sostenibilidad aplicada al sistema productivo': ('BOE-A-2023-16889', '1708'),
        'ingles profesional (gm)': ('BOE-A-2023-16889', '0156'),
        'proyecto intermodular': ('BOE-A-2024-10684', '1713'),
    },
    AF_CYCLE: {
        'itinerario personal para la empleabilidad i': ('BOE-A-2023-16889', '1709'),
        'itinerario personal para la empleabilidad ii': ('BOE-A-2023-16889', '1710'),
        'digitalizacion aplicada a los sectores productivos (gs)': ('BOE-A-2023-16889', '1665'),
        'sostenibilidad aplicada al sistema productivo': ('BOE-A-2023-16889', '1708'),
        'ingles profesional (gs)': ('BOE-A-2023-16889', '0179'),
        'proyecto de administracion y finanzas': ('BOE-A-2011-19533', '0657'),
    },
    AD_CYCLE: {
        'itinerario personal para la empleabilidad i': ('BOE-A-2023-16889', '1709'),
        'itinerario personal para la empleabilidad ii': ('BOE-A-2023-16889', '1710'),
        'digitalizacion aplicada a los sectores productivos (gs)': ('BOE-A-2023-16889', '1665'),
        'sostenibilidad aplicada al sistema productivo': ('BOE-A-2023-16889', '1708'),
        'ingles profesional (gs)': ('BOE-A-2023-16889', '0179'),
        'proyecto de asistencia a la direccion': ('BOE-A-2011-19531', '0664'),
    },
}
ORIGINAL_TITLE_BY_CYCLE = {
    GB_CYCLE: 'BOE-A-2014-2360',
    GA_CYCLE: 'BOE-A-2009-19148',
    AF_CYCLE: 'BOE-A-2011-19533',
    AD_CYCLE: 'BOE-A-2011-19531',
}
TITLE_LINKS = {
    'BOE-A-2023-16889': {
        'state_title':'https://www.boe.es/eli/es/rd/2023/07/18/659/con',
        'state_amendment':'https://www.boe.es/eli/es/rd/2024/07/09/658',
    },
    'BOE-A-2024-10683': {
        'state_title':'https://www.boe.es/eli/es/rd/2024/05/21/498/con',
    },
    'BOE-A-2024-10684': {
        'state_title':'https://www.boe.es/eli/es/rd/2024/05/21/499/con',
    },
    'BOE-A-2014-2360': {
        'state_title':'https://www.boe.es/eli/es/rd/2014/02/28/127/con',
        'state_amendment':'https://www.boe.es/eli/es/rd/2024/05/21/498',
        'canarias_curriculum':'https://www.gobiernodecanarias.org/boc/2023/025/001.html',
        'canarias_annex_3':'https://www.gobiernodecanarias.org/cmsweb/export/sites/educacion/web/formacion_profesional/_galerias/descargas/cfgb/4_CFGB-_servicios_administrativos.pdf',
    },
    'BOE-A-2011-19531': {
        'state_title':'https://www.boe.es/eli/es/rd/2011/11/04/1582/con',
        'state_amendment':'https://www.boe.es/eli/es/rd/2024/05/21/500',
    },
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
        'proyecto intermodular de aprendizaje colaborativo (gb)': 'proyecto intermodular de aprendizaje colaborativo',
        'proyecto intermodular de administracion y finanzas': 'proyecto de administracion y finanzas',
        'proyecto intermodular de asistencia a la direccion': 'proyecto de asistencia a la direccion',
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
    transverse = TRANSVERSAL_BY_CYCLE.get(cycle, {}).get(key)
    if transverse:
        return transverse
    if cycle == GB_CYCLE:
        return GB_SUPPORTED.get(key)
    if cycle == GA_CYCLE:
        return SUPPORTED.get(key)
    if cycle == AF_CYCLE:
        return AF_SUPPORTED.get(key)
    if cycle == AD_CYCLE:
        return AD_SUPPORTED.get(key)
    if cycle is None:  # Compatibilidad para clientes antiguos.
        common = {reg[key] for reg in TRANSVERSAL_BY_CYCLE.values() if key in reg}
        if common:
            return next(iter(common)) if len(common)==1 else None
        # Sin ciclo no se elige arbitrariamente entre dos títulos.
        candidates = [reg[key] for reg in (SUPPORTED, AF_SUPPORTED, AD_SUPPORTED, GB_SUPPORTED) if key in reg]
        return candidates[0] if len(candidates) == 1 else None
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
        'status': ('source_label_conflict_requires_review' if code=='1713'
                   else 'original_state_source_requires_review'),
        'notice': ('El RA5 contiene dos CE a) en el BOE original: revise la numeración antes de importar.'
                   if code=='1713' else 'Referencia estatal; contraste vigencia y normativa canaria.'),
    }


def basic_services_annex(document_text):
    """Aísla el anexo I del RD 127/2014, sin utilizar otros títulos del decreto."""
    plain = _plain(document_text).replace('\xa0', ' ')
    # El BOE de 2014 agrupa catorce títulos en el mismo documento.
    title = re.search(
        r'(?im)^[ \t]*ANEXO[ \t]+I[ \t]*\n\s*'
        r'T[ií]tulo\s+Profesional\s+B[aá]sico\s+en\s+Servicios\s+Administrativos[ \t.]*$',
        plain)
    if not title:
        raise ValueError('No se localiza el encabezado del anexo I de Servicios Administrativos.')
    remaining = plain[title.end():]
    following = re.search(r'(?im)^[ \t]*ANEXO[ \t]+II[ \t]*$', remaining)
    if not following:
        raise ValueError('No se localiza el límite del anexo I. No se consultarán otros títulos.')
    return remaining[:following.start()]


def parse_curriculum(document_text, module_name, expected_code=None):
    """Extrae solo enunciados numerados y CE literales del bloque del módulo."""
    txt=_plain(document_text).replace('\xa0',' ')
    txt=re.sub(r'(?m)[ \t]+',' ',txt)
    # El bloque debe contener un encabezado inequívoco con nombre y código del módulo.
    marker=re.compile(
        r'M[oó]dulo\s+Profesional\s*:\s*([^\r\n]{1,220}?)'
        r'\s*\.?\s*(?:(?:Equivalencia\s+en\s+cr[eé]ditos\s+ECTS'
        r'(?:\s*\([^)\r\n]{1,100}\))?|Duraci[oó]n)\s*:\s*[^\r\n]{1,100}\s*){0,2}'
        r'C[oó]digo\s*:\s*(\d{4})(?!\d)', re.IGNORECASE)
    wanted = _module_key(module_name)
    found = [match for match in marker.finditer(txt)
             if _module_key(match.group(1)) == wanted]
    if not found:
        raise ValueError('El BOE consultado no contiene un encabezado acreditado para este módulo y código.')
    block=None;code=None
    for match in found:
        candidate=txt[match.end():]
        following=re.search(r'M[oó]dulo\s+Profesional\s*:|(?m:^[ \t]*ANEXO[ \t]+[IVXLCDM]+[ \t]*$)',candidate,re.IGNORECASE)
        if following:candidate=candidate[:following.start()]
        if re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',candidate,re.I):
            block=candidate;code=match.group(2);break
    if block is None:raise ValueError('No se ha localizado el apartado oficial de RA y CE del módulo.')
    if expected_code and code!=expected_code:
        raise ValueError(f'El código de este módulo en la norma es {code}, no {expected_code}.')
    heading=re.search(r'Resultados de aprendizaje y criterios de evaluaci[oó]n',block,re.I)
    return {'outcomes': parse_ra_block(block[heading.end():]), 'module_code': code}


def parse_ra_block(block):
    """Extrae RA y CE del fragmento ya identificado, sin asignar pesos."""
    block=re.split(r'(?im)^[ \t]*(?:Duraci[oó]n\s*:|Contenidos(?: b[aá]sicos)?\s*[:.]|Orientaciones pedag[oó]gicas\b)',block,maxsplit=1)[0]
    lines=[re.sub(r'\s+',' ',x.strip()) for x in block.splitlines()]
    # La publicación utiliza indistintamente punto, dos puntos o ninguno.
    lines=[x for x in lines if x and _norm(x).strip(' .:') != 'criterios de evaluacion']
    ras=[];current=None;criterion=None
    for line in lines:
        # El RA4 de 0651 se publica sin punto después del número.
        m=re.match(r'^([1-9]\d?)(?:\.\s+|\s+(?=[A-ZÁÉÍÓÚÜÑ]))(.+)',line)
        if m:
            # Algunos anexos de 2023 sitúan el rótulo CE al final del RA.
            description=re.sub(r'\s+Criterios de evaluaci[oó]n\s*[:.]?\s*$', '', m.group(2),flags=re.I)
            current={'code':'RA'+m.group(1),'description':description,'weight':None,'criteria':[]}
            ras.append(current);criterion=None;continue
        c=re.match(r'^([a-z])\)\s+(.+)',line,re.I)
        if c and current:
            criterion={'code':current['code']+'.'+c.group(1).lower(),
                       'description':c.group(2),'weight':None}
            current['criteria'].append(criterion);continue
        if criterion and current and not line.lower().startswith(('módulo profesional','resultados de aprendizaje')):
            # Las líneas partidas por maquetación pertenecen al mismo criterio.
            if line and line not in ('.', ':'):
                criterion['description']+=' '+line
        elif current and not criterion and len(line)>12 and len(current['description'])<250:
            current['description']+=' '+line
    if any(not r['criteria'] for r in ras):
        raise ValueError('La extracción contiene un RA sin CE; revise la disposición.')
    if len(ras)<2 or sum(len(r['criteria']) for r in ras)<8:
        raise ValueError('El texto obtenido no contiene suficientes RA/CE verificables; consulte la norma original.')
    # No inventamos ponderaciones: son propias de la programación y su política de calificación.
    return ras


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
    if not cycle and boe_id:
        key = _module_key(module_name)
        requested = str(boe_id).strip().upper()
        # Una norma explícita resuelve la ambigüedad sin perder el cotejo del código.
        candidates = [reg[key] for reg in (SUPPORTED, AF_SUPPORTED, AD_SUPPORTED, GB_SUPPORTED)
                      if key in reg and reg[key][0] == requested]
        if len(candidates) == 1:
            template = candidates[0]
    if boe_id is None or not str(boe_id).strip():
        if not template:
            raise ValueError('Para este módulo indique el identificador BOE-A-AAAA-NNN de la norma aplicable.')
        boe_id=template[0]
    boe_id=str(boe_id).strip().upper()
    if not BOE_PATTERN.fullmatch(boe_id):
        raise ValueError('Introduzca un identificador oficial BOE-A-AAAA-NNN válido.')
    title_source = ORIGINAL_TITLE_BY_CYCLE.get(_cycle_key(cycle))
    # Impedir que un módulo transversal de otro nivel se importe usando su nombre.
    key = _module_key(module_name)
    transversals = {k for reg in TRANSVERSAL_BY_CYCLE.values() for k in reg}
    if cycle and key in transversals and not TRANSVERSAL_BY_CYCLE.get(_cycle_key(cycle), {}).get(key):
        raise ValueError('El módulo transversal o proyecto corresponde a otro nivel o título.')
    if cycle and template and key in transversals and boe_id != template[0]:
        raise ValueError('Utilice la disposición específica de este módulo transversal; revise otra fuente manualmente.')
    if title_source and boe_id in ORIGINAL_TITLE_BY_CYCLE.values() and boe_id != title_source:
        raise ValueError('La disposición original corresponde a otro ciclo formativo.')
    url='https://www.boe.es/diario_boe/txt.php?id='+boe_id
    req=urllib.request.Request(url,headers={'User-Agent':'EvaluaFP-ConsultaCurricular/1.0',
                                              'Accept':'text/html, text/plain'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            charset=r.headers.get_content_charset() or 'utf-8'
            # El RD 127/2014 reúne catorce títulos; admitir su HTML completo,
            # de forma acotada, antes de aislar el anexo de Servicios Administrativos.
            limit=24_000_000 if boe_id=='BOE-A-2014-2360' else 6_000_000
            raw=r.read(limit+1)
            if len(raw)>limit:raise ValueError('La disposición supera el tamaño máximo permitido.')
            document=raw.decode(charset,'replace')
    except (OSError,TimeoutError) as exc:
        raise ValueError('No se puede consultar el BOE. Revise la conexión y vuelva a intentarlo.') from exc
    expected=template[1] if template else None
    if boe_id=='BOE-A-2014-2360':
        if _module_key(module_name) not in GB_SUPPORTED:
            raise ValueError('Solo se recuperan automáticamente los seis módulos profesionales del anexo I. Los ámbitos y módulos transversales requieren su propia normativa.')
        document=basic_services_annex(document)
    parsed=parse_curriculum(document,module_name,expected)
    counts=EXPECTED_COVERAGE.get((boe_id, parsed['module_code']))
    if counts:
        if (boe_id, parsed['module_code']) == ('BOE-A-2024-10684', '1713'):
            # El original repite a) en RA5. No renumerar ni perder un criterio.
            if [ce['code'] for ce in parsed['outcomes'][-1]['criteria']] == ['RA5.a','RA5.a','RA5.b','RA5.c']:
                raise ValueError('El BOE original de 1713 repite a) en RA5. Revise la fuente y resuelva la numeración mediante revisión documental antes de importar.')
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
