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
REGISTRY = {
    "CFGM Gestión Administrativa": _GM,
    "CFGS Administración y Finanzas": _AF,
    "CFGS Asistencia a la Dirección": _AD,
}
SOURCE_PAGE = {
    "CFGM Gestión Administrativa": 38875,
    "CFGS Administración y Finanzas": 38876,
    "CFGS Asistencia a la Dirección": 38877,
}


def list_modules(cycle: str, academic_year: str) -> dict:
    """Lista de propuestas de denominación, nunca material académico confirmado."""
    from territorial_profiles import year_code
    year = year_code(academic_year)
    canonical = canarias_ag.canonical_cycle(cycle)
    rows = REGISTRY.get(canonical, ())
    items = [
        {"code": code, "name": name, "course": course,
         "reference_annual_hours": hours, "reference_weekly_hours": weekly,
         "source_url": SOURCE_URL, "source_page": SOURCE_PAGE[canonical],
         "reference_academic_year": REFERENCE_YEAR,
         "curriculum_confirmed": False, "hours_confirmed": False}
        for code, name, course, hours, weekly in rows
    ]
    return {
        "territory": "Canarias", "family": "Administración y Gestión",
        "academic_year": year, "cycle": canonical, "count": len(items),
        "modules": items, "source_url": SOURCE_URL, "source_title": SOURCE_TITLE,
        "reference_academic_year": REFERENCE_YEAR,
        "status": "reference_requires_current_verification",
        "notice": ("Listado de referencia del anexo VI de 2024. Compruebe la "
                   "vigencia y las modificaciones posteriores para " + year +
                   ". Las horas no se asignan a ninguna programación y los "
                   "RA/CE no se importan sin confirmación. Los módulos "
                   "optativos dependen de la oferta concreta del centro."
                   if rows else
                   "La edición aún no incorpora el índice de módulos de "
                   "Grado Básico. Introduzca la denominación desde el currículo "
                   "canario que corresponda al curso y verifíquela."),
    }
