"""Orientación académica de Grado D presencial ordinario, Canarias, 2026-27.

No atribuye notas, dispensa requisitos, expide certificados ni formaliza
acuerdos. Las entradas son datos de expediente contrastados por el docente.
"""
from decimal import Decimal, InvalidOperation
import canarias_ag as ag

BASE='https://www.gobiernodecanarias.org/boc/2025/118/2219.html'
AMENDMENT='https://www.gobiernodecanarias.org/boc/2025/249/4298.html'
DUAL='https://www.gobiernodecanarias.org/boc/2024/230/3794.html'
PRL='https://www.gobiernodecanarias.org/boc/2026/210/3623.html'
VERSION='2026-11-21'
STATUS=('superado','no_superado','pendiente')


def number(raw,maximum):
    try:
        n=Decimal(str(raw))
    except (ValueError,InvalidOperation):
        raise ValueError('Valor numérico incorrecto.') from None
    if not n.is_finite() or n<0 or n>maximum or n.as_tuple().exponent < -4:
        raise ValueError('Valor numérico incorrecto.')
    return n


def integer(raw,maximum):
    if type(raw) is not int or not 0<=raw<=maximum:
        raise ValueError('Número entero incorrecto.')
    return raw


def state(raw):
    if raw not in STATUS:
        raise ValueError('Seleccione superado, no superado o pendiente de comprobación.')
    return raw


def result(status,reason,sources,**extra):
    return {'status':status,'reason':reason,'sources':sources,'rules_version':VERSION,
            'official_decision':False,**extra}


def promotion(basic,raw):
    session=raw.get('session')
    if session not in ('ordinaria','extraordinaria'):
        raise ValueError('Seleccione la evaluación final.')
    count=integer(raw.get('pending_modules'),100)
    hours=number(raw.get('pending_hours'),2000)
    total=number(raw.get('total_hours'),2000)
    if not total or hours>total or bool(count)!=bool(hours):
        raise ValueError('Recuento y carga de pendientes incoherentes.')
    if raw.get('record_complete') is not True:
        return result('pendiente','Falta contrastar todos los módulos y ámbitos del expediente.',[BASE,AMENDMENT])
    if basic:
        if total!=30:
            return result('revision','La regla de seis horas se aplica al horario semanal ordinario de 30 horas.',[AMENDMENT])
        common=integer(raw.get('pending_common'),2)
        if count==0 and common==0:
            return result('cumple','Todos los módulos y materias/ámbitos requeridos están superados.',[AMENDMENT])
        if session=='ordinaria':
            return result('extraordinaria','No reúne las condiciones de promoción ordinaria. Corresponde evaluación extraordinaria.',[AMENDMENT])
        if count==0 or (hours<=6 and common<=1):
            return result('posible','Puede promocionar con pendientes; corresponde al equipo docente acordarlo y planificar la recuperación.',[AMENDMENT])
        return result('no_cumple','No encaja en los supuestos de promoción extraordinaria.',[AMENDMENT])
    if count==0 or hours*5<=total:
        return result('cumple','No quedan módulos pendientes o su carga no excede el 20 % de primero.',[BASE])
    if count==1:
        return result('excepcion','Un único módulo supera el 20 %: el equipo docente puede autorizar la promoción excepcional.',[BASE])
    return result('no_cumple','Varios módulos pendientes superan el 20 % de la carga horaria.',[BASE])


def permanence(basic,raw):
    years=integer(raw.get('years_used'),20)
    if raw.get('record_complete') is not True:
        return result('pendiente','Compruebe los cursos efectivos de permanencia.',[AMENDMENT,BASE])
    if basic:
        if years>=4:
            return result('limite','Se alcanza el límite ordinario de cuatro cursos; revisar expediente y situaciones especiales.',[AMENDMENT])
        return result('revision','La permanencia es excepcional y requiere agotar medidas ordinarias de apoyo.',[AMENDMENT],remaining=4-years)
    duration=integer(raw.get('cycle_years'),4)
    if duration!=2:
        return result('revision','Esta versión solo contempla ciclos presenciales ordinarios de dos cursos.',[BASE])
    return result('limite' if years>=duration+2 else 'dentro_limite',
                  'Límite general de permanencia; compruebe renuncias, convocatorias y autorizaciones.',[BASE],remaining=max(0,duration+2-years))


def feoe(basic,raw):
    course=integer(raw.get('course'),2)
    if course not in (1,2):
        raise ValueError('Curso no válido.')
    age=state(raw.get('age_16'))
    prl=state(raw.get('prl'))
    annex=state(raw.get('annex_v'))
    if basic and course!=2:
        return result('no_cumple','El acceso ordinario de Grado Básico se ubica en segundo.',[BASE,DUAL])
    if age=='no_superado' or prl=='no_superado' or annex=='no_superado':
        return result('no_cumple','No se acredita edad mínima o competencias preventivas; no procede iniciar la estancia.',[BASE,DUAL])
    if 'pendiente' in (age,prl,annex):
        return result('pendiente','Falta comprobar edad, competencias PRL o valoración conjunta aplicable.',[BASE,DUAL])
    certificate=raw.get('specific_certificate')
    if certificate not in ('no_requerido','pendiente','expedido'):
        raise ValueError('Indique el estado de la certificación específica solicitada por la empresa.')
    if certificate=='pendiente':
        return result('pendiente','La empresa exige certificación académica específica: debe tramitarla el centro antes de la estancia.',[PRL,BASE])
    if raw.get('conditions_confirmed') is not True:
        return result('pendiente','Falta confirmar las condiciones de incorporación y el plan formativo.',[BASE,DUAL])
    return result('cumple','Requisitos comprobados para propuesta de acceso; falta la decisión y tramitación del centro.',[BASE,DUAL,PRL])


def graduation(basic,raw):
    modules=state(raw.get('modules'))
    project=state(raw.get('project'))
    company=raw.get('feoe')
    if company not in ('superado','no_superado','pendiente','exencion_resuelta'):
        raise ValueError('Indique el estado de la FEOE.')
    common=state(raw.get('common')) if basic else 'superado'
    values=(modules,project,common,company)
    if 'no_superado' in values:
        return result('no_cumple','Hay enseñanzas o formación en empresa no superadas.',[BASE])
    if 'pendiente' in values or raw.get('record_complete') is not True:
        return result('pendiente','Falta verificar el expediente completo, incluidos los pendientes anteriores.',[BASE])
    return result('cumple','Cumple los requisitos aportados para propuesta de titulación, pendiente de acuerdo colegiado.',[BASE],
                  titles=['Graduado en ESO','Técnico Básico'] if basic else ['Título del ciclo correspondiente'])


def evaluate(raw):
    if not isinstance(raw,dict):
        raise ValueError('Solicitud incorrecta.')
    cycle=ag.canonical_cycle(raw.get('cycle'))
    basic=cycle.startswith('CFGB ')
    if raw.get('academic_year')!='2026-2027' or raw.get('modality')!='presencial_ordinaria':
        return result('revision','Fuera del ámbito validado: curso 2026-2027, Grado D presencial ordinario.',[BASE,AMENDMENT])
    action=raw.get('action')
    functions={'promotion':promotion,'permanence':permanence,'feoe':feoe,'graduation':graduation}
    if action not in functions:
        raise ValueError('Seleccione una decisión académica.')
    return {**functions[action](basic,raw),'cycle':cycle,'action':action}
