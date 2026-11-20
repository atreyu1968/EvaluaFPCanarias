"""Biblioteca de materiales didácticos locales y selección de pasajes verificables.

No se transfieren documentos a proveedores al importarlos. Los fragmentos seleccionados
son la única base documental enviada al generar preguntas con IA.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import re
from pathlib import Path

import database as dbm
import logic

CHUNK_CHARS = 1250
OVERLAP = 150
MAX_TEXT = 8_000_000
MAX_CHUNKS = 10000
STOPWORDS = frozenset('de la el los las en un una unos unas para por que con del al como son sea sus se lo o y a es no un su desde sobre según aplicar según resultado criterio evaluación profesional alumnado alumno realiza realizar identificar explicar describir diferenciar conoce conocimiento unidad empresa'.split())


def pages_from_original(path):
    """Lista (página real o bloque lógico, texto); no atribuir páginas ficticias a DOCX."""
    ext = path.suffix.lower()
    if ext == '.pdf':
        import fitz
        with fitz.open(path) as doc:
            if len(doc)>700:raise ValueError('El material supera el límite de 700 páginas por PDF.')
            if doc.is_encrypted:raise ValueError('El PDF está protegido y no permite extraer texto.')
            return [('página', n, p.get_text('text', sort=True)) for n,p in enumerate(doc,1)]
    if ext == '.docx':
        from docx import Document
        doc=Document(str(path))
        parts=[p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                text=' | '.join(c.text.strip() for c in row.cells)
                if text.strip():parts.append(text)
        # No conocemos el paginado de Word: bloques secuenciales.
        blocks=[];buf=''
        for part in parts:
            if len(buf)+len(part)>4000 and buf:
                blocks.append(buf);buf=''
            buf += part+'\n'
        if buf:blocks.append(buf)
        return [('bloque',i,t) for i,t in enumerate(blocks,1)]
    text=path.read_text(encoding='utf-8-sig',errors='replace')
    return [('bloque',i,t) for i,t in enumerate([text[n:n+5000] for n in range(0,len(text),5000)],1)]


def make_chunks(units):
    chunks=[]
    for loc_kind, n, raw in units:
        clean=re.sub(r'\s+',' ',raw).strip()
        if not clean:continue
        pos=0
        while pos<len(clean):
            part=clean[pos:pos+CHUNK_CHARS].strip()
            if len(part)>=40:
                chunks.append({'location_kind':loc_kind,'location_number':n,'text':part})
            if pos+CHUNK_CHARS>=len(clean):break
            pos+=CHUNK_CHARS-OVERLAP
            if len(chunks)>MAX_CHUNKS:raise ValueError('El documento supera el límite de fragmentos permitidos.')
    return chunks


def save_material(db, module_id, programming_id, filename, blob):
    from pathlib import Path
    ext=logic.check_signature(filename,blob,programming=True)
    programming=db.execute('SELECT id FROM programmings WHERE id=? AND module_id=?',(programming_id,module_id)).fetchone()
    if programming is None:raise ValueError('Seleccione una programación perteneciente al módulo.')
    digest=hashlib.sha256(blob).hexdigest()
    folder=dbm.STORAGE/'materiales'/str(module_id)/str(programming_id)
    folder.mkdir(parents=True,exist_ok=True)
    dest=folder/(digest[:20]+'_'+dbm.slug(Path(filename).stem)+ext)
    if dest.exists():
        if dest.read_bytes()!=blob:raise ValueError('Conflicto con nombre de material existente.')
        # No reutilizar un mismo archivo asociado dos veces.
        existing=db.execute('SELECT id FROM materials WHERE module_id=? AND programming_id=? AND sha256=?',
                            (module_id,programming_id,digest)).fetchone()
        if existing:raise ValueError(f'Este material ya está incorporado (registro {existing["id"]}).')
    else:dest.write_bytes(blob)
    try:
        units=pages_from_original(dest)
        full_size=sum(len(t) for _,_,t in units)
        if full_size>MAX_TEXT:raise ValueError('Material demasiado extenso; divídalo en documentos más pequeños.')
        chunks=make_chunks(units)
        if not chunks:
            raise ValueError('El documento no contiene texto extraíble. Si es un libro escaneado, aplique OCR antes de incorporarlo.')
        db.execute('''INSERT INTO materials(module_id,programming_id,filename,local_path,sha256,
                     mime,unit_count,chunk_count,uploaded_at,active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                   (module_id,programming_id,filename,str(dest),digest,
                    {'pdf':'application/pdf','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'txt':'text/plain','md':'text/markdown'}[ext[1:]],len(units),len(chunks),dbm.now()))
        material_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.executemany('''INSERT INTO material_passages(material_id,location_kind,location_number,body)
                 VALUES(?,?,?,?)''',[(material_id,x['location_kind'],x['location_number'],x['text']) for x in chunks])
        dbm.log(db,'material_uploaded','material',material_id,{'module_id':module_id,'programming_id':programming_id,
                     'filename':filename,'sha256':digest,'chunks':len(chunks)})
        return {'id':material_id,'filename':filename,'units':len(units),'passages':len(chunks),'sha256':digest}
    except Exception:
        if not db.execute('SELECT 1 FROM materials WHERE local_path=?',(str(dest),)).fetchone():dest.unlink(missing_ok=True)
        raise


def words(text):
    words=re.findall(r'[a-záéíóúñü0-9]{3,}',text.lower())
    return {w for w in words if w not in STOPWORDS}


def retrieve_for_slots(db,module_id,slots,programming_id=None):
    """Recuperación léxica local; obliga a vincular cada pregunta a pasajes concretos.

    El proveedor solo recibe los pasajes seleccionados y no el libro completo.
    """
    params=[module_id];where='m.module_id=? AND m.active=1'
    if programming_id is not None:
        where+=' AND m.programming_id=?';params.append(programming_id)
    mats=db.execute(f'SELECT m.* FROM materials m WHERE {where} ORDER BY id',params).fetchall()
    if not mats:return {},[]
    rows=db.execute(f'''SELECT p.id,p.material_id,p.location_kind,p.location_number,p.body,m.filename
        FROM material_passages p JOIN materials m ON m.id=p.material_id WHERE {where} ORDER BY p.id''',params).fetchall()
    if not rows:raise ValueError('No hay texto legible en los materiales activos.')
    indexed=[(p,words(p['body'])) for p in rows]
    selected={}
    for slot in slots:
        terms=words(slot['criterion_description']+' '+slot['criterion_code'])
        # Preferencia por pasajes con vocabulario del criterio, con dispersión entre páginas.
        ranks=[]
        for item,lex in indexed:
            matched=terms & lex
            score=len(matched)
            ranks.append((score,item))
        ranks.sort(key=lambda x:(-x[0],x[1]['material_id'],x[1]['location_number'],x[1]['id']))
        chosen=[];locations=set()
        for score,item in ranks:
            loc=(item['material_id'],item['location_number'])
            if loc in locations and len(chosen)<2:continue
            chosen.append(dict(item));locations.add(loc)
            if len(chosen)>=3:break
        selected[slot['number']]=chosen
    return selected,[dict(m) for m in mats]


def ensure_citation(question,passages):
    """Comprueba que el modelo señala un pasaje real y cita texto literal de ese pasaje."""
    src=question.get('source')
    if not isinstance(src,dict):raise ValueError('La IA omitió la referencia del material didáctico.')
    try: pid=int(src.get('passage_id'))
    except (TypeError,ValueError):raise ValueError('Referencia de material mal formada.')
    passage=next((x for x in passages if x['id']==pid),None)
    if passage is None:raise ValueError('La IA citó un pasaje no proporcionado.')
    evidence=re.sub(r'\s+',' ',str(src.get('evidence','')).strip())
    source_text=re.sub(r'\s+',' ',passage['body'])
    if len(evidence)<12 or evidence.casefold() not in source_text.casefold():
        raise ValueError('La referencia generada no contiene una cita literal verificable del documento.')
    return {'material_id':passage['material_id'],'filename':passage['filename'],
            'passage_id':pid,'location_kind':passage['location_kind'],
            'location_number':passage['location_number'],'evidence':evidence}
