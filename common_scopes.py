"""Borradores competenciales de los ámbitos comunes de CFGB Canarias.

No son RA profesionales, no generan notas oficiales por materia y no modifican
las tablas outcomes/criteria ni las ponderaciones de módulos existentes.
"""
import json
import re
import unicodedata
import database as data

SOURCE_URL = 'https://www.gobiernodecanarias.org/boc/2023/025/001.html'
ANNEX_URL = 'https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/formacion_profesional/_galerias/descargas/cfgb/1_ambitos_comunes.pdf'
SOURCE_ID = 'BOC-A-2023-025-402'
SOURCE_TITLE = 'Decreto 9/2023, de 26 de enero, anexo 1'
CYCLE = 'cfgb servicios administrativos'
COMM = 'Comunicación y Ciencias Sociales'
SCI = 'Ciencias Aplicadas'
MATTERS = {
    'lengua castellana y ciencias sociales': (COMM, 8),
    'lengua extranjera de iniciacion profesional': (COMM, 8),
    'matematicas y ciencias aplicadas': (SCI, 11),
    'actividad fisica y bienestar emocional': (SCI, 11),
}


def key(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(value or '').casefold())
                            if not unicodedata.combining(c)).split())


def profile(name, cycle, territory):
    if key(cycle)!=CYCLE or key(territory)!='canarias':
        return None
    item=MATTERS.get(key(name))
    if not item:
        return None
    return {'ambito':item[0],'max_competencies':item[1],
            'source_id':SOURCE_ID,'source_title':SOURCE_TITLE,
            'source_url':SOURCE_URL,'annex_url':ANNEX_URL,
            'scope':'materia_borrador_no_calificacion_oficial'}


def module_profile(db, module_id):
    row=db.execute('SELECT name,cycle,territory FROM modules WHERE id=?',(module_id,)).fetchone()
    if not row:
        raise ValueError('El módulo seleccionado no existe.')
    return profile(row['name'],row['cycle'],row['territory'])


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS common_scope_drafts (
        module_id INTEGER PRIMARY KEY REFERENCES modules(id) ON DELETE CASCADE,
        content_json TEXT NOT NULL, updated_at TEXT NOT NULL)""")


def clean_text(value, limit=12000):
    if not isinstance(value,str) or len(value)>limit or '\x00' in value:
        raise ValueError('Texto curricular no válido o demasiado largo.')
    return value.strip()


def items(value, maximum):
    if not isinstance(value,list) or len(value)>maximum or any(not isinstance(x,dict) for x in value):
        raise ValueError('Listado curricular incorrecto.')
    return value


def normalise(raw, meta):
    if not isinstance(raw,dict):
        raise ValueError('Borrador competencial no válido.')
    if set(raw)-{'competencies','saberes','teacher_reviewed'}:
        raise ValueError('El borrador contiene campos desconocidos.')
    seen=set()
    competencies=[]
    for entry in items(raw.get('competencies',[]),meta['max_competencies']):
        code=clean_text(entry.get('code',''),10)
        if not re.fullmatch(r'[1-9][0-9]?',code) or int(code)>meta['max_competencies'] or code in seen:
            raise ValueError('Número de competencia específica inválido o repetido.')
        seen.add(code)
        description=clean_text(entry.get('description',''))
        if not description:
            raise ValueError('Indique el enunciado de cada competencia incorporada.')
        criteria=[]
        criterion_codes=set()
        for ce in items(entry.get('criteria',[]),100):
            number=clean_text(ce.get('code',''),20)
            if not re.fullmatch(re.escape(code)+r'\.[1-9][0-9]*',number) or number in criterion_codes:
                raise ValueError('El criterio debe pertenecer a su competencia y no repetirse.')
            criterion_codes.add(number)
            desc=clean_text(ce.get('description',''))
            if not desc:
                raise ValueError('Indique el enunciado del criterio '+number+'.')
            criteria.append({'code':number,'description':desc,
                             'descriptors':clean_text(ce.get('descriptors',''),500)})
        if not criteria:
            raise ValueError('Cada competencia incorporada debe tener al menos un criterio.')
        competencies.append({'code':code,'description':description,
                             'descriptors':clean_text(entry.get('descriptors',''),500),
                             'criteria':criteria})
    reviewed=raw.get('teacher_reviewed',False)
    if type(reviewed) is not bool or (reviewed and not competencies):
        raise ValueError('La revisión requiere competencias y criterios.')
    return {'competencies':competencies,'saberes':clean_text(raw.get('saberes',''),80000),
            'teacher_reviewed':reviewed}


def load(db,module_id):
    meta=module_profile(db,module_id)
    if not meta:
        raise ValueError('La materia no pertenece a los ámbitos comunes registrados de Canarias.')
    migrate(db)
    stored=db.execute('SELECT content_json,updated_at FROM common_scope_drafts WHERE module_id=?',
                      (module_id,)).fetchone()
    draft=json.loads(stored['content_json']) if stored else normalise({},meta)
    return {'profile':meta,'draft':draft,'updated_at':stored['updated_at'] if stored else None}


def save(db,module_id,raw):
    meta=module_profile(db,module_id)
    if not meta:
        raise ValueError('La materia no pertenece a los ámbitos comunes registrados de Canarias.')
    clean=normalise(raw,meta)
    migrate(db)
    db.execute("""INSERT INTO common_scope_drafts(module_id,content_json,updated_at)
        VALUES(?,?,?) ON CONFLICT(module_id) DO UPDATE SET
        content_json=excluded.content_json,updated_at=excluded.updated_at""",
        (module_id,json.dumps(clean,ensure_ascii=False),data.now()))
    data.log(db,'common_scope_draft_saved','module',module_id,
             {'source_id':SOURCE_ID,'ambito':meta['ambito'],
              'competencies':len(clean['competencies']),
              'criteria':sum(len(x['criteria']) for x in clean['competencies']),
              'teacher_reviewed':clean['teacher_reviewed']})
    return load(db,module_id)
