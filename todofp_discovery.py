"""Consulta restringida a fichas y enlaces de currículo publicados en TodoFP.

No transforma una ficha informativa en norma aplicable. La selección definitiva de
códigos, horas, RA/CE, territorio y curso corresponde a la fuente curricular
vigente y a la validación docente. No almacena ni transmite datos del alumnado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler
import re

import territorial_profiles as territories

OFFICIAL_HOSTS = frozenset(('www.todofp.es', 'todofp.es'))
PREFIX = '/que-estudiar/'
MAX_HTML_BYTES = 2_000_000
MAX_MODULES = 75
MAX_REGIONAL_LINKS = 160


def validate_todofp_url(raw):
    """Evita SSRF, rutas de otros sitios y hosts parecidos a TodoFP."""
    if not isinstance(raw, str) or not 25 <= len(raw) <= 700:
        raise ValueError('Introduzca la dirección HTTPS de una ficha de ciclo de TodoFP.')
    raw = raw.strip()
    parts = urlsplit(raw)
    if (parts.scheme != 'https' or parts.hostname not in OFFICIAL_HOSTS or
            parts.port not in (None, 443) or parts.username or parts.password or
            parts.query or parts.fragment or '\\' in raw or '%' in parts.path or
            not parts.path.startswith(PREFIX) or not parts.path.endswith('.html') or
            '..' in parts.path.split('/') or '//' in parts.path):
        raise ValueError('Solo se consultan páginas HTML de títulos y currículos del portal oficial TodoFP (HTTPS).')
    segments = parts.path.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+(?:\.html)?',part) for part in segments if part):
        raise ValueError('La ruta de la ficha de TodoFP tiene caracteres no admitidos.')
    return raw


class _RestrictedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_todofp_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_todofp(url, opener=None):
    """Solicitud en vivo limitada por host, redirección, tiempo y tamaño."""
    url=validate_todofp_url(url)
    client=opener or build_opener(_RestrictedRedirect()).open
    req=Request(url,headers={'User-Agent':'EvaluaFP/1.2.4 (consulta educativa)', 'Accept':'text/html'})
    try:
        with client(req,timeout=12) as response:
            final=validate_todofp_url(response.geturl())
            if response.headers.get('Content-Type','text/html').split(';')[0].lower().strip() not in ('text/html','application/xhtml+xml'):
                raise ValueError('TodoFP no ha devuelto una página HTML.')
            content=response.read(MAX_HTML_BYTES+1)
            if len(content)>MAX_HTML_BYTES:
                raise ValueError('La ficha supera el límite de consulta permitido.')
    except ValueError:raise
    except (OSError,TimeoutError) as exc:
        raise ValueError('No ha sido posible consultar TodoFP. Compruebe la conexión o abra el enlace manualmente.') from exc
    try:return final,content.decode('utf-8-sig')
    except UnicodeError as exc:raise ValueError('La ficha no tiene una codificación de texto compatible.') from exc


class _DocumentEvents(HTMLParser):
    """Extrae eventos mínimos, sin librerías adicionales para el portátil."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events=[]
        self.headings=[]
        self.links=[]
        self._heading=[]
        self._link=[]
        self._list=[]
        self._in_ignored=0

    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag in ('script','style','noscript'):
            self._in_ignored+=1
        if self._in_ignored:return
        if tag in ('h1','h2','h3','h4','h5'):
            self._heading.append({'tag':tag,'texts':[]})
        if tag=='a':self._link.append({'href':attributes.get('href',''),'texts':[]})
        if tag=='li':self._list.append({'texts':[]})
        if tag=='img' and attributes.get('alt'):
            self.events.append({'type':'image','text':attributes['alt'].strip()})

    def handle_data(self,data):
        if self._in_ignored:return
        if self._heading:self._heading[-1]['texts'].append(data)
        if self._link:self._link[-1]['texts'].append(data)
        for row in self._list:row['texts'].append(data)

    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):
            self._in_ignored=max(0,self._in_ignored-1)
            return
        if self._in_ignored:return
        if tag=='a' and self._link:
            row=self._link.pop()
            text=' '.join(''.join(row['texts']).split())
            result={'type':'link','text':text,'href':row['href']}
            self.links.append(result);self.events.append(result)
        if tag=='li' and self._list:
            row=self._list.pop()
            text=' '.join(''.join(row['texts']).split())
            self.events.append({'type':'list','text':text})
        if tag in ('h1','h2','h3','h4','h5') and self._heading:
            row=self._heading.pop()
            text=' '.join(''.join(row['texts']).split())
            result={'type':'heading','level':tag,'text':text}
            self.headings.append(result);self.events.append(result)


def _external_link(href,base):
    if not href or href.startswith('#'):return None
    result=urljoin(base,href)
    p=urlsplit(result)
    if p.scheme not in ('https',) or not p.hostname or p.username or p.password or '\\' in result or len(result)>1100:
        return None
    return result


def parse_cycle(html,url):
    """Extrae módulos de la sección de plan de formación, no de anuncios ni menús."""
    p=_DocumentEvents();p.feed(html)
    title=next((x['text'] for x in p.headings if x['level']=='h1' and x['text']), '')
    if not title:raise ValueError('No se ha identificado el nombre del título en la ficha oficial.')
    t=territories.fold(title)
    grade=('Especialización' if 'curso de especializacion' in t else
           'Superior' if 'tecnico superior' in t else
           'Básico' if 'tecnico basico' in t or 'tecnica basica' in t else
           'Medio' if 'tecnico en' in t or 'tecnica en' in t else '')
    section=False;seen=set();modules=[]
    for event in p.events:
        if event['type']=='heading' and event.get('level')=='h2':
            section='plan de formacion' in territories.fold(event['text'])
        elif section and event['type']=='list':
            name=event['text'].strip(' .\t')
            fold=territories.fold(name)
            if (not name or len(name)>180 or fold.startswith(('incluye una fase','si estudias','modulos que','la formacion en empresa')) or
                    fold in seen or name in ('1.º','2.º')):continue
            match=re.fullmatch(r'(\d{4})\.\s*(.+)',name)
            code=match.group(1) if match else ''
            label=match.group(2).strip(' .') if match else name
            if not re.search(r'[A-Za-zÀ-ÿ]{3}',label):continue
            if not code and re.search(r'\b\d{4}\.\s*',name):continue
            seen.add(fold)
            modules.append({'code':code,'name':label,'code_confirmed_from_page':bool(code),
                            'optional':('optativo' in fold),'source':'plan_formacion_todofp'})
            if len(modules)>MAX_MODULES:raise ValueError('Ficha con demasiados módulos para una lectura segura.')
    curricula_link=None;royal_decree=None
    for link in p.links:
        label=territories.fold(link['text'])
        href=_external_link(link['href'],url)
        if not href:continue
        if 'curriculos ccaa' in label or 'curriculos de las comunidades' in label:
            if urlsplit(href).hostname in OFFICIAL_HOSTS and href.endswith('/curriculos-ccaa.html'):
                curricula_link=href
        if ('real decreto' in label or label=='real decreto') and 'boe.es' in (urlsplit(href).hostname or ''):
            royal_decree=href
    return {'title':title,'grade':grade,'modules':modules,'curricula_url':curricula_link,
            'state_norm_url':royal_decree,'source_url':url,
            'modules_count':len(modules),
            'notice':'Los módulos proceden de una ficha informativa de TodoFP. No se han confirmado todos sus códigos ni su distribución por curso para este territorio y año.'}


def _region_from_alt(value):
    # Las imágenes de cabecera del apartado autonómico tienen como texto ALT
    # el nombre de la comunidad, con variantes habituales.
    key=territories.fold(value).replace('image: ','').replace('imagen: ','').strip()
    if key in ('comunidad valenciana','comunitat valenciana'):return 'VC'
    if key in ('andalucia','andalusia'):return 'AN'
    return territories.territory_code(key)


def parse_regional_curricula(html,url,region):
    wanted=territories.territory_code(territories.require_territory(region))
    p=_DocumentEvents();p.feed(html)
    current=None;seen=set();all_links=[]
    for event in p.events:
        if event['type']=='image':
            marker=_region_from_alt(event['text'])
            if marker:current=marker
        elif event['type']=='link' and current:
            label=event['text'].strip()
            kind=territories.fold(label)
            # Ignorar navegación y links irrelevantes; conservar modificaciones.
            if not label or len(label)>140 or kind in ('subir','volver') or not any(k in kind for k in ('curriculo','modificacion','ordenacion','instrucciones','optativ','empresa','titulacion','certificacion','estructura')):
                continue
            href=_external_link(event.get('href'),url)
            if not href or (current,href) in seen:continue
            seen.add((current,href))
            all_links.append({'territory_code':current,'label':label,'url':href,
                              'type':('modificacion' if 'modific' in kind else
                                      'curriculo' if 'curriculo' in kind else 'referencia_adicional'),
                              'status':'enlace_publicado_por_todofp_pendiente_vigencia'})
            if len(all_links)>MAX_REGIONAL_LINKS:
                raise ValueError('La página presenta demasiados enlaces autonómicos.')
    chosen=[x for x in all_links if x['territory_code']==wanted]
    return {'region':territories.require_territory(region),'links':chosen,
            'count':len(chosen),'other_territories_linked':len({x['territory_code'] for x in all_links}),
            'source_url':url,'notice':('Estos enlaces proceden del directorio TodoFP por ciclo. No garantizan por sí solos que la disposición esté vigente ni que rija las horas del módulo en el curso seleccionado. '
                'Es necesario revisar el boletín autonómico, las modificaciones posteriores y el calendario escolar del curso.')}


def _cycle_core(value):
    value=territories.fold(value)
    patterns=(r'^cf(?:g|p)[bms]\s*',r'^ciclo formativo de fp (?:grado )?(?:basico|medio|superior)\s*',
              r'^ciclo formativo de grado (?:basico|medio|superior)\s*',
              r'^tecnic[oa] superior en\s*',r'^tecnic[oa] en\s*',
              r'^tecnic[oa] basico en\s*')
    for pattern in patterns:value=re.sub(pattern,'',value).strip()
    return value


def _matching_cycle(selected, official):
    left,right=_cycle_core(selected),_cycle_core(official)
    return bool(left and len(left)>6 and left==right)


def explore(url,region,academic_year,opener=None,cycle_name='',module_name=''):

    """Vista previa nacional; no escribe RA/CE, horas, calendario ni SQLite."""
    region=territories.require_territory(region)
    year=territories.year_code(academic_year)
    link=validate_todofp_url(url)
    actual,html=fetch_todofp(link,opener=opener)
    if actual.endswith('/curriculos-ccaa.html'):
        profile=None
        curr=parse_regional_curricula(html,actual,region)
    else:
        profile=parse_cycle(html,actual)
        curr=None
        if profile['curricula_url']:
            try:
                second,page=fetch_todofp(profile['curricula_url'],opener=opener)
                curr=parse_regional_curricula(page,second,region)
            except ValueError:
                # El título sigue visible, con advertencia de la falta de enlaces.
                curr={'links':[],'count':0,'source_url':profile['curricula_url'],
                      'notice':'No se ha podido consultar la página de currículos autonómicos. Abra la fuente en el navegador y compruebe su disponibilidad.'}
    match_cycle=None
    match_module=None
    if profile is not None and cycle_name:
        match_cycle=_matching_cycle(cycle_name,profile['title'])
    if profile is not None and module_name and profile['modules']:
        match_module=any(territories.fold(m['name'])==territories.fold(module_name) for m in profile['modules'])
    suitable=(match_cycle is not False and match_module is not False)
    return {'profile':profile,'regional_curricula':curr,'region':region,
            'matches_selected_cycle':match_cycle,'matches_selected_module':match_module,
            'suitable_for_current_module':suitable,
            'academic_year':year,'consulted_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'approval_required':True,
            'notice':('Exploración informativa de TodoFP: no implica que el ciclo esté implantado en este territorio o centro. '
                       'La importación de módulos al catálogo local requiere sus códigos y la verificación de la disposición. '
                       'No se han guardado ni alterado RA/CE, unidades, horas, calendario ni calificaciones.')}
