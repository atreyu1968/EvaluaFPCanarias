"""Clasificación asistida de preguntas manuales en resultados y criterios de FP.

La IA propone asociaciones al catálogo validado, nunca inventa RA ni CE ni cierra notas.
"""
from __future__ import annotations
import json
import math
import ia


def catalogue(db, module_id):
    rows=db.execute("""SELECT c.id AS criterion_id, c.code AS criterion_code,
       c.description AS criterion_description, o.code AS ra_code,
       o.description AS ra_description FROM criteria c
       JOIN outcomes o ON o.id=c.outcome_id WHERE o.module_id=?
       ORDER BY o.id,c.id""",(module_id,)).fetchall()
    return [dict(r) for r in rows]


def validate_allocations(question, allowed):
    """Acepta asignación manual anterior o múltiples CE con porcentaje sobre la pregunta."""
    targets=question.get('criteria_allocations')
    if targets is None:
        if question.get('criterion_id') is None:
            raise ValueError('Falta asignar al menos un CE para cada pregunta. Use «Proponer RA/CE con IA».')
        targets=[{'criterion_id':question['criterion_id'],'weight_pct':100,'rationale':'Asignación manual'}]
    if not isinstance(targets,list) or not 1<=len(targets)<=4:
        raise ValueError('Cada pregunta necesita de uno a cuatro criterios confirmados.')
    selected=[];seen=set()
    for raw in targets:
        try:
            cid=int(raw['criterion_id']);weight=float(raw.get('weight_pct',0))
        except (KeyError,ValueError,TypeError) as ex:
            raise ValueError('Identificador o ponderación de criterio inválidos.') from ex
        if cid not in allowed:
            raise ValueError(f'El CE {cid} no pertenece al currículo confirmado del módulo.')
        if cid in seen or not math.isfinite(weight) or weight<=0 or weight>100:
            raise ValueError('CE repetido o porcentaje inválido.')
        seen.add(cid)
        reason=str(raw.get('rationale','Revisión docente')).strip()[:1500]
        try:conf=float(raw.get('confidence',1))
        except (ValueError,TypeError):conf=0
        if not math.isfinite(conf) or not 0<=conf<=1:conf=0
        selected.append({'criterion_id':cid,'weight_pct':weight,'confidence':conf,'rationale':reason})
    if abs(sum(x['weight_pct'] for x in selected)-100)>0.05:
        raise ValueError('Los porcentajes de CE de cada pregunta deben sumar exactamente 100 %.')
    return selected


def suggest(db,module_id,questions):
    if not isinstance(questions,list) or not 1<=len(questions)<=40:
        raise ValueError('Introduzca entre 1 y 40 preguntas del examen manual.')
    candidates=catalogue(db,module_id)
    if not candidates:
        raise ValueError('El módulo no tiene CE confirmados. Consulte primero la programación o la normativa oficial.')
    prompts=[]
    for i,item in enumerate(questions,1):
        if not isinstance(item,dict) or not 8<=len(str(item.get('prompt','')).strip())<=12000:
            raise ValueError(f'Pregunta {i}: escriba un enunciado válido antes de analizarla.')
        prompts.append({'number':i,'kind':str(item.get('kind','desarrollo')),
                        'prompt':str(item['prompt'])[:12000],
                        'points':item.get('points'),
                        'ideal_answer':str(item.get('ideal_answer',''))[:1700]})
    context={'criteria':candidates, 'questions':prompts}
    prompt=('Asocia cada pregunta de un EXAMEN MANUAL de Formación Profesional con los criterios de evaluación'
            ' realmente evaluados. Solo puedes devolver criterion_id numéricos del catálogo proporcionado.'
            ' Considera el enunciado, sus apartados, los resultados de aprendizaje y las descripciones literales'
            ' de los criterios. No asocies un CE por simple coincidencia de palabras si no evalúa esa competencia.'
            ' Puedes asignar de 1 a 4 CE por pregunta, repartiendo su puntuación (weight_pct) y sumando 100.'
            ' Si no está suficientemente justificada ninguna asignación, devuelve criteria=[] y status="review".'
            ' confidence es un número entre 0 y 1; incluye rationale específico basado en lo evaluado.'
            ' Prohibido modificar los enunciados, inventar CE, RA, pesos oficiales o puntuaciones totales.'
            ' Responde exclusivamente JSON {"assignments":[{"number":1,"criteria":'
            '[{"criterion_id":17,"weight_pct":100,"confidence":0.9,"rationale":"..."}],'
            '"status":"proposed"}],"warnings":[]}.'
            ' Una asignación poco clara debe quedar en revisión, no se debe forzar.'
            '\nCATÁLOGO Y PREGUNTAS:\n'+json.dumps(context,ensure_ascii=False))
    result,model=ia.chat('analysis',prompt)
    if not isinstance(result,dict) or not isinstance(result.get('assignments'),list):
        raise ValueError('El modelo no devolvió asignaciones por pregunta válidas.')
    allowed={x['criterion_id']:x for x in candidates}
    by_number={}
    warnings=[str(w)[:300] for w in result.get('warnings',[]) if isinstance(w,str)][:20]
    for obj in result['assignments']:
        if not isinstance(obj,dict):continue
        try:n=int(obj['number'])
        except (KeyError,TypeError,ValueError):continue
        if n in by_number or not 1<=n<=len(questions):continue
        links=[]
        for item in obj.get('criteria',[]) if isinstance(obj.get('criteria',[]),list) else []:
            if not isinstance(item,dict):continue
            try:
                cid=int(item['criterion_id'])
                w=float(item['weight_pct']);c=float(item.get('confidence',0))
            except (KeyError,TypeError,ValueError):continue
            if cid not in allowed or not math.isfinite(w) or not math.isfinite(c) or c<0.65:continue
            links.append({'criterion_id':cid,'weight_pct':w,'confidence':c,
                'rationale':str(item.get('rationale','')).strip()[:1000],
                'ra_code':allowed[cid]['ra_code'], 'criterion_code':allowed[cid]['criterion_code']})
        try:
            valid=validate_allocations({'criteria_allocations':links},allowed)
            for row in valid:
                row['ra_code']=allowed[row['criterion_id']]['ra_code']
                row['criterion_code']=allowed[row['criterion_id']]['criterion_code']
            status='review' if str(obj.get('status','')).lower()=='review' else 'proposed'
            if status=='review':valid=[]
        except ValueError:
            valid=[];status='review'
        by_number[n]={'number':n,'criteria':valid,'status':status}
    assignments=[]
    for n in range(1,len(questions)+1):
        a=by_number.get(n,{'number':n,'criteria':[],'status':'review'})
        if a['status']=='review':warnings.append(f'Pregunta {n}: falta una asignación de RA/CE suficientemente fundamentada. Revísela manualmente.')
        assignments.append(a)
    return {'assignments':assignments,'model':model,'warnings':list(dict.fromkeys(warnings)),
            'criteria_available':len(candidates), 'needs_review':sum(not a['criteria'] for a in assignments)}
