"""Índice documental de módulos de Grado D (Canarias, familia A&G).

La Resolución de 30/10/2024, BOC 226 de 13/11/2024, anexo VI,
estableció las distribuciones para GM y GS. Los metadatos aquí recogidos
son referencias históricas al anexo, NO certificaciones de vigencia 2026-27
ni importaciones automáticas de RA, CE o cargas horarias confirmadas.
"""
from __future__ import annotations
from copy import deepcopy
import canarias_ag

SOURCE_URL = "https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/anexo-6-resolucion-instrucciones-implantacion-distribucion-horaria-curriculos-24.pdf"
SOURCE_TITLE = "BOC 2024/226, Resolución 30/10/2024, anexo VI: distribuciones horarias GM/GS"
REFERENCE_YEAR = "2024-2025"
# (código RD, denominación, curso, horas anuales de referencia, horas/semana)
_GM = (
    ("0437", "Comunicación empresarial y atención al cliente", 1, 173, 5),
    ("0438", "Operaciones administrativas de compraventa", 1, 173, 5),
    ("0439", "Empresa y administración", 1, 96, 3),
    ("0440", "Tratamiento informático de la información", 1, 206, 6),
    ("0441", "Técnica contable", 1, 96, 3),
    ("0156", "Inglés profesional (GM)", 1, 96, 3),
    ("1664", "Digitalización aplicada a los sectores productivos (GM)", 1, 64, 2),
    ("1709", "Itinerario personal para la empleabilidad I", 1, 96, 3),
    ("0442", "Operaciones administrativas de recursos humanos", 2, 170, 5),
    ("0443", "Tratamiento de la documentación contable", 2, 202, 6),
    ("0446", "Empresa en el aula", 2, 170, 5),
    ("0448", "Operaciones auxiliares de gestión de tesorería", 2, 170, 5),
    ("1708", "Sostenibilidad aplicada al sistema productivo", 2, 32, 1),
    ("1710", "Itinerario personal para la empleabilidad II", 2, 96, 3),
    ("1713", "Proyecto intermodular", 2, 64, 2),
)
_GS_COMMON = (
    ("0647", "Gestión de la documentación jurídica y empresarial", 1, 138, 4),
    ("0648", "Recursos humanos y responsabilidad social corporativa", 1, 64, 2),
    ("0649", "Ofimática y proceso de la información", 1, 170, 5),
    ("0650", "Proceso integral de la actividad comercial", 1, 202, 6),
    ("0651", "Comunicación y atención al cliente", 1, 170, 5),
    ("0179", "Inglés profesional (GS)", 1, 96, 3),
    ("1665", "Digitalización aplicada a los sectores productivos (GS)", 1, 64, 2),
    ("1709", "Itinerario personal para la empleabilidad I", 1, 96, 3),
)
_AF = _GS_COMMON + (
    ("0652", "Gestión de recursos humanos", 2, 138, 4),
    ("0653", "Gestión financiera", 2, 138, 4),
    ("0654", "Contabilidad y fiscalidad", 2, 138, 4),
    ("0655", "Gestión logística y comercial", 2, 138, 4),
    ("0656", "Simulación empresarial", 2, 160, 5),
    ("1708", "Sostenibilidad aplicada al sistema productivo", 2, 32, 1),
    ("1710", "Itinerario personal para la empleabilidad II", 2, 96, 3),
    ("0657", "Proyecto intermodular de administración y finanzas", 2, 64, 2),
)
_AD = _GS_COMMON + (
    ("0661", "Protocolo empresarial", 2, 205, 6),
    ("0662", "Organización de eventos empresariales", 2, 238, 7),
    ("0663", "Gestión avanzada de la información", 2, 173, 5),
    ("0180", "Segunda lengua extranjera", 2, 96, 3),
    ("1708", "Sostenibilidad aplicada al sistema productivo", 2, 32, 1),
    ("1710", "Itinerario personal para la empleabilidad II", 2, 96, 3),
    ("0664", "Proyecto intermodular de asistencia a la dirección", 2, 64, 2),
)

BASIC_SOURCE_URL = "https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/anexo-5-resolucion-instrucciones-implantacion-distribucion-horaria-curriculos-24.pdf"
BASIC_SOURCE_TITLE = "BOC 2024/226, anexo V: distribución de CFGB Servicios Administrativos"
# Tutoría no se indexa como módulo con RA/CE. Las materias sin código RD
# figuran con code=None, conservando curso y ámbito para diferenciarlas.
_BASIC = (
    ("3161", "Lengua castellana y Ciencias sociales", 1, 132, 4),
    (None, "Lengua extranjera de iniciación profesional", 1, 66, 2),
    ("3163", "Matemáticas y Ciencias aplicadas", 1, 132, 4),
    (None, "Actividad física y bienestar emocional", 1, 66, 2),
    ("3001", "Tratamiento informático de datos", 1, 236, 7),
    ("3003", "Técnicas administrativas básicas", 1, 236, 7),
    ("3006", "Preparación de pedidos y venta de productos", 1, 66, 2),
    (None, "Prevención y salud laboral", 1, 33, 1),
    ("3162", "Lengua castellana y Ciencias sociales", 2, 66, 2),
    (None, "Lengua extranjera de iniciación profesional", 2, 66, 2),
    ("3164", "Matemáticas y Ciencias aplicadas", 2, 132, 4),
    ("3002", "Aplicaciones básicas de ofimática", 2, 302, 9),
    ("3005", "Atención al cliente", 2, 66, 2),
    ("3004", "Archivo y comunicación", 2, 203, 6),
    ("3159", "Itinerario personal para la empleabilidad", 2, 66, 2),
    ("3160", "Proyecto intermodular de aprendizaje colaborativo (GB)", 2, 66, 2),
)
# Normas estatales de título que permiten localizar enseñanzas mínimas.
# NO sustituyen a los currículos ni a las instrucciones de Canarias.
NATIONAL_TITLES = {
    "CFGB Servicios Administrativos": {
        "title": "Real Decreto 127/2014, anexo I (Servicios Administrativos)",
        "url": "https://www.boe.es/eli/es/rd/2014/02/28/127",
    },
    "CFGM Gestión Administrativa": {
        "title": "Real Decreto 1631/2009 (Gestión Administrativa)",
        "url": "https://www.boe.es/eli/es/rd/2009/10/30/1631",
    },
    "CFGS Administración y Finanzas": {
        "title": "Real Decreto 1584/2011 (Administración y Finanzas)",
        "url": "https://www.boe.es/eli/es/rd/2011/11/04/1584",
    },
    "CFGS Asistencia a la Dirección": {
        "title": "Real Decreto 1582/2011 (Asistencia a la Dirección)",
        "url": "https://www.boe.es/eli/es/rd/2011/11/04/1582",
    },
}

REGISTRY = {
    "CFGB Servicios Administrativos": _BASIC,
    "CFGM Gestión Administrativa": _GM,
    "CFGS Administración y Finanzas": _AF,
    "CFGS Asistencia a la Dirección": _AD,
}
SOURCE_PAGE = {
    "CFGB Servicios Administrativos": 38847,
    "CFGM Gestión Administrativa": 38875,
    "CFGS Administración y Finanzas": 38876,
    "CFGS Asistencia a la Dirección": 38877,
}


def list_modules(cycle: str, academic_year: str, course: str | int | None = None) -> dict:
    """Lista de propuestas de denominación, nunca material académico confirmado."""
    from territorial_profiles import year_code
    year = year_code(academic_year)
    canonical = canarias_ag.canonical_cycle(cycle)
    if course not in (None, '') and str(course) not in ('1','2'):
        raise ValueError('El curso del ciclo debe ser primero o segundo.')
    selected_course = int(course) if course not in (None, '') else None
    complete = REGISTRY[canonical]
    rows = [item for item in complete if selected_course is None or item[2] == selected_course]
    is_basic = canonical == 'CFGB Servicios Administrativos'
    source = BASIC_SOURCE_URL if is_basic else SOURCE_URL
    source_title = BASIC_SOURCE_TITLE if is_basic else SOURCE_TITLE
    items = [
        {"code": code, "name": name, "course": course,
         "reference_annual_hours": hours, "reference_weekly_hours": weekly,
         "source_url": source, "source_page": SOURCE_PAGE[canonical],
         "reference_academic_year": REFERENCE_YEAR,
         "curriculum_confirmed": False, "hours_confirmed": False}
        for code, name, course, hours, weekly in rows
    ]
    return {
        "territory": "Canarias", "family": "Administración y Gestión",
        "academic_year": year, "cycle": canonical, "count": len(items),
        "total_count": len(complete), "filter_course": selected_course,
        "modules": items, "source_url": source, "source_title": source_title,
        "reference_academic_year": REFERENCE_YEAR,
        "state_title_regulation": deepcopy(NATIONAL_TITLES[canonical]),
        "state_title_status": "state_minimums_reference_only",
        "status": "reference_requires_current_verification",
        "notice": (
            "Referencia del anexo " + ("V" if is_basic else "VI") +
            " del BOC de 2024. Compruebe modificaciones y vigencia para " + year +
            ". Las horas no se incorporan automáticamente a las programaciones "
            "y no se importan RA/CE. La optativa y los ámbitos sin código "
            "RD requieren confirmación de la oferta y programación del centro. "
            "Tutoría queda fuera del índice de módulos. La norma estatal de "
            "título es una referencia para buscar RA y CE, pero debe "
            "contrastarse con las modificaciones y la normativa de Canarias."
        ),
    }
