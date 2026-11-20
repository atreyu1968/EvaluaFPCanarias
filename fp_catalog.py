"""Catálogo incremental de títulos y módulos (Grados D/E), por comunidad y curso.

Cada entrada es una ficha revisada por el docente y vinculada a una fuente.
No representa una descarga exhaustiva ni un certificado de vigencia del Ministerio.
No importa RA/CE, notas ni horas sin la validación específica de esos datos.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import re

import national_registry
import territorial_profiles as territories

MAX_TABLE_CHARS = 120_000
MAX_ROWS = 500
FIELDS = ('title_code','cycle','grade','family','module_code','module')
HEADER_ALIASES = {
 'title_code': ('codigo titulo','codigo del titulo','codigo ciclo','codigo de ciclo','codigo del ciclo','cod titulo'),
 'cycle': ('ciclo','ciclo formativo','titulo','nombre del ciclo','denominacion ciclo','denominacion del titulo'),
 'grade': ('grado','nivel','grado de fp','grado fp'),
 'family': ('familia','familia profesional'),
 'module_code': ('codigo modulo','codigo del modulo','cod modulo','cod modulo profesional'),
 'module': ('modulo','modulo profesional','nombre modulo','denominacion modulo'),
}
GRADE_ALIASES = {
 'basico':'Básico', 'grado basico':'Básico', 'grado d basico':'Básico',
 'medio':'Medio', 'grado medio':'Medio', 'grado d medio':'Medio',
 'superior':'Superior', 'grado superior':'Superior', 'grado d superior':'Superior',
 'especializacion':'Especialización', 'curso de especializacion':'Especialización', 'grado e':'Especialización',
}
CODE_PATTERN = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{1,27}\Z')


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS fp_catalog_entries(
        id INTEGER PRIMARY KEY,
        territory_code TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        title_code TEXT NOT NULL,
        title_name TEXT NOT NULL,
        grade TEXT NOT NULL,
        family TEXT NOT NULL,
        module_code TEXT NOT NULL,
        module_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT NOT NULL,
        table_sha256 TEXT NOT NULL,
        reviewed_at TEXT NOT NULL,
        reviewed_by_teacher INTEGER NOT NULL DEFAULT 1,
        UNIQUE(territory_code,academic_year,title_code,module_code)
    )''')
    db.execute('''CREATE INDEX IF NOT EXISTS ix_fp_catalog_scope
        ON fp_catalog_entries(territory_code,academic_year,title_name,module_name)''')
    db.execute('''CREATE TABLE IF NOT EXISTS fp_catalog_revisions(
        id INTEGER PRIMARY KEY,
        entry_id INTEGER NOT NULL REFERENCES fp_catalog_entries(id) ON DELETE CASCADE,
        previous_json TEXT NOT NULL,
        revised_at TEXT NOT NULL
    )''')


def _field(value, label, maxlen):
    if not isinstance(value, str) or not value.strip() or len(value)>maxlen or '\x00' in value:
        raise ValueError(f'{label}: falta el dato o supera {maxlen} caracteres.')
    return value.strip()


def _column_positions(header):
    def norm(s):
        return re.sub(r'[^a-z0-9]+',' ',territories.fold(s)).strip()
    positions={}
    for field,aliases in HEADER_ALIASES.items():
        options={norm(v) for v in aliases}
        found=[i for i,label in enumerate(header) if norm(label) in options]
        if len(found)!=1:
            raise ValueError('Falta o se repite la columna «'+field+'». Use: Código título;Ciclo;Grado;Familia;Código módulo;Módulo.')
        positions[field]=found[0]
    if len(set(positions.values()))!=len(FIELDS):
        raise ValueError('Las columnas del catálogo deben ser distintas.')
    return positions


def preview_table(raw):
    """No produce cambios; valida TODO el lote, incluidas colisiones."""
    if not isinstance(raw,str) or not 30<=len(raw)<=MAX_TABLE_CHARS or '\x00' in raw:
        raise ValueError('Pegue entre 30 y 120.000 caracteres de la tabla oficial.')
    first=raw.lstrip('\ufeff').splitlines()[0]
    try:
        delimiter=csv.Sniffer().sniff(raw[:4000],delimiters=';\t,').delimiter
    except csv.Error:
        delimiter='\t' if '\t' in first else ';'
    reader=csv.reader(io.StringIO(raw.lstrip('\ufeff')),delimiter=delimiter,strict=True)
    try:
        header=next(reader)
        positions=_column_positions(header)
        seen={};codes_by_title={}; titles={}; rows=[]
        for line_number,cells in enumerate(reader,2):
            if not any(x.strip() for x in cells):continue
            if len(rows)>=MAX_ROWS:raise ValueError('El catálogo admite 500 filas por importación.')
            if max(positions.values())>=len(cells):
                raise ValueError(f'Fila {line_number}: faltan columnas de la tabla.')
            values={key:cells[positions[key]] for key in FIELDS}
            cycle_code=_field(values['title_code'],f'Fila {line_number}, código del título',28)
            module_code=_field(values['module_code'],f'Fila {line_number}, código del módulo',28)
            if not CODE_PATTERN.fullmatch(cycle_code) or not CODE_PATTERN.fullmatch(module_code):
                raise ValueError(f'Fila {line_number}: código de ciclo o módulo inválido.')
            cycle=_field(values['cycle'],f'Fila {line_number}, ciclo',180)
            module=_field(values['module'],f'Fila {line_number}, módulo',180)
            family=_field(values['family'],f'Fila {line_number}, familia profesional',140)
            grade=GRADE_ALIASES.get(territories.fold(values['grade']))
            if grade is None:raise ValueError(f'Fila {line_number}: grado desconocido (Básico, Medio, Superior o Especialización).')
            key=(cycle_code.casefold(),module_code.casefold())
            if key in seen:raise ValueError(f'Fila {line_number}: código del módulo duplicado en el ciclo.')
            seen[key]=line_number
            ident=(cycle_code.casefold())
            title_meta=(territories.fold(cycle),grade,territories.fold(family))
            if ident in titles and titles[ident]!=title_meta:
                raise ValueError(f'Fila {line_number}: un mismo código de título tiene diferentes nombres, grados o familias.')
            titles[ident]=title_meta
            previous=codes_by_title.get(key)
            if previous and previous != territories.fold(module):
                raise ValueError(f'Fila {line_number}: código duplicado con diferente nombre de módulo.')
            codes_by_title[key]=territories.fold(module)
            rows.append({'title_code':cycle_code,'cycle':cycle,'grade':grade,'family':family,
                         'module_code':module_code,'module':module})
    except (csv.Error,UnicodeError) as exc:
        raise ValueError('CSV o tabla incorrecta; revise sus separadores y comillas.') from exc
    if not rows:raise ValueError('La tabla no contiene módulos identificables.')
    return {'rows':rows,'count':len(rows),'titles':len(titles),
            'notice':'Vista previa local: los códigos y nombres no han sido contrastados automáticamente con las disposiciones. Revise su fuente y vigencia antes de guardarlos.'}


def _scope(region,year):
    name=territories.require_territory(region)
    return name, territories.territory_code(name), territories.year_code(year)


def _entry_values(territory_code, year, row, source_url, source_title, digest, timestamp):
    return (territory_code,year,row['title_code'],row['cycle'],row['grade'],row['family'],
            row['module_code'],row['module'],source_url,source_title,digest,timestamp)


def import_table(db, raw, region, year, source_url, source_title,
                 *, teacher_confirmed=False, replace_existing=False):
    if teacher_confirmed is not True:
        raise ValueError('Antes de importar, confirme el territorio, curso, códigos y disposición oficial consultada.')
    name,code,year=_scope(region,year)
    url=national_registry.valid_url(source_url)
    title=national_registry.text_value(source_title,'el título y versión de la disposición',700)
    preview=preview_table(raw)
    sha=sha256(raw.encode('utf-8')).hexdigest()
    timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    updates=[];new=[];unchanged=0
    # Preparación de todo el lote ANTES de la primera escritura: no se permiten
    # importaciones parciales si aparece una fuente contradictoria.
    for row in preview['rows']:
        previous=db.execute('''SELECT * FROM fp_catalog_entries WHERE territory_code=?
          AND academic_year=? AND title_code=? COLLATE NOCASE AND module_code=? COLLATE NOCASE''',
          (code,year,row['title_code'],row['module_code'])).fetchone()
        if previous is None:
            new.append(row);continue
        old=dict(previous)
        same=(old['title_name']==row['cycle'] and old['grade']==row['grade'] and
              old['family']==row['family'] and old['module_name']==row['module'] and
              old['source_url']==url and old['source_title']==title)
        if same:
            unchanged+=1;continue
        if not replace_existing:
            raise ValueError('Existen fichas diferentes para '+row['title_code']+'/'+row['module_code']+
                             '. Revise el historial y confirme expresamente la actualización; no se ha importado ningún dato.')
        updates.append((old,row))
    for row in new:
        db.execute('''INSERT INTO fp_catalog_entries(territory_code,academic_year,title_code,
          title_name,grade,family,module_code,module_name,source_url,source_title,table_sha256,reviewed_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
          _entry_values(code,year,row,url,title,sha,timestamp))
    for old,row in updates:
        import json
        db.execute('''INSERT INTO fp_catalog_revisions(entry_id,previous_json,revised_at)
          VALUES(?,?,?)''',(old['id'],json.dumps(old,ensure_ascii=False),timestamp))
        db.execute('''UPDATE fp_catalog_entries SET title_name=?,grade=?,family=?,module_name=?,
          source_url=?,source_title=?,table_sha256=?,reviewed_at=? WHERE id=?''',
          (row['cycle'],row['grade'],row['family'],row['module'],url,title,sha,timestamp,old['id']))
    import database
    database.log(db,'catalog_fp_teacher_import','catalog',None,
        {'territory':code,'year':year,'added':len(new),'updated':len(updates),'unchanged':unchanged,'source_sha256':sha})
    return {'territory':name,'academic_year':year,'titles':preview['titles'],
            'added':len(new),'updated':len(updates),'unchanged':unchanged,
            'status':'fichas_confirmadas_por_docente_no_verificacion_automatizada',
            'notice':'Las fichas son reutilizables solo en el territorio y curso indicados. La importación no altera evaluaciones, RA/CE, notas ni horas.'}


def search(db, region, year, query='', limit=100):
    name,code,year=_scope(region,year)
    if not isinstance(query,str) or len(query)>100:raise ValueError('Búsqueda demasiado larga.')
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('El número de resultados debe estar entre 1 y 100.')
    rows=db.execute('''SELECT id,territory_code,academic_year,title_code,title_name,grade,
      family,module_code,module_name,source_url,source_title,reviewed_at
      FROM fp_catalog_entries WHERE territory_code=? AND academic_year=?
      ORDER BY title_name COLLATE NOCASE,module_name COLLATE NOCASE''',(code,year)).fetchall()
    needle=territories.fold(query)
    found=[]
    for entry in rows:
        item=dict(entry)
        haystack=territories.fold(' '.join(str(item[k]) for k in ('title_code','title_name','grade','family','module_code','module_name')))
        if needle and needle not in haystack:continue
        found.append(item)
    return {'territory':name,'academic_year':year,'count':len(found),'entries':found[:limit],
            'truncated':len(found)>limit,
            'catalog_source':'biblioteca_local_confirmada_por_docente',
            'notice':('Resultados de fichas revisadas por el docente. No equivalen a un catálogo nacional completo ni '
                      'garantizan vigencia, implantación en el centro ni distribución horaria autonómica.')}


def get_entry(db, entry_id, region, year):
    _,code,year=_scope(region,year)
    try:ident=int(entry_id)
    except (TypeError,ValueError):raise ValueError('Identificador de catálogo inválido.') from None
    row=db.execute('''SELECT * FROM fp_catalog_entries WHERE id=? AND territory_code=? AND academic_year=?''',
                   (ident,code,year)).fetchone()
    if row is None:
        raise ValueError('La ficha del catálogo no pertenece al territorio y curso seleccionados.')
    return dict(row)
