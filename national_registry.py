"""Biblioteca local versionada de fuentes educativas para los 19 ámbitos de España.

No presenta como 'verificado por EvalúaFP' un dato introducido por un docente.
Los registros solo se reutilizan en el MISMO curso, territorio, ciclo y módulo;
los calendarios de centro tampoco se trasladan a otro centro.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import database
import territorial_profiles as territories
import official_catalog
import schedule_engine

# Enlaces de entrada seleccionados desde el directorio del Ministerio TodoFP.
# Son PORTALES, no una certificación de horas ni calendarios para un ciclo concreto.
PORTALS = {
    'AN':'https://www.juntadeandalucia.es/educacion/portales/web/formacion-profesional-andaluza',
    'AR':'https://educa.aragon.es/formaci%C3%B3n-profesional',
    'AS':'https://www.educastur.es/estudiantes/formacion-profesional',
    'IB':'https://www.caib.es/sites/fp/ca/inici/',
    'CN':'https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/',
    'CB':'https://www.educantabria.es/fp',
    'CM':'https://www.educa.jccm.es/',
    'CL':'https://www.educa.jcyl.es/fp/es',
    'CT':'https://triaeducativa.gencat.cat/ca/fp/index.html',
    'VC':'https://ceice.gva.es/es/web/formacion-profesional',
    'EX':'https://www.educarex.es/fp/inicio.html',
    'GA':'https://www.edu.xunta.gal/fp/',
    'MD':'https://www.comunidad.madrid/servicios/educacion/formacion-profesional',
    'MC':'https://www.educarm.es/',
    'NC':'https://www.educacion.navarra.es/web/dpto/formacion-profesional',
    'PV':'https://www.euskadi.eus/gobierno-vasco/fp-educacion/',
    'RI':'https://fp.larioja.org/',
    'CE':'https://www.educacionfpydeportes.gob.es/',
    'ML':'https://www.educacionfpydeportes.gob.es/',
}
MINISTRY_INDEX = 'https://www.todofp.es/sobre-fp/webs-fp-ccaa.html'
NATIONAL_CATALOG = 'https://todofp.es/catalogos-registros-sistema-fp.html'
NATIONAL_TITLES = 'https://www.todofp.es/que-estudiar/material-descargable.html'
CYCLE_DIRECTORY = {
    'gestion administrativa': 'https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/gestion-administrativa/curriculos-ccaa.html',
    'administracion y finanzas': 'https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas/curriculos-ccaa.html',
}
BOE_API = 'https://www.boe.es/datosabiertos/api/api.php?lang=es'


def source_directory(territory, cycle, year):
    label = territories.require_territory(territory)
    code = territories.territory_code(label)
    year = territories.year_code(year)
    normalized = territories.fold(cycle)
    links = [
        {'label':f'Portal oficial de FP — {label}', 'url':PORTALS[code], 'kind':'portal'},
        {'label':'Directorio del Ministerio de las webs autonómicas de FP', 'url':MINISTRY_INDEX, 'kind':'directorio'},
        {'label':'Catálogo Nacional de Ofertas y Catálogo Modular de FP (TodoFP)', 'url':NATIONAL_CATALOG, 'kind':'catalogos'},
        {'label':'Catálogos descargables de títulos y ciclos (TodoFP)', 'url':NATIONAL_TITLES, 'kind':'titulos'},
        {'label':'BOE — datos abiertos y legislación consolidada', 'url':BOE_API, 'kind':'legislacion'},
    ]
    for key, url in CYCLE_DIRECTORY.items():
        if key in normalized:
            links.insert(0, {'label':'Currículos autonómicos de '+cycle+' (TodoFP)', 'url':url,'kind':'curriculos-ccaa'})
            break
    return {'territory':label,'territory_code':code,'academic_year':year,'links':links,
            'notice':'Estos son accesos a fuentes oficiales, no datos horarios comprobados. Abra la disposición vigente del curso y módulo antes de confirmar una cifra.'}


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS national_hour_records(
        territory_code TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        cycle_key TEXT NOT NULL,
        module_key TEXT NOT NULL,
        cycle_name TEXT NOT NULL,
        module_name TEXT NOT NULL,
        module_code TEXT NOT NULL DEFAULT '',
        total_hours REAL NOT NULL,
        weekly_hours REAL NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        checked_at TEXT NOT NULL,
        teacher_confirmed INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY(territory_code,academic_year,cycle_key,module_key))''')
    db.execute('''CREATE TABLE IF NOT EXISTS national_center_calendars(
        territory_code TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        center_key TEXT NOT NULL,
        center_name TEXT NOT NULL,
        configuration_json TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        checked_at TEXT NOT NULL,
        teacher_confirmed INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY(territory_code,academic_year,center_key))''')
    import calendar_versions
    calendar_versions.migrate(db)


def valid_url(raw):
    if not isinstance(raw, str) or len(raw) > 800:
        raise ValueError('La URL de la fuente no es válida.')
    url = raw.strip()
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or '\\' in url or any(ord(c) < 32 for c in url):
        raise ValueError('Introduzca una URL HTTPS pública que identifique la disposición consultada.')
    if parts.hostname in ('localhost','127.0.0.1','::1') or parts.hostname.endswith('.local'):
        raise ValueError('La fuente debe ser una disposición pública, no una dirección local.')
    return url


def text_value(value, name, maxlen=200):
    if not isinstance(value,str) or not value.strip() or len(value)>maxlen or '\x00' in value:
        raise ValueError(f'Complete {name} (máximo {maxlen} caracteres).')
    return value.strip()


def number(value, name, upper):
    try:
        number = Decimal(str(value).replace(',', '.'))
    except (ValueError,InvalidOperation):
        raise ValueError(f'{name}: indique una cantidad positiva.') from None
    if not number.is_finite() or number<=0 or number>upper or number.as_tuple().exponent<-2:
        raise ValueError(f'{name}: valor fuera de rango o con más de dos decimales.')
    return float(number)


def scope(db, module_id):
    row = db.execute('SELECT id,cycle,name,academic_year,territory FROM modules WHERE id=?',(module_id,)).fetchone()
    if not row:raise ValueError('Módulo no encontrado.')
    from program_builder import load
    draft = load(db,module_id)['draft']
    region = territories.require_territory(draft.get('region') or row['territory'])
    return dict(row),draft,territories.territory_code(region)


def hour_key(module,draft,code):
    return (territories.fold(module['cycle']),
            'code:'+code if code else 'name:'+territories.fold(module['name']))


def find_hours_for(db, module, draft, code):
    """Consulta interna sin volver a cargar el borrador (evita recursión)."""
    module_code = str(draft.get('official_module_code') or '').strip()
    keys = [('code:'+module_code)] if module_code else []
    keys += ['name:'+territories.fold(module['name'])]
    for key in keys:
        row=db.execute('''SELECT * FROM national_hour_records
            WHERE territory_code=? AND academic_year=? AND cycle_key=? AND module_key=?''',
            (code,module['academic_year'],territories.fold(module['cycle']),key)).fetchone()
        if row:
            result=dict(row)
            return {'code':result['module_code'],'title':result['module_name'],'cycle':result['cycle_name'],
                    'total_hours':result['total_hours'],'weekly_hours':result['weekly_hours'],
                    'source_url':result['source_url'],'source_date':result['checked_at'],
                    'source_title':result['source_title'],'status':'confirmado_por_docente_en_biblioteca_local',
                    'source':'biblioteca_local','require_confirmation':True,
                    'notice':'Fuente confirmada por un docente en esta instalación. Compruebe cambios normativos posteriores antes de aplicarla.'}
    return None


def find_hours(db, module_id):
    module,draft,code = scope(db,module_id)
    return find_hours_for(db,module,draft,code)


def save_hours(db, module_id, payload):
    if not isinstance(payload,dict) or payload.get('teacher_confirmed') is not True:
        raise ValueError('Confirme que ha comprobado la fuente horaria antes de guardar en la biblioteca.')
    module,draft,code=scope(db,module_id)
    mod_code = str(draft.get('official_module_code') or '').strip()
    if mod_code and (len(mod_code)>25 or not re.fullmatch(r'[\w./-]+',mod_code)):
        raise ValueError('Revise el código oficial del módulo.')
    cycle_key, mod_key=hour_key(module,draft,mod_code)
    total=number(payload.get('total_hours'),'Horas totales',2500)
    weekly=number(payload.get('weekly_hours'),'Horas semanales',40)
    source=valid_url(payload.get('source_url',''))
    title=text_value(payload.get('source_title',''),'el título y versión de la disposición')
    db.execute('''INSERT INTO national_hour_records
        (territory_code,academic_year,cycle_key,module_key,cycle_name,module_name,module_code,total_hours,weekly_hours,source_url,source_title,checked_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(territory_code,academic_year,cycle_key,module_key) DO UPDATE SET
        cycle_name=excluded.cycle_name,module_name=excluded.module_name,module_code=excluded.module_code,
        total_hours=excluded.total_hours,weekly_hours=excluded.weekly_hours,
        source_url=excluded.source_url,source_title=excluded.source_title,checked_at=excluded.checked_at''',
        (code,module['academic_year'],cycle_key,mod_key,module['cycle'],module['name'],mod_code,total,weekly,source,title,database.now()))
    database.log(db,'local_hour_reference_confirmed','module',module_id,
                 {'region':code,'academic_year':module['academic_year'],'weekly_hours':weekly,'total_hours':total})
    return find_hours(db,module_id)


def find_calendar(db,module_id):
    module,draft,code=scope(db,module_id)
    center=str(draft.get('center') or '').strip()
    if not center:return None
    # Preferir la versión del centro y MUNICIPIO/ISLA exactos. Una tabla
    # heredada solo por nombre de centro no debe mezclar localidades.
    import calendar_versions
    history=calendar_versions.list_versions(db,module_id)
    if history['versions']:
        latest=history['versions'][0]
        return {'territory_code':code,'academic_year':module['academic_year'],
            'center':center, 'schedule':{**latest['schedule'],'calendar_confirmed':False},
            'source_url':latest['source_url'],'source_title':latest['source_title'],
            'checked_at':latest['reviewed_at'],'status':'revisado_por_docente_en_historial_local',
            'notice':'Calendario archivado para este centro, municipio, isla y curso. Revise las disposiciones recientes antes de volver a confirmarlo.'}
    row=db.execute('''SELECT * FROM national_center_calendars WHERE territory_code=?
      AND academic_year=? AND center_key=?''',
        (code,module['academic_year'],territories.fold(center))).fetchone()
    if not row:return None
    result=dict(row)
    stored=json.loads(result['configuration_json'])
    current=draft['schedule']
    if territories.fold(stored.get('municipality','')) != territories.fold(current.get('municipality','')):
        return None
    if territories.fold(stored.get('island','')) != territories.fold(current.get('island','')):
        return None
    return {'territory_code':code,'academic_year':module['academic_year'],'center':center,
            'schedule':stored,
            'source_url':result['source_url'],'source_title':result['source_title'],
            'checked_at':result['checked_at'],'status':'confirmado_por_docente_en_biblioteca_local',
            'notice':'Calendario conservado para el mismo centro y curso. Revise actualizaciones y festivos locales antes de aplicarlo a otro grupo.'}


def save_calendar(db,module_id,payload):
    if not isinstance(payload,dict) or payload.get('teacher_confirmed') is not True:
        raise ValueError('Confirme que ha revisado el calendario del centro.')
    module,draft,code=scope(db,module_id)
    center=text_value(draft.get('center',''),'el nombre del centro',220)
    # El calendario se toma del borrador guardado: nunca de campos sueltos que puedan
    # corresponder a otro territorio. No guarda horarios ni FEOE de un módulo concreto.
    cfg=schedule_engine.clean(draft['schedule'],module['academic_year'])
    if not cfg['start_date'] or not cfg['end_date'] or not cfg['calendar_confirmed']:
        raise ValueError('Guarde y confirme primero las fechas y festivos del calendario.')
    if territories.territory_code(cfg['region'])!=code or cfg['calendar_academic_year']!=module['academic_year']:
        raise ValueError('El calendario no corresponde al territorio o curso de este módulo.')
    source=valid_url(cfg['calendar_source_url'])
    title=text_value(cfg['calendar_source_description'],'la disposición del calendario',700)
    fields=['region','island','municipality','start_date','end_date','evaluation_ends',
            'vacation_periods','regional_non_teaching_days','extra_non_teaching_days',
            'calendar_profile_id','calendar_academic_year','calendar_source_url',
            'calendar_source_description','calendar_correction_urls','calendar_confirmed']
    calendar={key:cfg[key] for key in fields}
    db.execute('''INSERT INTO national_center_calendars
        (territory_code,academic_year,center_key,center_name,configuration_json,source_url,source_title,checked_at)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(territory_code,academic_year,center_key) DO UPDATE SET
        center_name=excluded.center_name,configuration_json=excluded.configuration_json,
        source_url=excluded.source_url,source_title=excluded.source_title,checked_at=excluded.checked_at''',
        (code,module['academic_year'],territories.fold(center),center,
         json.dumps(calendar,ensure_ascii=False),source,title,database.now()))
    import calendar_versions
    version=calendar_versions.record_from_draft(db,module_id,cfg)
    database.log(db,'local_center_calendar_confirmed','module',module_id,
                 {'territory':code,'academic_year':module['academic_year'],'center':center})
    return {**find_calendar(db,module_id),'revision':version}


def propose_module_sources(db,module_id):
    module,draft,code=scope(db,module_id)
    return {'sources':source_directory(draft['region'],module['cycle'],module['academic_year']),
            'hours_record':find_hours(db,module_id),
            'calendar_record':find_calendar(db,module_id),
            'static_reference':official_catalog.find(draft['region'],module['cycle'],module['name'],draft.get('official_module_code',''))}


def extract_hours_with_ai(db, module_id, fragment, authorize_ai=False):
    """Interpreta un extracto que el usuario ha copiado de su norma.

    No consulta webs por iniciativa propia, no modifica SQLite ni considera la
    respuesta de la IA prueba de vigencia. Exige una cita literal comprobable.
    """
    import ia
    if authorize_ai is not True:
        raise ValueError('Autorice expresamente el envío del extracto oficial al proveedor de IA.')
    if not isinstance(fragment,str) or not 60<=len(fragment.strip())<=14000:
        raise ValueError('Copie un extracto de entre 60 y 14.000 caracteres con la fila de su módulo.')
    module,draft,code=scope(db,module_id)
    if not ia.key_available():
        raise ValueError('Configure y desbloquee una API de IA en Ajustes antes de analizar el extracto.')
    data={'tarea':'Extraer de un documento legal aportado una fila de carga horaria. Devuelve JSON estricto.',
          'formato':{'module_name':'texto del módulo','module_code':'código visible o cadena vacía',
                     'total_hours':'número o null','weekly_hours':'número o null',
                     'literal_quote':'cita textual copiada EXACTAMENTE del fragmento'},
          'reglas':['NO infieras la carga horaria desde el RD estatal: puede haber diferencias autonómicas.',
                    'Si no hay horas semanales explícitas, devuelve null. No calcules horas semanales a partir de las anuales.',
                    'Si el extracto es ambiguo o no contiene la fila del módulo correcto, devuelve null en las horas.',
                    'La cita literal debe contener el código o nombre del módulo Y los números de ambas horas.'],
          'territorio':draft['region'],'curso':module['academic_year'],'ciclo':module['cycle'],
          'nombre_modulo':module['name'],'codigo_modulo':draft.get('official_module_code',''),
          'extracto_literal_del_docente':fragment}
    result,model=ia.chat('generation',json.dumps(data,ensure_ascii=False),limit=21000)
    if not isinstance(result,dict):
        raise ValueError('La IA no devolvió un objeto con los datos horarios.')
    quote=result.get('literal_quote','')
    if not isinstance(quote,str) or not 20<=len(quote)<=1000:
        raise ValueError('Falta una cita textual verificable. No se han propuesto horas.')
    normalize=lambda s: re.sub(r'\s+',' ',s).strip().casefold()
    if normalize(quote) not in normalize(fragment):
        raise ValueError('La IA ha incluido una cita que no figura literalmente en la fuente: propuesta descartada.')
    module_code=str(draft.get('official_module_code','')).strip()
    if module_code:
        if result.get('module_code')!=module_code or module_code not in quote:
            raise ValueError('El código de la fila no coincide con el módulo confirmado. Propuesta descartada.')
    elif territories.fold(module['name']) not in territories.fold(quote):
        raise ValueError('La cita no identifica el módulo por su nombre. Introduzca el código o amplíe el extracto.')
    total=number(result.get('total_hours'),'Horas totales',2500)
    weekly=number(result.get('weekly_hours'),'Horas semanales',40)
    # Los valores deben aparecer como cifras en la misma cita, no solo en la respuesta.
    for val,label in ((total,'totales'),(weekly,'semanales')):
        token=('%g' % val).replace('.',r'[.,]')
        # Número aislado: evita interpretar 202 como 2027.
        if not re.search(r'(?<!\d)'+token+r'(?!\d)',quote):
            raise ValueError('No se puede encontrar el valor de horas '+label+' en la cita original.')
    return {'module_code':module_code or result.get('module_code',''),
            'module_name':module['name'],'total_hours':total,'weekly_hours':weekly,
            'literal_quote':quote,'model':model,'source':'IA sobre fragmento facilitado',
            'requires_teacher_confirmation':True,
            'notice':'La IA solo interpreta el texto aportado. Compruebe la disposición, año, modificación y validez antes de guardarlo.'}


def preview_hours_table(raw):
    """Lee filas copiadas de Calc/Excel o un CSV del anexo horario.

    No intenta deducir cifras mediante IA. Exige cabeceras inequívocas.
    """
    import csv
    import io
    if not isinstance(raw,str) or not 20<=len(raw)<=80000 or '\x00' in raw:
        raise ValueError('Pegue una tabla de hasta 80.000 caracteres.')
    sample=raw[:4000]
    try:
        delimiter=csv.Sniffer().sniff(sample,delimiters=';\t,').delimiter
    except csv.Error:
        delimiter='\t' if '\t' in raw.splitlines()[0] else ';'
    reader=csv.reader(io.StringIO(raw),delimiter=delimiter)
    header=next(reader,None)
    if not header or len(header)<4:
        raise ValueError('La tabla necesita cuatro columnas con encabezados claros.')
    def key(v):
        value=territories.fold(v)
        value=re.sub(r'[^\w ]+', ' ', value)
        return re.sub(r'\s+',' ',value).strip()
    aliases={
        'code':{'codigo','codigo modulo','cod modulo','codigo del modulo','codigo modulo profesional'},
        'name':{'modulo','modulo profesional','nombre modulo','nombre del modulo','denominacion modulo'},
        'total':{'horas totales','horas anuales','total horas','horas curso','horas del modulo','duracion horas'},
        'weekly':{'horas semanales','horas semana','horas por semana','h semanales','h semana'},
    }
    cols={}
    for semantic, options in aliases.items():
        matches=[i for i,text in enumerate(header) if key(text) in options]
        if len(matches)!=1:raise ValueError('No se identifica de forma inequívoca la columna '+semantic+'. Use encabezados Código; Módulo; Horas totales; Horas semanales.')
        cols[semantic]=matches[0]
    if len(set(cols.values()))!=4:
        raise ValueError('Las columnas de código, módulo y horas deben ser distintas.')
    rows=[];seen=set()
    for i,line in enumerate(reader,2):
        if not any(x.strip() for x in line):continue
        if len(rows)>=300:raise ValueError('La tabla admite un máximo de 300 módulos.')
        if max(cols.values())>=len(line):raise ValueError(f'Fila {i}: faltan columnas.')
        code=text_value(line[cols['code']],f'código en fila {i}',30)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{2,30}',code):
            raise ValueError(f'Fila {i}: el código del módulo contiene caracteres no válidos.')
        name=text_value(line[cols['name']],f'módulo en fila {i}',180)
        total=number(line[cols['total']],f'horas totales de fila {i}',2500)
        weekly=number(line[cols['weekly']],f'horas semanales de fila {i}',40)
        if code.casefold() in seen:raise ValueError(f'Código duplicado en la tabla: {code}.')
        seen.add(code.casefold())
        rows.append({'code':code,'name':name,'total_hours':total,'weekly_hours':weekly})
    if not rows:raise ValueError('No se han detectado módulos en la tabla.')
    return {'count':len(rows),'rows':rows,'notice':'Los datos se han leído como texto, no se ha verificado la vigencia de la disposición. Confirme la fuente y el ciclo antes de guardarlos.'}


def import_hours_table(db,module_id,raw,source_url,source_title,teacher_confirmed=False,replace_existing=False):
    if teacher_confirmed is not True:
        raise ValueError('Confirme la procedencia, el ciclo y el curso de todas las filas antes de importar.')
    info=preview_hours_table(raw)
    module,draft,code=scope(db,module_id)
    url=valid_url(source_url)
    title=text_value(source_title,'la disposición normativa',700)
    # Una tabla de otro ciclo no puede incorporarse a este ciclo por accidente:
    # debe contener al menos el módulo seleccionado, identificado por código
    # oficial o, si no consta ese código, por denominación normalizada exacta.
    # Esta comprobación se realiza ANTES de insertar cualquier fila.
    selected_code=str(draft.get('official_module_code') or '').strip()
    matched=(
        any(str(row['code']).casefold()==selected_code.casefold() for row in info['rows'])
        if selected_code else
        any(territories.fold(row['name'])==territories.fold(module['name']) for row in info['rows'])
    )
    if not matched:
        raise ValueError('La tabla no contiene el módulo seleccionado. Compruebe que el anexo pertenece al ciclo correcto; no se ha guardado ningún dato.')
    cycle_key=territories.fold(module['cycle'])
    imported=0;skipped=0
    for row in info['rows']:
        # Guardar ambas formas exactas de identificación evita depender de
        # que otro docente escriba el código cuando el nombre es inequívoco.
        for module_key in ('code:'+row['code'], 'name:'+territories.fold(row['name'])):
            existing=db.execute('''SELECT 1 FROM national_hour_records WHERE territory_code=? AND academic_year=?
                AND cycle_key=? AND module_key=?''',
                (code,module['academic_year'],cycle_key,module_key)).fetchone()
            if existing and not replace_existing:
                skipped+=1;continue
            db.execute('''INSERT INTO national_hour_records
                (territory_code,academic_year,cycle_key,module_key,cycle_name,module_name,
                 module_code,total_hours,weekly_hours,source_url,source_title,checked_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(territory_code,academic_year,cycle_key,module_key) DO UPDATE SET
                cycle_name=excluded.cycle_name,module_name=excluded.module_name,
                module_code=excluded.module_code,total_hours=excluded.total_hours,
                weekly_hours=excluded.weekly_hours,source_url=excluded.source_url,
                source_title=excluded.source_title,checked_at=excluded.checked_at''',
                (code,module['academic_year'],cycle_key,module_key,module['cycle'],row['name'],
                 row['code'],row['total_hours'],row['weekly_hours'],url,title,database.now()))
            imported+=1
    database.log(db,'local_hour_table_confirmed','module',module_id,
                 {'region':code,'academic_year':module['academic_year'],
                  'cycle':module['cycle'],'module_count':info['count'],
                  'rows_saved':imported,'rows_unchanged':skipped})
    return {'count':info['count'],'records_saved':imported,'records_unchanged':skipped,
            'notice':'Los registros se reutilizan únicamente en este ciclo, comunidad y curso. Revise las modificaciones del anexo en cursos posteriores.'}
