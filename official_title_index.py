"""Índice estatal de títulos TodoFP por nivel. No acredita implantación autonómica.

Cada búsqueda consulta un listado oficial (Básico, Medio, Superior o Especialización)
con límites de tiempo, tamaño y dominio heredados del lector TodoFP. El nombre
es una *candidatura a título*, no un código validado ni horas oficiales.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

import todofp_discovery as todofp
import territorial_profiles as territories

INDICES = {
    'Básico': 'https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html',
    'Medio': 'https://www.todofp.es/que-estudiar/grados-d/grado-medio.html',
    'Superior': 'https://www.todofp.es/que-estudiar/grados-d/grado-superior.html',
    'Especialización': 'https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html',
}
MAX_TITLES = 400
MAX_MATCHES = 65
TITLE_URL_RE = re.compile(r'^/que-estudiar/familias-profesionales/[a-z0-9-]+/[a-z0-9-]+\.html$', re.I)
_TITLE_WORDS = {
    'Básico': ('titulo profesional basico ', 'tecnico basico ', 'tecnica basica '),
    'Medio': ('tecnico en ', 'tecnica en '),
    'Superior': ('tecnico superior en ', 'tecnica superior en '),
    'Especialización': ('curso de especializacion ', 'especialista en ', 'master de formacion profesional '),
}


def _title_anchor(href, base):
    url=todofp._external_link(href,base)
    if not url:return None
    parts=urlsplit(url)
    if parts.hostname not in todofp.OFFICIAL_HOSTS or parts.query or parts.fragment or parts.port not in (None,443):return None
    if not TITLE_URL_RE.fullmatch(parts.path):return None
    return todofp.validate_todofp_url(url)


def _is_title(text,grade):
    value=territories.fold(text)
    if ('no vigente' in value or 'titulo antiguo' in value or len(value)>200):return False
    return any(value.startswith(start) for start in _TITLE_WORDS[grade])


def parse_index(html,url,grade,query=''):
    """Toma únicamente enlaces a fichas de ciclos, nunca enlaces de navegación.

    No deduce código de título ni carga horaria de la ruta, ni otorga
    validez/implantación territorial a lo publicado.
    """
    if grade not in INDICES:raise ValueError('Seleccione Básico, Medio, Superior o Especialización.')
    if url!=INDICES[grade]:raise ValueError('La fuente no corresponde al nivel seleccionado.')
    if not isinstance(query,str) or len(query)>120:raise ValueError('Consulta de títulos demasiado larga.')
    parser=todofp._DocumentEvents();parser.feed(html)
    titles=[];seen=set()
    for link in parser.links:
        name=' '.join(link['text'].split())
        if not _is_title(name,grade):continue
        path=_title_anchor(link.get('href',''),url)
        if not path or path in seen:continue
        seen.add(path)
        titles.append({'name':name,'grade':grade,'url':path,
                       'title_code':'', 'code_status':'no_aparece_en_el_indice',
                       'status':'ficha_estatal_localizada_pendiente_validacion_autonomica'})
        if len(titles)>MAX_TITLES:
            raise ValueError('El índice de TodoFP supera el número esperado de títulos: compruebe la fuente.')
    needle=territories.fold(query)
    matches=[entry for entry in titles if not needle or needle in territories.fold(entry['name'])]
    return {'grade':grade,'source_url':url,'total_in_index':len(titles),
            'count':len(matches),'results':matches[:MAX_MATCHES],
            'truncated':len(matches)>MAX_MATCHES}


def search(grade,query,region,academic_year,opener=None):
    """Consulta pública, no registra fuentes ni modifica el currículo local."""
    if grade not in INDICES:raise ValueError('Nivel de FP no reconocido.')
    if not isinstance(query,str) or len(query)>120:raise ValueError('Introduzca un término de búsqueda de hasta 120 caracteres.')
    label=territories.require_territory(region)
    year=territories.year_code(academic_year)
    src=INDICES[grade]
    final,html=todofp.fetch_todofp(src,opener=opener)
    if final != src:raise ValueError('El índice ha redirigido a otra página; revise la fuente.')
    result=parse_index(html,src,grade,query)
    return {**result,'territory':label,'academic_year':year,
            'approval_required':True,
            'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'notice':('Este índice estatal ayuda a localizar títulos; no acredita su implantación en la comunidad, '
                      'el código oficial del título, las horas semanales ni la vigencia de su currículo autonómico. '
                      'Abra la ficha y consulte su normativa antes de registrar datos curriculares.')}
