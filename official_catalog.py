"""Distribución horaria de referencia de la FP de Canarias.

Datos transcritos del Anexo VI (BOC n.º 226, 13-11-2024): tablas de los
ciclos 12142101 Gestión Administrativa y 12142103 Administración y Finanzas.
No se deduce la carga del BOE: el RD del título no fija necesariamente la
carga semanal aprobada por cada comunidad. Comprobar modificaciones vigentes.
"""
from __future__ import annotations
import re
import unicodedata
import territorial_profiles as territory

SOURCE = 'https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/anexo-6-resolucion-instrucciones-implantacion-distribucion-horaria-curriculos-24.pdf'
SOURCE_DATE = '2024-11-13'
GENERAL = [
 ('Ley Orgánica 3/2022, de 31 de marzo, de ordenación e integración de la Formación Profesional', 'https://www.boe.es/buscar/act.php?id=BOE-A-2022-5139'),
 ('Real Decreto 659/2023, de 18 de julio, por el que se desarrolla la ordenación del Sistema de Formación Profesional', 'https://www.boe.es/buscar/act.php?id=BOE-A-2023-16889'),
 ('Ley Orgánica 2/2006, de 3 de mayo, de Educación, en su texto consolidado', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-7899'),
]
CANARIAS = [
 ('Anexo VI de la Resolución autonómica sobre implantación y distribución horaria de los grados D y E (BOC de 13-11-2024)', SOURCE),
 ('Ley 6/2014, de 25 de julio, Canaria de Educación no Universitaria', 'https://www.gobiernodecanarias.org/educacion/web/servicios/inspeccion_educativa/normativa_clasificada/organizacion_funcionamiento/documentos-institucionales/'),
 ('Resolución de 9 de junio de 2025, evaluación de los grados C, D y E de FP (Canarias)', 'https://www.gobiernodecanarias.org/boc/2025/118/2219.html'),
 ('Resolución de 3 de diciembre de 2025, modificación de la evaluación de FP (Canarias)', 'https://www.gobiernodecanarias.org/boc/2025/249/4298.html'),
 ('Página autonómica con ampliaciones y modificaciones 2025-2026 de la distribución horaria de FP', 'https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/implantacion_curriculos/imolantacion-curriculos-lomloe-looifp/'),
]
# ciclo, código, módulo, curso, horas anuales, horas semanales
_ROWS = [
 ('gestion administrativa','0437','Comunicación empresarial y atención al cliente',1,173,5),
 ('gestion administrativa','0438','Operaciones administrativas de compraventa',1,173,5),
 ('gestion administrativa','0439','Empresa y administración',1,96,3),
 ('gestion administrativa','0440','Tratamiento informático de la información',1,206,6),
 ('gestion administrativa','0441','Técnica contable',1,96,3),
 ('gestion administrativa','0442','Operaciones administrativas de recursos humanos',2,170,5),
 ('gestion administrativa','0443','Tratamiento de la documentación contable',2,202,6),
 ('gestion administrativa','0446','Empresa en el aula',2,170,5),
 ('gestion administrativa','0448','Operaciones auxiliares de gestión de tesorería',2,170,5),
 ('administracion y finanzas','0647','Gestión de la documentación jurídica y empresarial',1,138,4),
 ('administracion y finanzas','0648','Recursos humanos y responsabilidad social corporativa',1,64,2),
 ('administracion y finanzas','0649','Ofimática y proceso de la información',1,170,5),
 ('administracion y finanzas','0650','Proceso integral de la actividad comercial',1,202,6),
 ('administracion y finanzas','0651','Comunicación y atención al cliente',1,170,5),
 ('administracion y finanzas','0652','Gestión de recursos humanos',2,138,4),
 ('administracion y finanzas','0653','Gestión financiera',2,138,4),
 ('administracion y finanzas','0654','Contabilidad y fiscalidad',2,138,4),
 ('administracion y finanzas','0655','Gestión logística y comercial',2,138,4),
 ('administracion y finanzas','0656','Simulación empresarial',2,160,5),
 ('administracion y finanzas','0657','Proyecto intermodular de administración y finanzas',2,64,2),
]

def fold(value):
    s=unicodedata.normalize('NFKD',str(value or '').casefold())
    return re.sub(r'\s+',' ',''.join(c for c in s if not unicodedata.combining(c))).strip()

def find(region,cycle,name,code=''):
    """Solo ofrece una coincidencia inequívoca por título y ciclo, nunca por parecido."""
    if territory.territory_code(region) != 'CN':return None
    c=fold(cycle);n=fold(name)
    groups=[grp for grp in ('gestion administrativa','administracion y finanzas') if grp in c]
    if len(groups)!=1:return None
    group=groups[0]
    code=str(code or '').strip()
    found=[]
    for cyc,mod_code,title,course,annual,weekly in _ROWS:
        if cyc != group: continue
        same_code= bool(code) and code == mod_code
        exact_name= n == fold(title)
        inline_code=mod_code in re.findall(r'(?<!\d)\d{4}(?!\d)',n)
        if same_code or exact_name or inline_code:
            found.append((cyc,mod_code,title,course,annual,weekly))
    if len(found)!=1:return None
    cyc,mod_code,title,course,annual,weekly=found[0]
    return {'code':mod_code,'title':title,'cycle':cyc,'course':course,
            'total_hours':float(annual),'weekly_hours':float(weekly),
            'region':'Canarias','source_url':SOURCE,'source_date':SOURCE_DATE,
            'status':'reference_to_verify',
            'notice':'Datos publicados en el Anexo VI de 2024. Comprueba las modificaciones y distribución vigente de tu curso antes de confirmarlos.'}

def normative_proposal(region,cycle,name,code='',academic_year='2026-2027'):
    refs=list(GENERAL)
    region=territory.require_territory(region)
    if territory.territory_code(region)=='CN':refs+=CANARIAS
    profile=territory.calendar_profile(region,academic_year)
    if profile:
        refs += [('Calendario escolar ' + region + ' ' + academic_year + ' (resolución y corrección)',url) for url in profile['source_urls']]
    else:
        refs += [('Localizar currículo y normativa de la administración educativa competente en TodoFP (portal de entrada, no fuente normativa)', 'https://www.todofp.es/')]
    if 'gestion administrativa' in fold(cycle):
        refs.append(('Real Decreto 1631/2009, de 30 de octubre, título de Técnico en Gestión Administrativa',
                     'https://www.boe.es/eli/es/rd/2009/10/30/1631'))
    if 'administracion y finanzas' in fold(cycle):
        refs.append(('Real Decreto 1584/2011, de 4 de noviembre, título de Técnico Superior en Administración y Finanzas',
                     'https://www.boe.es/buscar/act.php?id=BOE-A-2011-19533'))
    lines=[f'- {title}. Fuente: {url}' for title,url in refs]
    lines.append(f'- PENDIENTE DE COMPROBAR: currículo de {region} para {academic_year}, distribución horaria, modificaciones vigentes y acuerdos del centro.')
    lines.append('- Estas son FUENTES PARA REVISIÓN DOCENTE, no una declaración automática de vigencia jurídica ni de adecuación al módulo.')
    return '\n'.join(lines)
