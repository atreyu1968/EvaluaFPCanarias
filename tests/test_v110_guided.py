"""1.1: borrador, comprobación curricular y exportación sin modificar notas o pesos."""
from __future__ import annotations
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database as database
import program_builder


class GuidedPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init()

    def setUp(self):
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGM Gestión Administrativa','Modulo de prueba 1.1','1 A',database.now()))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]

    def add_ra_ce(self):
        with database.connect() as db:
            db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                       (self.mid,'RA1','Realiza operaciones documentales y comprueba los resultados',100))
            ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                       (ra,'RA1.a','Resuelve una actividad administrativa',100))
            return ra,db.execute('SELECT last_insert_rowid()').fetchone()[0]

    def draft(self):
        return {'source_type':'create','region':'Canarias','center':'IES de prueba',
                'normative_references':'Normativa pendiente de contraste en el centro',
                'assessment':'Evaluación continua por criterios de evaluación',
                'methodology':'Aprendizaje mediante supuestos prácticos',
                'recovery':'Actividades de recuperación de CE no superados',
                'enterprise':'Revisar los acuerdos sobre formación en empresa',
                'units':[{'code':'UD01','title':'Simulación de oficina','term':1,
                          'hours':24,'criteria_codes':['RA1.a']}]}

    def test_new_empty_module_diagnosis_is_unapproved(self):
        with database.connect() as db:
            info=program_builder.diagnose(db,self.mid)
        self.assertFalse(info['approved'])
        self.assertFalse(info['ready_for_assessment'])
        self.assertGreaterEqual(len(info['errors']),2)
        self.assertEqual(info['counts']['documents'],0)

    def test_saving_preserves_weights_and_evidence_and_is_repeatable(self):
        ra,ce=self.add_ra_ce()
        with database.connect() as db:
            db.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(self.mid,'A001','Alumno de ejemplo'))
            saved=program_builder.save(db,self.mid,self.draft())
            after=program_builder.load(db,self.mid)
            self.assertTrue(saved['saved'])
            self.assertTrue(saved['diagnosis']['ready_for_assessment'])
            self.assertFalse(saved['diagnosis']['approved'])
            self.assertEqual(after['draft']['units'][0]['title'],'Simulación de oficina')
            self.assertEqual(db.execute('SELECT weight FROM outcomes WHERE id=?',(ra,)).fetchone()[0],100)
            self.assertEqual(db.execute('SELECT weight FROM criteria WHERE id=?',(ce,)).fetchone()[0],100)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students WHERE module_id=?',(self.mid,)).fetchone()[0],1)
            newer=self.draft();newer['methodology']='Metodología actualizada'
            program_builder.save(db,self.mid,newer)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM programming_drafts WHERE module_id=?',(self.mid,)).fetchone()[0],1)

    def test_exports_are_real_and_preserve_spanish_text(self):
        self.add_ra_ce()
        with database.connect() as db:
            program_builder.save(db,self.mid,self.draft())
            md,mime,name=program_builder.export(db,self.mid,'md')
            self.assertIn('Simulación de oficina',md.decode())
            self.assertIn('BORRADOR',md.decode())
            self.assertIn('RA1.a',md.decode())
            docx,mime,name=program_builder.export(db,self.mid,'docx')
            self.assertIn('word/document.xml',zipfile.ZipFile(io.BytesIO(docx)).namelist())
            pdf,mime,name=program_builder.export(db,self.mid,'pdf')
            self.assertTrue(pdf.startswith(b'%PDF-'))
            self.assertGreater(len(pdf),1000)

    def test_duplicate_units_and_malformed_body_are_rejected(self):
        payload=self.draft()
        payload['units'].append(dict(payload['units'][0]))
        with self.assertRaisesRegex(ValueError,'repetido'):
            program_builder.normalise(payload)
        payload=self.draft();payload['units'][0]['hours']=float('nan')
        with self.assertRaisesRegex(ValueError,'horas'):
            program_builder.normalise(payload)
        with self.assertRaisesRegex(ValueError,'campos no reconocidos'):
            program_builder.normalise({'source_type':'create','teacher_approved':True})

    def test_uncovered_criteria_and_unknown_criterion_are_visible(self):
        self.add_ra_ce()
        payload=self.draft()
        payload['units'][0]['criteria_codes']=['RA1.z']
        with database.connect() as db:
            result=program_builder.save(db,self.mid,payload)
        warnings=' '.join(result['diagnosis']['warnings'])
        self.assertIn('desconocido',warnings)
        self.assertIn('no asociados',warnings)

    def test_no_export_can_be_named_official_or_approved(self):
        self.add_ra_ce()
        with database.connect() as db:
            program_builder.save(db,self.mid,self.draft())
            text=program_builder.export(db,self.mid,'md')[0].decode()
        self.assertIn('No es una programación aprobada',text)


if __name__ == '__main__':unittest.main()


class GuidedHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.app=app
        cls.server,cls.base=app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def api(self, endpoint, payload=None, token=True):
        import urllib.request
        headers={'Content-Type':'application/json'}
        if token:headers['X-App-Token']=self.app.TOKEN
        raw=json.dumps(payload).encode('utf-8') if payload is not None else None
        req=urllib.request.Request(self.base+endpoint,data=raw,headers=headers,
                                   method='POST' if payload is not None else 'GET')
        with urllib.request.urlopen(req,timeout=8) as resp:
            content=resp.read()
            if resp.headers.get('Content-Type','').startswith('application/json'):
                return json.loads(content)
            return content

    def test_http_save_diagnose_export_and_auth(self):
        import urllib.error
        m=self.api('api/modules',{'academic_year':'2026-2027','cycle':'CFGM',
             'name':'Ejemplo de asistente 1.1','group_name':'1A'})
        mid=m['id']
        summary=self.api(f'api/programming-builder/{mid}')
        self.assertFalse(summary['approved'])
        self.assertTrue(summary['errors'])
        with self.assertRaises(urllib.error.HTTPError) as exc:
            self.api(f'api/programming-builder/{mid}',token=False)
        self.assertEqual(exc.exception.code,403)
        self.api('api/programming-builder/save',{'module_id':mid,'draft':{
            'source_type':'evaluation','region':'Canarias','assessment':'Evaluación por criterios'
        }})
        doc=self.api(f'api/programming-builder/{mid}/export.docx')
        with zipfile.ZipFile(io.BytesIO(doc)) as content:self.assertIsNone(content.testzip())
        pdf=self.api(f'api/programming-builder/{mid}/export.pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))
        md=self.api(f'api/programming-builder/{mid}/export.md').decode()
        self.assertIn('Ejemplo de asistente',md)
