"""Integración: material ligado a programación y citas comprobadas sin IA real."""
import io
import json
import re
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import database as dbm
import materiales

class MaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server,cls.url=app.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def req(self,path,data=None,ctype='application/json'):
        if data is not None and not isinstance(data,bytes):data=json.dumps(data).encode()
        req=urllib.request.Request(self.url+path,data,
            {'X-App-Token':app.TOKEN,'Content-Type':ctype},method='POST' if data is not None else 'GET')
        with urllib.request.urlopen(req,timeout=6) as res:
            blob=res.read()
            return json.loads(blob) if 'application/json' in res.headers.get('Content-Type','') else blob

    def multipart(self,fields,files):
        boundary='materialboundary001'
        blocks=[]
        for k,v in fields.items():
            blocks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for fld,name,content in files:
            blocks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{fld}"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+content+b'\r\n')
        blocks.append(f'--{boundary}--\r\n'.encode())
        return b''.join(blocks),f'multipart/form-data; boundary={boundary}'

    def test_sources_are_mandatory_and_provenance_is_saved(self):
        mid=self.req('api/modules',{'academic_year':'2026-2027','cycle':'GM','name':'Biblioteca de prueba','group_name':'A'})['id']
        ra=self.req('api/outcomes',{'module_id':mid,'code':'RA3','description':'Operaciones de compras','weight':100})['id']
        ce=self.req('api/criteria',{'outcome_id':ra,'code':'RA3.b','description':'Registrar compras mercaderías con proveedores','weight':100})['id']
        programming=b'RA3: Operaciones de compras. RA3.b: Registrar compras mercaderias con proveedores. Ponderacion 100%.'
        payload,typ=self.multipart({'module_id':str(mid)},[('document','programacion.txt',programming)])
        pid=self.req('api/programmings/upload',payload,typ)['id']
        text=('En contabilidad, las compras de mercaderías se registran en la cuenta 600. '
              'La deuda con los proveedores se refleja en la cuenta 400. '
              'Los importes corresponden a una factura debidamente documentada. ')*3
        input_,ctype=self.multipart({'module_id':str(mid),'programming_id':str(pid)},
               [('documents','unidad_compras.txt',text.encode()),('documents','glosario.md',
                 b'Un proveedor aporta bienes y servicios necesarios para la actividad empresarial.')])
        received=self.req('api/materials/upload',input_,ctype)
        self.assertEqual(len(received['created']),2)
        material_id=received['created'][0]['id']
        self.assertEqual(self.req(f'api/materials/{material_id}/original'),text.encode())
        module=self.req(f'api/modules/{mid}')
        self.assertEqual(len(module['materials']),2)
        self.assertEqual(module['materials'][0]['programming_id'],pid)
        payload={'module_id':mid,'programming_id':pid,'criteria_ids':[ce],
                 'title':'Prueba fundamentada','kind':'desarrollo','total_points':10,'question_count':1}
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req('api/exams/generate',payload)
        self.assertEqual(ctx.exception.code,400)
        payload['authorize_external_transfer']=True
        with dbm.connect() as db:
            passages,docs=materiales.retrieve_for_slots(db,mid,[{'number':1,'criterion_code':'RA3.b',
                      'criterion_description':'Registrar compras mercaderías con proveedores'}],pid)
        self.assertEqual(len(docs),2)
        first=next(x for x in passages[1] if x['material_id']==material_id)
        source={'passage_id':first['id'],'evidence':'las compras de mercaderías se registran en la cuenta 600'}
        question={'number':1,'prompt':'¿Qué cuenta registra las compras de mercaderías?',
                   'options':[],'correct_option':'','ideal_answer':'La cuenta 600.',
                   'rubric':[{'criterion':'Identifica la cuenta de compras','weight_pct':100}],
                   'source':source}
        counter=[0]
        def emit_distinct(role,prompt,images=None):
            counter[0]+=1
            # El banco nuevo exige al menos triple de preguntas diferentes.
            import re
            slots=json.loads(prompt.split('PLAN DE PREGUNTAS: ',1)[1].split('\nRESTRICCIÓN OBLIGATORIA',1)[0])
            batch=[]
            for n,_ in enumerate(slots,1):
                q=dict(question)
                q['number']=n
                q['prompt']=f'¿Qué cuenta corresponde a la compra de mercaderías? ' + ((f'contexto{counter[0]}-{n}-')*30)
                batch.append(q)
            return {'questions':batch},'simulado'
        with patch.object(app.logic.ia,'chat',side_effect=emit_distinct):
            try:exam=self.req('api/exams/generate',payload)
            except urllib.error.HTTPError as exc:raise AssertionError(exc.read().decode()) from exc
        detail=self.req(f'api/exams/{exam["id"]}')
        self.assertEqual(detail['exam']['source_mode'],'materials')
        self.assertEqual(detail['questions'][0]['source_refs'][0]['material_id'],material_id)
        self.assertIn('compras de mercaderías',detail['questions'][0]['source_refs'][0]['evidence'])
        self.assertEqual(len(detail['materials']),2)
        question['source']['evidence']='La cuenta 9999 que no aparece nunca en el material'
        with patch.object(app.logic.ia,'chat',side_effect=emit_distinct):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.req('api/exams/generate',{**payload,'title':'Examen sin evidencia'})
        self.assertEqual(ctx.exception.code,400)
        # No se debe guardar el examen cuya cita es inventada.
        self.assertFalse(any(e['title']=='Examen sin evidencia' for e in self.req('api/exams')))
        self.req('api/materials/active',{'module_id':mid,'material_id':material_id,'active':False})
        self.assertEqual(self.req(f'api/modules/{mid}')['materials'][1]['active'],0)

    def test_image_only_pdf_does_not_fake_content(self):
        import fitz
        pdf=fitz.open();pdf.new_page()
        raw=pdf.tobytes();pdf.close()
        mid=self.req('api/modules',{'academic_year':'2026-2027','cycle':'GM','name':'PDF escaneado','group_name':''})['id']
        with dbm.connect() as db:
            db.execute('INSERT INTO programmings(module_id,filename,local_path,sha256,extracted_text,uploaded_at) VALUES(?,?,?,?,?,?)',
                (mid,'manual.txt','/tmp/manual.txt','test','texto',dbm.now()))
            pid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
        content,ct=self.multipart({'module_id':str(mid),'programming_id':str(pid)},[('documents','escaneado.pdf',raw)])
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.req('api/materials/upload',content,ct)
        self.assertEqual(ctx.exception.code,400)
        self.assertFalse(self.req(f'api/modules/{mid}')['materials'])

if __name__=='__main__':unittest.main()
