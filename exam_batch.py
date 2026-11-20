"""Banco de preguntas multcriterio optimizado y distribución sin reemplazo."""
from collections import OrderedDict
import logic

def build_exam_models(title, kind, total, slots, model_count=1, difficulty='medio', additional='', sources=None, progress=None):
    """Genera bancos completos en lotes multcriterio y modelos sin reemplazo.

    Reduce las llamadas secuenciales: agrupa CE diferentes cuando hay hueco.
    Conserva la triple reserva, tipo, CE, rúbricas y sin duplicados por modelo.
    """
    generate_exam=logic.generate_exam
    is_repeated_question=logic.is_repeated_question
    question_fingerprint=logic.question_fingerprint
    if not isinstance(model_count,int) or isinstance(model_count,bool) or not 1 <= model_count <= 6:
        raise ValueError('Elija entre 1 y 6 modelos distintos.')
    if difficulty not in ('bajo','medio','alto'):
        raise ValueError('Dificultad no válida.')
    if not slots:raise ValueError('No hay preguntas para generar.')
    buckets=OrderedDict()
    for slot in slots:
        buckets.setdefault((slot['criterion_id'],slot['kind']),[]).append(slot)
    multiplier=max(3,model_count)
    targets={key:len(items)*multiplier for key,items in buckets.items()}
    per_bucket={key:[] for key in buckets}
    accepted_fps=[];all_prompts=[];model_name=None;consecutive_failures=0
    total_questions=sum(targets.values())
    batches=0
    while sum(len(v) for v in per_bucket.values())<total_questions:
        # Problemas largos generan JSON voluminoso: lotes más pequeños.
        limit=(4 if any(key[1]=='problema' for key in buckets) else
               6 if any(key[1]=='desarrollo' for key in buckets) else 8)
        batch=[];batch_sources=[];scheduled={k:0 for k in buckets}
        while len(batch)<limit:
            added=False
            # Repartir por CE/tipo en rotación: no esperar una petición por cada CE.
            for key,templates in buckets.items():
                if len(batch)>=limit:break
                if len(per_bucket[key])+scheduled[key]>=targets[key]:continue
                template=templates[(len(per_bucket[key])+scheduled[key])%len(templates)]
                batch.append({**template,'number':len(batch)+1})
                batch_sources.append(sources.get(template['number'],[]) if sources else [])
                scheduled[key]+=1;added=True
            if not added:break
        if not batch:raise RuntimeError('No se ha podido formar un lote de preguntas.')
        src={i+1:chunks for i,chunks in enumerate(batch_sources)} if sources else None
        try:
            questions,model=generate_exam(title,kind,total,batch,additional,src,difficulty,all_prompts)
        except ValueError:
            consecutive_failures+=1
            if consecutive_failures>=4:raise
            continue
        model_name=model;batches+=1
        found=0
        for q in questions:
            key=(q['criterion_id'],q['kind'])
            if len(per_bucket[key])>=targets[key] or is_repeated_question(q['prompt'],accepted_fps):continue
            per_bucket[key].append(q)
            accepted_fps.append(question_fingerprint(q['prompt']))
            all_prompts.append(q['prompt'])
            found+=1
        consecutive_failures=0 if found else consecutive_failures+1
        if consecutive_failures>=4:
            raise ValueError('La IA repite preguntas y no es posible completar el banco sin duplicados. No se ha creado el examen.')
        if progress:
            progress(sum(len(v) for v in per_bucket.values()), total_questions, batches)
    bank=[q for qs in per_bucket.values() for q in qs]
    models=[]
    for n in range(model_count):
        cursor={key:0 for key in buckets}
        model_questions=[]
        for number,template in enumerate(slots,1):
            key=(template['criterion_id'],template['kind'])
            pos=n*len(buckets[key])+cursor[key]
            cursor[key]+=1
            question=per_bucket[key][pos]
            model_questions.append({**question,**template,'number':number})
        models.append(model_questions)
    assert len(bank)>=3*len(slots)
    assert len({question_fingerprint(q['prompt']) for q in bank})==len(bank)
    return models,bank,model_name

