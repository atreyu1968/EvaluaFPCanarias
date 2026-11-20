"""Importador conservador de programaciones didácticas FP.

No genera ni valida leyes, resultados de aprendizaje ni ponderaciones.
Extrae el máximo texto con procedencia, recupera apartados y propone su
asignación a los campos editables; nada se guarda en la programación
normalizada sin confirmación docente. El original permanece intacto.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

MAX_SECTIONS = 120
MAX_IMPORT_TEXT = 300_000
MAX_FIELD_TEXT = 12_000

# Repertorio amplio: adaptado a ejemplos de FP canaria, no restringido a un título.
FIELD_NAMES = {
    'center': 'Centro educativo (identificado en portada)',
    'teacher': 'Profesorado (identificado en portada)',
    'academic_context': 'Contextualización del centro, alumnado y entorno',
    'competencies': 'Competencias relacionadas con el título',
    'instruments': 'Instrumentos de evaluación documentados',
    'justification': 'Justificación y principios de la programación',
    'normative_references': 'Marco normativo (pendiente de verificación)',
    'academic_context': 'Contextualización de la programación',
    'center_characteristics': 'Características del centro educativo',
    'student_characteristics': 'Características del alumnado',
    'environment_context': 'Entorno socioproductivo',
    'identification_data': 'Datos identificativos del módulo',
    'qualifications': 'Competencias y cualificaciones profesionales',
    'objectives': 'Objetivos generales y del módulo',
    'competencies': 'Competencias profesionales, personales y sociales',
    'contents': 'Contenidos y saberes',
    'learning_activities': 'Distribución de actividades y unidades de trabajo',
    'methodology': 'Metodología y principios metodológicos',
    'interdisciplinarity': 'Interdisciplinariedad y coordinación',
    'inclusion': 'Atención a la diversidad',
    'resources': 'Recursos y materiales',
    'extracurricular': 'Actividades complementarias, extraescolares y salidas',
    'assessment': 'Evaluación y procedimientos',
    'assessment_sessions': 'Sesiones de evaluación',
    'grading': 'Calificación y ponderaciones',
    'promotion': 'Promoción y acceso a segundo curso',
    'enterprise': 'Formación en empresa (FEOE)',
    'attendance': 'Asistencia y puntualidad',
    'recovery': 'Recuperación',
    'extraordinary_assessment': 'Pruebas extraordinarias',
}

# El orden importa: los encabezados concretos preceden a sus epígrafes generales.
HEADING_RULES = (
 ('resultados de aprendizaje y criterios de evaluacion compartidos', 'enterprise'),
 ('datos identificativos', 'identification_data'),
 ('punto de partida', 'academic_context'),
 ('justificacion', 'justification'),
 ('concrecion objetivos', 'objectives'),
 ('secuencia situaciones aprendizaje', 'learning_activities'),
 ('evaluacion y calificacion', 'assessment'),
 ('temporalizacion', 'learning_activities'),
 ('resultados de aprendizaje y criterios de evaluacion', 'curriculum_excerpt'),
 ('actividades formativas en la empresa', 'enterprise'),
 ('acceso a la formacion en empresa', 'enterprise'),
 ('formacion en empresa', 'enterprise'),
 ('distribucion de las actividades de aprendizaje', 'learning_activities'),
 ('temporalizacion de las unidades', 'learning_activities'),
 ('distribucion temporal', 'learning_activities'),
 ('actividades extraescolares y complementarias', 'extracurricular'),
 ('actividades complementarias y extraescolares', 'extracurricular'),
 ('actividades complementarias', 'extracurricular'),
 ('caracteristicas del alumnado', 'student_characteristics'),
 ('caracteristicas del centro', 'center_characteristics'),
 ('influencia del entorno', 'environment_context'),
 ('contextualizacion de la programacion', 'academic_context'),
 ('principios basicos de la programacion', 'justification'),
 ('justificacion teorica', 'justification'),
 ('marco normativo de la programacion', 'normative_references'),
 ('marco normativo', 'normative_references'),
 ('referencias normativas', 'normative_references'),
 ('objetivos del titulo y del modulo', 'objectives'),
 ('objetivos generales', 'objectives'),
 ('competencias y cualificaciones profesionales', 'qualifications'),
 ('competencias profesionales', 'competencies'),
 ('datos identificativos', 'identification_data'),
 ('principios de la metodologia', 'methodology'),
 ('estructura de la metodologia', 'methodology'),
 ('metodologia didactica', 'methodology'),
 ('metodologia', 'methodology'),
 ('interdisciplinariedad', 'interdisciplinarity'),
 ('atencion a la diversidad', 'inclusion'),
 ('recursos y materiales', 'resources'),
 ('recursos materiales', 'resources'),
 ('sesiones de evaluacion', 'assessment_sessions'),
 ('criterios de calificacion', 'grading'),
 ('calificacion', 'grading'),
 ('promocion de primero a segundo', 'promotion'),
 ('faltas de asistencia', 'attendance'),
 ('asistencia a clase', 'attendance'),
 ('actividades de recuperacion', 'recovery'),
 ('pruebas extraordinarias', 'extraordinary_assessment'),
 ('evaluacion', 'assessment'),
 ('contenidos', 'contents'),
)


def ascii_key(value: str) -> str:
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii','ignore').decode('ascii')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9 ]+', ' ', value)).strip().lower()


def known_heading(value):
    text=ascii_key(value)
    text=re.sub(r'^(?:\d{1,2}\s+){1,3}', '', text)
    if not 5 <= len(text) <= 120:
        return None
    words=text.split()
    letters=[c for c in value if c.isalpha()]
    caps=(sum(c.isupper() for c in letters)/len(letters)) if letters else 0
    for prefix,field in HEADING_RULES:
        matched=(text == prefix or (text.startswith(prefix+' ') and
                 len(text)-len(prefix)<(85 if caps>.8 else 36)))
        if not matched:continue
        # Evita tratar las palabras «Evaluación» de una tabla o las frases
        # «metodología de ...» dentro de los CE como títulos.
        if len(words)==1 and caps < .8:continue
        if text != prefix and caps < .70 and not (prefix in (
                'resultados de aprendizaje y criterios de evaluacion compartidos',
                'actividades formativas en la empresa')):continue
        return field
    return None


def potential_heading(line):
    """Conserva epígrafes adicionales en mayúscula sin confundirlos con texto."""
    text=line.strip()
    if not 8 <= len(text) <= 105 or len(text.split())<2 or re.match(r'^(?:tabla|figura|fuente|curso|ies|ce |ra )\b',ascii_key(text)):
        return False
    letters=[c for c in text if c.isalpha()]
    return bool(letters and len(letters)>=9 and sum(c.isupper() for c in letters)/len(letters)>.92
                and not text.endswith(('.',':',';')))


def pages_from_file(path, text=None):
    file=Path(path)
    if file.suffix.lower()=='.pdf':
        import fitz
        with fitz.open(file) as doc:
            return [p.get_text('text') for p in doc]
    if text is not None: return [text]
    if file.suffix.lower() == '.docx':
        # El texto del DOCX se extrae respetando el orden de párrafos y tablas.
        # Los títulos de Word se convierten a encabezados reconocibles, aunque
        # no estén escritos enteramente en mayúsculas. Los datos no se cambian.
        from docx import Document
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        document=Document(file)
        chunks=[]
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                value=block.text.strip()
                if not value:continue
                style=block.style.name if block.style is not None else ''
                is_heading=style.lower().startswith(('heading', 'título', 'titulo'))
                if is_heading:
                    value=value.upper()
                chunks.append(value)
            elif isinstance(block, Table):
                for row in block.rows:
                    cells=[cell.text.strip().replace('\n',' / ') for cell in row.cells]
                    if any(cells):chunks.append(' | '.join(cells))
        return ['\n'.join(chunks)]
    import logic
    return [logic.extract_program(file)]


def split_sections(pages):
    all_sections=[]
    current={'title':'Portada e introducción','field':None,'page_start':1,'page_end':1,'body':[]}
    promotion_open=False
    def finish():
        body='\n'.join(current['body']).strip()
        if body:
            all_sections.append({'title':current['title'], 'field':current['field'],
                   'page_start':current['page_start'], 'page_end':current['page_end'], 'body':body})
    for page_no,txt in enumerate(pages,1):
        lines=[x.strip() for x in txt.splitlines() if x.strip()]
        i=0
        while i<len(lines):
            line=lines[i]
            multi=' '.join(lines[i:i+2]) if i+1<len(lines) else line
            field=known_heading(line)
            consumed=1
            if field is None and len(line)<75 and known_heading(multi):
                field=known_heading(multi);consumed=2
            header=(field is not None or (potential_heading(line) and (i+1==len(lines) or not re.match(r'^\s*[a-z]\)',lines[i+1],re.I))))
            if header and len(all_sections)<MAX_SECTIONS-1:
                finish()
                name=multi if consumed==2 and field else line
                if field is not None:
                    promotion_open=(field=='promotion')
                elif promotion_open and ascii_key(name).startswith(('a ciclos','b ciclos')):
                    field='promotion'
                current={'title':name,'field':field,'page_start':page_no,'page_end':page_no,'body':[]}
                i+=consumed
                continue
            current['body'].append(line)
            current['page_end']=page_no
            i+=1
    finish()
    return all_sections[:MAX_SECTIONS]


def extract_hours(text):
    """Solo valores EXPRESOS del documento; nunca inferir horas oficiales."""
    key=ascii_key(text)
    # Acepta redactados de la forma «duración de 202 horas ... 6 horas semanales».
    pairs=[]
    patterns=[r'(?:duracion|carga horaria)(?:.{0,80}?)(\d{2,4})\s+horas(?:.{0,100}?)(\d{1,2})\s+horas\s+semanales',
              r'(\d{2,4})\s+horas(?:.{0,65}?)(\d{1,2})\s+horas\s+semanales']
    for pat in patterns:
        for m in re.finditer(pat,key,re.I):
            total,weekly=int(m.group(1)),int(m.group(2))
            if 30<=total<=2500 and 1<=weekly<=40:
                pairs.append((total,weekly))
    if not pairs:
        return {'total_hours':None,'weekly_hours':None,'source':'documento','confirmed_official':False}
    total,weekly=pairs[0]
    return {'total_hours':total,'weekly_hours':weekly,'source':'documento','confirmed_official':False,
            'warning':'Las horas constan en la programación importada; confirme su vigencia con la norma aplicable.'}


def unit_candidates(sections):
    """Reconoce filas de UT en tablas de temporalización, sin inventar duraciones."""
    excerpts='\n'.join(s['body'] for s in sections if s['field']=='learning_activities')
    if not excerpts:return []
    before=re.split(r'(?i)tabla\s*3\s*[.\-:]|trazabilidad\s+entre',excerpts,maxsplit=1)[0]
    lines=[v.strip() for v in before.splitlines() if v.strip()]
    units=[]
    i=0
    while i<len(lines) and len(units)<45:
        if not re.fullmatch(r'\d{1,2}',lines[i]):i+=1;continue
        code=int(lines[i]);
        if code<1 or code>40 or (units and code!=len(units)+1) or (not units and code!=1):i+=1;continue
        j=i+1;parts=[]
        while j<len(lines) and j<i+11 and lines[j] != 'X' and not re.fullmatch(r'[123](?:ª|º)',lines[j]):
            val=lines[j]
            if 'Fuente:' in val or re.search(r'(?i)^tabla\s+[0-9]',val):break
            parts.append(val);j+=1
        if not parts or j>=len(lines) or lines[j]!='X':i+=1;continue
        k=j+1
        if k<len(lines) and lines[k]=='X':k+=1
        if k>=len(lines) or not re.fullmatch(r'[123](?:ª|º)',lines[k]):i+=1;continue
        title=' '.join(parts)
        if len(title)>220 or len(title)<9:i+=1;continue
        units.append({'code':'UD'+str(code).zfill(2),'title':title,'term':int(lines[k][0]),
                      'hours':None,'criteria_codes':[],'needs_hours':True,'source':'tabla del documento'})
        i=k+1
    return units


def feoe_criteria_candidates(sections):
    """CE mencionados expresamente dentro del apartado FEOE (propuesta revisable)."""
    found=[];seen=set()
    ra_pattern=re.compile(r'(?i)^(?:[•o\-]\s*)?RA\s*(\d{1,2})(?:\s*[.:])?\s')
    ce_pattern=re.compile(r'(?i)^(?:[•o\-]\s*)?CE\s*([a-z])\s*[).]')
    for sec in sections:
        if sec['field']!='enterprise':continue
        current=None
        for line in sec['body'].splitlines():
            t=line.strip()
            ra=ra_pattern.match(t)
            if ra:current=ra.group(1)
            ce=ce_pattern.match(t)
            if ce and current:
                code=f'RA{current}.{ce.group(1).lower()}'
                if code not in seen:
                    seen.add(code)
                    found.append({'code':code,'page':sec['page_start'],'source':'apartado FEOE'})
    return found


def analyze_document(path, text=None):
    pages=pages_from_file(path,text=text)
    document_text='\n'.join(pages)
    if not document_text.strip():
        raise ValueError('La programación no tiene texto extraíble. Necesita OCR o un documento editable.')
    if len(document_text)>MAX_IMPORT_TEXT:
        raise ValueError('La programación tiene demasiado texto para la revisión. Divida el documento.')
    sections=split_sections(pages)
    grouped={field:[] for field in FIELD_NAMES}
    for section in sections:
        field=section['field']
        if field in grouped:
            grouped[field].append(section)
    fields={}
    overflows=[]
    for name,matched in grouped.items():
        blocks=[s['body'] for s in matched if s['body'].strip()]
        if not blocks:continue
        value='\n\n'.join(blocks)
        if len(value)>MAX_FIELD_TEXT:
            overflows.append(name)
        fields[name]=value[:MAX_FIELD_TEXT].rstrip()
    # Algunas programaciones distribuyen la información entre apartados hijos.
    # Reutilizamos solo fragmentos que figuran en el documento; no completamos con IA.
    if 'academic_context' not in fields:
        related=[(FIELD_NAMES[k],fields[k]) for k in (
            'center_characteristics','student_characteristics','environment_context') if fields.get(k)]
        if related:
            fields['academic_context']='\n\n'.join(title+'\n'+body for title,body in related)[:MAX_FIELD_TEXT]
    if 'competencies' not in fields and fields.get('qualifications'):
        fields['competencies']=fields['qualifications'][:MAX_FIELD_TEXT]
    if 'instruments' not in fields and fields.get('grading'):
        # No adoptar porcentajes como reglas: es el texto del documento que el docente revisa.
        fields['instruments']=fields['grading'][:MAX_FIELD_TEXT]
    # Identificadores que constan expresamente en portada (sin deducir identidades).
    cover='\n'.join(pages[:2])[:6000]
    teacher=re.search(r'(?im)^\s*profesor(?:\s*/\s*a)?\s*:\s*(?:\n\s*)?([^\n]{5,100})',cover)
    if teacher:
        candidate=teacher.group(1).strip()
        if not re.search(r'(?i)pendiente|\d{4}|^profesor',candidate):fields.setdefault('teacher',candidate)
    center=re.search(r'(?im)^\s*((?:IES|CIFP|CIPFP|CPIFP|CEPA|CEO|CEIP)\s+[^\n]{6,105})$',cover)
    if center:fields.setdefault('center',center.group(1).strip())
    stats={'sections_detected':len(sections),'sections_mapped':sum(1 for s in sections if s['field'] in FIELD_NAMES),
           'fields_identified':len(fields),'additional_sections':sum(1 for s in sections if s['field'] not in FIELD_NAMES),
           'pages':len(pages), 'text_characters':len(document_text)}
    return {'fields':fields,'field_labels':FIELD_NAMES,'sections':sections,'statistics':stats,
            'proposed_hours':extract_hours(document_text),'proposed_units':unit_candidates(sections),
            'proposed_feoe_criteria':feoe_criteria_candidates(sections),
            'warnings':(['Algunos apartados extensos se muestran recortados en los campos editables; el texto completo se conserva como transcripción de origen: '+', '.join(overflows)] if overflows else [])+
                ['La normativa y las horas extraídas son datos del documento, no verificaciones legales.',
                 'Los RA/CE se incorporan mediante una revisión curricular independiente y explícita.'],
            'source':'documento importado','model':'reglas locales, sin envío a IA',
            'approved':False}
