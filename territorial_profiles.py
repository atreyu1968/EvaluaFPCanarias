"""Identidades educativas y calendarios VERSIONADOS.

No presume que el calendario laboral equivalga al escolar. Un territorio o curso
sin ficha oficial cargada siempre requiere fechas y festivos del docente.
"""
from __future__ import annotations
from datetime import date
import re
import unicodedata

TERRITORIES = (
    ('AN', 'Andalucía'), ('AR', 'Aragón'), ('AS', 'Principado de Asturias'),
    ('IB', 'Illes Balears'), ('CN', 'Canarias'), ('CB', 'Cantabria'),
    ('CM', 'Castilla-La Mancha'), ('CL', 'Castilla y León'), ('CT', 'Cataluña'),
    ('VC', 'Comunitat Valenciana'), ('EX', 'Extremadura'), ('GA', 'Galicia'),
    ('MD', 'Comunidad de Madrid'), ('MC', 'Región de Murcia'),
    ('NC', 'Comunidad Foral de Navarra'), ('PV', 'País Vasco'), ('RI', 'La Rioja'),
    ('CE', 'Ceuta'), ('ML', 'Melilla'),
)

LABELS = dict(TERRITORIES)


def fold(text):
    s = unicodedata.normalize('NFKD', str(text or '').casefold())
    return re.sub(r'\s+', ' ', ''.join(c for c in s if not unicodedata.combining(c))).strip()

ALIASES = {fold(label): code for code, label in TERRITORIES}
ALIASES.update({
    'asturias': 'AS', 'baleares': 'IB', 'islas baleares': 'IB',
    'comunidad valenciana': 'VC', 'valencia': 'VC', 'comunidad de valencia': 'VC',
    'madrid': 'MD', 'murcia': 'MC', 'navarra': 'NC', 'euskadi': 'PV',
    'castilla la mancha': 'CM', 'castilla leon': 'CL', 'catalunya': 'CT',
    'canary islands': 'CN',
})


def territory_code(name):
    text = fold(name)
    code = str(name or '').strip().upper()
    return code if code in LABELS else ALIASES.get(text)


def require_territory(name):
    code = territory_code(name)
    if not code:
        raise ValueError('Seleccione uno de los 19 ámbitos educativos: las 17 comunidades autónomas, Ceuta o Melilla.')
    return LABELS[code]


def year_code(raw):
    text = str(raw or '').strip().replace('/', '-')
    match = re.fullmatch(r'(20\d{2})-(20\d{2})', text)
    if not match or int(match[2]) != int(match[1])+1:
        raise ValueError('Indique un curso académico válido, por ejemplo 2026-2027.')
    return text


# Fuentes comprobadas para la modalidad general de FP, NO para todas las posibles
# adaptaciones de FP Dual y grupos especiales. Los cierres de evaluación se ofrecen
# como sugerencias organizativas y deben contrastarse con la PGA del centro.
_CALENDAR_CANARIAS_2026 = {
    'id': 'CN:FP:2026-2027:BOC-2026-075-1240',
    'territory_code': 'CN', 'academic_year': '2026-2027',
    'stage': 'FP Grado D ordinario, calendario general',
    'source_description': 'Calendario escolar Canarias 2026-2027 y corrección oficial de 10/04/2026',
    'source_urls': [
        'https://www.gobiernodecanarias.org/boc/2026/061/1025.html',
        'https://www.gobiernodecanarias.org/boc/2026/075/1240.html',
    ],
    'start_date': '2026-09-16', 'end_date': '2027-06-22',
    'evaluation_ends': ['2026-12-21', '2027-03-19', '2027-06-22'],
    'vacation_periods': [
        {'start': '2026-12-23', 'end': '2027-01-08', 'label': 'Vacaciones de Navidad (BOC corregido)'},
        {'start': '2027-03-22', 'end': '2027-03-26', 'label': 'Vacaciones de Semana Santa'},
    ],
    # 2026: festivos escolares expresos BOC; 2027: los laborales aplicables
    # se contrastan con Decreto 115/2026 (BOC 03/07/2026).
    'regional_non_teaching_days': [
        {'date': '2026-10-12', 'reason': 'Fiesta Nacional'},
        {'date': '2026-11-02', 'reason': 'Todos los Santos, traslado'},
        {'date': '2026-12-07', 'reason': 'Día del Enseñante y Estudiante'},
        {'date': '2026-12-08', 'reason': 'Inmaculada Concepción'},
        {'date': '2027-01-01', 'reason': 'Año Nuevo'},
        {'date': '2027-01-06', 'reason': 'Reyes'},
        {'date': '2027-03-25', 'reason': 'Jueves Santo'},
        {'date': '2027-03-26', 'reason': 'Viernes Santo'},
        {'date': '2027-05-01', 'reason': 'Fiesta del Trabajo'},
        {'date': '2027-05-30', 'reason': 'Día de Canarias'},
    ],
    'holiday_source_url': 'https://www.gobiernodecanarias.org/boc/2026/133/2334.html',
    'status': 'referencia_oficial_pendiente_concrecion_centro',
    'notice': ('El BOC fija el calendario general: confirme festivos insulares, locales, '
               'días no lectivos del centro y posibles adaptaciones de FP Dual. '
               'Los cierres de evaluación son orientativos, no fechas aprobadas.'),
}

INSULAR_2026 = {
    'gran canaria': ('2026-09-08', 'Nuestra Señora del Pino'),
    'lanzarote': ('2026-09-15', 'Nuestra Señora de los Volcanes'),
    'la graciosa': ('2026-09-15', 'Nuestra Señora de los Volcanes'),
    'fuerteventura': ('2026-09-18', 'Nuestra Señora de la Peña'),
    'el hierro': ('2026-09-24', 'Nuestra Señora de los Reyes'),
    'la gomera': ('2026-10-05', 'Nuestra Señora de Guadalupe'),
}
INSULAR_2027 = {'tenerife': ('2027-02-02', 'Virgen de la Candelaria')}


def calendar_profile(region, academic_year, island=''):
    code = territory_code(region)
    year = year_code(academic_year)
    if code != 'CN' or year != '2026-2027':
        return None
    from copy import deepcopy
    profile = deepcopy(_CALENDAR_CANARIAS_2026)
    # Festivos insulares: únicamente si se conoce la isla; no se adivinan.
    place = fold(island)
    for lookup in (INSULAR_2026, INSULAR_2027):
        if place in lookup:
            day, name = lookup[place]
            profile['regional_non_teaching_days'].append({'date': day, 'reason': f'{name} ({island})'})
    profile['island'] = island
    if place:
        profile['source_urls'].append(profile['holiday_source_url'])
    return profile


def public_profile(region, academic_year, island=''):
    year = year_code(academic_year)
    label = require_territory(region)
    p = calendar_profile(label, year, island)
    return {'territory_code': territory_code(label), 'territory': label,
            'academic_year': year, 'profile': p,
            'requires_manual_calendar': p is None,
            'notice': (p['notice'] if p else
                'No hay un calendario escolar de FP de este territorio y curso contrastado en el catálogo local. '
                'Introduzca las fechas, vacaciones, festivos y la URL de la disposición oficial; '
                'la aplicación no reutilizará un calendario de otra comunidad o año.'),
            'territories': [{'code': code, 'label': label} for code, label in TERRITORIES]}

# Una pequeña entrada municipal comprobada y vinculada al año de la norma.
# NO sirve como valor por defecto para el resto de municipios de España.
LOCAL_HOLIDAYS = {
    ('CN', 'guia de isora', '2026-2027'): (
        {'date': '2026-09-21', 'reason': 'Festividad del Santísimo Cristo de la Dulce Muerte (Guía de Isora)'},
        {'date': '2027-06-24', 'reason': 'San Juan Bautista (Guía de Isora)'},
    ),
}
LOCAL_SOURCES = {
    ('CN', 'guia de isora', '2026-2027'):
        ['https://www.gobiernodecanarias.org/boc/2025/165/3029.html',
         'https://www.gobiernodecanarias.org/boc/2026/168/3035.html'],
}


def known_local_holidays(region,academic_year,municipality):
    key=(territory_code(region),fold(municipality),year_code(academic_year))
    return list(LOCAL_HOLIDAYS.get(key,()))


def known_local_sources(region,academic_year,municipality):
    key=(territory_code(region),fold(municipality),year_code(academic_year))
    return list(LOCAL_SOURCES.get(key,()))
