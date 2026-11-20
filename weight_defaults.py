"""Ponderaciones curriculares por defecto; conserva el origen de cada decisión.

Sin ponderación expresa, cada CE vale lo mismo en el módulo: por ello
RA_i = 100 * número_CE_i / total_CE, y CE_dentro_RA = 100 / número_CE_i.
Los pesos expresos o editados a mano se respetan. Las reglas curriculares
no infieren por sí solas una ponderación distinta para la formación en empresa.
"""
from __future__ import annotations


def migrate(db):
    db.execute('''CREATE TABLE IF NOT EXISTS weight_origins (
        kind TEXT NOT NULL CHECK(kind IN ('ra','ce')),
        record_id INTEGER NOT NULL,
        origin TEXT NOT NULL CHECK(origin IN ('default','programming','manual')),
        PRIMARY KEY(kind,record_id))''')


def mark(db, kind, record_id, origin):
    if kind not in {'ra','ce'} or origin not in {'default','programming','manual'}:
        raise ValueError('Origen de ponderación no reconocido')
    db.execute('''INSERT INTO weight_origins(kind,record_id,origin) VALUES(?,?,?)
                ON CONFLICT(kind,record_id) DO UPDATE SET origin=excluded.origin''',
                (kind, int(record_id), origin))


def origin(db,kind,record_id):
    row=db.execute('SELECT origin FROM weight_origins WHERE kind=? AND record_id=?',
                   (kind,record_id)).fetchone()
    return row['origin'] if row else None


def distribute_cents(amount, weights):
    """Reparte centésimas con restos mayores: el total cuadra exactamente."""
    if not weights or amount<0:
        return []
    total=sum(weights)
    if total<=0: return [0.0]*len(weights)
    raw=[amount*w/total for w in weights]
    out=[int(x) for x in raw]
    for ix in sorted(range(len(weights)), key=lambda i:(-(raw[i]-out[i]),i))[:amount-sum(out)]:
        out[ix]+=1
    return [x/100 for x in out]


def _allocate(db,kind,rows,total,weights):
    """Conserva pesos explícitos; rellena el resto entre los registros automáticos."""
    missing=[];specified=0.0
    for row,weight in zip(rows,weights):
        current=origin(db,kind,row['id'])
        if current=='default' or row['weight'] is None:
            if not current: mark(db,kind,row['id'],'default')
            if weight>0:
                missing.append((row,weight))
            else:
                db.execute(f"UPDATE {'outcomes' if kind=='ra' else 'criteria'} SET weight=NULL WHERE id=?",(row['id'],))
        else:
            specified+=float(row['weight'])
    if not missing:return
    if specified>total+0.000001 or sum(w for r,w in missing)<=0:
        # No fuerza un total incoherente: permanece sin pesos nuevos.
        for row,_ in missing:
            db.execute(f"UPDATE {'outcomes' if kind=='ra' else 'criteria'} SET weight=NULL WHERE id=?",(row['id'],))
        return
    residual=max(0,round((total-specified)*100))
    allocations=distribute_cents(residual,[w for _,w in missing])
    for (row,_),value in zip(missing,allocations):
        db.execute(f"UPDATE {'outcomes' if kind=='ra' else 'criteria'} SET weight=? WHERE id=?",(value,row['id']))


def recalculate(db,module_id):
    """Recalcula solo pesos automáticos para el módulo indicado."""
    migrate(db)
    ras=db.execute('SELECT id,weight FROM outcomes WHERE module_id=? ORDER BY id',(module_id,)).fetchall()
    if not ras:return
    counts=[]
    for ra in ras:
        ces=db.execute('SELECT id,weight FROM criteria WHERE outcome_id=? ORDER BY id',(ra['id'],)).fetchall()
        counts.append(len(ces))
        if ces:_allocate(db,'ce',ces,100,[1]*len(ces))
    # Un RA sin CE no tiene peso computable y debe seguir pendiente.
    _allocate(db,'ra',ras,100,counts)
