"""Cálculo orientativo de ámbitos comunes con materias diferenciadas.

Resolución de 9/06/2025, BOC 118 de 17/06/2025, anexo I, séptima.
No genera actas, no deduce una etiqueta cualitativa de una media ni
redondea para decidir superación. Requiere las horas contrastadas y
todas las materias del ámbito para el curso del alumnado.
"""
from decimal import Decimal, InvalidOperation, localcontext
from common_scopes import COMM, SCI

SOURCE='https://www.gobiernodecanarias.org/boc/2025/118/2219.html'
CONVERSION={'IN':Decimal(3),'SU':Decimal(5),'BI':Decimal(6),
            'NT':Decimal('7.5'),'SB':Decimal(9)}
MATTERS={
    (COMM,1):('lengua_social','extranjera'),
    (COMM,2):('lengua_social','extranjera'),
    (SCI,1):('matematicas_ciencias','actividad_fisica'),
    (SCI,2):('matematicas_ciencias',),
}


def calculate(ambito, course, session, matters, hours_confirmed=False):
    if type(course) is not int or (ambito,course) not in MATTERS:
        raise ValueError('Seleccione el ámbito y curso correspondientes.')
    if session not in ('ordinaria','extraordinaria'):
        raise ValueError('Seleccione la convocatoria final.')
    if hours_confirmed is not True:
        raise ValueError('Contraste la carga horaria de las materias antes del cálculo.')
    expected=MATTERS[(ambito,course)]
    if not isinstance(matters,list) or len(matters)!=len(expected):
        raise ValueError('Incluya todas las materias del ámbito para el curso.')
    values={}
    for row in matters:
        if not isinstance(row,dict) or row.get('matter') not in expected or row['matter'] in values:
            raise ValueError('Materia ajena, duplicada o incompleta.')
        grade=row.get('grade')
        if not isinstance(grade,str) or grade not in CONVERSION:
            raise ValueError('Indique una calificación cualitativa validada de cada materia.')
        try:
            hours=Decimal(str(row.get('hours')))
        except (InvalidOperation,ValueError):
            raise ValueError('Carga horaria incorrecta.') from None
        if not hours.is_finite() or not Decimal(0)<hours<=Decimal(1000):
            raise ValueError('Carga horaria incorrecta.')
        if hours.as_tuple().exponent < -4:
            raise ValueError('Como máximo cuatro decimales en la carga horaria.')
        values[row['matter']]=(CONVERSION[grade],hours)
    with localcontext() as ctx:
        ctx.prec=28
        total=sum(h for _,h in values.values())
        weighted=sum(g*h for g,h in values.values())
        mean=weighted/total
        # Comparación exacta, sin redondeo de la media visible.
        passed=all(g>=5 for g,_ in values.values()) if session=='ordinaria' else weighted>=5*total
    return {'mean':str(mean),'passed':passed,'session':session,
            'ambito':ambito,'course':course,'source_url':SOURCE,
            'official_grade':None,'status':'orientativo_pendiente_equipo_docente'}
