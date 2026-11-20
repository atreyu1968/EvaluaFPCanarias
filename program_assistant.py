"""Propuestas pedagógicas para una programación completa: deterministas o IA autorizada.

El contenido generado es un BORRADOR editable. Las horas y la normativa solo
provienen de una ficha identificada y siempre requieren revisión docente.
La IA no modifica directamente la base de datos ni RA/CE confirmados.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
import re

import ia
import official_catalog
import schedule_engine

# Una matriz amplia inspirada en las secciones de programaciones aportadas:
# no se toman hechos particulares de un centro como verdades para otros centros.
FIELD_TITLES = {
 'justification':'Justificación y principios de la programación',
 'identification_data':'Identificación y características del módulo',
 'academic_context':'Punto de partida y diagnóstico pedagógico',
 'center_characteristics':'Características y recursos del centro',
 'student_characteristics':'Características generales del grupo',
 'environment_context':'Entorno socioproductivo y relación con empresas',
 'normative_references':'Marco normativo (fuentes identificadas)',
 'objectives':'Objetivos generales y contribución del módulo',
 'competencies':'Competencias profesionales, personales y sociales',
 'qualifications':'Cualificaciones y estándares profesionales',
 'contents':'Contenidos y saberes del módulo',
 'learning_activities':'Secuencia de situaciones y actividades de aprendizaje',
 'methodology':'Principios y estructura de la metodología',
 'interdisciplinarity':'Interdisciplinariedad y coordinación',
 'inclusion':'Atención a la diversidad y DUA',
 'resources':'Recursos, espacios y materiales',
 'assessment':'Evaluación continua de los RA y CE',
 'instruments':'Instrumentos, evidencias y rúbricas',
 'grading':'Criterios de calificación y ponderaciones',
 'assessment_sessions':'Sesiones de evaluación',
 'recovery':'Recuperación de aprendizajes pendientes',
 'extraordinary_assessment':'Pruebas de recuperación y evaluación extraordinaria',
 'promotion':'Promoción y continuidad formativa',
 'attendance':'Asistencia, seguimiento y situaciones de pérdida de evaluación continua',
 'enterprise':'Formación en empresa u organismo equiparado (FEOE)',
 'extracurricular':'Actividades complementarias y extraescolares',
 'observations':'Contingencias y seguimiento de la programación',
}
# Solo se entregan en el prompt datos curriculares generales, nunca centro,
# docentes, lista de alumnado, nombres propios ni contenido no autorizado.
AI_FIELDS = set(FIELD_TITLES)-{'normative_references','identification_data','promotion'}


def module_context(db, module_id):
    row=db.execute('SELECT id,name,cycle,academic_year FROM modules WHERE id=?',(module_id,)).fetchone()
    if row is None:raise ValueError('El módulo no existe.')
    outcomes=[dict(r) for r in db.execute('SELECT id,code,description,weight FROM outcomes WHERE module_id=? ORDER BY id',(module_id,))]
    criteria=[dict(c) for c in db.execute('''SELECT c.id,c.code,c.description,c.outcome_id,o.code AS ra_code
             FROM criteria c JOIN outcomes o ON o.id=c.outcome_id WHERE o.module_id=? ORDER BY o.id,c.id''',(module_id,))]
    return dict(row), outcomes, criteria


def hours_proposal(module, region):
    # Solo se muestra la referencia histórica cuando el curso está cubierto
    # por la beta actual. Para años posteriores se exige una nueva fuente.
    if module.get('academic_year') != '2026-2027':
        return None
    lookup=official_catalog.find(region,module['cycle'],module['name'])
    if lookup:
        lookup=dict(lookup)
        lookup['status']='pendiente_de_contraste_docente'
        lookup['require_confirmation']=True
        lookup['amendments']=[{
            'title':'Ampliaciones y modificaciones de la distribución horaria 2025-2026',
            'url':'https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/implantacion_curriculos/imolantacion-curriculos-lomloe-looifp/'
        }]
    return lookup


def simple_reference_list(module,region):
    # La ficha es una propuesta de lectura. No se afirma que sea el texto
    # consolidado vigente ni que aplique automáticamente a todo módulo.
    return official_catalog.normative_proposal(region,module['cycle'],module['name'],academic_year=module['academic_year'])


def _ra_summary(outcomes):
    return '; '.join(f'{r["code"]}: {r["description"]}' for r in outcomes[:12]) or 'RA pendientes de incorporación desde currículo oficial'


def base_fields(module, outcomes, criteria, region='Canarias'):
    """Propuesta de escritura local y editable sin afirmar que haya intervenido IA."""
    m=module['name'];cycle=module['cycle'];year=module['academic_year'];ra=_ra_summary(outcomes)
    n=len(criteria)
    no_ra='La distribución precisa de actividades se completará después de confirmar los RA y CE oficiales. '
    baseline={
      'justification':f'La programación del módulo «{m}», integrado en {cycle}, organiza una formación aplicada al desempeño profesional. Se prioriza el desarrollo progresivo de competencias, la accesibilidad, la igualdad de oportunidades y la transferencia de los aprendizajes a situaciones auténticas. Esta propuesta se adaptará a las características del grupo y a los acuerdos del departamento.',
      'identification_data':f'Módulo profesional: {m}. Ciclo formativo: {cycle}. Curso académico: {year}. Comunidad autónoma: {region}. Pendientes de confirmar: código oficial, curso del ciclo, horario del grupo y concreción departamental.',
      'academic_context':'El punto de partida se establecerá mediante una evaluación inicial y revisión de aprendizajes previos. La secuencia didáctica se ajustará a la diversidad de ritmos y experiencias del alumnado, sin anticipar resultados o características personales no comprobadas.',
      'center_characteristics':'El centro aportará los espacios educativos, recursos digitales y materiales autorizados que permitan desarrollar las actividades previstas. Deben completarse los datos específicos del proyecto educativo, instalaciones y dotaciones disponibles.',
      'student_characteristics':'La planificación prevé distintas experiencias de partida, niveles de autonomía y necesidades de apoyo. Los datos concretos de grupo y el resultado de la evaluación inicial serán consignados por el docente sin incluir datos personales innecesarios.',
      'environment_context':f'El desarrollo del módulo «{m}» se relacionará con procesos reales del sector y con las necesidades del tejido productivo próximo. Se propondrán situaciones contextualizadas y colaboración con entidades cuando existan acuerdos efectivos.',
      'normative_references':simple_reference_list(module,region),
      'objectives':f'El módulo contribuirá a desarrollar actuaciones profesionales propias de {cycle}, integrando conocimientos, procedimientos, autonomía, precisión y calidad del trabajo. La concreción se realizará vinculando cada objetivo operativo con los RA confirmados: {ra}. Los objetivos oficiales del título deberán contrastarse con su norma reguladora.',
      'competencies':f'La propuesta prioriza competencias de organización, resolución de problemas, comunicación profesional, tratamiento riguroso de la información, uso responsable de herramientas digitales, trabajo en equipo y cumplimiento de la normativa aplicable. Relación curricular de partida: {ra}. Comprobar códigos y formulaciones oficiales en el título.',
      'qualifications':'Se identificarán las cualificaciones profesionales, estándares de competencia y correspondencias que efectivamente figuren en la norma del título. No se incorporan códigos de unidades de competencia por conjetura.',
      'contents':f'Los contenidos se secuenciarán desde los fundamentos a la aplicación integrada, tomando como eje los resultados de aprendizaje confirmados: {ra}. Se completarán los contenidos básicos y autonómicos tras revisar la fuente curricular.',
      'learning_activities':f'{no_ra if not n else "Cada CE confirmado tendrá, al menos, una oportunidad de aprendizaje y una evidencia evaluable asociada. "}Se incluirán actividades de activación de conocimientos previos, análisis de casos, demostración guiada, práctica individual y colaborativa, producción aplicada, retroalimentación y reflexión sobre el proceso.',
      'methodology':'Se combinarán explicaciones breves y demostraciones con aprendizaje basado en problemas, casos y tareas profesionales contextualizadas. Cada unidad incluirá una fase de activación, una de desarrollo guiado, otra de aplicación autónoma y una de evaluación formativa con retroalimentación específica.',
      'interdisciplinarity':f'Se fomentará la coordinación con los restantes módulos de {cycle} para compartir vocabulario técnico, proyectos integrados, tareas intermodulares y criterios transversales de calidad, cuando esté previsto en los acuerdos de equipo docente.',
      'inclusion':'Se aplicarán los principios del Diseño Universal para el Aprendizaje: diversidad de formas de acceso a la información, participación y expresión del aprendizaje. Se utilizarán apoyos graduados, instrucciones claras, recursos accesibles, variedad de evidencias y adaptación metodológica conforme a la evaluación inicial.',
      'resources':'Se prevén aula ordinaria, materiales curriculares actualizados, documentos profesionales o simulados, equipos informáticos cuando estén disponibles, herramientas de ofimática y plataformas autorizadas por el centro. La dotación concreta y las licencias se verificarán antes de programar actividades.',
      'assessment':'La evaluación será continua, criterial y vinculada a los RA y CE confirmados. Cada criterio se evidenciará mediante tareas observables y se registrarán las valoraciones para facilitar la retroalimentación, la revisión y la recuperación. La calificación seguirá la ponderación aprobada por el docente o departamento.',
      'instruments':'Se propone combinar pruebas de aplicación, ejercicios prácticos, tareas de proyecto, rúbricas analíticas, listas de cotejo, portafolios y observación documentada. La selección concreta se asignará a cada unidad y a los CE correspondientes, evitando instrumentos sin evidencia identificable.',
      'grading':'Las ponderaciones se obtendrán de la matriz RA–CE aprobada en EvalúaFP. Si el departamento no ha fijado pesos expresos, el reparto igual por CE se mostrará como propuesta revisable. No se añadirá un porcentaje de FEOE aparte que duplique la calificación.',
      'assessment_sessions':'Se tomarán como referencia las tres evaluaciones previstas en el calendario del curso, con registro de evidencias, identificación de CE pendientes y planes de mejora. Las fechas concretas de las sesiones se ajustarán al calendario aprobado por el centro.',
      'recovery':'Se organizarán actividades de apoyo, práctica dirigida y nuevas oportunidades de demostrar los CE no alcanzados. Cada recuperación identificará el resultado o criterio pendiente, el instrumento, la fecha prevista y los criterios de corrección, manteniendo la trazabilidad.',
      'extraordinary_assessment':'Cuando proceda, se facilitará una propuesta individualizada de actividades y pruebas centradas exclusivamente en los RA o CE pendientes, conforme a la normativa aplicable y los acuerdos del centro.',
      'promotion':'La promoción se ajustará a la normativa vigente del nivel formativo y a las decisiones del equipo docente. Las condiciones concretas se incorporarán únicamente cuando puedan contrastarse con las instrucciones de evaluación aplicables.',
      'attendance':'La asistencia y participación se registrarán conforme a las normas del centro. Si se produce una situación que afecte a la evaluación continua, se aplicará el procedimiento normativo y departamental vigente, garantizando información al alumnado y evidencias de evaluación.',
      'enterprise':'Se identificarán RA/CE susceptibles de trabajarse en la formación en empresa, el calendario aproximado, el plan formativo, las evidencias y el seguimiento coordinado con la tutoría de empresa. La asignación se validará junto al plan del ciclo; no generará porcentajes de nota adicionales por sí misma.',
      'extracurricular':'Se propondrán visitas profesionales, charlas de entidades, talleres y salidas vinculadas a los RA y CE. Se distinguirán actividades complementarias en horario escolar y extraescolares fuera de él. Su realización quedará condicionada a disponibilidad, autorizaciones y planificación del centro.',
      'observations':'La programación podrá ajustarse por cambios de calendario, recursos, características del grupo o coordinación con empresas. Cada modificación relevante se documentará y se contrastará con la programación aprobada por el departamento.',
    }
    return {k:v[:11000] for k,v in baseline.items()}


def propose(db,module_id,region='Canarias',mode='base',only_fields=None):
    if mode not in ('base','ai'):
        raise ValueError('Modo de generación no admitido.')
    module,outcomes,criteria=module_context(db,module_id)
    if not isinstance(region,str) or len(region)>80:raise ValueError('Comunidad autónoma no válida.')
    baseline=base_fields(module,outcomes,criteria,region)
    if only_fields is not None:
        if not isinstance(only_fields,list) or not only_fields or len(only_fields)>len(FIELD_TITLES) or any(k not in FIELD_TITLES for k in only_fields):
            raise ValueError('Campos no válidos para la propuesta.')
        baseline={k:v for k,v in baseline.items() if k in only_fields}
    source='Plantillas locales editables (sin llamada a IA)'
    if mode=='ai':
        if not ia.key_available():
            raise ValueError('Para generar con IA configure y desbloquee la clave API en Ajustes. Mientras tanto puede utilizar el borrador local.')
        keys=[key for key in baseline if key in AI_FIELDS]
        prompt={
          'tarea':'Elabora propuestas pedagógicas para una programación de FP. Devuelve un JSON con objeto "fields": {clave: texto}. Todas las claves solicitadas deben aparecer. Mantén textos sustantivos, específicos y editables (aprox. 100-250 palabras según apartado).',
          'reglas':['Usa SOLO el currículo confirmado facilitado y el contexto académico general.',
           'NO inventes datos del centro, del alumnado, normas, códigos oficiales, fechas, horas, pesos, porcentajes, reglamentos ni acuerdos del departamento.',
           'Evita cualquier referencia nominal al docente o al alumnado. No añadas referencias normativas: vienen de catálogo independiente.',
           'Cuando falte un dato, indica expresamente pendiente de confirmación docente.',
           'Proporciona instrumentos concretos, secuencias y ejemplos vinculados a los RA/CE existentes sin alterar sus enunciados.',
           'No incluyas HTML ni Markdown de documento completo; solo texto por campo.'],
          'campos':{k:FIELD_TITLES[k] for k in keys},
          'modulo':module['name'],'ciclo':module['cycle'],'curso':module['academic_year'],
          'comunidad':region,
          'RA':[{ 'code':r['code'],'description':r['description'][:900]} for r in outcomes[:16]],
          'CE':[{ 'code':c['code'],'RA':c['ra_code'],'description':c['description'][:350]} for c in criteria[:85]],
          'base_local':{k:baseline[k][:900] for k in keys}}
        data,model=ia.chat('generation',json.dumps(prompt,ensure_ascii=False),limit=20000)
        if not isinstance(data,dict) or not isinstance(data.get('fields'),dict):
            raise ValueError('La IA no ha devuelto los apartados esperados. No se ha modificado el borrador.')
        newdata={}
        for key in keys:
            value=data['fields'].get(key)
            if not isinstance(value,str) or not 30<=len(value.strip())<=11500:
                raise ValueError(f'La propuesta de IA para {FIELD_TITLES[key]} no es válida; no se ha modificado nada.')
            newdata[key]=value.strip()
        baseline.update(newdata)
        source='IA ('+model+') · propuesta no validada'
    return {'fields':baseline,'source':source,'hour_reference':hours_proposal(module,region),
            'notes':['Solo se generan propuestas. El docente debe revisar y confirmar.',
                     'No se han cambiado RA, CE, ponderaciones ni horas aprobadas.',
                     'No se han enviado datos del alumnado ni nombres de docentes a la IA.']}


def improve_text(db,module_id,field,text,authorize_ai=False):
    if field not in AI_FIELDS and field!='normative_references':
        raise ValueError('Seleccione un campo de texto de la programación.')
    if not isinstance(text,str) or len(text)>11500 or not text.strip():
        raise ValueError('Escriba un texto de hasta 11.500 caracteres antes de solicitar la mejora.')
    if not authorize_ai:raise ValueError('Autorice expresamente el envío del texto al proveedor de IA.')
    module,outcomes,criteria=module_context(db,module_id)
    if not ia.key_available():raise ValueError('Configure y desbloquee antes su clave API.')
    prompt={
      'tarea':'Mejora la redacción en español de España, formal y propia de una programación didáctica de FP. Devuelve solo {"text":"..."}.',
      'apartado':FIELD_TITLES[field], 'modulo':module['name'],'ciclo':module['cycle'],
      'texto_docente':text,
      'reglas':['Conserva exactamente todos los datos, fechas, códigos RA/CE, horas, porcentajes y nombres propios facilitados.',
        'No inventes referencias legales ni completes citas normativas dudosas.',
        'No cambies decisiones pedagógicas ni de ponderaciones.',
        'Ordena párrafos, corrige ortografía y mejora cohesión; no alteres la intención.']}
    result,model=ia.chat('generation',json.dumps(prompt,ensure_ascii=False))
    improved=result.get('text') if isinstance(result,dict) else None
    if not isinstance(improved,str) or len(improved)<15 or len(improved)>15000:
        raise ValueError('La respuesta de la IA no puede utilizarse. El texto original sigue intacto.')
    # Protección básica frente a pérdidas de fechas y porcentajes críticos.
    guards=[r'\b\d{4}-\d{2}-\d{2}\b',r'\bRA\s*\d+\b',r'\b\d+(?:[,.]\d+)?\s*%',r'\b\d+(?:[,.]\d+)?\s*(?:horas|h/semana)\b']
    for pattern in guards:
        old=re.findall(pattern,text,re.I)
        if old and not all(v in improved for v in old):
            raise ValueError('La propuesta de IA parece omitir una fecha, porcentaje, hora o RA del texto. Se ha descartado para proteger la información.')
    return {'field':field,'original':text,'proposal':improved.strip(),'source':'IA ('+model+')',
            'requires_acceptance':True}


def propose_units(db,module_id,schedule,region='Canarias'):
    """Una unidad por RA. El total es el documentado, nunca 6*32 supuesto."""
    module,outcomes,criteria=module_context(db,module_id)
    if not outcomes or not criteria:
        raise ValueError('Confirme primero el currículo RA/CE del módulo.')
    cfg=schedule_engine.clean(schedule,module['academic_year'])
    if not cfg['weekly_hours'] or not cfg['total_hours']:
        raise ValueError('Indique las horas semanales y totales correctas antes de distribuir las unidades.')
    counts=[sum(c['outcome_id']==o['id'] for c in criteria) for o in outcomes]
    if any(n==0 for n in counts):
        raise ValueError('Hay RA sin criterios. Complete el currículo antes de generar unidades.')
    total=Decimal(str(cfg['total_hours']))
    n_total=sum(counts)
    cents=int((total*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    if cents<len(outcomes):raise ValueError('No hay horas suficientes para crear una unidad por RA.')
    allocated=[(cents*n)//n_total for n in counts]
    remainder=cents-sum(allocated)
    order=sorted(range(len(allocated)),key=lambda i:(-(cents*counts[i] % n_total),i))
    for i in order[:remainder]:allocated[i]+=1
    # Distribución razonada por las horas lectivas de cada evaluación.
    probe=schedule_engine.plan({'schedule':cfg,'units':[]},criteria,module['academic_year'])
    capacities=[t['capacity'] for t in probe.get('terms',[])]
    if len(capacities)!=3 or not sum(capacities):
        raise ValueError('El calendario no ofrece horas: revise fechas, horario y festivos.')
    # Partición global de la secuencia de RA en tres evaluaciones. Evita el
    # fallo de un algoritmo codicioso que agota la 3.ª evaluación antes de
    # distribuir el resto de RA. La unidad no se divide ni retrocede de fecha.
    hours_by_ra=[h/100 for h in allocated]
    cumulative=[0.0]
    for h in hours_by_ra:cumulative.append(cumulative[-1]+h)
    n=len(hours_by_ra)
    best=None
    for end1 in range(n+1):
        for end2 in range(end1,n+1):
            loads=(cumulative[end1],cumulative[end2]-cumulative[end1],cumulative[n]-cumulative[end2])
            overload=[max(0.,loads[j]-float(capacities[j])) for j in range(3)]
            # Prioridad absoluta: minimizar los excesos por evaluación.
            # Empates: aprovechar evaluaciones con horas disponibles y
            # preservar la progresión cronológica de los RA.
            cost=(round(sum(v*v for v in overload),6),
                  round(sum(overload),6),
                  round(sum(abs(loads[j]-min(sum(capacities),cumulative[n])*float(capacities[j])/max(0.01,sum(capacities))) for j in range(3)),6),
                  abs(end1-n/3)+abs(end2-2*n/3))
            if best is None or cost<best[0]:best=(cost,end1,end2)
    _,end1,end2=best
    units=[]
    for i,(o,h) in enumerate(zip(outcomes,allocated)):
        term=0 if i<end1 else (1 if i<end2 else 2)
        mine=[c['code'] for c in criteria if c['outcome_id']==o['id']]
        units.append({'code':f'UD{i+1:02d}','title':o['description'][:220],
             'term':term+1,'hours':h/100,'criteria_codes':mine,
             'instruments':'Actividad de aplicación con rúbrica; prueba o tarea práctica y portafolio (propuesta revisable)',
             'resources':'Supuestos profesionales, material curricular y herramientas digitales autorizadas (adaptar al centro)'})
    preview=schedule_engine.plan({'schedule':cfg,'units':units},criteria,module['academic_year'])
    return {'units':units,'calendar_plan':preview,'source':'Distribución calculada a partir de RA/CE y horas del borrador; revisable',
            'warnings':preview['warnings']}


def update_weights(db,module_id,mode,rows=None,teacher_confirmed=False):
    """Edición atómica de pesos curriculares con cierre docente obligatorio."""
    from decimal import InvalidOperation
    import database
    import weight_defaults
    if teacher_confirmed is not True:
        raise ValueError('Es obligatorio confirmar expresamente el cambio de ponderaciones.')
    if mode not in ('automatic','manual'):
        raise ValueError('Modo de ponderación no admitido.')
    module,outcomes,criteria=module_context(db,module_id)
    if not outcomes or not criteria or any(not any(c['outcome_id']==ra['id'] for c in criteria) for ra in outcomes):
        raise ValueError('Revise los RA/CE: todos los RA deben tener al menos un CE.')
    closed=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evaluation_closures'").fetchone()
    if closed and db.execute('SELECT COUNT(*) FROM evaluation_closures WHERE module_id=?',(module_id,)).fetchone()[0]:
        raise ValueError('Este módulo tiene notas finales cerradas. Revise los cierres y las consecuencias antes de modificar los pesos desde el modo avanzado.')
    ra_ids={r['id'] for r in outcomes};ce_ids={c['id'] for c in criteria}
    if mode=='manual':
        if not isinstance(rows,list) or len(rows)!=len(outcomes):
            raise ValueError('Deben figurar todos los RA del módulo.')
        def pct(value):
            try:n=Decimal(str(value))
            except (InvalidOperation,TypeError):raise ValueError('Ponderación no numérica.')
            if not n.is_finite() or n<=0 or n>100 or n.as_tuple().exponent<-2:
                raise ValueError('Cada peso debe estar entre 0,01 y 100,00 % con dos decimales como máximo.')
            return n
        verified=[];assigned_ra=set();assigned_ce=set();ra_sum=Decimal('0')
        for record in rows:
            if not isinstance(record,dict):raise ValueError('Estructura de ponderación incorrecta.')
            rid=int(record.get('id',0))
            if rid not in ra_ids or rid in assigned_ra:raise ValueError('RA desconocido o repetido.')
            assigned_ra.add(rid);rw=pct(record.get('weight'));ra_sum+=rw
            ces=record.get('criteria')
            if not isinstance(ces,list):raise ValueError('Faltan CE de un RA.')
            ce_sum=Decimal('0');updated=[]
            for ce in ces:
                cid=int(ce.get('id',0))
                if cid not in ce_ids or cid in assigned_ce or next(c['outcome_id'] for c in criteria if c['id']==cid)!=rid:
                    raise ValueError('CE desconocido, duplicado o asociado al RA incorrecto.')
                assigned_ce.add(cid);cw=pct(ce.get('weight'));ce_sum+=cw;updated.append((cid,cw))
            if ce_sum!=Decimal('100.00'):raise ValueError(f'Los CE de {rid} suman {ce_sum} %, y deben sumar 100,00 %.')
            verified.append((rid,rw,updated))
        if ra_sum!=Decimal('100.00'):raise ValueError(f'Los RA suman {ra_sum} %, y deben sumar 100,00 %.')
        if assigned_ra!=ra_ids or assigned_ce!=ce_ids:raise ValueError('Faltan RA o CE por ponderar.')
        for rid,rw,children in verified:
            db.execute('UPDATE outcomes SET weight=? WHERE id=?',(float(rw),rid))
            weight_defaults.mark(db,'ra',rid,'manual')
            for cid,cw in children:
                db.execute('UPDATE criteria SET weight=? WHERE id=?',(float(cw),cid))
                weight_defaults.mark(db,'ce',cid,'manual')
    else:
        for r in outcomes:weight_defaults.mark(db,'ra',r['id'],'default')
        for c in criteria:weight_defaults.mark(db,'ce',c['id'],'default')
        weight_defaults.recalculate(db,module_id)
    database.log(db,'programming_weights_updated','module',module_id,
                 {'mode':mode,'teacher_confirmed':True,'RA':len(outcomes),'CE':len(criteria)})
    return {'saved':True,'mode':mode}


def enrich_unit_details(db,module_id,units,authorize_ai=False):
    """Propone evidencias y recursos concretos por unidad sin alterar el currículo.

    No guarda nada. La interfaz muestra la propuesta al docente para aceptar
    individualmente o conservar las decisiones ya tomadas.
    """
    if authorize_ai is not True:
        raise ValueError('Es obligatorio autorizar el uso de IA para mejorar las unidades.')
    if not ia.key_available():
        raise ValueError('Configure y desbloquee su clave API antes de solicitar propuestas.')
    if not isinstance(units,list) or not 1<=len(units)<=100:
        raise ValueError('Primero debe configurar entre 1 y 100 unidades.')
    module,outcomes,criteria=module_context(db,module_id)
    valid_codes={c['code']:c for c in criteria}
    request=[];seen=set()
    for unit in units:
        if not isinstance(unit,dict):raise ValueError('Unidad incorrecta.')
        code=unit.get('code');codes=unit.get('criteria_codes')
        if not isinstance(code,str) or not code or len(code)>30 or code in seen:
            raise ValueError('Códigos de unidad vacíos o repetidos.')
        seen.add(code)
        if not isinstance(codes,list) or any(x not in valid_codes for x in codes):
            raise ValueError(f'Unidad {code}: contiene CE sin confirmar.')
        title=unit.get('title','')
        if not isinstance(title,str) or len(title)>220:raise ValueError('Título de unidad incorrecto.')
        request.append({'code':code,'title':title,'CE':[{'code':x,'description':valid_codes[x]['description'][:280]} for x in codes]})
    prompt={'tarea':'Propón instrumentos de evaluación y recursos específicos para cada unidad de FP. Devuelve exclusivamente JSON {"units":[{"code":"...","instruments":"...","resources":"..."}]}.',
      'ciclo':module['cycle'],'modulo':module['name'],'unidades':request,
      'restricciones':['No crees, elimines ni renombres códigos de unidad o de CE.',
        'No inventes dotaciones, licencias, instalaciones, visitas autorizadas o normativa oficial.',
        'Escribe 2–4 instrumentos/evidencias plausibles vinculados a los CE, y 2–4 recursos adaptables.',
        'No incluyas información personal de alumnado ni profesorado.',
        'No cambies horas, fechas, RA, CE ni ponderaciones.']}
    data,model=ia.chat('generation',json.dumps(prompt,ensure_ascii=False),limit=17000)
    if not isinstance(data,dict) or not isinstance(data.get('units'),list):
        raise ValueError('La IA no ha devuelto propuestas de unidades válidas.')
    out={}
    for item in data['units']:
        if not isinstance(item,dict):raise ValueError('Estructura de propuesta incorrecta.')
        code=item.get('code')
        if code not in seen or code in out:raise ValueError('La IA ha cambiado o duplicado el código de una unidad.')
        values={}
        for field in ('instruments','resources'):
            value=item.get(field)
            if not isinstance(value,str) or not 25<=len(value.strip())<=3000:
                raise ValueError('La IA ha devuelto una propuesta de unidades incompleta o excesiva.')
            values[field]=value.strip()
        out[code]=values
    if set(out)!=seen:raise ValueError('La IA ha omitido alguna unidad: no se ha aplicado ninguna propuesta.')
    return {'units':[{'code':u['code'],**out[u['code']]} for u in request],
            'source':'IA ('+model+')','requires_acceptance':True}
