"""Ámbito local de EvalúaFP Canarias: familia Administración y Gestión.

Registro de identidad de enseñanzas, NO repositorio de currículos validados.
Nunca infiere RA, CE, horas o normativa a partir de la mera denominación.
"""
from __future__ import annotations

from copy import deepcopy
import unicodedata

FAMILY = "Administración y Gestión"
TERRITORY = "Canarias"
CATALOG_URL = ("https://www.gobiernodecanarias.org/educacion/web/"
               "formacion_profesional/ensenanzas/titulos/")

# Son Grados D publicados para Administración y Gestión por la Consejería.
# Los enlaces son informativos; las fichas antiguas NO acreditan los módulos
# vigentes ni la distribución horaria del curso 2026-2027.
CYCLES = (
    {"key": "CFGB-SA", "grade": "Básico",
     "name": "CFGB Servicios Administrativos",
     "title": "Técnico Básico en Servicios Administrativos",
     "source_url": "https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/fpgb/curriculos_fpgb/"},
    {"key": "CFGM-GA", "grade": "Medio",
     "name": "CFGM Gestión Administrativa",
     "title": "Técnico en Gestión Administrativa",
     "source_url": "https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/"},
    {"key": "CFGS-AF", "grade": "Superior",
     "name": "CFGS Administración y Finanzas",
     "title": "Técnico Superior en Administración y Finanzas",
     "source_url": "https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/"},
    {"key": "CFGS-AD", "grade": "Superior",
     "name": "CFGS Asistencia a la Dirección",
     "title": "Técnico Superior en Asistencia a la Dirección",
     "source_url": "https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/"},
)
REGULATIONS = (
    {"title": "Ley Orgánica 3/2022, de ordenación e integración de la FP",
     "url": "https://www.boe.es/eli/es/lo/2022/03/31/3/con"},
    {"title": "Real Decreto 659/2023, de ordenación del Sistema de FP",
     "url": "https://www.boe.es/eli/es/rd/2023/07/18/659/con"},
    {"title": "Decreto 9/2023: currículos de Grado Básico de Canarias",
     "url": "https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/fpgb/curriculos_fpgb/"},
    {"title": "Resolución 29/10/2026: Grados C y B de nivel 1, Anexo I de Administración y Gestión",
     "url": "https://www.gobiernodecanarias.org/boc/2026/227/3917.html"},
)


def _fold(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def ensure_territory(value: object) -> str:
    """No permite crear módulos pertenecientes a otra comunidad."""
    if _fold(value) not in ("canarias", "cn"):
        raise ValueError("Esta edición solo admite enseñanzas de Canarias.")
    return TERRITORY


def canonical_cycle(value: object) -> str:
    """Admite denominaciones oficiales y abreviaturas inequívocas."""
    name = _fold(value)
    for cycle in CYCLES:
        accepted = {_fold(cycle["name"]), _fold(cycle["title"]),
                    _fold(cycle["name"].split(" ", 1)[-1])}
        if name in accepted:
            return cycle["name"]
    raise ValueError(
        "El ciclo no pertenece a los cuatro Grados D de Administración y Gestión "
        "incluidos en la primera edición para Canarias. Selecciónelo del catálogo."
    )


def public_catalog() -> dict:
    """Solo devuelve títulos identificados: no crea módulos ni criterios ficticios."""
    return {
        "edition": "EvalúaFP Canarias · Administración y Gestión",
        "territory": TERRITORY,
        "family": FAMILY,
        "catalog_grade": "D",
        "cycles": deepcopy(CYCLES),
        "sources": deepcopy(REGULATIONS),
        "module_catalog_status": "pendiente_de_contraste",
        "verified_modules": [],
        "verified_outcomes": [],
        "verified_criteria": [],
        "notice": (
            "Las denominaciones de los cuatro títulos se han cotejado con "
            "la oferta oficial de Canarias. Los módulos, códigos, RA, CE, "
            "horas, calendarios y ponderaciones se revisan para cada curso "
            "antes de considerarse confirmados. Los Grados A/B/C se añadirán "
            "separadamente sin confundirlos con los títulos de Grado D."
        ),
        "taxation_notice": (
            "Para supuestos canarios se utilizará IGIC cuando proceda. "
            "Los tipos y exenciones no deben aplicarse sin verificar el caso."
        ),
    }
